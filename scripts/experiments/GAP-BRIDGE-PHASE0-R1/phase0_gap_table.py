#!/usr/bin/env python3
"""Export frozen-P3 gaps, then project comparator relation labels."""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


BRIDGE = "COMPARATOR_BRIDGE_SUPPORTED"
SEPARATION = "COMPARATOR_SEPARATION_SUPPORTED"
AMBIGUOUS = "COMPARATOR_RELATION_AMBIGUOUS"
FLANK = 256

CANDIDATE_FIELDS = [
    "candidate_id", "seqid",
    "left_run_start", "left_run_end", "left_run_length",
    "gap_start", "gap_end", "gap_length",
    "right_run_start", "right_run_end", "right_run_length",
    "span_length", "callable", "n_bp", "eligible_main",
    "touches_window_seam", "nearest_window_seam_signed_distance",
    "nearest_window_seam_abs_distance",
    "gap_gc_fraction", "gap_entropy", "gap_max_homopolymer",
    "left_flank_gc_fraction", "right_flank_gc_fraction",
    "flank_3mer_jaccard", "microhomology_bp",
    "pte_gap_mean", "pte_gap_min", "pte_gap_max",
    "pte_left_run_mean", "pte_right_run_mean",
    "pte_left_edge", "pte_right_edge",
    "state_background_gap_mean", "state_interior_gap_mean",
    "state_left_boundary_gap_max", "state_right_boundary_gap_max",
    "state_right_boundary_left_edge", "state_left_boundary_right_edge",
]

LABEL_FIELDS = [
    "comparator_relation", "clean_target",
    "gap_comparator_positive_bp", "gap_comparator_negative_bp",
    "gap_comparator_unknown_bp",
]


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def read_intervals(path: Path) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with _open_text(path) as handle:
        lines = [line.rstrip("\r\n") for line in handle if line.strip() and not line.startswith("#")]
    if not lines:
        return {}
    first = lines[0].split("\t")
    header = {field.lower(): index for index, field in enumerate(first)}
    has_header = {"seqid", "start", "end"}.issubset(header)
    rows = lines[1:] if has_header else lines
    seq_index = header["seqid"] if has_header else 0
    start_index = header["start"] if has_header else 1
    end_index = header["end"] if has_header else 2
    for line in rows:
        fields = line.split("\t")
        start, end = int(fields[start_index]), int(fields[end_index])
        if start < 0 or end <= start:
            raise ValueError(f"invalid half-open interval: {fields[seq_index]}:{start}-{end}")
        grouped[fields[seq_index]].append((start, end))
    return {seqid: merge_intervals(values) for seqid, values in grouped.items()}


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def read_region(path: Path) -> tuple[str, int, int, str, list[int]]:
    rows = []
    with _open_text(path) as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"empty region JSONL: {path}")
    rows.sort(key=lambda row: int(row["start"]))
    seqid = str(rows[0]["chr"])
    region_start = int(rows[0]["start"])
    next_start = region_start
    pieces: list[str] = []
    seams: list[int] = []
    for index, row in enumerate(rows):
        start, end = int(row["start"]), int(row["end"])
        sequence = str(row["sequence"]).upper()
        if str(row["chr"]) != seqid or start != next_start or end - start != len(sequence):
            raise ValueError("region JSONL must contain one contiguous coordinate shard")
        if index:
            seams.append(start)
        pieces.append(sequence)
        next_start = end
    return seqid, region_start, next_start, "".join(pieces), seams


def clipped_runs(
    intervals: dict[str, list[tuple[int, int]]], seqid: str, start: int, end: int,
) -> list[tuple[int, int]]:
    values = [
        (max(left, start), min(right, end))
        for left, right in intervals.get(seqid, [])
        if left < end and right > start
    ]
    return merge_intervals((left, right) for left, right in values if left < right)


def nearest_seam(start: int, end: int, seams: list[int]) -> tuple[str, str, str]:
    if not seams:
        return "0", "NA", "NA"
    index = bisect.bisect_left(seams, start)
    nearby = seams[index:index + 1]
    if index:
        nearby.append(seams[index - 1])
    choices = []
    for seam in nearby:
        if seam < start:
            distance = seam - start
        elif seam > end:
            distance = seam - end
        else:
            distance = 0
        choices.append((abs(distance), distance, seam))
    absolute, signed, _ = min(choices)
    return str(int(absolute == 0)), str(signed), str(absolute)


