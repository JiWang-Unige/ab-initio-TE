#!/usr/bin/env python3
"""Describe overlap of qualified mappings with the fixed CHM13v2 2022 TE run.

The input mapping table contains every old-confusion interval.  Only a row
with one same-length reciprocal destination on target chr2/3/4 is queried
against the target annotation.  Mapping failures remain in the output table
with their original status and no fabricated zero-overlap values.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple, Union


VALID_STATES = ("TP", "FP", "FN", "TN")
VALID_STATE_SET = set(VALID_STATES)
CATEGORIES = ("TE", "UNKNOWN", "NONTE", "UNRECOGNIZED")
LAYERS = (("any", 0.0), ("ge50", 0.50), ("ge80", 0.80))
QUALIFIED_STATUS = "UNIQUE_RECIPROCAL_SAME_LENGTH"
TE_CLASSES = {"SINE", "LINE", "LTR", "DNA", "RC", "RETROPOSON"}
KNOWN_NONTE_CLASSES = {
    "SIMPLE_REPEAT",
    "LOW_COMPLEXITY",
    "SATELLITE",
    "RNA",
    "SNRNA",
    "SCRNA",
    "SRPRNA",
    "TRNA",
    "RRNA",
}


def resolve_path(root: Path, value: Union[str, Path]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def annotation_category(class_field: str) -> str:
    """Assign exactly one category from the RepeatMasker base class."""
    normalized = class_field.strip().upper()
    base = normalized.split("/", 1)[0]
    if base == "UNKNOWN" or "?" in normalized:
        return "UNKNOWN"
    if base in TE_CLASSES:
        return "TE"
    if base in KNOWN_NONTE_CLASSES:
        return "NONTE"
    return "UNRECOGNIZED"


def merge_intervals(intervals: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    merged: List[Tuple[int, int]] = []
    for start, end in sorted(intervals):
        if start < 0 or end <= start:
            raise ValueError(f"invalid annotation interval: {start}-{end}")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


class UnionIndex:
    """Overlap queries against sorted, disjoint union intervals."""

    def __init__(self, intervals: Sequence[Tuple[int, int]]) -> None:
        self.intervals = list(intervals)
        self.starts = [start for start, _ in self.intervals]

    def overlap_bp(self, start: int, end: int) -> int:
        if end <= start:
            raise ValueError(f"invalid query interval: {start}-{end}")
        # Include one interval before the first start >= query start because it
        # may span the query's left edge.
        index = max(0, bisect.bisect_left(self.starts, start) - 1)
        total = 0
        while index < len(self.intervals):
            interval_start, interval_end = self.intervals[index]
            if interval_start >= end:
                break
            total += max(0, min(end, interval_end) - max(start, interval_start))
            index += 1
        return total


def parse_annotation(
    path: Path, allowed_target: set[str]
) -> Tuple[
    Dict[str, Dict[str, UnionIndex]],
    Dict[str, Dict[str, int]],
    Dict[str, Dict[str, int]],
]:
    """Read only allowed target chromosomes, filtering before field parsing."""
    raw: Dict[str, Dict[str, List[Tuple[int, int]]]] = {
        category: {chrom: [] for chrom in sorted(allowed_target)} for category in CATEGORIES
    }
    record_counts: Dict[str, Dict[str, int]] = {
        category: {chrom: 0 for chrom in sorted(allowed_target)} for category in CATEGORIES
    }
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 7:
                continue
            # Do not parse coordinates or class fields on excluded chromosomes.
            chrom = fields[4]
            if chrom not in allowed_target:
                continue
            try:
                start0 = int(fields[5]) - 1
                end = int(fields[6])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: invalid allowed-target coordinates") from exc
            if start0 < 0 or end <= start0:
                raise ValueError(f"{path}:{line_no}: invalid allowed-target interval")
            category = annotation_category(fields[10] if len(fields) > 10 else "")
            raw[category][chrom].append((start0, end))
            record_counts[category][chrom] += 1
    merged: Dict[str, Dict[str, UnionIndex]] = {
        category: {
            chrom: UnionIndex(merge_intervals(raw[category][chrom]))
            for chrom in sorted(allowed_target)
        }
        for category in CATEGORIES
    }
    union_bp: Dict[str, Dict[str, int]] = {
        category: {
            chrom: sum(end - start for start, end in merged[category][chrom].intervals)
            for chrom in sorted(allowed_target)
        }
        for category in CATEGORIES
    }
    return merged, record_counts, union_bp


def empty_metrics() -> Dict[str, object]:
    result: Dict[str, object] = {}
    for category in CATEGORIES:
        for layer, _ in LAYERS:
            result[f"{category}_{layer}_overlap_bp"] = ""
            result[f"{category}_{layer}_supported"] = ""
        result[f"{category}_overlap_bp"] = ""
        result[f"{category}_coverage_fraction"] = ""
    return result


def compute_metrics(
    target_chrom: str,
    start: int,
    end: int,
    indices: Mapping[str, Mapping[str, UnionIndex]],
) -> Dict[str, object]:
    length = end - start
    if length <= 0:
        raise ValueError("qualified target interval has non-positive length")
    metrics: Dict[str, object] = {}
    for category in CATEGORIES:
        overlap = indices[category][target_chrom].overlap_bp(start, end)
        fraction = overlap / float(length)
        metrics[f"{category}_overlap_bp"] = overlap
        metrics[f"{category}_coverage_fraction"] = f"{fraction:.12g}"
        for layer, threshold in LAYERS:
            supported = overlap >= 1 if layer == "any" else fraction >= threshold
            metrics[f"{category}_{layer}_overlap_bp"] = overlap
            metrics[f"{category}_{layer}_supported"] = supported
    return metrics


def parse_mapping_rows(
    path: Path, allowed_source: set[str], allowed_target: set[str]
) -> Tuple[List[dict], List[str]]:
    """Parse mapping rows while filtering source chromosome before coordinates."""
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"mapping outcome has no header: {path}")
        required = {
            "source_chrom",
            "state",
            "mapping_status",
            "forward_chrom",
            "forward_start0",
            "forward_end",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"mapping outcome missing fields: {sorted(missing)}")
        for row in reader:
            source_chrom = row["source_chrom"]
            if source_chrom not in allowed_source:
                # Preserve the raw row, but do not parse coordinate fields from
                # an excluded source chromosome.
                rows.append(row)
                continue
            if row["state"] not in VALID_STATE_SET:
                raise ValueError(f"unexpected mapping state: {row['state']!r}")
            status = row["mapping_status"]
            if status == QUALIFIED_STATUS:
                target_chrom = row["forward_chrom"]
                if target_chrom not in allowed_target:
                    raise ValueError(
                        f"qualified mapping points outside target panel: {target_chrom!r}"
                    )
                try:
                    int(row["forward_start0"])
                    int(row["forward_end"])
                except ValueError as exc:
                    raise ValueError("qualified mapping has invalid target coordinates") from exc
            rows.append(row)
    return rows, list(reader.fieldnames)


def write_overlap_rows(
    path: Path,
    rows: Sequence[dict],
    fieldnames: Sequence[str],
    indices: Mapping[str, Mapping[str, UnionIndex]],
    allowed_source: set[str],
    allowed_target: set[str],
) -> Tuple[collections.Counter, Dict[str, Dict[str, int]], int, int]:
    extra = [field for field in empty_metrics() if field not in fieldnames]
    output_fields = list(fieldnames) + extra
    status_counts: collections.Counter = collections.Counter()
    state_status: Dict[str, Dict[str, int]] = {
        state: collections.Counter() for state in VALID_STATES
    }
    qualified_count = 0
    qualified_bp = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            status = row.get("mapping_status", "")
            status_counts[status] += 1
            state = row.get("state", "")
            if state in state_status:
                state_status[state][status] += 1
            metrics = empty_metrics()
            if row.get("source_chrom") in allowed_source and status == QUALIFIED_STATUS:
                target_chrom = row.get("forward_chrom", "")
                if target_chrom not in allowed_target:
                    raise ValueError(f"qualified target outside panel: {target_chrom!r}")
                start = int(row["forward_start0"])
                end = int(row["forward_end"])
                metrics = compute_metrics(target_chrom, start, end, indices)
                qualified_count += 1
                qualified_bp += end - start
            output_row = dict(row)
            output_row.update(metrics)
            writer.writerow(output_row)
    return status_counts, state_status, qualified_count, qualified_bp


def build_summary(
    config: dict,
    root: Path,
    mapping_path: Path,
    annotation_path: Path,
    rows: Sequence[dict],
    status_counts: collections.Counter,
    state_status: Mapping[str, Mapping[str, int]],
    qualified_count: int,
    qualified_bp: int,
    record_counts: Mapping[str, Mapping[str, int]],
    union_bp: Mapping[str, Mapping[str, int]],
) -> dict:
    state_counts = collections.Counter(row.get("state", "") for row in rows)
    qualified_by_state = collections.Counter(
        row.get("state", "")
        for row in rows
        if row.get("mapping_status") == QUALIFIED_STATUS
        and row.get("source_chrom") in set(config["allowed_source_chromosomes"])
    )
    return {
        "status": "CHM13_2022_DESCRIPTIVE_OVERLAP_COMPLETED",
        "protocol": config["protocol"],
        "source_interval_count": len(rows),
        "source_state_counts": dict(state_counts),
        "mapping_outcome_counts": dict(status_counts),
        "mapping_outcome_counts_by_state": {
            state: dict(state_status[state]) for state in VALID_STATES
        },
        "qualified_unique_reciprocal_same_length_count": qualified_count,
        "qualified_target_bp": qualified_bp,
        "qualified_count_by_state": dict(qualified_by_state),
        "annotation_rows_by_category_and_chromosome": record_counts,
        "annotation_union_bp_by_category_and_chromosome": union_bp,
        "source": {
            "mapping_outcomes": str(mapping_path),
            "annotation": str(annotation_path),
            "annotation_source_url": config["annotation_source_url"],
            "annotation_release": config["annotation_release"],
        },
        "allowed_source_chromosomes": config["allowed_source_chromosomes"],
        "allowed_target_chromosomes": config["allowed_target_chromosomes"],
        "forbidden_source_chromosomes": config["forbidden_source_chromosomes"],
        "forbidden_target_chromosomes": config["forbidden_target_chromosomes"],
        "overlap_definition": config["overlap_definition"],
        "claim_policy": config["claim_policy"],
        "target_annotations_read": True,
        "same_base_f1_computed": False,
        "fp_rescue_claim": False,
    }


def run(args: argparse.Namespace) -> dict:
    root = args.root.resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    mapping_path = resolve_path(root, config["mapping_outcomes"])
    annotation_path = resolve_path(root, config["annotation"])
    if not mapping_path.is_file():
        raise FileNotFoundError(f"mapping outcome table not found: {mapping_path}")
    if not annotation_path.is_file():
        raise FileNotFoundError(f"fixed 2022 annotation not found: {annotation_path}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    allowed_source = set(config["allowed_source_chromosomes"])
    allowed_target = set(config["allowed_target_chromosomes"])
    rows, fieldnames = parse_mapping_rows(mapping_path, allowed_source, allowed_target)
    indices, record_counts, union_bp = parse_annotation(annotation_path, allowed_target)
    status_counts, state_status, qualified_count, qualified_bp = write_overlap_rows(
        output / "annotation_overlap.tsv",
        rows,
        fieldnames,
        indices,
        allowed_source,
        allowed_target,
    )
    summary = build_summary(
        config,
        root,
        mapping_path,
        annotation_path,
        rows,
        status_counts,
        state_status,
        qualified_count,
        qualified_bp,
        record_counts,
        union_bp,
    )
    summary["outputs"] = {
        "annotation_overlap": str(output / "annotation_overlap.tsv"),
        "summary": str(output / "summary.json"),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "completion.json").write_text(
        json.dumps(
            {
                "status": summary["status"],
                "target_annotations_read": True,
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
