#!/usr/bin/env python3
"""Project frozen chr13 comparator family labels onto candidate flanks."""
from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


SEQID = "chr13"
ROLES = ("DEV", "CAL_FIT", "CAL_GATE")
ROLE_SET = frozenset(ROLES)
MANIFEST_FIELDS = ("candidate_id", "seqid", "role", "gap_start", "gap_end")
OUTPUT_FIELDS = (
    "candidate_id", "seqid", "role", "gap_start", "gap_end",
    "left_labels", "right_labels", "status", "family_stratum",
)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    seqid: str
    role: str
    gap_start: int
    gap_end: int


@dataclass(frozen=True)
class BedInterval:
    start: int
    end: int
    label: str
    repeat_class: str
    family: str


def _open_text(path: Path) -> TextIO:
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def read_candidates(path: Path) -> list[Candidate]:
    """Read only the frozen geometry columns used by this evaluation projection."""
    candidates: list[Candidate] = []
    seen: set[str] = set()
    with _open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not set(MANIFEST_FIELDS) <= set(reader.fieldnames):
            raise ValueError("candidate manifest lacks family-projection geometry fields")
        for row in reader:
            if row["seqid"] != SEQID or row["role"] not in ROLE_SET:
                continue
            candidate_id = row["candidate_id"]
            if not candidate_id:
                raise ValueError("processed candidate has an empty candidate_id")
            if candidate_id in seen:
                raise ValueError(f"duplicate processed candidate_id: {candidate_id}")
            gap_start = int(row["gap_start"])
            gap_end = int(row["gap_end"])
            if gap_end <= gap_start:
                raise ValueError(f"invalid candidate gap interval: {candidate_id}")
            seen.add(candidate_id)
            candidates.append(Candidate(
                candidate_id=candidate_id,
                seqid=SEQID,
                role=row["role"],
                gap_start=gap_start,
                gap_end=gap_end,
            ))
    return candidates


def _combined_label(fields: list[str]) -> tuple[str, str, str]:
    repeat_class = fields[6].strip() if len(fields) > 6 else ""
    family = fields[7].strip() if len(fields) > 7 else ""
    label = fields[8].strip() if len(fields) > 8 else ""
    if not label:
        if repeat_class and family:
            label = f"{repeat_class}/{family}"
        else:
            label = repeat_class or family
    return label, repeat_class, family


def read_intervals(path: Path) -> list[BedInterval]:
    """Read labelled chr13 intervals from the frozen 0-based half-open BED."""
    intervals: list[BedInterval] = []
    with _open_text(path) as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) < 3:
                raise ValueError("strict BED row has fewer than three columns")
            if fields[0] != SEQID:
                continue
            start = int(fields[1])
            end = int(fields[2])
            if end <= start:
                raise ValueError("strict BED interval is empty or reversed")
            label, repeat_class, family = _combined_label(fields)
            if not label:
                continue
            intervals.append(BedInterval(start, end, label, repeat_class, family))
    intervals.sort(key=lambda row: (row.start, row.end, row.label, row.repeat_class, row.family))
    return intervals


def labels_at(intervals: list[BedInterval], positions: list[int]) -> list[tuple[str, ...]]:
    """Return sorted unique labels at each position using BED half-open semantics."""
    queries = sorted(enumerate(positions), key=lambda item: (item[1], item[0]))
    results: list[tuple[str, ...]] = [()] * len(positions)
    active: list[tuple[int, int, str]] = []
    counts: Counter[str] = Counter()
    next_interval = 0
    for query_index, position in queries:
        while next_interval < len(intervals) and intervals[next_interval].start <= position:
            interval = intervals[next_interval]
            heapq.heappush(active, (interval.end, next_interval, interval.label))
            counts[interval.label] += 1
            next_interval += 1
        while active and active[0][0] <= position:
            _end, _interval_index, label = heapq.heappop(active)
            counts[label] -= 1
            if counts[label] == 0:
                del counts[label]
        results[query_index] = tuple(sorted(counts))
    return results


def classify(left_labels: tuple[str, ...], right_labels: tuple[str, ...]) -> tuple[str, str]:
    if not left_labels or not right_labels:
        return "UNSUPPORTED", ""
    if len(left_labels) > 1 or len(right_labels) > 1:
        return "MULTIPLE", ""
    if left_labels == right_labels:
        return "SAME_UNIQUE", left_labels[0]
    return "DIFFERENT", ""


def serialize_labels(labels: tuple[str, ...]) -> str:
    return ";".join(labels)


def project(
    candidate_manifest: Path,
    strict_bed: Path,
    output_dir: Path,
) -> dict[str, object]:
    candidates = read_candidates(candidate_manifest)
    intervals = read_intervals(strict_bed)
    positions: list[int] = []
    for candidate in candidates:
        positions.extend((candidate.gap_start - 1, candidate.gap_end))
    projected = labels_at(intervals, positions)

    output_dir.mkdir(parents=True, exist_ok=False)
    output_tsv = output_dir / "chr13_family_projection.tsv"
    status_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    with output_tsv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, candidate in enumerate(candidates):
            left_labels = projected[2 * index]
            right_labels = projected[2 * index + 1]
            status, family_stratum = classify(left_labels, right_labels)
            status_counts[status] += 1
            if family_stratum:
                family_counts[family_stratum] += 1
            writer.writerow({
                "candidate_id": candidate.candidate_id,
                "seqid": candidate.seqid,
                "role": candidate.role,
                "gap_start": candidate.gap_start,
                "gap_end": candidate.gap_end,
                "left_labels": serialize_labels(left_labels),
                "right_labels": serialize_labels(right_labels),
                "status": status,
                "family_stratum": family_stratum,
            })

    census: dict[str, object] = {
        "schema": "gap_bridge_neural_stage1_family_projection_v1",
        "status": "PASS",
        "evaluation_only": True,
        "seqid": SEQID,
        "roles": list(ROLES),
        "processed_candidates": len(candidates),
        "chr13_bed_intervals": len(intervals),
        "status_counts": dict(sorted(status_counts.items())),
        "same_unique_family_strata": dict(sorted(family_counts.items())),
        "candidate_manifest": str(candidate_manifest),
        "strict_bed": str(strict_bed),
        "output_tsv": str(output_tsv),
        "flank_positions": "gap_start-1 and gap_end",
        "coordinate_convention": "zero_based_half_open",
        "scientific_metrics_computed": False,
    }
    (output_dir / "family_projection_census.json").write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")
    return census


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--strict-bed", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = project(args.candidate_manifest, args.strict_bed, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