def gc_fraction(sequence: str) -> str | float:
    bases = [base for base in sequence if base in "ACGT"]
    if not bases:
        return ""
    return (bases.count("G") + bases.count("C")) / len(bases)


def entropy(sequence: str) -> float:
    bases = [base for base in sequence if base in "ACGT"]
    if not bases:
        return 0.0
    counts = Counter(bases)
    return -sum((count / len(bases)) * math.log2(count / len(bases)) for count in counts.values())


def max_homopolymer(sequence: str) -> int:
    best = current = 0
    previous = ""
    for base in sequence:
        if base not in "ACGT":
            previous = ""
            current = 0
        elif base == previous:
            current += 1
        else:
            previous = base
            current = 1
        best = max(best, current)
    return best


def kmer_jaccard(left: str, right: str, k: int = 3) -> float:
    left_kmers = {left[index:index + k] for index in range(len(left) - k + 1) if "N" not in left[index:index + k]}
    right_kmers = {right[index:index + k] for index in range(len(right) - k + 1) if "N" not in right[index:index + k]}
    union = left_kmers | right_kmers
    return len(left_kmers & right_kmers) / len(union) if union else 0.0


def microhomology(left: str, right: str, maximum: int = 32) -> int:
    for length in range(min(maximum, len(left), len(right)), 0, -1):
        if left[-length:] == right[:length] and set(left[-length:]) <= set("ACGT"):
            return length
    return 0


def load_track(path: Path | None, region_start: int, region_end: int) -> tuple[np.ndarray | None, int]:
    if path is None:
        return None, 0
    values = np.load(path, mmap_mode="r", allow_pickle=False)
    region_length = region_end - region_start
    if values.shape[0] == region_length:
        return values, region_start
    if values.shape[0] >= region_end:
        return values, 0
    raise ValueError("probability coordinates do not cover the region")


