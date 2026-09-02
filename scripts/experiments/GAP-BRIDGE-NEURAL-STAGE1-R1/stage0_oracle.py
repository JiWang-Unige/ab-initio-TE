#!/usr/bin/env python3
"""Evaluate the whole-gap oracle ceiling before neural gap-head training."""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable


PROTOCOL = "GAP_BRIDGE_NEURAL_STAGE1_R1"
CHROMOSOMES = ("chr3", "chr5", "chr13")
TRAIN_CHROMOSOMES = ("chr3", "chr5")
SUPERBLOCK_BP = 640 * 8192
FLANK_BP = 256
MAX_GAP_BP = 512
SHORT_BP = 80
BRIDGE = "COMPARATOR_BRIDGE_SUPPORTED"
ACGT = frozenset("ACGT")


@dataclass(frozen=True)
class BaseCandidate:
    candidate_id: str
    seqid: str
    left_run_start: int
    left_run_end: int
    gap_start: int
    gap_end: int
    right_run_start: int
    right_run_end: int

    @property
    def length(self) -> int:
        return self.gap_end - self.gap_start


@dataclass(frozen=True)
class Candidate:
    base: BaseCandidate
    relation: str
    positive_bp: int
    negative_bp: int
    unknown_bp: int

    @property
    def risk(self) -> Fraction:
        return Fraction(self.negative_bp, self.base.length)


@dataclass
class ChromData:
    seqid: str
    length: int
    eval_regions: list[tuple[int, int]]
    genome_callable_regions: list[tuple[int, int]]
    callable_regions: list[tuple[int, int]]
    positive: list[tuple[int, int]]
    unknown: list[tuple[int, int]]
    raw_mask: list[tuple[int, int]]
    candidates: list[Candidate]


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
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
    left_values = merge_intervals(left)
    right_values = merge_intervals(right)
    result: list[tuple[int, int]] = []
    right_index = 0
    for start, end in left_values:
        while right_index < len(right_values) and right_values[right_index][1] <= start:
            right_index += 1
        index = right_index
        while index < len(right_values) and right_values[index][0] < end:
            overlap_start = max(start, right_values[index][0])
            overlap_end = min(end, right_values[index][1])
            if overlap_start < overlap_end:
                result.append((overlap_start, overlap_end))
            index += 1
    return merge_intervals(result)


