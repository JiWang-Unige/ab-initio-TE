#!/usr/bin/env python3
"""Qualify hg19-to-CHM13 sequence correspondence and select old-TN controls.

The matcher deliberately has no input for the newer CHM13 annotation or for
model probabilities.  It reads the old mapping outcome table, old hg19
RepeatMasker coordinates, the two reciprocal chain files, and source/target
FASTA records.  Control selection is completed before the later reporting
pass joins the already-computed CHM13 annotation-support table.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


VALID_STATES = ("TP", "FP", "FN", "TN")
VALID_STATE_SET = set(VALID_STATES)
QUALIFIED_STATUS = "UNIQUE_RECIPROCAL_SAME_LENGTH"
TE_CLASSES = {"SINE", "LINE", "LTR", "DNA", "RC", "RETROPOSON"}
DISTANCE_BINS = ("ZERO", "1_10", "11_50", "51_200", "GT_200", "NO_TE")
GC_TOLERANCE = 0.02


def resolve_path(root: Path, value: Union[str, Path]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _as_bool(value: object) -> str:
    return "True" if bool(value) else "False"


@dataclass(frozen=True)
class ChainBlock:
    chain_id: int
    t_name: str
    q_name: str
    q_size: int
    q_strand: str
    t_start: int
    t_end: int
    q_start: int
    q_end: int
    block_index: int
    size: int
    dt: int
    dq: int


@dataclass(frozen=True)
class Chain:
    chain_id: int
    t_name: str
    q_name: str
    q_size: int
    q_strand: str
    t_start: int
    t_end: int
    blocks: Tuple[ChainBlock, ...]
    block_starts: Tuple[int, ...]


@dataclass(frozen=True)
class PathInspection:
    chain_id: int
    q_strand: str
    block_count: int
    source_covered_bp: int
    source_gap_bp: int
    source_edge_uncovered_bp: int
    target_covered_bp: int
    target_gap_bp: int
    target_overlap_bp: int
    mapped_start: Optional[int]
    mapped_end: Optional[int]
    full_source_coverage: bool
    exact_target: bool
    strict_internal_bijection: bool


class IntervalUnion:
    """A sorted union of half-open old-TE intervals for one chromosome."""

    def __init__(self, intervals: Sequence[Tuple[int, int]]) -> None:
        self.intervals = self._merge(intervals)
        self.starts = [start for start, _ in self.intervals]
        self.boundaries = sorted(
            boundary for interval in self.intervals for boundary in interval
        )

    @staticmethod
    def _merge(intervals: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
        merged: List[Tuple[int, int]] = []
        for start, end in sorted(intervals):
            if start < 0 or end <= start:
                raise ValueError(f"invalid interval {start}-{end}")
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def overlap_bp(self, start: int, end: int) -> int:
        total = 0
        index = max(0, bisect.bisect_left(self.starts, start) - 1)
        while index < len(self.intervals):
            left, right = self.intervals[index]
            if left >= end:
                break
            total += max(0, min(end, right) - max(start, left))
            index += 1
        return total

    def distance_and_relation(self, start: int, end: int) -> Tuple[Optional[int], str]:
        if not self.boundaries:
            return None, "NO_OLD_TE"
        overlap = self.overlap_bp(start, end)
        if overlap > 0:
            return 0, "OVERLAP"
        candidates: List[int] = []
        for endpoint in (start, end):
            index = bisect.bisect_left(self.boundaries, endpoint)
            if index < len(self.boundaries):
                candidates.append(abs(self.boundaries[index] - endpoint))
            if index:
                candidates.append(abs(endpoint - self.boundaries[index - 1]))
        distance = min(candidates) if candidates else None
        if distance == 0:
            return 0, "ADJACENT"
        return distance, "ISOLATED"


def distance_bin(distance: Optional[int]) -> str:
    if distance is None:
        return "NO_TE"
    if distance == 0:
        return "ZERO"
    if distance <= 10:
        return "1_10"
    if distance <= 50:
        return "11_50"
    if distance <= 200:
        return "51_200"
    return "GT_200"


def parse_old_te_unions(
    path: Path, allowed_source: set[str]
) -> Tuple[Dict[str, IntervalUnion], Dict[str, int]]:
    intervals: Dict[str, List[Tuple[int, int]]] = {
        chrom: [] for chrom in sorted(allowed_source)
    }
    record_counts: Dict[str, int] = collections.Counter()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 12:
                continue
            chrom = fields[5]
            if chrom not in allowed_source:
                continue
            try:
                start, end = int(fields[6]), int(fields[7])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid old comparator coordinates") from exc
            if start < 0 or end <= start:
                raise ValueError(f"{path}:{line_no}: invalid old comparator interval")
            base_class = fields[11].strip().upper().split("/", 1)[0]
            if base_class in TE_CLASSES:
                intervals[chrom].append((start, end))
                record_counts[chrom] += 1
    unions = {chrom: IntervalUnion(values) for chrom, values in intervals.items()}
    return unions, dict(record_counts)


def parse_fasta(path: Path, wanted: set[str]) -> Dict[str, str]:
    """Load only the requested FASTA records."""
    opener = gzip.open if path.name.endswith(".gz") else open
    records: Dict[str, str] = {}
    current: Optional[str] = None
    pieces: List[str] = []
    with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[arg-type]
        for line in handle:
            if line.startswith(">"):
                if current in wanted:
                    records[current] = "".join(pieces).upper()
                current = line[1:].split()[0]
                pieces = []
            elif current in wanted:
                pieces.append(line.strip())
        if current in wanted:
            records[current] = "".join(pieces).upper()
    missing = wanted - set(records)
    if missing:
        raise ValueError(f"{path}: missing FASTA records {sorted(missing)}")
    return records


def parse_chains(path: Path) -> List[Chain]:
    chains: List[Chain] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            fields = line.split()
            if fields[0] != "chain" or len(fields) != 13:
                raise ValueError(f"{path}:{line_no}: invalid chain header")
            try:
                chain_id = int(fields[12])
                t_size = int(fields[3])
                t_start = int(fields[5])
                t_end = int(fields[6])
                q_size = int(fields[8])
                q_start = int(fields[10])
                q_end = int(fields[11])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid chain header numbers") from exc
            if fields[4] != "+":
                raise ValueError(f"{path}:{line_no}: unexpected target strand {fields[4]!r}")
            q_strand = fields[9]
            if q_strand not in {"+", "-"}:
                raise ValueError(f"{path}:{line_no}: unexpected query strand {q_strand!r}")
            blocks: List[ChainBlock] = []
            t_cursor = t_start
            q_cursor = q_start
            for block_no, block_line in enumerate(handle):
                if not block_line.strip():
                    break
                parts = block_line.split()
                if len(parts) not in {1, 3}:
                    raise ValueError(f"{path}: invalid chain block at header line {line_no}")
                try:
                    size = int(parts[0])
                    dt = int(parts[1]) if len(parts) == 3 else 0
                    dq = int(parts[2]) if len(parts) == 3 else 0
                except ValueError as exc:
                    raise ValueError(f"{path}: invalid chain block at header line {line_no}") from exc
                if size <= 0 or dt < 0 or dq < 0:
                    raise ValueError(f"{path}: invalid chain block values at header line {line_no}")
                q_oriented_start = q_cursor
                q_oriented_end = q_cursor + size
                if q_strand == "+":
                    q_forward_start, q_forward_end = q_oriented_start, q_oriented_end
                else:
                    q_forward_start = q_size - q_oriented_end
                    q_forward_end = q_size - q_oriented_start
                blocks.append(
                    ChainBlock(
                        chain_id=chain_id,
                        t_name=fields[2],
                        q_name=fields[7],
                        q_size=q_size,
                        q_strand=q_strand,
                        t_start=t_cursor,
                        t_end=t_cursor + size,
                        q_start=q_forward_start,
                        q_end=q_forward_end,
                        block_index=block_no,
                        size=size,
                        dt=dt,
                        dq=dq,
                    )
                )
                t_cursor += size
                q_cursor += size
                if len(parts) == 3:
                    t_cursor += dt
                    q_cursor += dq
                else:
                    break
            if not blocks:
                raise ValueError(f"{path}:{line_no}: chain has no blocks")
            if t_cursor > t_end or q_cursor > q_end:
                raise ValueError(f"{path}:{line_no}: chain block coordinates exceed header")
            if t_end > t_size or q_end > q_size:
                raise ValueError(f"{path}:{line_no}: chain header outside sequence size")
            chains.append(
                Chain(
                    chain_id=chain_id,
                    t_name=fields[2],
                    q_name=fields[7],
                    q_size=q_size,
                    q_strand=q_strand,
                    t_start=t_start,
                    t_end=t_end,
                    blocks=tuple(blocks),
                    block_starts=tuple(block.t_start for block in blocks),
                )
            )
    return chains


class ChainIndex:
    def __init__(self, chains: Iterable[Chain]) -> None:
        grouped: Dict[Tuple[str, str], List[Chain]] = collections.defaultdict(list)
        for chain in chains:
            grouped[(chain.t_name, chain.q_name)].append(chain)
        self.grouped = {
            key: sorted(values, key=lambda chain: (chain.t_start, chain.chain_id))
            for key, values in grouped.items()
        }
        self.starts = {
            key: [chain.t_start for chain in values]
            for key, values in self.grouped.items()
        }

    def candidates(self, t_name: str, q_name: str, start: int, end: int) -> List[Chain]:
        key = (t_name, q_name)
        values = self.grouped.get(key, [])
        starts = self.starts.get(key, [])
        upper = bisect.bisect_right(starts, start)
        return [
            chain
            for chain in values[:upper]
            if chain.t_end > start and chain.t_start < end
        ]


def inspect_chain_path(
    chain: Chain, start: int, end: int, expected_start: int, expected_end: int
) -> PathInspection:
    first = max(0, bisect.bisect_left(chain.block_starts, start) - 1)
    last = bisect.bisect_left(chain.block_starts, end)
    blocks = [
        block
        for block in chain.blocks[first:last]
        if block.t_end > start and block.t_start < end
    ]
    if not blocks:
        return PathInspection(
            chain.chain_id,
            chain.q_strand,
            0,
            0,
            0,
            end - start,
            0,
            0,
            0,
            None,
            None,
            False,
            False,
            False,
        )
    clips: List[Tuple[ChainBlock, int, int, int, int]] = []
    source_covered = 0
    target_covered = 0
    internal_source_gap = 0
    for block in blocks:
        clip_start = max(start, block.t_start)
        clip_end = min(end, block.t_end)
        if clip_start >= clip_end:
            continue
        offset_start = clip_start - block.t_start
        offset_end = clip_end - block.t_start
        if chain.q_strand == "+":
            q_start = block.q_start + offset_start
            q_end = block.q_start + offset_end
        else:
            q_start = block.q_end - offset_end
            q_end = block.q_end - offset_start
        clips.append((block, clip_start, clip_end, q_start, q_end))
        source_covered += clip_end - clip_start
        target_covered += q_end - q_start
    for previous, current in zip(clips, clips[1:]):
        internal_source_gap += max(0, current[1] - previous[2])
    source_edge_uncovered = max(0, clips[0][1] - start) + max(0, end - clips[-1][2])
    target_gap = 0
    target_overlap = 0
    for previous, current in zip(clips, clips[1:]):
        if chain.q_strand == "+":
            delta = current[3] - previous[4]
        else:
            delta = previous[3] - current[4]
        if delta >= 0:
            target_gap += delta
        else:
            target_overlap += -delta
    mapped_start = min(clip[3] for clip in clips)
    mapped_end = max(clip[4] for clip in clips)
    full_source = source_covered == end - start and source_edge_uncovered == 0 and internal_source_gap == 0
    exact_target = mapped_start == expected_start and mapped_end == expected_end
    strict = (
        full_source
        and exact_target
        and target_gap == 0
        and target_overlap == 0
        and target_covered == expected_end - expected_start
    )
    return PathInspection(
        chain_id=chain.chain_id,
        q_strand=chain.q_strand,
        block_count=len(clips),
        source_covered_bp=source_covered,
        source_gap_bp=internal_source_gap,
        source_edge_uncovered_bp=source_edge_uncovered,
        target_covered_bp=target_covered,
        target_gap_bp=target_gap,
        target_overlap_bp=target_overlap,
        mapped_start=mapped_start,
        mapped_end=mapped_end,
        full_source_coverage=full_source,
        exact_target=exact_target,
        strict_internal_bijection=strict,
    )


def find_paths(
    index: ChainIndex,
    t_name: str,
    q_name: str,
    start: int,
    end: int,
    expected_start: int,
    expected_end: int,
) -> List[PathInspection]:
    return [
        inspect_chain_path(chain, start, end, expected_start, expected_end)
        for chain in index.candidates(t_name, q_name, start, end)
    ]


def sequence_metrics(
    source_seq: str,
    target_seq: str,
    source_start: int,
    source_end: int,
    target_start: int,
    target_end: int,
    q_strand: str,
) -> Dict[str, object]:
    source = source_seq[source_start:source_end]
    target_raw = target_seq[target_start:target_end]
    target_oriented = target_raw if q_strand == "+" else reverse_complement(target_raw)
    mismatch = None
    compared = min(len(source), len(target_oriented))
    if len(source) == len(target_oriented):
        mismatch = sum(a != b for a, b in zip(source, target_oriented))
    source_gc = sum(base in "GC" for base in source)
    target_gc = sum(base in "GC" for base in target_raw)
    source_non_acgt = sum(base not in "ACGT" for base in source)
    target_non_acgt = sum(base not in "ACGT" for base in target_raw)
    result: Dict[str, object] = {
        "source_gc_count": source_gc,
        "source_gc_fraction": source_gc / float(len(source)) if source else None,
        "source_non_acgt_count": source_non_acgt,
        "target_gc_count": target_gc,
        "target_gc_fraction": target_gc / float(len(target_raw)) if target_raw else None,
        "target_non_acgt_count": target_non_acgt,
        "sequence_source_length": len(source),
        "sequence_target_length": len(target_raw),
        "sequence_length_delta": len(target_raw) - len(source),
        "alignment_compared_bp": compared,
        "mismatch_bp": mismatch,
        "mismatch_fraction": (mismatch / float(len(source))) if mismatch is not None and source else None,
    }
    return result


def source_sequence_covariates(sequence: str, start: int, end: int) -> Dict[str, object]:
    """Compute matching covariates without consulting the target sequence."""
    source = sequence[start:end]
    if not source:
        raise ValueError(f"empty source sequence slice {start}-{end}")
    gc_count = sum(base in "GC" for base in source)
    non_acgt_count = sum(base not in "ACGT" for base in source)
    return {
        "source_gc_count": gc_count,
        "source_gc_fraction": gc_count / float(len(source)),
        "source_non_acgt_count": non_acgt_count,
        "sequence_source_length": len(source),
    }


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


def parse_mapping_rows(path: Path) -> Tuple[List[dict], List[str]]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"mapping outcome has no header: {path}")
        required = {
            "row_id",
            "mapping_id",
            "source_chrom",
            "source_start0",
            "source_end",
            "source_length",
            "state",
            "mapping_status",
            "target_scope",
            "forward_chrom",
            "forward_start0",
            "forward_end",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"mapping outcome missing fields: {sorted(missing)}")
        for row in reader:
            if row.get("state") not in VALID_STATE_SET:
                raise ValueError(f"unexpected mapping state {row.get('state')!r}")
            rows.append(row)
        return rows, list(reader.fieldnames)


def empty_qualification() -> Dict[str, object]:
    fields = {
        "old_te_overlap_bp": "",
        "old_te_distance_bp": "",
        "old_te_relation": "",
        "old_te_distance_bin": "",
        "eligible_for_matching": False,
        "forward_chain_path_count": "",
        "forward_exact_path_count": "",
        "forward_full_path_count": "",
        "forward_strict_path_count": "",
        "forward_chain_id": "",
        "forward_chain_strand": "",
        "forward_block_count": "",
        "forward_source_gap_bp": "",
        "forward_source_edge_uncovered_bp": "",
        "forward_target_gap_bp": "",
        "forward_target_overlap_bp": "",
        "reverse_chain_path_count": "",
        "reverse_exact_path_count": "",
        "reverse_full_path_count": "",
        "reverse_strict_path_count": "",
        "reverse_chain_id": "",
        "reverse_chain_strand": "",
        "reverse_block_count": "",
        "reverse_source_gap_bp": "",
        "reverse_source_edge_uncovered_bp": "",
        "reverse_target_gap_bp": "",
        "reverse_target_overlap_bp": "",
        "chain_orientation_consistent": "",
        "chain_stratum": "NOT_MAPPING_QUALIFIED",
        "sequence_status": "NOT_MAPPING_QUALIFIED",
        "source_gc_count": "",
        "source_gc_fraction": "",
        "source_non_acgt_count": "",
        "target_gc_count": "",
        "target_gc_fraction": "",
        "target_non_acgt_count": "",
        "sequence_source_length": "",
        "sequence_target_length": "",
        "sequence_length_delta": "",
        "alignment_compared_bp": "",
        "mismatch_bp": "",
        "mismatch_fraction": "",
    }
    return fields


def summarize_paths(paths: Sequence[PathInspection]) -> Dict[str, object]:
    exact = [path for path in paths if path.exact_target]
    full = [path for path in exact if path.full_source_coverage]
    strict = [path for path in full if path.strict_internal_bijection]
    chosen = sorted(strict or full or exact or paths, key=lambda path: path.chain_id)
    return {
        "path_count": len(paths),
        "exact_path_count": len(exact),
        "full_path_count": len(full),
        "strict_path_count": len(strict),
        "chosen": chosen[0] if chosen else None,
        "paths": paths,
    }


def qualify_row(
    row: Mapping[str, str],
    allowed_source: set[str],
    allowed_target: set[str],
    old_unions: Mapping[str, IntervalUnion],
    forward_index: ChainIndex,
    reverse_index: ChainIndex,
    source_fasta: Mapping[str, str],
    target_fasta: Mapping[str, str],
) -> Dict[str, object]:
    result = empty_qualification()
    source_chrom = row["source_chrom"]
    start = int(row["source_start0"])
    end = int(row["source_end"])
    union = old_unions.get(source_chrom)
    if union is not None:
        overlap = union.overlap_bp(start, end)
        distance, relation = union.distance_and_relation(start, end)
        result["old_te_overlap_bp"] = overlap
        result["old_te_distance_bp"] = "" if distance is None else distance
        result["old_te_relation"] = relation
        result["old_te_distance_bin"] = distance_bin(distance)
    if source_chrom not in allowed_source or row["mapping_status"] != QUALIFIED_STATUS:
        return result
    target_chrom = row.get("forward_chrom", "")
    if target_chrom not in allowed_target:
        result["chain_stratum"] = "TARGET_OUT_OF_SCOPE"
        result["sequence_status"] = "TARGET_OUT_OF_SCOPE"
        return result
    target_start = int(row["forward_start0"])
    target_end = int(row["forward_end"])
    result["eligible_for_matching"] = True
    # These source-only fields are required even when chain geometry later
    # excludes the interval from strict sequence qualification.
    result.update(source_sequence_covariates(source_fasta[source_chrom], start, end))
    forward_paths = find_paths(
        forward_index,
        source_chrom,
        target_chrom,
        start,
        end,
        target_start,
        target_end,
    )
    reverse_paths = find_paths(
        reverse_index,
        target_chrom,
        source_chrom,
        target_start,
        target_end,
        start,
        end,
    )
    forward_summary = summarize_paths(forward_paths)
    reverse_summary = summarize_paths(reverse_paths)
    for prefix, summary in (("forward", forward_summary), ("reverse", reverse_summary)):
        result[f"{prefix}_chain_path_count"] = summary["path_count"]
        result[f"{prefix}_exact_path_count"] = summary["exact_path_count"]
        result[f"{prefix}_full_path_count"] = summary["full_path_count"]
        result[f"{prefix}_strict_path_count"] = summary["strict_path_count"]
        chosen = summary["chosen"]
        if chosen is not None:
            assert isinstance(chosen, PathInspection)
            result[f"{prefix}_chain_id"] = chosen.chain_id
            result[f"{prefix}_chain_strand"] = chosen.q_strand
            result[f"{prefix}_block_count"] = chosen.block_count
            result[f"{prefix}_source_gap_bp"] = chosen.source_gap_bp
            result[f"{prefix}_source_edge_uncovered_bp"] = chosen.source_edge_uncovered_bp
            result[f"{prefix}_target_gap_bp"] = chosen.target_gap_bp
            result[f"{prefix}_target_overlap_bp"] = chosen.target_overlap_bp
    chosen_forward = forward_summary["chosen"]
    chosen_reverse = reverse_summary["chosen"]
    strict_forward = [path for path in forward_paths if path.strict_internal_bijection]
    strict_reverse = [path for path in reverse_paths if path.strict_internal_bijection]
    orientation_pairs = [
        (forward, reverse)
        for forward in strict_forward
        for reverse in strict_reverse
        if forward.q_strand == reverse.q_strand
    ]
    orientation_consistent = bool(orientation_pairs)
    result["chain_orientation_consistent"] = orientation_consistent
    if not forward_paths:
        result["chain_stratum"] = "NO_FORWARD_CHAIN_PATH"
        result["sequence_status"] = "NO_FORWARD_CHAIN_PATH"
        return result
    if not forward_summary["exact_path_count"]:
        if any(path.source_gap_bp > 0 for path in forward_paths):
            result["chain_stratum"] = "INTERNAL_SOURCE_GAP"
        elif any(path.target_gap_bp > 0 or path.target_overlap_bp > 0 for path in forward_paths):
            result["chain_stratum"] = "INTERNAL_TARGET_INDEL"
        else:
            result["chain_stratum"] = "FORWARD_CHAIN_COORDINATE_MISMATCH"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    if not forward_summary["full_path_count"]:
        chosen_exact = next(path for path in forward_paths if path.exact_target)
        if chosen_exact.source_gap_bp > 0:
            result["chain_stratum"] = "INTERNAL_SOURCE_GAP"
        elif chosen_exact.target_gap_bp > 0 or chosen_exact.target_overlap_bp > 0:
            result["chain_stratum"] = "INTERNAL_TARGET_INDEL"
        else:
            result["chain_stratum"] = "EDGE_UNCOVERED"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    if not reverse_paths or not reverse_summary["exact_path_count"]:
        result["chain_stratum"] = "REVERSE_CHAIN_INCONSISTENT"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    if not reverse_summary["full_path_count"]:
        result["chain_stratum"] = "REVERSE_CHAIN_EDGE_UNCOVERED"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    if not strict_forward or not strict_reverse:
        chosen = chosen_forward or chosen_reverse
        if chosen is not None and (
            chosen.source_gap_bp > 0 or chosen.source_edge_uncovered_bp > 0
        ):
            result["chain_stratum"] = "INTERNAL_SOURCE_GAP"
        elif chosen is not None and (chosen.target_gap_bp > 0 or chosen.target_overlap_bp > 0):
            result["chain_stratum"] = "INTERNAL_TARGET_INDEL"
        else:
            result["chain_stratum"] = "CHAIN_NOT_INTERNALLY_BIJECTIVE"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    if not orientation_consistent:
        result["chain_stratum"] = "CHAIN_ORIENTATION_INCONSISTENT"
        result["sequence_status"] = "CHAIN_NOT_STRICT"
        return result
    chosen_pair = sorted(orientation_pairs, key=lambda pair: (pair[0].chain_id, pair[1].chain_id))[0]
    chosen_forward_strict, chosen_reverse_strict = chosen_pair
    result["forward_chain_id"] = chosen_forward_strict.chain_id
    result["forward_chain_strand"] = chosen_forward_strict.q_strand
    result["forward_block_count"] = chosen_forward_strict.block_count
    result["forward_source_gap_bp"] = chosen_forward_strict.source_gap_bp
    result["forward_source_edge_uncovered_bp"] = chosen_forward_strict.source_edge_uncovered_bp
    result["forward_target_gap_bp"] = chosen_forward_strict.target_gap_bp
    result["forward_target_overlap_bp"] = chosen_forward_strict.target_overlap_bp
    result["reverse_chain_id"] = chosen_reverse_strict.chain_id
    result["reverse_chain_strand"] = chosen_reverse_strict.q_strand
    result["reverse_block_count"] = chosen_reverse_strict.block_count
    result["reverse_source_gap_bp"] = chosen_reverse_strict.source_gap_bp
    result["reverse_source_edge_uncovered_bp"] = chosen_reverse_strict.source_edge_uncovered_bp
    result["reverse_target_gap_bp"] = chosen_reverse_strict.target_gap_bp
    result["reverse_target_overlap_bp"] = chosen_reverse_strict.target_overlap_bp
    result["chain_stratum"] = (
        "SINGLE_BLOCK"
        if chosen_forward_strict.block_count == 1 and chosen_reverse_strict.block_count == 1
        else "MULTIBLOCK_CONTIGUOUS"
    )
    sequence = sequence_metrics(
        source_fasta[source_chrom],
        target_fasta[target_chrom],
        start,
        end,
        target_start,
        target_end,
        chosen_forward_strict.q_strand,
    )
    result.update(sequence)
    result["sequence_status"] = (
        "SEQUENCE_EXACT" if sequence["mismatch_bp"] == 0 else "SEQUENCE_MISMATCH"
    )
    return result


def _match_candidate_key(case: Mapping[str, object], control: Mapping[str, object]) -> Tuple[float, int, int]:
    case_gc = float(case["source_gc_fraction"])
    control_gc = float(control["source_gc_fraction"])
    case_distance = int(case["old_te_distance_bp"] or 0)
    control_distance = int(control["old_te_distance_bp"] or 0)
    return (abs(case_gc - control_gc), abs(case_distance - control_distance), int(control["row_id"]))


def select_controls(
    qualified_rows: Sequence[dict],
) -> Tuple[List[dict], dict]:
    cases = sorted(
        [row for row in qualified_rows if row["state"] == "FP"],
        key=lambda row: int(row["row_id"]),
    )
    controls = [row for row in qualified_rows if row["state"] == "TN"]
    selected_counts: collections.Counter = collections.Counter()
    output: List[dict] = []
    for case in cases:
        candidates = [
            control
            for control in controls
            if control["source_chrom"] == case["source_chrom"]
            and int(control["source_length"]) == int(case["source_length"])
            and control["old_te_relation"] == case["old_te_relation"]
            and int(control["source_non_acgt_count"]) == int(case["source_non_acgt_count"])
            and control["old_te_distance_bin"] == case["old_te_distance_bin"]
            and abs(float(control["source_gc_fraction"]) - float(case["source_gc_fraction"]))
            <= GC_TOLERANCE + 1e-12
        ]
        base = {
            "fp_mapping_id": case["mapping_id"],
            "fp_row_id": case["row_id"],
            "fp_source_chrom": case["source_chrom"],
            "fp_source_start0": case["source_start0"],
            "fp_source_end": case["source_end"],
            "fp_source_length": case["source_length"],
            "fp_old_te_relation": case["old_te_relation"],
            "fp_old_te_distance_bp": case["old_te_distance_bp"],
            "fp_old_te_distance_bin": case["old_te_distance_bin"],
            "fp_source_gc_fraction": case["source_gc_fraction"],
            "fp_source_non_acgt_count": case["source_non_acgt_count"],
            "fp_chain_stratum": case["chain_stratum"],
            "fp_sequence_status": case["sequence_status"],
            "candidate_count": len(candidates),
            "control_mapping_id": "",
            "control_row_id": "",
            "control_source_chrom": "",
            "control_source_start0": "",
            "control_source_end": "",
            "control_source_length": "",
            "control_old_te_relation": "",
            "control_old_te_distance_bp": "",
            "control_old_te_distance_bin": "",
            "control_source_gc_fraction": "",
            "control_source_non_acgt_count": "",
            "control_chain_stratum": "",
            "control_sequence_status": "",
            "gc_abs_diff": "",
            "boundary_distance_abs_diff": "",
            "control_reused": False,
            "match_status": "UNMATCHED_FP",
        }
        if not candidates:
            output.append(base)
            continue
        control = min(candidates, key=lambda candidate: _match_candidate_key(case, candidate))
        control_id = str(control["mapping_id"])
        was_reused = selected_counts[control_id] > 0
        selected_counts[control_id] += 1
        base.update(
            {
                "control_mapping_id": control_id,
                "control_row_id": control["row_id"],
                "control_source_chrom": control["source_chrom"],
                "control_source_start0": control["source_start0"],
                "control_source_end": control["source_end"],
                "control_source_length": control["source_length"],
                "control_old_te_relation": control["old_te_relation"],
                "control_old_te_distance_bp": control["old_te_distance_bp"],
                "control_old_te_distance_bin": control["old_te_distance_bin"],
                "control_source_gc_fraction": control["source_gc_fraction"],
                "control_source_non_acgt_count": control["source_non_acgt_count"],
                "control_chain_stratum": control["chain_stratum"],
                "control_sequence_status": control["sequence_status"],
                "gc_abs_diff": abs(
                    float(case["source_gc_fraction"]) - float(control["source_gc_fraction"])
                ),
                "boundary_distance_abs_diff": abs(
                    int(case["old_te_distance_bp"] or 0) - int(control["old_te_distance_bp"] or 0)
                ),
                "control_reused": was_reused,
                "match_status": "MATCHED_TN",
            }
        )
        output.append(base)
    relation_summary: Dict[str, dict] = {}
    for relation in sorted({str(row["old_te_relation"]) for row in cases}):
        subset = [row for row in output if row["fp_old_te_relation"] == relation]
        relation_summary[relation] = {
            "fp_n": len(subset),
            "matched_n": sum(row["match_status"] == "MATCHED_TN" for row in subset),
            "unmatched_n": sum(row["match_status"] != "MATCHED_TN" for row in subset),
        }
    summary = {
        "case_fp_qualified_n": len(cases),
        "control_tn_qualified_n": len(controls),
        "matched_pairs_n": sum(row["match_status"] == "MATCHED_TN" for row in output),
        "unmatched_fp_n": sum(row["match_status"] != "MATCHED_TN" for row in output),
        "unique_controls_used_n": len(selected_counts),
        "controls_reused_n": sum(count > 1 for count in selected_counts.values()),
        "max_control_reuse": max(selected_counts.values(), default=0),
        "control_reuse_histogram": dict(collections.Counter(selected_counts.values())),
        "by_old_te_relation": relation_summary,
        "matching_rule": {
            "same_source_chromosome": True,
            "exact_source_length": True,
            "same_old_te_relation": True,
            "exact_source_non_acgt_count": True,
            "same_old_te_distance_bin": True,
            "gc_tolerance_fraction": GC_TOLERANCE,
            "selection_order": "absolute GC fraction, absolute old-TE-boundary distance, row_id",
            "control_reuse_allowed": True,
            "seed": 42,
        },
        "selection_excludes": [
            "CHM13 target annotation support",
            "model probability or margin",
            "target sequence identity",
        ],
    }
    return output, summary


def qualification_fieldnames() -> List[str]:
    return list(empty_qualification())


def write_qualification_table(path: Path, rows: Sequence[dict], original_fields: Sequence[str]) -> None:
    fields = list(original_fields) + [field for field in qualification_fieldnames() if field not in original_fields]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_match_table(path: Path, rows: Sequence[dict]) -> None:
    fields = list(rows[0]) if rows else ["match_status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> dict:
    root = args.root.resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    allowed_source = set(config["allowed_source_chromosomes"])
    allowed_target = set(config["allowed_target_chromosomes"])
    mapping_path = resolve_path(root, config["mapping_outcomes"])
    old_comparator = resolve_path(root, config["old_comparator"])
    source_fasta_path = resolve_path(root, config["source_fasta"])
    target_fasta_path = resolve_path(root, config["target_fasta"])
    forward_chain_path = resolve_path(root, config["forward_chain"])
    reverse_chain_path = resolve_path(root, config["reverse_chain"])
    for path in (
        mapping_path,
        old_comparator,
        source_fasta_path,
        target_fasta_path,
        forward_chain_path,
        reverse_chain_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)

    rows, original_fields = parse_mapping_rows(mapping_path)
    old_unions, old_record_counts = parse_old_te_unions(old_comparator, allowed_source)
    source_fasta = parse_fasta(source_fasta_path, allowed_source)
    target_fasta = parse_fasta(target_fasta_path, allowed_target)
    forward_index = ChainIndex(parse_chains(forward_chain_path))
    reverse_index = ChainIndex(parse_chains(reverse_chain_path))

    qualified_rows: List[dict] = []
    all_rows: List[dict] = []
    chain_strata: collections.Counter = collections.Counter()
    sequence_strata: collections.Counter = collections.Counter()
    for row in rows:
        result = dict(row)
        result.update(
            qualify_row(
                row,
                allowed_source,
                allowed_target,
                old_unions,
                forward_index,
                reverse_index,
                source_fasta,
                target_fasta,
            )
        )
        if result["eligible_for_matching"]:
            # Matching covariates must be available for every eligible row.
            if result["source_gc_fraction"] == "" or result["source_non_acgt_count"] == "":
                raise ValueError(f"missing source covariates for {row['mapping_id']}")
            qualified_rows.append(result)
        chain_strata[str(result["chain_stratum"])] += 1
        sequence_strata[str(result["sequence_status"])] += 1
        all_rows.append(result)
    if len(all_rows) != len(rows):
        raise AssertionError("qualification changed source denominator")
    matches, match_summary = select_controls(qualified_rows)
    source_state_counts = collections.Counter(row["state"] for row in all_rows)
    qualified_state_counts = collections.Counter(row["state"] for row in qualified_rows)
    write_qualification_table(output / "interval_qualification.tsv", all_rows, original_fields)
    write_match_table(output / "matched_controls.tsv", matches)
    summary = {
        "status": "MATCHED_BACKGROUND_AND_SEQUENCE_QUALIFICATION_COMPLETED",
        "protocol": config["protocol"],
        "seed": 42,
        "source_interval_count": len(all_rows),
        "source_state_counts": dict(source_state_counts),
        "qualified_mapping_count": len(qualified_rows),
        "qualified_count_by_state": dict(qualified_state_counts),
        "chain_strata": dict(chain_strata),
        "sequence_strata": dict(sequence_strata),
        "old_te_record_counts_by_chromosome": old_record_counts,
        "matching": match_summary,
        "source": {
            "mapping_outcomes": str(mapping_path),
            "old_comparator": str(old_comparator),
            "source_fasta": str(source_fasta_path),
            "target_fasta": str(target_fasta_path),
            "forward_chain": str(forward_chain_path),
            "reverse_chain": str(reverse_chain_path),
        },
        "allowed_source_chromosomes": config["allowed_source_chromosomes"],
        "allowed_target_chromosomes": config["allowed_target_chromosomes"],
        "forbidden_source_chromosomes": config["forbidden_source_chromosomes"],
        "forbidden_target_chromosomes": config["forbidden_target_chromosomes"],
        "target_annotation_support_read": False,
        "model_probability_used_for_matching": False,
        "same_base_f1_computed": False,
        "fp_rescue_claim": False,
        "outputs": {
            "interval_qualification": str(output / "interval_qualification.tsv"),
            "matched_controls": str(output / "matched_controls.tsv"),
            "summary": str(output / "summary.json"),
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "completion.json").write_text(
        json.dumps(
            {
                "status": summary["status"],
                "target_annotation_support_read": False,
                "model_probability_used_for_matching": False,
                "same_base_f1_computed": False,
                "fp_rescue_claim": False,
                "summary": str(output / "summary.json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