def export_candidates(
    p3_canonical: Path,
    data_jsonl: Path,
    output: Path,
    pte_npy: Path | None = None,
    state_probabilities_npy: Path | None = None,
) -> int:
    seqid, region_start, region_end, sequence, seams = read_region(data_jsonl)
    runs = clipped_runs(read_intervals(p3_canonical), seqid, region_start, region_end)
    probability, probability_offset = load_track(pte_npy, region_start, region_end)
    state_probability, state_offset = load_track(state_probabilities_npy, region_start, region_end)
    if probability is not None and probability.ndim != 1:
        raise ValueError("P_TE probability input must be one-dimensional")
    if state_probability is not None and (state_probability.ndim != 2 or state_probability.shape[1] != 4):
        raise ValueError("state probability input must have shape (region_length, 4)")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for left, right in zip(runs, runs[1:]):
            gap_start, gap_end = left[1], right[0]
            if gap_end <= gap_start:
                continue
            gap = sequence[gap_start - region_start:gap_end - region_start]
            left_flank = sequence[max(region_start, gap_start - FLANK) - region_start:gap_start - region_start]
            right_flank = sequence[gap_end - region_start:min(region_end, gap_end + FLANK) - region_start]
            non_acgt = sum(base not in "ACGT" for base in gap)
            touch, seam_signed, seam_absolute = nearest_seam(gap_start, gap_end, seams)
            if probability is None:
                gap_values = None
                left_values = right_values = None
                left_edge = right_edge = ""
            else:
                gap_values = probability[gap_start - probability_offset:gap_end - probability_offset]
                left_values = probability[left[0] - probability_offset:left[1] - probability_offset]
                right_values = probability[right[0] - probability_offset:right[1] - probability_offset]
                left_edge = float(probability[gap_start - 1 - probability_offset])
                right_edge = float(probability[gap_end - probability_offset])
            if state_probability is None:
                state_features = {
                    "state_background_gap_mean": "", "state_interior_gap_mean": "",
                    "state_left_boundary_gap_max": "", "state_right_boundary_gap_max": "",
                    "state_right_boundary_left_edge": "", "state_left_boundary_right_edge": "",
                }
            else:
                state_gap = state_probability[gap_start - state_offset:gap_end - state_offset]
                state_features = {
                    "state_background_gap_mean": float(state_gap[:, 0].mean()),
                    "state_interior_gap_mean": float(state_gap[:, 1].mean()),
                    "state_left_boundary_gap_max": float(state_gap[:, 2].max()),
                    "state_right_boundary_gap_max": float(state_gap[:, 3].max()),
                    "state_right_boundary_left_edge": float(state_probability[gap_start - 1 - state_offset, 3]),
                    "state_left_boundary_right_edge": float(state_probability[gap_end - state_offset, 2]),
                }
            row = {
                "candidate_id": f"{seqid}:{gap_start}-{gap_end}", "seqid": seqid,
                "left_run_start": left[0], "left_run_end": left[1], "left_run_length": left[1] - left[0],
                "gap_start": gap_start, "gap_end": gap_end, "gap_length": gap_end - gap_start,
                "right_run_start": right[0], "right_run_end": right[1], "right_run_length": right[1] - right[0],
                "span_length": right[1] - left[0], "callable": int(non_acgt == 0),
                "n_bp": gap.count("N"),
                "eligible_main": int(1 <= gap_end - gap_start <= 512 and non_acgt == 0),
                "touches_window_seam": touch,
                "nearest_window_seam_signed_distance": seam_signed,
                "nearest_window_seam_abs_distance": seam_absolute,
                "gap_gc_fraction": gc_fraction(gap), "gap_entropy": entropy(gap),
                "gap_max_homopolymer": max_homopolymer(gap),
                "left_flank_gc_fraction": gc_fraction(left_flank),
                "right_flank_gc_fraction": gc_fraction(right_flank),
                "flank_3mer_jaccard": kmer_jaccard(left_flank, right_flank),
                "microhomology_bp": microhomology(left_flank, right_flank),
                "pte_gap_mean": float(gap_values.mean()) if gap_values is not None else "",
                "pte_gap_min": float(gap_values.min()) if gap_values is not None else "",
                "pte_gap_max": float(gap_values.max()) if gap_values is not None else "",
                "pte_left_run_mean": float(left_values.mean()) if left_values is not None else "",
                "pte_right_run_mean": float(right_values.mean()) if right_values is not None else "",
                "pte_left_edge": left_edge, "pte_right_edge": right_edge,
                **state_features,
            }
            writer.writerow(row)
            count += 1
    return count