def subtract_intervals(
    source: Iterable[tuple[int, int]], blockers: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    sources = merge_intervals(source)
    cuts = merge_intervals(blockers)
    result: list[tuple[int, int]] = []
    cut_index = 0
    for start, end in sources:
        cursor = start
        while cut_index < len(cuts) and cuts[cut_index][1] <= cursor:
            cut_index += 1
        index = cut_index
        while index < len(cuts):
            cut_start, cut_end = cuts[index]
            if cut_start >= end:
                break
            if cut_start > cursor:
                result.append((cursor, min(cut_start, end)))
            cursor = max(cursor, cut_end)
            if cursor >= end:
                break
            index += 1
        cut_index = index
        if cursor < end:
            result.append((cursor, end))
    return result


def interval_bp(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)


def overlap_bp(left: Iterable[tuple[int, int]], right: Iterable[tuple[int, int]]) -> int:
    return interval_bp(intersect_intervals(left, right))


def query_overlap_bp(
    intervals: list[tuple[int, int]], starts: list[int], queries: Iterable[tuple[int, int]],
) -> int:
    total = 0
    for query_start, query_end in queries:
        index = max(0, bisect.bisect_right(starts, query_start) - 1)
        while index < len(intervals) and intervals[index][0] < query_end:
            start, end = intervals[index]
            total += max(0, min(end, query_end) - max(start, query_start))
            index += 1
    return total


def read_bed(path: Path, wanted: set[str]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with open_text(path) as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if fields[0].lower() in {"seqid", "chrom"}:
                continue
            if fields[0] not in wanted:
                continue
            start, end = int(fields[1]), int(fields[2])
            if start < 0 or end <= start:
                raise ValueError(f"invalid interval {fields[0]}:{start}-{end} in {path}")
            grouped[fields[0]].append((start, end))
    return {seqid: merge_intervals(grouped.get(seqid, [])) for seqid in wanted}


def chr13_split(length: int) -> tuple[dict[int, str], list[dict[str, object]]]:
    blocks = [
        (index, start, min(start + SUPERBLOCK_BP, length))
        for index, start in enumerate(range(0, length, SUPERBLOCK_BP))
    ]
    ranked = sorted(
        blocks,
        key=lambda item: hashlib.sha256(
            f"{PROTOCOL}|chr13|{item[1]}|{item[2]}".encode("utf-8"),
        ).hexdigest(),
    )
    exact = (0.4 * len(blocks), 0.3 * len(blocks), 0.3 * len(blocks))
    counts = [math.floor(value) for value in exact]
    remaining = len(blocks) - sum(counts)
    order = sorted(range(3), key=lambda index: (-(exact[index] - counts[index]), index))
    for index in order[:remaining]:
        counts[index] += 1
    roles = ("DEV", "CAL_FIT", "CAL_GATE")
    role_by_block: dict[int, str] = {}
    cursor = 0
    for role, count in zip(roles, counts):
        for block_index, _start, _end in ranked[cursor:cursor + count]:
            role_by_block[block_index] = role
        cursor += count
    manifest = []
    for block_index, start, end in blocks:
        key = f"{PROTOCOL}|chr13|{start}|{end}"
        manifest.append({
            "block_index": block_index,
            "start": start,
            "end": end,
            "role": role_by_block[block_index],
            "rank_key": hashlib.sha256(key.encode("utf-8")).hexdigest(),
        })
    return role_by_block, manifest


def read_region_sequence(path: Path, seqid: str) -> str:
    pieces: list[str] = []
    expected_start = 0
    with open_text(path) as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            start, end = int(row["start"]), int(row["end"])
            sequence = str(row["sequence"]).upper()
            if row["chr"] != seqid or start != expected_start or end - start != len(sequence):
                raise ValueError(f"non-contiguous {seqid} region asset")
            pieces.append(sequence)
            expected_start = end
    if not pieces:
        raise ValueError(f"empty region asset for {seqid}")
    return "".join(pieces)


def acgt_runs(sequence: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"[ACGT]+", sequence)]


def load_base_candidates(path: Path, seqid: str) -> list[BaseCandidate]:
    required = {
        "candidate_id", "seqid", "left_run_start", "left_run_end", "gap_start",
        "gap_end", "right_run_start", "right_run_end",
    }
    candidates: list[BaseCandidate] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError(f"candidate schema mismatch: {path}")
        for row in reader:
            if row["seqid"] != seqid:
                raise ValueError(f"candidate from {row['seqid']} found in {seqid}")
            candidate = BaseCandidate(
                row["candidate_id"], seqid,
                int(row["left_run_start"]), int(row["left_run_end"]),
                int(row["gap_start"]), int(row["gap_end"]),
                int(row["right_run_start"]), int(row["right_run_end"]),
            )
            if candidate.length < 1:
                raise ValueError(f"empty candidate gap: {candidate.candidate_id}")
            candidates.append(candidate)
    return candidates


def label_blind_assets(
    source_root: Path, seqid: str,
) -> tuple[int, list[tuple[int, int]], list[tuple[int, int]], dict[str, BaseCandidate], list[dict[str, object]], int]:
    chromosome_root = source_root / seqid
    bases = load_base_candidates(chromosome_root / "candidates.tsv", seqid)
    sequence = read_region_sequence(chromosome_root / "region.jsonl.gz", seqid)
    length = len(sequence)
    all_acgt = acgt_runs(sequence)
    split_manifest: list[dict[str, object]] = []
    if seqid == "chr13":
        role_by_block, split_manifest = chr13_split(length)
        eval_regions = [
            (int(row["start"]), int(row["end"]))
            for row in split_manifest if row["role"] == "DEV"
        ]
    else:
        role_by_block = {}
        eval_regions = [(0, length)]
    eligible: dict[str, BaseCandidate] = {}
    for candidate in bases:
        crop_start = candidate.gap_start - FLANK_BP
        crop_end = candidate.gap_end + FLANK_BP
        if candidate.length > MAX_GAP_BP or crop_start < 0 or crop_end > length:
            continue
        if seqid == "chr13":
            first_block = crop_start // SUPERBLOCK_BP
            last_block = (crop_end - 1) // SUPERBLOCK_BP
            if first_block != last_block or role_by_block[first_block] != "DEV":
                continue
        if set(sequence[crop_start:crop_end]) <= ACGT:
            eligible[candidate.candidate_id] = candidate
    del sequence
    return length, eval_regions, all_acgt, eligible, split_manifest, len(bases) - len(eligible)


def load_labels(path: Path, eligible: dict[str, BaseCandidate], seqid: str) -> list[Candidate]:
    required = {
        "candidate_id", "seqid", "gap_start", "gap_end", "comparator_relation",
        "gap_comparator_positive_bp", "gap_comparator_negative_bp",
        "gap_comparator_unknown_bp",
    }
    result: list[Candidate] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError(f"labeled schema mismatch: {path}")
        for row in reader:
            candidate_id = row["candidate_id"]
            base = eligible.get(candidate_id)
            if base is None:
                continue
            if row["seqid"] != seqid or int(row["gap_start"]) != base.gap_start or int(row["gap_end"]) != base.gap_end:
                raise ValueError(f"label geometry mismatch: {candidate_id}")
            positive = int(row["gap_comparator_positive_bp"])
            negative = int(row["gap_comparator_negative_bp"])
            unknown = int(row["gap_comparator_unknown_bp"])
            if positive + negative + unknown != base.length:
                raise ValueError(f"label bp do not sum to gap length: {candidate_id}")
            result.append(Candidate(base, row["comparator_relation"], positive, negative, unknown))
            seen.add(candidate_id)
    if seen != set(eligible):
        raise ValueError(f"missing comparator projection for {seqid} eligible candidates")
    return result


def mask_counts(
    mask: list[tuple[int, int]], positive: list[tuple[int, int]],
    callable_regions: list[tuple[int, int]],
) -> dict[str, int | float | None]:
    prediction = intersect_intervals(mask, callable_regions)
    truth = intersect_intervals(positive, callable_regions)
    callable_bp = interval_bp(callable_regions)
    predicted_bp = interval_bp(prediction)
    positive_bp = interval_bp(truth)
    tp = overlap_bp(prediction, truth)
    fp = predicted_bp - tp
    fn = positive_bp - tp
    tn = callable_bp - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / positive_bp if positive_bp else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "callable_bp": callable_bp, "positive_bp": positive_bp,
        "predicted_bp": predicted_bp, "true_positive_bp": tp,
        "false_positive_bp": fp, "false_negative_bp": fn, "true_negative_bp": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "mcc": (tp * tn - fp * fn) / denominator if denominator else None,
    }


def fragment_counts(mask: list[tuple[int, int]], truth: list[tuple[int, int]]) -> tuple[dict[str, int | float | None], list[tuple[int, int]]]:
    mask = merge_intervals(mask)
    truth = merge_intervals(truth)
    fragments = missed = split = left_missing = right_missing = terminal = terminal_bp = 0
    internal: list[tuple[int, int]] = []
    mask_index = 0
    for start, end in truth:
        while mask_index < len(mask) and mask[mask_index][1] <= start:
            mask_index += 1
        covered: list[tuple[int, int]] = []
        index = mask_index
        while index < len(mask) and mask[index][0] < end:
            covered.append((max(mask[index][0], start), min(mask[index][1], end)))
            index += 1
        fragments += len(covered)
        if not covered:
            missed += 1
            left_missing += 1
            right_missing += 1
            terminal += 1
            terminal_bp += end - start
            continue
        if len(covered) >= 2:
            split += 1
            internal.extend(
                (previous[1], current[0])
                for previous, current in zip(covered, covered[1:])
                if previous[1] < current[0]
            )
        left = covered[0][0] > start
        right = covered[-1][1] < end
        left_missing += int(left)
        right_missing += int(right)
        terminal += int(left or right)
        terminal_bp += (covered[0][0] - start if left else 0) + (end - covered[-1][1] if right else 0)
    truth_count = len(truth)
    truth_bp = interval_bp(truth)
    return {
        "truth_runs": truth_count, "truth_bp": truth_bp, "fragments": fragments,
        "fragments_per_truth": fragments / truth_count if truth_count else None,
        "missed_truth_runs": missed, "missed_rate": missed / truth_count if truth_count else None,
        "split_truth_runs": split, "split_rate": split / truth_count if truth_count else None,
        "left_terminal_omission_truth_runs": left_missing,
        "right_terminal_omission_truth_runs": right_missing,
        "terminal_omission_truth_runs": terminal,
        "terminal_omission_rate": terminal / truth_count if truth_count else None,
        "terminal_omitted_bp": terminal_bp,
        "terminal_omitted_bp_rate": terminal_bp / truth_bp if truth_bp else None,
        "internal_gap_count": len(internal), "internal_gap_bp": interval_bp(internal),
    }, internal


