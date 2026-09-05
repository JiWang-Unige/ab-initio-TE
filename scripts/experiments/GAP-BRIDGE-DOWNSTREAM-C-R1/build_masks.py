#!/usr/bin/env python3
"""Build the frozen chr13 downstream-C softmask intervention bundle.

The bundle contains one record per chr13 DEV superblock plus a fixed halo in
each of three FASTA files:

``M0``
    The original P3 canonical mask.
``MW``
    ``M0`` plus complete gaps that are known and entirely comparator-positive.
``MP``
    ``M0`` plus comparator-positive bases inside every DEV candidate gap.

The sequence letters are held constant across the three modes.  Lowercase is
the softmasked representation; only case changes between modes.  Candidate
labels are used solely to define the DEV-core additions, never to select a
gene or a halo.  This script reads only chr13 region/interval rows and does
not use the historical chr19-specific evaluator.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


SEQID = "chr13"
SUPERBLOCK_BP = 640 * 8192
MAX_DEV_CORES = 9
DEFAULT_HALO_BP = 100_000
MODES = ("M0", "MW", "MP")


@dataclass(frozen=True)
class Candidate:
    """Minimal frozen-manifest row needed for the two intervention masks."""

    candidate_id: str
    block_index: int
    gap_start: int
    gap_end: int
    gap_length: int
    comparator_known: bool
    positive_bp: int
    negative_bp: int
    unknown_bp: int


@dataclass(frozen=True)
class Core:
    block_index: int
    core_start: int
    core_end: int
    halo_start: int
    halo_end: int
    candidates: tuple[Candidate, ...]


class InputError(ValueError):
    """Raised when an input violates the frozen chr13 mask contract."""


def read_frozen_dev_cores(
    chromosome_length: int,
    stage0_json: Path,
) -> dict[int, tuple[int, int]]:
    """Read the existing Stage 0 DEV split, including cores with no candidates.

    The Stage 1 candidate manifest is not a partition manifest: a valid DEV
    core can have zero eligible candidates.  The already-produced Stage 0 JSON
    is therefore required as the source of truth for all nine cores.
    """

    try:
        payload = json.loads(stage0_json.read_text(encoding="utf-8"))
        rows = payload["chr13_split"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise InputError(f"stage0 JSON lacks chr13_split: {stage0_json}") from error

    if not isinstance(rows, list):
        raise InputError("Stage 0 chr13_split must be a list")
    dev_cores: dict[int, tuple[int, int]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("role") != "DEV":
            continue
        try:
            block_index = _parse_nonnegative_int(row["block_index"], "Stage 0 block_index")
            start = _parse_nonnegative_int(row["start"], "Stage 0 block start")
            end = _parse_nonnegative_int(row["end"], "Stage 0 block end")
        except (KeyError, InputError) as error:
            raise InputError("invalid DEV row in Stage 0 chr13_split") from error
        if start >= end or end > chromosome_length or end - start > SUPERBLOCK_BP:
            raise InputError(f"invalid DEV core interval in Stage 0 split: {block_index}")
        if block_index in dev_cores:
            raise InputError(f"duplicate DEV core in Stage 0 split: {block_index}")
        dev_cores[block_index] = (start, end)
    if len(dev_cores) != MAX_DEV_CORES:
        raise InputError(
            f"Stage 0 split must contain exactly {MAX_DEV_CORES} DEV cores; "
            f"found {len(dev_cores)}",
        )
    for previous, current in zip(sorted(dev_cores.values()), sorted(dev_cores.values())[1:]):
        if current[0] < previous[1]:
            raise InputError("Stage 0 DEV cores overlap")
    return dict(sorted(dev_cores.items()))


def open_text(path: Path) -> AbstractContextManager[TextIO]:
    """Open plain or gzip-compressed text without changing the coordinate API."""

    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge sorted/unsorted half-open intervals, including touching ones."""

    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def intersect_intervals(
    left: Iterable[tuple[int, int]], right: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return the merged intersection of two interval collections."""

    left_values = merge_intervals(left)
    right_values = merge_intervals(right)
    result: list[tuple[int, int]] = []
    right_index = 0
    for left_start, left_end in left_values:
        while right_index < len(right_values) and right_values[right_index][1] <= left_start:
            right_index += 1
        index = right_index
        while index < len(right_values) and right_values[index][0] < left_end:
            start = max(left_start, right_values[index][0])
            end = min(left_end, right_values[index][1])
            if start < end:
                result.append((start, end))
            index += 1
    return merge_intervals(result)


def interval_bp(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start for start, end in merge_intervals(intervals))


def _parse_nonnegative_int(value: object, field: str) -> int:
    try:
        result = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise InputError(f"invalid integer in {field}: {value!r}") from error
    if result < 0:
        raise InputError(f"negative integer in {field}: {result}")
    return result


def _parse_binary(value: object, field: str) -> bool:
    text = str(value).strip()
    if text not in {"0", "1"}:
        raise InputError(f"{field} must be 0 or 1, got {value!r}")
    return text == "1"


def read_region(path: Path) -> str:
    """Read the contiguous zero-aligned chr13 JSONL region asset."""

    sequence_parts: list[str] = []
    expected_start = 0
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
                row_chr = str(row["chr"])
                start = int(row["start"])
                end = int(row["end"])
                sequence = str(row["sequence"]).upper()
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise InputError(f"invalid region JSONL row {line_number}: {path}") from error
            if row_chr != SEQID:
                raise InputError(f"region asset is not {SEQID}: row {line_number} has {row_chr}")
            if start != expected_start or end <= start or end - start != len(sequence):
                raise InputError(f"non-contiguous {SEQID} region row {line_number}: {path}")
            sequence_parts.append(sequence)
            expected_start = end
    if not sequence_parts:
        raise InputError(f"empty region asset: {path}")
    return "".join(sequence_parts)


def _interval_columns(first_fields: list[str]) -> tuple[int, int, int] | None:
    lowered = {field.strip().lower(): index for index, field in enumerate(first_fields)}
    sequence_index = next(
        (lowered[name] for name in ("seqid", "chrom", "chromosome") if name in lowered),
        None,
    )
    if sequence_index is None or "start" not in lowered or "end" not in lowered:
        return None
    return sequence_index, lowered["start"], lowered["end"]


def _fields(raw: str) -> list[str]:
    fields = raw.rstrip("\r\n").split("\t")
    if len(fields) < 3:
        fields = raw.rstrip("\r\n").split()
    return fields


def read_intervals(path: Path, chromosome_length: int) -> list[tuple[int, int]]:
    """Read a BED-like half-open interval asset, retaining only chr13 rows."""

    intervals: list[tuple[int, int]] = []
    first_data: list[str] | None = None
    columns: tuple[int, int, int] | None = None
    with open_text(path) as handle:
        for raw in handle:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            fields = _fields(raw)
            if first_data is None:
                first_data = fields
                columns = _interval_columns(fields)
                if columns is not None:
                    continue
                columns = (0, 1, 2)
            assert columns is not None
            seq_index, start_index, end_index = columns
            if max(columns) >= len(fields):
                raise InputError(f"interval row has fewer than three columns: {path}")
            if fields[seq_index] != SEQID:
                continue
            start = _parse_nonnegative_int(fields[start_index], "interval start")
            end = _parse_nonnegative_int(fields[end_index], "interval end")
            if end <= start or end > chromosome_length:
                raise InputError(f"invalid {SEQID} interval {start}-{end} in {path}")
            intervals.append((start, end))
    return merge_intervals(intervals)


MANIFEST_FIELDS = {
    "candidate_id", "seqid", "role", "chr13_block_index", "gap_start", "gap_end",
    "gap_length", "comparator_known", "positive_bp", "negative_bp", "unknown_bp",
}


def read_manifest(
    path: Path,
    chromosome_length: int,
    dev_core_map: dict[int, tuple[int, int]] | None = None,
) -> list[Candidate]:
    """Read every chr13/DEV candidate, not a selected tail or other role."""

    candidates: list[Candidate] = []
    seen: set[str] = set()
    with open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not MANIFEST_FIELDS <= set(reader.fieldnames):
            missing = sorted(MANIFEST_FIELDS - set(reader.fieldnames or ()))
            raise InputError(f"candidate manifest lacks fields: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            if row.get("seqid") != SEQID or row.get("role") != "DEV":
                continue
            candidate_id = (row.get("candidate_id") or "").strip()
            if not candidate_id:
                raise InputError(f"empty chr13 DEV candidate_id at manifest row {row_number}")
            if candidate_id in seen:
                raise InputError(f"duplicate chr13 DEV candidate_id: {candidate_id}")
            seen.add(candidate_id)
            block_index = _parse_nonnegative_int(row["chr13_block_index"], "chr13_block_index")
            gap_start = _parse_nonnegative_int(row["gap_start"], "gap_start")
            gap_end = _parse_nonnegative_int(row["gap_end"], "gap_end")
            gap_length = _parse_nonnegative_int(row["gap_length"], "gap_length")
            if gap_end <= gap_start or gap_end - gap_start != gap_length:
                raise InputError(f"invalid gap geometry for {candidate_id}")
            if gap_end > chromosome_length:
                raise InputError(f"candidate gap exceeds {SEQID} region: {candidate_id}")
            if dev_core_map is None:
                core_start = block_index * SUPERBLOCK_BP
                core_end = min(core_start + SUPERBLOCK_BP, chromosome_length)
            else:
                try:
                    core_start, core_end = dev_core_map[block_index]
                except KeyError as error:
                    raise InputError(f"candidate block is not a frozen DEV core: {candidate_id}") from error
            if core_start >= chromosome_length or gap_start < core_start or gap_end > core_end:
                raise InputError(f"candidate gap is outside its DEV core: {candidate_id}")
            comparator_known = _parse_binary(row["comparator_known"], "comparator_known")
            positive_bp = _parse_nonnegative_int(row["positive_bp"], "positive_bp")
            negative_bp = _parse_nonnegative_int(row["negative_bp"], "negative_bp")
            unknown_bp = _parse_nonnegative_int(row["unknown_bp"], "unknown_bp")
            if positive_bp + negative_bp + unknown_bp != gap_length:
                raise InputError(f"label masses do not sum to gap length: {candidate_id}")
            if comparator_known != (unknown_bp == 0):
                raise InputError(f"comparator_known disagrees with unknown_bp: {candidate_id}")
            candidates.append(Candidate(
                candidate_id=candidate_id,
                block_index=block_index,
                gap_start=gap_start,
                gap_end=gap_end,
                gap_length=gap_length,
                comparator_known=comparator_known,
                positive_bp=positive_bp,
                negative_bp=negative_bp,
                unknown_bp=unknown_bp,
            ))
    if not candidates:
        raise InputError(f"manifest contains no {SEQID} DEV candidates: {path}")
    candidates.sort(key=lambda candidate: (candidate.block_index, candidate.gap_start, candidate.gap_end, candidate.candidate_id))
    core_count = len({candidate.block_index for candidate in candidates})
    if core_count > MAX_DEV_CORES:
        raise InputError(
            f"manifest has more than the frozen {MAX_DEV_CORES} DEV cores: "
            f"{core_count}",
        )
    for previous, current in zip(candidates, candidates[1:]):
        if previous.block_index == current.block_index and current.gap_start < previous.gap_end:
            raise InputError(
                f"overlapping DEV candidate gaps: {previous.candidate_id}, {current.candidate_id}",
            )
    return candidates


def build_cores(
    candidates: Iterable[Candidate],
    chromosome_length: int,
    halo_bp: int,
    dev_core_map: dict[int, tuple[int, int]],
) -> list[Core]:
    if halo_bp < 0:
        raise InputError(f"halo_bp must be nonnegative: {halo_bp}")
    by_block: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        by_block.setdefault(candidate.block_index, []).append(candidate)
    cores: list[Core] = []
    for block_index, (core_start, core_end) in sorted(dev_core_map.items()):
        cores.append(Core(
            block_index=block_index,
            core_start=core_start,
            core_end=core_end,
            halo_start=max(0, core_start - halo_bp),
            halo_end=min(chromosome_length, core_end + halo_bp),
            candidates=tuple(sorted(by_block.get(block_index, []), key=lambda c: (c.gap_start, c.gap_end, c.candidate_id))),
        ))
    return cores


def mode_masks(
    p3_intervals: list[tuple[int, int]],
    candidates: Iterable[Candidate],
    comparator_positive: list[tuple[int, int]],
) -> dict[str, list[tuple[int, int]]]:
    """Construct M0/MW/MP genome-coordinate mask interval sets."""

    candidate_values = list(candidates)
    mw_additions = [
        (candidate.gap_start, candidate.gap_end)
        for candidate in candidate_values
        if candidate.comparator_known and candidate.positive_bp == candidate.gap_length
    ]
    candidate_gaps = [(candidate.gap_start, candidate.gap_end) for candidate in candidate_values]
    mp_additions = intersect_intervals(comparator_positive, candidate_gaps)
    return {
        "M0": merge_intervals(p3_intervals),
        "MW": merge_intervals([*p3_intervals, *mw_additions]),
        "MP": merge_intervals([*p3_intervals, *mp_additions]),
    }


def mode_masks_for_core(
    mode: str,
    p3_intervals: list[tuple[int, int]],
    core: Core,
    comparator_positive: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Build one record's mask, keeping MW/MP additions inside that core.

    A DEV halo can overlap a neighboring DEV core because the frozen split can
    assign adjacent superblocks to DEV.  Additions therefore remain local to
    the record's own core; only the original P3 mask extends through its halo.
    """

    if mode == "M0":
        additions: list[tuple[int, int]] = []
    elif mode == "MW":
        additions = [
            (candidate.gap_start, candidate.gap_end)
            for candidate in core.candidates
            if candidate.comparator_known and candidate.positive_bp == candidate.gap_length
        ]
    elif mode == "MP":
        additions = intersect_intervals(
            comparator_positive,
            [(candidate.gap_start, candidate.gap_end) for candidate in core.candidates],
        )
    else:
        raise InputError(f"unknown mask mode: {mode}")
    return merge_intervals([*p3_intervals, *additions])


def masked_sequence(
    sequence: str,
    start: int,
    end: int,
    masks: Iterable[tuple[int, int]],
) -> str:
    """Render one halo as uppercase sequence with selected intervals lowercase."""

    pieces: list[str] = []
    cursor = start
    for mask_start, mask_end in masks:
        if mask_end <= start:
            continue
        if mask_start >= end:
            break
        clipped_start = max(start, mask_start)
        clipped_end = min(end, mask_end)
        if clipped_start > cursor:
            pieces.append(sequence[cursor:clipped_start].upper())
        if clipped_end > max(cursor, clipped_start):
            pieces.append(sequence[max(cursor, clipped_start):clipped_end].upper().lower())
        cursor = max(cursor, clipped_end)
        if cursor >= end:
            break
    if cursor < end:
        pieces.append(sequence[cursor:end].upper())
    return "".join(pieces)


def write_fasta(
    path: Path,
    sequence: str,
    cores: Iterable[Core],
    mode: str,
    p3_intervals: list[tuple[int, int]],
    comparator_positive: list[tuple[int, int]],
    line_width: int = 80,
) -> None:
    with path.open("w", encoding="ascii", newline="\n") as handle:
        for core in cores:
            header = (
                f"{SEQID}|dev_block={core.block_index}|"
                f"core={core.core_start}-{core.core_end}|"
                f"halo={core.halo_start}-{core.halo_end}"
            )
            masks = mode_masks_for_core(mode, p3_intervals, core, comparator_positive)
            rendered = masked_sequence(sequence, core.halo_start, core.halo_end, masks)
            handle.write(f">{header}\n")
            for offset in range(0, len(rendered), line_width):
                handle.write(rendered[offset:offset + line_width] + "\n")


def _mask_bp_in_halos(
    mode: str,
    p3_intervals: list[tuple[int, int]],
    cores: Iterable[Core],
    comparator_positive: list[tuple[int, int]],
) -> int:
    return sum(
        interval_bp(intersect_intervals(
            mode_masks_for_core(mode, p3_intervals, core, comparator_positive),
            [(core.halo_start, core.halo_end)],
        ))
        for core in cores
    )


def write_geometry(
    path: Path,
    cores: Iterable[Core],
    p3_intervals: list[tuple[int, int]],
    comparator_positive: list[tuple[int, int]],
) -> None:
    fields = (
        "block_index", "core_start", "core_end", "halo_start", "halo_end", "context_bp",
        "candidate_count", "known_candidate_count", "mw_complete_positive_count",
        "candidate_positive_bp", "candidate_negative_bp", "candidate_unknown_bp",
        "m0_mask_bp_in_halo", "mw_added_mask_bp_in_halo", "mp_added_mask_bp_in_halo",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for core in cores:
            m0_bp = interval_bp(intersect_intervals(
                mode_masks_for_core("M0", p3_intervals, core, comparator_positive),
                [(core.halo_start, core.halo_end)],
            ))
            mw_bp = interval_bp(intersect_intervals(
                mode_masks_for_core("MW", p3_intervals, core, comparator_positive),
                [(core.halo_start, core.halo_end)],
            ))
            mp_bp = interval_bp(intersect_intervals(
                mode_masks_for_core("MP", p3_intervals, core, comparator_positive),
                [(core.halo_start, core.halo_end)],
            ))
            writer.writerow({
                "block_index": core.block_index,
                "core_start": core.core_start,
                "core_end": core.core_end,
                "halo_start": core.halo_start,
                "halo_end": core.halo_end,
                "context_bp": core.halo_end - core.halo_start,
                "candidate_count": len(core.candidates),
                "known_candidate_count": sum(candidate.comparator_known for candidate in core.candidates),
                "mw_complete_positive_count": sum(
                    candidate.comparator_known and candidate.positive_bp == candidate.gap_length
                    for candidate in core.candidates
                ),
                "candidate_positive_bp": sum(candidate.positive_bp for candidate in core.candidates),
                "candidate_negative_bp": sum(candidate.negative_bp for candidate in core.candidates),
                "candidate_unknown_bp": sum(candidate.unknown_bp for candidate in core.candidates),
                "m0_mask_bp_in_halo": m0_bp,
                "mw_added_mask_bp_in_halo": mw_bp - m0_bp,
                "mp_added_mask_bp_in_halo": mp_bp - m0_bp,
            })


def validate_positive_projection(
    candidates: Iterable[Candidate], comparator_positive: list[tuple[int, int]],
) -> None:
    """Ensure the P interval asset agrees with every frozen manifest mass."""

    # Both inputs are already genomic-coordinate sorted; the positive intervals
    # are merged by read_intervals. Do not rescan/sort the chromosome per gap.
    index = 0
    for candidate in candidates:
        while index < len(comparator_positive) and comparator_positive[index][1] <= candidate.gap_start:
            index += 1
        current, observed = index, 0
        while current < len(comparator_positive) and comparator_positive[current][0] < candidate.gap_end:
            start, end = comparator_positive[current]
            observed += max(0, min(end, candidate.gap_end) - max(start, candidate.gap_start))
            current += 1
        if observed != candidate.positive_bp:
            raise InputError(
                f"comparator-positive asset disagrees with positive_bp for "
                f"{candidate.candidate_id}: manifest={candidate.positive_bp}, observed={observed}",
            )


def build(
    *,
    region: Path,
    p3_canonical: Path,
    candidate_manifest: Path,
    comparator_positive: Path,
    output_dir: Path,
    halo_bp: int = DEFAULT_HALO_BP,
    stage0_json: Path,
) -> dict[str, object]:
    """Validate inputs and write the complete three-mode downstream bundle."""

    sequence = read_region(region)
    chromosome_length = len(sequence)
    dev_core_map = read_frozen_dev_cores(chromosome_length, stage0_json)
    p3_intervals = read_intervals(p3_canonical, chromosome_length)
    candidates = read_manifest(candidate_manifest, chromosome_length, dev_core_map)
    positive_intervals = read_intervals(comparator_positive, chromosome_length)
    validate_positive_projection(candidates, positive_intervals)
    cores = build_cores(candidates, chromosome_length, halo_bp, dev_core_map)
    masks = mode_masks(p3_intervals, candidates, positive_intervals)

    if output_dir.exists():
        raise InputError(f"refusing to reuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    fasta_paths = {mode: output_dir / f"{mode}.fasta" for mode in MODES}
    for mode in MODES:
        write_fasta(fasta_paths[mode], sequence, cores, mode, p3_intervals, positive_intervals)
    geometry_path = output_dir / "geometry.tsv"
    write_geometry(geometry_path, cores, p3_intervals, positive_intervals)

    emitted_m0_bp = _mask_bp_in_halos("M0", p3_intervals, cores, positive_intervals)
    emitted_summary: dict[str, dict[str, object]] = {}
    for mode in MODES:
        emitted_mask_bp = _mask_bp_in_halos(mode, p3_intervals, cores, positive_intervals)
        emitted_summary[mode] = {
            "fasta": str(fasta_paths[mode]),
            "mask_interval_bp_in_halos": emitted_mask_bp,
            "added_mask_bp_in_halos": emitted_mask_bp - emitted_m0_bp,
            "mask_interval_count": len(masks[mode]),
        }

    complete_positive = [
        candidate for candidate in candidates
        if candidate.comparator_known and candidate.positive_bp == candidate.gap_length
    ]
    summary: dict[str, object] = {
        "schema": "gap_bridge_downstream_c_mask_bundle_v1",
        "status": "PASS",
        "seqid": SEQID,
        "region_start": 0,
        "chromosome_length": chromosome_length,
        "superblock_bp": SUPERBLOCK_BP,
        "max_dev_cores": MAX_DEV_CORES,
        "dev_core_count": len(cores),
        "dev_core_indices": [core.block_index for core in cores],
        "halo_bp": halo_bp,
        "candidate_count": len(candidates),
        "known_candidate_count": sum(candidate.comparator_known for candidate in candidates),
        "known_complete_positive_candidate_count": len(complete_positive),
        "mp_candidate_count": len(candidates),
        "candidate_label_bp": {
            "positive_bp": sum(candidate.positive_bp for candidate in candidates),
            "negative_bp": sum(candidate.negative_bp for candidate in candidates),
            "unknown_bp": sum(candidate.unknown_bp for candidate in candidates),
        },
        "comparator_positive_asset_bp": interval_bp(positive_intervals),
        "masks": emitted_summary,
        "geometry": str(geometry_path),
        "inputs": {
            "region": str(region),
            "p3_canonical": str(p3_canonical),
            "candidate_manifest": str(candidate_manifest),
            "comparator_positive": str(comparator_positive),
            "stage0_json": str(stage0_json),
        },
        "chr19_read": False,
        "label_selection": "DEV_core_only; halo remains M0; no gene annotation used",
    }
    summary_path = output_dir / "masksummary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, type=Path, help="chr13 region.jsonl[.gz]")
    parser.add_argument("--p3-canonical", required=True, type=Path, help="original P3 canonical BED/TSV")
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--comparator-positive", required=True, type=Path, help="comparator-positive BED/TSV")
    parser.add_argument("--stage0-json", required=True, type=Path, help="frozen Stage 0 JSON containing chr13_split")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--halo-bp", type=int, default=DEFAULT_HALO_BP)
    args = parser.parse_args()
    result = build(
        region=args.region,
        p3_canonical=args.p3_canonical,
        candidate_manifest=args.candidate_manifest,
        comparator_positive=args.comparator_positive,
        output_dir=args.output_dir,
        halo_bp=args.halo_bp,
        stage0_json=args.stage0_json,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