def subtract_intervals(
    intervals: list[tuple[int, int]], blockers: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    blocker_index = 0
    for start, end in intervals:
        cursor = start
        while blocker_index < len(blockers) and blockers[blocker_index][1] <= cursor:
            blocker_index += 1
        index = blocker_index
        while index < len(blockers) and blockers[index][0] < end:
            left, right = blockers[index]
            if left > cursor:
                result.append((cursor, min(left, end)))
            cursor = max(cursor, right)
            if cursor >= end:
                break
            index += 1
        if cursor < end:
            result.append((cursor, end))
    return result


def overlap_bp(intervals: list[tuple[int, int]], starts: list[int], start: int, end: int) -> int:
    index = max(0, bisect.bisect_right(starts, start) - 1)
    total = 0
    for left, right in intervals[index:]:
        if left >= end:
            break
        total += max(0, min(end, right) - max(start, left))
    return total


def covering_run(
    intervals: list[tuple[int, int]], starts: list[int], position: int,
) -> tuple[int, int] | None:
    index = bisect.bisect_right(starts, position) - 1
    if index >= 0 and intervals[index][1] > position:
        return intervals[index]
    return None


def project_labels(
    candidates: Path,
    comparator_positive: Path,
    comparator_unknown: Path,
    output: Path,
) -> int:
    positive = read_intervals(comparator_positive)
    unknown = read_intervals(comparator_unknown)
    with candidates.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not set(CANDIDATE_FIELDS).issubset(reader.fieldnames):
            raise ValueError("candidate TSV does not match the Phase-0 export schema")
        input_fields = list(reader.fieldnames)
        rows = list(reader)
    if any(field in input_fields for field in LABEL_FIELDS):
        raise ValueError("candidate TSV is already comparator-projected")

    tracks: dict[str, tuple[list[tuple[int, int]], list[int], list[tuple[int, int]], list[int]]] = {}
    for seqid in {row["seqid"] for row in rows}:
        positive_runs = positive.get(seqid, [])
        effective_unknown = subtract_intervals(unknown.get(seqid, []), positive_runs)
        tracks[seqid] = (
            positive_runs, [start for start, _ in positive_runs],
            effective_unknown, [start for start, _ in effective_unknown],
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=input_fields + LABEL_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            start, end = int(row["gap_start"]), int(row["gap_end"])
            length = end - start
            positive_runs, positive_starts, unknown_runs, unknown_starts = tracks[row["seqid"]]
            positive_bp = overlap_bp(positive_runs, positive_starts, start, end)
            unknown_bp = overlap_bp(unknown_runs, unknown_starts, start, end)
            negative_bp = length - positive_bp - unknown_bp
            left_run = covering_run(positive_runs, positive_starts, start - 1)
            right_run = covering_run(positive_runs, positive_starts, end)
            relation = AMBIGUOUS
            if row["callable"] == "1" and overlap_bp(unknown_runs, unknown_starts, start - 1, end + 1) == 0:
                if positive_bp == length and left_run is not None and left_run == right_run:
                    relation = BRIDGE
                elif positive_bp == 0 and left_run is not None and right_run is not None and left_run != right_run:
                    relation = SEPARATION
            row.update({
                "comparator_relation": relation,
                "clean_target": "1" if relation == BRIDGE else "0" if relation == SEPARATION else "",
                "gap_comparator_positive_bp": positive_bp,
                "gap_comparator_negative_bp": negative_bp,
                "gap_comparator_unknown_bp": unknown_bp,
            })
            writer.writerow(row)
    return len(rows)


def write_census(labeled: Path, output: Path) -> dict[str, object]:
    with labeled.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    relations_all = Counter(row["comparator_relation"] for row in rows)
    eligible_rows = [row for row in rows if row["eligible_main"] == "1"]
    relations_eligible = Counter(row["comparator_relation"] for row in eligible_rows)
    result: dict[str, object] = {
        "schema": "gap_bridge_e0_candidate_census_v2",
        "status": "PASS",
        "candidates": len(rows),
        "eligible_main": len(eligible_rows),
        "relations_all": {
            label: relations_all[label] for label in (BRIDGE, SEPARATION, AMBIGUOUS)
        },
        "relations_eligible_main": {
            label: relations_eligible[label] for label in (BRIDGE, SEPARATION, AMBIGUOUS)
        },
        "gap_bp": sum(int(row["gap_length"]) for row in rows),
        "scientific_metrics_computed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    candidates = commands.add_parser("candidates", help="export label-blind adjacent P3 gaps")
    candidates.add_argument("--p3-canonical", required=True, type=Path)
    candidates.add_argument("--data-jsonl", required=True, type=Path)
    candidates.add_argument("--pte-npy", type=Path)
    candidates.add_argument("--state-probabilities-npy", type=Path)
    candidates.add_argument("--output", required=True, type=Path)

    labels = commands.add_parser("project-labels", help="append clean comparator relation labels")
    labels.add_argument("--candidates", required=True, type=Path)
    labels.add_argument("--comparator-positive", required=True, type=Path)
    labels.add_argument("--comparator-unknown", required=True, type=Path)
    labels.add_argument("--output", required=True, type=Path)

    census = commands.add_parser("census", help="summarize the engineering candidate denominator")
    census.add_argument("--labeled", required=True, type=Path)
    census.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "candidates":
        export_candidates(
            args.p3_canonical, args.data_jsonl, args.output,
            args.pte_npy, args.state_probabilities_npy,
        )
    elif args.command == "project-labels":
        project_labels(args.candidates, args.comparator_positive, args.comparator_unknown, args.output)
    else:
        write_census(args.labeled, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