def aggregate_counts(rows: list[dict[str, int | float | None]]) -> dict[str, int | float | None]:
    keys = (
        "callable_bp", "positive_bp", "predicted_bp", "true_positive_bp",
        "false_positive_bp", "false_negative_bp", "true_negative_bp",
    )
    totals = {key: sum(int(row[key]) for row in rows) for key in keys}
    tp, fp = totals["true_positive_bp"], totals["false_positive_bp"]
    fn, tn = totals["false_negative_bp"], totals["true_negative_bp"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        **totals, "precision": precision, "recall": recall, "f1": f1,
        "mcc": (tp * tn - fp * fn) / denominator if denominator else None,
    }


def aggregate_fragments(rows: list[dict[str, int | float | None]]) -> dict[str, int | float | None]:
    sum_keys = (
        "truth_runs", "truth_bp", "fragments", "missed_truth_runs", "split_truth_runs",
        "left_terminal_omission_truth_runs", "right_terminal_omission_truth_runs",
        "terminal_omission_truth_runs", "terminal_omitted_bp", "internal_gap_count",
        "internal_gap_bp",
    )
    totals = {key: sum(int(row[key]) for row in rows) for key in sum_keys}
    truth_count, truth_bp = totals["truth_runs"], totals["truth_bp"]
    return {
        **totals,
        "fragments_per_truth": totals["fragments"] / truth_count if truth_count else None,
        "missed_rate": totals["missed_truth_runs"] / truth_count if truth_count else None,
        "split_rate": totals["split_truth_runs"] / truth_count if truth_count else None,
        "terminal_omission_rate": totals["terminal_omission_truth_runs"] / truth_count if truth_count else None,
        "terminal_omitted_bp_rate": totals["terminal_omitted_bp"] / truth_bp if truth_bp else None,
    }


def short_summary(mask: list[tuple[int, int]]) -> dict[str, int | float | None]:
    short = sum(end - start < SHORT_BP for start, end in mask)
    return {
        "predicted_runs": len(mask), "short_predicted_runs": short,
        "short_rate": short / len(mask) if mask else None,
    }


def evaluate_dataset(data: list[ChromData], selected_ids: set[str]) -> dict[str, object]:
    raw_whole = []
    refined_whole = []
    raw_fragments = []
    refined_fragments = []
    raw_short_runs = raw_runs = refined_short_runs = refined_runs = 0
    raw_internal_count = raw_internal_bp = recovered_internal_bp = 0
    raw_long_bp = recovered_long_bp = 0
    selected_candidates: list[Candidate] = []
    for chromosome in data:
        selected = [candidate for candidate in chromosome.candidates if candidate.base.candidate_id in selected_ids]
        selected_candidates.extend(selected)
        raw_mask = intersect_intervals(chromosome.raw_mask, chromosome.eval_regions)
        refined_mask = merge_intervals([
            *raw_mask,
            *((candidate.base.gap_start, candidate.base.gap_end) for candidate in selected),
        ])
        truth = intersect_intervals(chromosome.positive, chromosome.callable_regions)
        raw_whole.append(mask_counts(raw_mask, truth, chromosome.callable_regions))
        refined_whole.append(mask_counts(refined_mask, truth, chromosome.callable_regions))
        raw_fragment, raw_internal = fragment_counts(raw_mask, truth)
        refined_fragment, _ = fragment_counts(refined_mask, truth)
        raw_fragments.append(raw_fragment)
        refined_fragments.append(refined_fragment)
        raw_short = short_summary(raw_mask)
        refined_short = short_summary(refined_mask)
        raw_runs += int(raw_short["predicted_runs"])
        raw_short_runs += int(raw_short["short_predicted_runs"])
        refined_runs += int(refined_short["predicted_runs"])
        refined_short_runs += int(refined_short["short_predicted_runs"])
        added = subtract_intervals(refined_mask, raw_mask)
        raw_internal_count += len(raw_internal)
        raw_internal_bp += interval_bp(raw_internal)
        recovered_internal_bp += overlap_bp(added, raw_internal)
        long_internal = [(start, end) for start, end in raw_internal if end - start > 5]
        raw_long_bp += interval_bp(long_internal)
        recovered_long_bp += overlap_bp(added, long_internal)
    return {
        "selected_candidates": len(selected_candidates),
        "selected_gap_bp": sum(candidate.base.length for candidate in selected_candidates),
        "selected_positive_bp": sum(candidate.positive_bp for candidate in selected_candidates),
        "selected_negative_bp": sum(candidate.negative_bp for candidate in selected_candidates),
        "selected_unknown_bp": sum(candidate.unknown_bp for candidate in selected_candidates),
        "all_original_p3_positive_bases_retained": True,
        "whole_mask": {"raw": aggregate_counts(raw_whole), "refined": aggregate_counts(refined_whole)},
        "fragmentation": {
            "raw": aggregate_fragments(raw_fragments),
            "refined": aggregate_fragments(refined_fragments),
        },
        "short_predictions": {
            "raw": {
                "predicted_runs": raw_runs, "short_predicted_runs": raw_short_runs,
                "short_rate": raw_short_runs / raw_runs if raw_runs else None,
            },
            "refined": {
                "predicted_runs": refined_runs, "short_predicted_runs": refined_short_runs,
                "short_rate": refined_short_runs / refined_runs if refined_runs else None,
            },
        },
        "internal_gap_recovery": {
            "raw_internal_gap_count": raw_internal_count,
            "raw_internal_gap_bp": raw_internal_bp,
            "recovered_internal_gap_bp": recovered_internal_bp,
            "internal_gap_bp_recall": recovered_internal_bp / raw_internal_bp if raw_internal_bp else None,
            "raw_internal_gap_gt5_bp": raw_long_bp,
            "recovered_internal_gap_gt5_bp": recovered_long_bp,
            "internal_gap_gt5_bp_recall": recovered_long_bp / raw_long_bp if raw_long_bp else None,
        },
    }


class ShortUnion:
    def __init__(self, runs: list[tuple[int, int]]) -> None:
        self.parent = list(range(len(runs)))
        self.lengths = [end - start for start, end in runs]
        self.components = len(runs)
        self.short = sum(length < SHORT_BP for length in self.lengths)
        self.by_end = {end: index for index, (_start, end) in enumerate(runs)}
        self.by_start = {start: index for index, (start, _end) in enumerate(runs)}

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def add_gap(self, candidate: Candidate) -> None:
        left_index = self.by_end.get(candidate.base.gap_start)
        right_index = self.by_start.get(candidate.base.gap_end)
        if left_index is None or right_index is None:
            raise ValueError(f"candidate is not between raw P3 runs: {candidate.base.candidate_id}")
        left_root, right_root = self.find(left_index), self.find(right_index)
        if left_root == right_root:
            return
        self.short -= int(self.lengths[left_root] < SHORT_BP) + int(self.lengths[right_root] < SHORT_BP)
        self.parent[right_root] = left_root
        self.lengths[left_root] += candidate.base.length + self.lengths[right_root]
        self.short += int(self.lengths[left_root] < SHORT_BP)
        self.components -= 1


def relative_decrease(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return (before - after) / before


def non_gene_gate(
    raw_whole: dict[str, int | float | None], refined_whole: dict[str, int | float | None],
    raw_fragment: dict[str, int | float | None], refined_fragment: dict[str, int | float | None],
    raw_short_rate: float | None, refined_short_rate: float | None,
    selected_count: int, universe_count: int, selected_positive: int, selected_negative: int,
    positive_denominator: int, selected_long_positive: int, long_positive_denominator: int,
    callable_bp: int,
) -> dict[str, bool]:
    minimum_selected = max(1000, math.ceil(0.01 * universe_count))
    raw_precision, refined_precision = raw_whole["precision"], refined_whole["precision"]
    raw_f1, refined_f1 = raw_whole["f1"], refined_whole["f1"]
    raw_recall, refined_recall = raw_whole["recall"], refined_whole["recall"]
    split_decrease = relative_decrease(raw_fragment["split_rate"], refined_fragment["split_rate"])
    fragment_decrease = relative_decrease(
        raw_fragment["fragments_per_truth"], refined_fragment["fragments_per_truth"],
    )
    return {
        "selected_candidate_minimum": selected_count >= minimum_selected,
        "known_negative_bp_per_mb": selected_negative * 1_000_000 / callable_bp <= 10,
        "whole_mask_precision_drop": (
            raw_precision is not None and refined_precision is not None
            and refined_precision >= raw_precision - 0.001
        ),
        "whole_mask_f1_non_decrease": raw_f1 is not None and refined_f1 is not None and refined_f1 >= raw_f1,
        "whole_mask_recall_non_decrease": (
            raw_recall is not None and refined_recall is not None and refined_recall >= raw_recall
        ),
        "split_rate_relative_decrease": split_decrease is not None and split_decrease >= 0.10,
        "fragments_per_truth_relative_decrease": fragment_decrease is not None and fragment_decrease >= 0.10,
        "short_rate_non_increase": (
            raw_short_rate is not None and refined_short_rate is not None
            and refined_short_rate <= raw_short_rate
        ),
        "positive_gap_bp_recovery": (
            positive_denominator > 0 and selected_positive / positive_denominator >= 0.10
        ),
        "positive_gap_gt5_bp_recovery": (
            long_positive_denominator > 0
            and selected_long_positive / long_positive_denominator >= 0.05
        ),
    }


def parse_refgene(path: Path, wanted: set[str]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    with open_text(path) as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) == 16:
                name, chrom, strand = fields[1], fields[2], fields[3]
                tx_start, tx_end = int(fields[4]), int(fields[5])
                cds_start, cds_end = int(fields[6]), int(fields[7])
                exon_count, starts_text, ends_text, gene = int(fields[8]), fields[9], fields[10], fields[12]
            elif len(fields) == 15:
                name, chrom, strand = fields[0], fields[1], fields[2]
                tx_start, tx_end = int(fields[3]), int(fields[4])
                cds_start, cds_end = int(fields[5]), int(fields[6])
                exon_count, starts_text, ends_text, gene = int(fields[7]), fields[8], fields[9], fields[11]
            else:
                raise ValueError("refGene row must have 15 or 16 columns")
            if chrom not in wanted:
                continue
            starts = [int(value) for value in starts_text.rstrip(",").split(",") if value]
            ends = [int(value) for value in ends_text.rstrip(",").split(",") if value]
            if len(starts) != exon_count or len(ends) != exon_count:
                raise ValueError(f"refGene exon count mismatch for {name}")
            grouped[chrom].append({
                "name": name, "gene": gene or name, "strand": strand,
                "tx_start": tx_start, "tx_end": tx_end,
                "cds_start": cds_start, "cds_end": cds_end,
                "exons": list(zip(starts, ends)),
            })
    return grouped


def gene_safety(
    data: list[ChromData], selected_ids: set[str], transcripts: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    total_cds = total_coding_exon = total_exon = total_promoter = 0
    negative_cds = negative_coding_exon = negative_exon = negative_promoter = negative_splice = 0
    max_transcript_negative = 0
    for chromosome in data:
        selected_gaps = [
            (candidate.base.gap_start, candidate.base.gap_end)
            for candidate in chromosome.candidates
            if candidate.base.candidate_id in selected_ids
        ]
        selected_negative = subtract_intervals(
            selected_gaps, [*chromosome.positive, *chromosome.unknown],
        )
        selected_negative_starts = [start for start, _end in selected_negative]
        cds: list[tuple[int, int]] = []
        coding_exons: list[tuple[int, int]] = []
        exons: list[tuple[int, int]] = []
        promoters: list[tuple[int, int]] = []
        splice: list[tuple[int, int]] = []
        transcript_cds: list[list[tuple[int, int]]] = []
        for transcript in transcripts.get(chromosome.seqid, []):
            tx_cds: list[tuple[int, int]] = []
            exon_values = transcript["exons"]
            assert isinstance(exon_values, list)
            for exon_index, (start, end) in enumerate(exon_values):
                exons.append((start, end))
                coding_start = max(start, int(transcript["cds_start"]))
                coding_end = min(end, int(transcript["cds_end"]))
                if coding_start < coding_end:
                    cds.append((coding_start, coding_end))
                    coding_exons.append((start, end))
                    tx_cds.append((coding_start, coding_end))
                if exon_index < len(exon_values) - 1:
                    splice.append((max(0, end - 2), end + 2))
                    next_start = exon_values[exon_index + 1][0]
                    splice.append((max(0, next_start - 2), next_start + 2))
            tss = int(transcript["tx_start"]) if transcript["strand"] == "+" else int(transcript["tx_end"])
            promoters.append((max(0, tss - 200), tss + 200))
            transcript_cds.append(intersect_intervals(tx_cds, chromosome.eval_regions))
        cds_union = intersect_intervals(cds, chromosome.eval_regions)
        callable_cds = intersect_intervals(cds_union, chromosome.callable_regions)
        coding_exon_union = intersect_intervals(coding_exons, chromosome.eval_regions)
        exon_union = intersect_intervals(exons, chromosome.eval_regions)
        promoter_union = intersect_intervals(promoters, chromosome.eval_regions)
        splice_union = intersect_intervals(splice, chromosome.eval_regions)
        total_cds += interval_bp(callable_cds)
        total_coding_exon += interval_bp(coding_exon_union)
        total_exon += interval_bp(exon_union)
        total_promoter += interval_bp(promoter_union)
        negative_cds += overlap_bp(selected_negative, callable_cds)
        negative_coding_exon += overlap_bp(selected_negative, coding_exon_union)
        negative_exon += overlap_bp(selected_negative, exon_union)
        negative_promoter += overlap_bp(selected_negative, promoter_union)
        negative_splice += overlap_bp(selected_negative, splice_union)
        for values in transcript_cds:
            max_transcript_negative = max(
                max_transcript_negative,
                query_overlap_bp(selected_negative, selected_negative_starts, values),
            )
    gates = {
        "splice_pm2_worst_case_negative_bp_zero": negative_splice == 0,
        "callable_cds_negative_rate": total_cds > 0 and negative_cds / total_cds <= 1e-5,
        "max_transcript_cds_negative_bp": max_transcript_negative <= 20,
        "all_exon_negative_rate": total_exon > 0 and negative_exon / total_exon <= 2e-5,
        "promoter_negative_rate": total_promoter > 0 and negative_promoter / total_promoter <= 5e-5,
    }
    return {
        "callable_cds_bp": total_cds, "callable_cds_negative_bp": negative_cds,
        "callable_cds_negative_rate": negative_cds / total_cds if total_cds else None,
        "coding_exon_bp": total_coding_exon,
        "coding_exon_negative_bp": negative_coding_exon,
        "coding_exon_negative_rate": (
            negative_coding_exon / total_coding_exon if total_coding_exon else None
        ),
        "all_exon_bp": total_exon, "all_exon_negative_bp": negative_exon,
        "all_exon_negative_rate": negative_exon / total_exon if total_exon else None,
        "promoter_bp": total_promoter, "promoter_negative_bp": negative_promoter,
        "promoter_negative_rate": negative_promoter / total_promoter if total_promoter else None,
        "splice_pm2_negative_bp": negative_splice,
        "max_transcript_cds_negative_bp": max_transcript_negative,
        "gates": gates,
    }


def build_data(
    source_root: Path, positive_path: Path, unknown_path: Path,
) -> tuple[dict[str, ChromData], list[dict[str, object]], dict[str, int]]:
    label_blind: dict[str, tuple[int, list[tuple[int, int]], list[tuple[int, int]], dict[str, BaseCandidate]]] = {}
    split_manifest: list[dict[str, object]] = []
    exclusions: dict[str, int] = {}
    for seqid in CHROMOSOMES:
        length, eval_regions, all_acgt, eligible, manifest, excluded = label_blind_assets(source_root, seqid)
        label_blind[seqid] = (length, eval_regions, all_acgt, eligible)
        if manifest:
            split_manifest = manifest
        exclusions[seqid] = excluded
    positives = read_bed(positive_path, set(CHROMOSOMES))
    unknown_sources = read_bed(unknown_path, set(CHROMOSOMES))
    result: dict[str, ChromData] = {}
    for seqid in CHROMOSOMES:
        length, eval_regions, all_acgt, eligible = label_blind[seqid]
        positive = intersect_intervals(positives[seqid], eval_regions)
        unknown = intersect_intervals(subtract_intervals(unknown_sources[seqid], positives[seqid]), eval_regions)
        genome_callable_regions = intersect_intervals(all_acgt, eval_regions)
        callable_regions = subtract_intervals(genome_callable_regions, unknown)
        raw_mask = intersect_intervals(
            read_bed(source_root / seqid / "prediction.canonical.tsv", {seqid})[seqid], eval_regions,
        )
        candidates = load_labels(source_root / seqid / "labeled.tsv", eligible, seqid)
        result[seqid] = ChromData(
            seqid, length, eval_regions, genome_callable_regions, callable_regions,
            positive, unknown, raw_mask, candidates,
        )
    return result, split_manifest, exclusions


def selected_for_risk(data: list[ChromData], risk: Fraction) -> set[str]:
    return {
        candidate.base.candidate_id
        for chromosome in data for candidate in chromosome.candidates
        if candidate.unknown_bp == 0 and candidate.risk <= risk
    }


def length_stratum(length: int) -> str:
    if length == 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 5:
        return "3-5"
    if length <= 20:
        return "6-20"
    if length <= 100:
        return "21-100"
    return "101-512"


def candidate_strata(data: list[ChromData], selected_ids: set[str]) -> dict[str, dict[str, int | float | None]]:
    labels = ("1", "2", "3-5", "6-20", "21-100", "101-512", "L<=2", "L>5")
    summaries = {
        label: {
            "known_candidates": 0, "known_gap_bp": 0, "known_positive_bp": 0,
            "selected_candidates": 0, "selected_gap_bp": 0,
            "selected_positive_bp": 0, "selected_negative_bp": 0,
            "strict_bridge_selected": 0,
        }
        for label in labels
    }
    for chromosome in data:
        for candidate in chromosome.candidates:
            if candidate.unknown_bp:
                continue
            bucket_names = [length_stratum(candidate.base.length)]
            bucket_names.append("L<=2" if candidate.base.length <= 2 else "L>5" if candidate.base.length > 5 else "")
            for bucket_name in (name for name in bucket_names if name):
                summary = summaries[bucket_name]
                summary["known_candidates"] += 1
                summary["known_gap_bp"] += candidate.base.length
                summary["known_positive_bp"] += candidate.positive_bp
                if candidate.base.candidate_id in selected_ids:
                    summary["selected_candidates"] += 1
                    summary["selected_gap_bp"] += candidate.base.length
                    summary["selected_positive_bp"] += candidate.positive_bp
                    summary["selected_negative_bp"] += candidate.negative_bp
                    summary["strict_bridge_selected"] += int(candidate.relation == BRIDGE)
    for summary in summaries.values():
        positive = int(summary["known_positive_bp"])
        summary["positive_gap_bp_recovery"] = (
            int(summary["selected_positive_bp"]) / positive if positive else None
        )
        selected_bp = int(summary["selected_gap_bp"])
        summary["added_bp_precision"] = (
            int(summary["selected_positive_bp"]) / selected_bp if selected_bp else None
        )
    return summaries


def zero_risk_topology(data: list[ChromData]) -> dict[str, object]:
    strict_ids = {
        candidate.base.candidate_id
        for chromosome in data for candidate in chromosome.candidates
        if candidate.unknown_bp == 0 and candidate.negative_bp == 0 and candidate.relation == BRIDGE
    }
    non_bridge_ids = {
        candidate.base.candidate_id
        for chromosome in data for candidate in chromosome.candidates
        if candidate.unknown_bp == 0 and candidate.negative_bp == 0 and candidate.relation != BRIDGE
    }
    strict = evaluate_dataset(data, strict_ids)
    non_bridge = evaluate_dataset(data, non_bridge_ids)
    return {
        "strict_bridge": {
            "candidate_count": len(strict_ids),
            "gap_bp": strict["selected_gap_bp"],
            "fragmentation": strict["fragmentation"],
            "internal_gap_recovery": strict["internal_gap_recovery"],
        },
        "all_positive_non_bridge": {
            "candidate_count": len(non_bridge_ids),
            "gap_bp": non_bridge["selected_gap_bp"],
            "fragmentation": non_bridge["fragmentation"],
            "internal_gap_recovery": non_bridge["internal_gap_recovery"],
            "interpretation": "material-safe under the comparator; not evidence of same-instance repair",
        },
    }


def selection_diagnostics(data: list[ChromData], selected_ids: set[str]) -> dict[str, int]:
    selected: list[Candidate] = []
    distinct_run_fusions = 0
    for chromosome in data:
        positive_starts = [start for start, _ in chromosome.positive]
        for candidate in chromosome.candidates:
            if candidate.base.candidate_id not in selected_ids:
                continue
            selected.append(candidate)
            left_index = bisect.bisect_right(positive_starts, candidate.base.gap_start - 1) - 1
            right_index = bisect.bisect_right(positive_starts, candidate.base.gap_end) - 1
            left_inside = (
                left_index >= 0
                and candidate.base.gap_start - 1 < chromosome.positive[left_index][1]
            )
            right_inside = (
                right_index >= 0
                and candidate.base.gap_end < chromosome.positive[right_index][1]
            )
            distinct_run_fusions += int(
                left_inside and right_inside and left_index != right_index
            )
    return {
        "selected_candidates": len(selected),
        "selected_gap_bp": sum(candidate.base.length for candidate in selected),
        "selected_negative_containing_candidates": sum(candidate.negative_bp > 0 for candidate in selected),
        "selected_negative_bp": sum(candidate.negative_bp for candidate in selected),
        "selected_strict_bridge_candidates": sum(candidate.relation == BRIDGE for candidate in selected),
        "selected_all_positive_non_bridge_candidates": sum(
            candidate.negative_bp == 0 and candidate.relation != BRIDGE for candidate in selected
        ),
        "selected_comparator_separation_supported_candidates": sum(
            candidate.relation == "COMPARATOR_SEPARATION_SUPPORTED" for candidate in selected
        ),
        "selected_distinct_comparator_run_fusions": distinct_run_fusions,
    }


def candidate_label_census(data: list[ChromData]) -> dict[str, int]:
    candidates = [candidate for chromosome in data for candidate in chromosome.candidates]
    unknown = [candidate for candidate in candidates if candidate.unknown_bp > 0]
    return {
        "model_eligible_candidates": len(candidates),
        "model_eligible_gap_bp": sum(candidate.base.length for candidate in candidates),
        "comparator_known_candidates": len(candidates) - len(unknown),
        "comparator_known_gap_bp": sum(
            candidate.base.length for candidate in candidates if candidate.unknown_bp == 0
        ),
        "comparator_unknown_candidates": len(unknown),
        "comparator_unknown_candidate_gap_bp": sum(candidate.base.length for candidate in unknown),
        "effective_comparator_unknown_bp": sum(candidate.unknown_bp for candidate in unknown),
    }


def write_selected(path: Path, datasets: dict[str, tuple[str, list[ChromData], set[str]]]) -> None:
    fields = (
        "dataset", "candidate_id", "seqid", "gap_start", "gap_end", "gap_length",
        "risk", "selected", "comparator_relation", "positive_bp", "negative_bp", "unknown_bp",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for dataset, data, selected_ids in datasets.values():
            for chromosome in data:
                for candidate in chromosome.candidates:
                    if candidate.unknown_bp:
                        continue
                    writer.writerow({
                        "dataset": dataset, "candidate_id": candidate.base.candidate_id,
                        "seqid": candidate.base.seqid, "gap_start": candidate.base.gap_start,
                        "gap_end": candidate.base.gap_end, "gap_length": candidate.base.length,
                        "risk": float(candidate.risk),
                        "selected": int(candidate.base.candidate_id in selected_ids),
                        "comparator_relation": candidate.relation,
                        "positive_bp": candidate.positive_bp,
                        "negative_bp": candidate.negative_bp,
                        "unknown_bp": candidate.unknown_bp,
                    })


def run_oracle(
    source_root: Path, positive_path: Path, unknown_path: Path, refgene_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    data_by_chrom, split_manifest, exclusions = build_data(source_root, positive_path, unknown_path)
    train = [data_by_chrom[seqid] for seqid in TRAIN_CHROMOSOMES]
    dev = [data_by_chrom["chr13"]]
    transcripts = parse_refgene(refgene_path, set(CHROMOSOMES))
    train_known = [
        candidate for chromosome in train for candidate in chromosome.candidates
        if candidate.unknown_bp == 0
    ]
    risk_groups: dict[Fraction, list[Candidate]] = defaultdict(list)
    for candidate in train_known:
        risk_groups[candidate.risk].append(candidate)
    zero_ids = {candidate.base.candidate_id for candidate in train_known if candidate.negative_bp == 0}
    zero_evaluation = evaluate_dataset(train, zero_ids)
    raw_whole = zero_evaluation["whole_mask"]["raw"]
    raw_fragment = zero_evaluation["fragmentation"]["raw"]
    refined_fragment_zero = zero_evaluation["fragmentation"]["refined"]
    unions = {
        chromosome.seqid: ShortUnion(intersect_intervals(chromosome.raw_mask, chromosome.eval_regions))
        for chromosome in train
    }
    universe_count = len(train_known)
    universe_gap_bp = sum(candidate.base.length for candidate in train_known)
    positive_denominator = sum(candidate.positive_bp for candidate in train_known)
    long_positive_denominator = sum(
        candidate.positive_bp for candidate in train_known if candidate.base.length > 5
    )
    callable_bp = sum(interval_bp(chromosome.genome_callable_regions) for chromosome in train)
    selected_count = selected_positive = selected_negative = selected_long_positive = 0
    raw_short_count = sum(union.short for union in unions.values())
    raw_run_count = sum(union.components for union in unions.values())
    raw_short_rate = raw_short_count / raw_run_count if raw_run_count else None
    selected_risk: Fraction | None = None
    selected_non_gene: dict[str, bool] | None = None
    selected_train_evaluation: dict[str, object] | None = None
    frontier_rows: list[dict[str, object]] = []
    for risk in sorted(risk_groups):
        for candidate in risk_groups[risk]:
            unions[candidate.base.seqid].add_gap(candidate)
            selected_count += 1
            selected_positive += candidate.positive_bp
            selected_negative += candidate.negative_bp
            if candidate.base.length > 5:
                selected_long_positive += candidate.positive_bp
        refined_counts = dict(raw_whole)
        refined_counts["predicted_bp"] = int(raw_whole["predicted_bp"]) + selected_positive + selected_negative
        refined_counts["true_positive_bp"] = int(raw_whole["true_positive_bp"]) + selected_positive
        refined_counts["false_positive_bp"] = int(raw_whole["false_positive_bp"]) + selected_negative
        refined_counts["false_negative_bp"] = int(raw_whole["false_negative_bp"]) - selected_positive
        refined_counts["true_negative_bp"] = int(raw_whole["true_negative_bp"]) - selected_negative
        tp, fp = int(refined_counts["true_positive_bp"]), int(refined_counts["false_positive_bp"])
        fn, tn = int(refined_counts["false_negative_bp"]), int(refined_counts["true_negative_bp"])
        refined_counts["precision"] = tp / (tp + fp) if tp + fp else None
        refined_counts["recall"] = tp / (tp + fn) if tp + fn else None
        precision, recall = refined_counts["precision"], refined_counts["recall"]
        refined_counts["f1"] = 2 * precision * recall / (precision + recall) if precision and recall else None
        denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        refined_counts["mcc"] = (tp * tn - fp * fn) / denominator if denominator else None
        refined_short_count = sum(union.short for union in unions.values())
        refined_run_count = sum(union.components for union in unions.values())
        refined_short_rate = refined_short_count / refined_run_count if refined_run_count else None
        gates = non_gene_gate(
            raw_whole, refined_counts, raw_fragment, refined_fragment_zero,
            raw_short_rate, refined_short_rate, selected_count, universe_count,
            selected_positive, selected_negative, positive_denominator,
            selected_long_positive, long_positive_denominator, callable_bp,
        )
        frontier_row = {
            "risk_numerator": risk.numerator, "risk_denominator": risk.denominator,
            "risk": float(risk), "selected_candidates": selected_count,
            "selected_positive_bp": selected_positive, "selected_negative_bp": selected_negative,
            "gap_bp_coverage": (selected_positive + selected_negative) / universe_gap_bp if universe_gap_bp else None,
            "added_bp_precision": (
                selected_positive / (selected_positive + selected_negative)
                if selected_positive + selected_negative else None
            ),
            "known_negative_bp_per_mb": selected_negative * 1_000_000 / callable_bp,
            "positive_gap_bp_recovery": selected_positive / positive_denominator if positive_denominator else None,
            "positive_gap_gt5_bp_recovery": (
                selected_long_positive / long_positive_denominator if long_positive_denominator else None
            ),
            "short_rate": refined_short_rate,
            "optimistic_non_gene_gate_pass": all(gates.values()),
            "exact_mask_evaluated": False,
            "exact_non_gene_gate_pass": "",
            "exact_whole_precision": "", "exact_whole_recall": "", "exact_whole_f1": "",
            "exact_split_rate": "", "exact_fragments_per_truth": "",
            "exact_missed_rate": "", "exact_short_rate": "",
        }
        for name, passed in gates.items():
            frontier_row[f"optimistic_gate_{name}"] = passed
            frontier_row[f"exact_gate_{name}"] = ""
        frontier_rows.append(frontier_row)
        if selected_risk is None and all(gates.values()):
            candidate_ids = selected_for_risk(train, risk)
            exact = evaluate_dataset(train, candidate_ids)
            exact_gates = non_gene_gate(
                exact["whole_mask"]["raw"], exact["whole_mask"]["refined"],
                exact["fragmentation"]["raw"], exact["fragmentation"]["refined"],
                exact["short_predictions"]["raw"]["short_rate"],
                exact["short_predictions"]["refined"]["short_rate"],
                int(exact["selected_candidates"]), universe_count,
                int(exact["selected_positive_bp"]), int(exact["selected_negative_bp"]),
                positive_denominator, selected_long_positive, long_positive_denominator,
                callable_bp,
            )
            frontier_row["exact_mask_evaluated"] = True
            frontier_row["exact_non_gene_gate_pass"] = all(exact_gates.values())
            frontier_row["exact_whole_precision"] = exact["whole_mask"]["refined"]["precision"]
            frontier_row["exact_whole_recall"] = exact["whole_mask"]["refined"]["recall"]
            frontier_row["exact_whole_f1"] = exact["whole_mask"]["refined"]["f1"]
            frontier_row["exact_split_rate"] = exact["fragmentation"]["refined"]["split_rate"]
            frontier_row["exact_fragments_per_truth"] = exact["fragmentation"]["refined"]["fragments_per_truth"]
            frontier_row["exact_missed_rate"] = exact["fragmentation"]["refined"]["missed_rate"]
            frontier_row["exact_short_rate"] = exact["short_predictions"]["refined"]["short_rate"]
            for name, passed in exact_gates.items():
                frontier_row[f"exact_gate_{name}"] = passed
            if all(exact_gates.values()):
                selected_risk = risk
                selected_non_gene = exact_gates
                selected_train_evaluation = exact
                break
            if not exact_gates["fragments_per_truth_relative_decrease"]:
                break
        if selected_negative * 1_000_000 / callable_bp > 10:
            break
    train_result: dict[str, object]
    dev_result: dict[str, object] | None = None
    train_selected_ids: set[str] = set()
    dev_selected_ids: set[str] = set()
    if selected_risk is None:
        train_result = {
            "status": "WHOLE_GAP_ORACLE_NO_GO", "reason": "no train frontier point passed non-gene gates",
            "zero_risk_evaluation": zero_evaluation,
            "length_strata": candidate_strata(train, set()),
            "selection_diagnostics": selection_diagnostics(train, set()),
        }
    else:
        train_selected_ids = selected_for_risk(train, selected_risk)
        train_evaluation = selected_train_evaluation or evaluate_dataset(train, train_selected_ids)
        train_gene = gene_safety(train, train_selected_ids, transcripts)
        assert selected_non_gene is not None
        train_gates = {**selected_non_gene, **train_gene["gates"]}
        train_result = {
            "status": "PASS" if all(train_gates.values()) else "WHOLE_GAP_ORACLE_NO_GO",
            "selected_risk": {
                "numerator": selected_risk.numerator,
                "denominator": selected_risk.denominator,
                "value": float(selected_risk),
            },
            "gates": train_gates, "evaluation": train_evaluation, "gene_safety": train_gene,
            "length_strata": candidate_strata(train, train_selected_ids),
            "selection_diagnostics": selection_diagnostics(train, train_selected_ids),
        }
        if all(train_gates.values()):
            dev_selected_ids = selected_for_risk(dev, selected_risk)
            dev_evaluation = evaluate_dataset(dev, dev_selected_ids)
            dev_known = [candidate for candidate in dev[0].candidates if candidate.unknown_bp == 0]
            dev_raw = dev_evaluation["whole_mask"]["raw"]
            dev_refined = dev_evaluation["whole_mask"]["refined"]
            dev_raw_fragment = dev_evaluation["fragmentation"]["raw"]
            dev_refined_fragment = dev_evaluation["fragmentation"]["refined"]
            dev_non_gene = non_gene_gate(
                dev_raw, dev_refined, dev_raw_fragment, dev_refined_fragment,
                dev_evaluation["short_predictions"]["raw"]["short_rate"],
                dev_evaluation["short_predictions"]["refined"]["short_rate"],
                int(dev_evaluation["selected_candidates"]), len(dev_known),
                int(dev_evaluation["selected_positive_bp"]), int(dev_evaluation["selected_negative_bp"]),
                sum(candidate.positive_bp for candidate in dev_known),
                sum(
                    candidate.positive_bp for candidate in dev_known
                    if candidate.base.length > 5 and candidate.risk <= selected_risk
                ),
                sum(candidate.positive_bp for candidate in dev_known if candidate.base.length > 5),
                sum(interval_bp(chromosome.genome_callable_regions) for chromosome in dev),
            )
            dev_gene = gene_safety(dev, dev_selected_ids, transcripts)
            dev_gates = {**dev_non_gene, **dev_gene["gates"]}
            dev_result = {
                "status": "PASS" if all(dev_gates.values()) else "WHOLE_GAP_ORACLE_NO_GO",
                "gates": dev_gates, "evaluation": dev_evaluation, "gene_safety": dev_gene,
                "length_strata": candidate_strata(dev, dev_selected_ids),
                "selection_diagnostics": selection_diagnostics(dev, dev_selected_ids),
            }
    overall_pass = train_result["status"] == "PASS" and dev_result is not None and dev_result["status"] == "PASS"
    result: dict[str, object] = {
        "schema": "gap_bridge_neural_stage0_oracle_v1",
        "protocol": PROTOCOL,
        "status": "PASS_TO_STAGE1" if overall_pass else "WHOLE_GAP_ORACLE_NO_GO",
        "action": "fill_complete_gap_or_abstain",
        "target": "comparator_negative_bp_fraction",
        "chromosome_roles": {
            "train": list(TRAIN_CHROMOSOMES), "dev": "chr13 DEV superblocks",
            "sealed_test_labels_not_retained_or_used": "chr19",
            "reserve_labels_not_retained_or_used": ["chr20", "chr21", "chr22"],
        },
        "risk_denominators": {
            "known_negative_bp_per_mb": "label-blind ACGT bp in the evaluated chromosome regions",
            "whole_mask": "ACGT bp excluding effective comparator-unknown intervals",
        },
        "label_blind_excluded_candidates": exclusions,
        "candidate_label_census": {
            "train": candidate_label_census(train),
            "chr13_dev": candidate_label_census(dev),
        },
        "chr13_split": split_manifest,
        "train": train_result,
        "dev": dev_result,
        "zero_risk_topology": {
            "train": zero_risk_topology(train),
            "chr13_dev": zero_risk_topology(dev),
        },
        "frontier_note": (
            "Thresholds are visited in increasing exact negative-fraction order. Comparator split-rate "
            "improvement saturates after the zero-negative group. The zero-risk fragmentation result is "
            "used only as an optimistic screen; the first otherwise feasible point is rebuilt and scored "
            "exactly before selection. The first admissible point wins the frozen fewer-negative-bp tie-break."
        ),
        "claim_boundary": "Human comparator-consistent whole-gap softmask feasibility only",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "stage0_oracle.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    with (output_dir / "train_frontier.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(frontier_rows[0]) if frontier_rows else ["risk"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(frontier_rows)
    write_selected(
        output_dir / "selected_candidates.tsv",
        {
            "train": ("TRAIN_CHR3_CHR5", train, train_selected_ids),
            "dev": ("CHR13_DEV", dev, dev_selected_ids),
        },
    )
    (output_dir / "STATUS").write_text("COMPLETED\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--comparator-positive", required=True, type=Path)
    parser.add_argument("--comparator-unknown", required=True, type=Path)
    parser.add_argument("--refgene", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = run_oracle(
        args.source_root, args.comparator_positive, args.comparator_unknown,
        args.refgene, args.output_dir,
    )
    print(json.dumps({"status": result["status"], "output": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
