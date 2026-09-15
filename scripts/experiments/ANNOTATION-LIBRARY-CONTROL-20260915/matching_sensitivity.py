#!/usr/bin/env python3
"""Source-only no-reuse control matching sensitivity analysis.

This is deliberately separate from the original matched table.  It uses the
same frozen covariates and deterministic greedy ordering, but removes a TN
control from the pool after its first assignment.  No model score, new
annotation, target annotation, or sequence identity is read.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple


VALID_STATES = {"FP", "TN"}
GC_TOLERANCE = 0.02


def _true(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _candidate_key(case: Mapping[str, str], control: Mapping[str, str]) -> Tuple[float, int, int]:
    return (
        abs(float(case["source_gc_fraction"]) - float(control["source_gc_fraction"])),
        abs(int(case["old_te_distance_bp"] or 0) - int(control["old_te_distance_bp"] or 0)),
        int(control["row_id"]),
    )


def _compatible(case: Mapping[str, str], control: Mapping[str, str]) -> bool:
    return (
        control["source_chrom"] == case["source_chrom"]
        and int(control["source_length"]) == int(case["source_length"])
        and control["old_te_relation"] == case["old_te_relation"]
        and int(control["source_non_acgt_count"]) == int(case["source_non_acgt_count"])
        and control["old_te_distance_bin"] == case["old_te_distance_bin"]
        and abs(float(control["source_gc_fraction"]) - float(case["source_gc_fraction"]))
        <= GC_TOLERANCE + 1e-12
    )


def _group_key(row: Mapping[str, str]) -> Tuple[str, int, str, int, str]:
    return (
        row["source_chrom"],
        int(row["source_length"]),
        row["old_te_relation"],
        int(row["source_non_acgt_count"]),
        row["old_te_distance_bin"],
    )


def read_qualification(path: Path, allowed: Sequence[str]) -> List[dict]:
    allowed_set = set(allowed)
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"qualification table has no header: {path}")
        required = {
            "row_id", "mapping_id", "source_chrom", "source_length", "state",
            "old_te_relation", "old_te_distance_bp", "old_te_distance_bin",
            "source_gc_fraction", "source_non_acgt_count", "eligible_for_matching",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"qualification table missing fields: {sorted(missing)}")
        for line_no, row in enumerate(reader, 2):
            if row["source_chrom"] not in allowed_set or row["state"] not in VALID_STATES:
                continue
            if not _true(row["eligible_for_matching"]):
                continue
            for field in ("row_id", "source_length", "old_te_distance_bp", "source_non_acgt_count"):
                int(row[field])
            float(row["source_gc_fraction"])
            rows.append(row)
    return rows


def select_no_reuse(rows: Sequence[Mapping[str, str]]) -> Tuple[List[dict], dict]:
    cases = sorted((dict(row) for row in rows if row["state"] == "FP"), key=lambda row: int(row["row_id"]))
    controls = [dict(row) for row in rows if row["state"] == "TN"]
    controls_by_group: Dict[Tuple[str, int, str, int, str], List[dict]] = collections.defaultdict(list)
    for control in controls:
        controls_by_group[_group_key(control)].append(control)
    used: set[str] = set()
    selected: List[dict] = []
    candidate_counts: List[int] = []
    available_counts: List[int] = []
    for case in cases:
        all_candidates = [control for control in controls_by_group[_group_key(case)] if _compatible(case, control)]
        available = [control for control in all_candidates if control["mapping_id"] not in used]
        candidate_counts.append(len(all_candidates))
        available_counts.append(len(available))
        base = {
            "fp_mapping_id": case["mapping_id"],
            "fp_row_id": case["row_id"],
            "fp_source_chrom": case["source_chrom"],
            "fp_source_start0": case.get("source_start0", ""),
            "fp_source_end": case.get("source_end", ""),
            "fp_source_length": case["source_length"],
            "fp_old_te_relation": case["old_te_relation"],
            "fp_old_te_distance_bp": case["old_te_distance_bp"],
            "fp_old_te_distance_bin": case["old_te_distance_bin"],
            "fp_source_gc_fraction": case["source_gc_fraction"],
            "fp_source_non_acgt_count": case["source_non_acgt_count"],
            "candidate_count": len(all_candidates),
            "available_candidate_count": len(available),
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
            "gc_abs_diff": "",
            "boundary_distance_abs_diff": "",
            "control_reused": False,
            "match_status": "UNMATCHED_FP",
            "unmatched_reason": "NO_COVARIATE_CANDIDATE" if not all_candidates else "CONTROL_EXHAUSTED",
        }
        if available:
            control = min(available, key=lambda item: _candidate_key(case, item))
            used.add(control["mapping_id"])
            base.update(
                {
                    "control_mapping_id": control["mapping_id"],
                    "control_row_id": control["row_id"],
                    "control_source_chrom": control["source_chrom"],
                    "control_source_start0": control.get("source_start0", ""),
                    "control_source_end": control.get("source_end", ""),
                    "control_source_length": control["source_length"],
                    "control_old_te_relation": control["old_te_relation"],
                    "control_old_te_distance_bp": control["old_te_distance_bp"],
                    "control_old_te_distance_bin": control["old_te_distance_bin"],
                    "control_source_gc_fraction": control["source_gc_fraction"],
                    "control_source_non_acgt_count": control["source_non_acgt_count"],
                    "gc_abs_diff": abs(float(case["source_gc_fraction"]) - float(control["source_gc_fraction"])),
                    "boundary_distance_abs_diff": abs(int(case["old_te_distance_bp"] or 0) - int(control["old_te_distance_bp"] or 0)),
                    "match_status": "MATCHED_TN",
                    "unmatched_reason": "",
                }
            )
        selected.append(base)
    by_relation: Dict[str, dict] = {}
    for relation in sorted({row["fp_old_te_relation"] for row in selected}):
        subset = [row for row in selected if row["fp_old_te_relation"] == relation]
        by_relation[relation] = {
            "fp_n": len(subset),
            "matched_n": sum(row["match_status"] == "MATCHED_TN" for row in subset),
            "unmatched_n": sum(row["match_status"] == "UNMATCHED_FP" for row in subset),
            "unmatched_no_covariate_candidate_n": sum(row["unmatched_reason"] == "NO_COVARIATE_CANDIDATE" for row in subset),
            "unmatched_control_exhausted_n": sum(row["unmatched_reason"] == "CONTROL_EXHAUSTED" for row in subset),
        }
    summary = {
        "status": "NO_REUSE_MATCHING_COMPLETED",
        "qualified_case_fp_n": len(cases),
        "qualified_control_tn_n": len(controls),
        "matched_pairs_n": sum(row["match_status"] == "MATCHED_TN" for row in selected),
        "unmatched_fp_n": sum(row["match_status"] == "UNMATCHED_FP" for row in selected),
        "unique_controls_used_n": len(used),
        "control_reuse_allowed": False,
        "max_control_reuse": 1 if used else 0,
        "control_reuse_histogram": {"1": len(used)} if used else {},
        "candidate_count": {
            "min": min(candidate_counts, default=0),
            "median": sorted(candidate_counts)[len(candidate_counts) // 2] if candidate_counts else 0,
            "max": max(candidate_counts, default=0),
            "available_min": min(available_counts, default=0),
        },
        "by_old_te_relation": by_relation,
        "matching_rule": {
            "same_source_chromosome": True,
            "exact_source_length": True,
            "same_old_te_relation": True,
            "exact_source_non_acgt_count": True,
            "same_old_te_distance_bin": True,
            "gc_tolerance_fraction": GC_TOLERANCE,
            "selection_order": "absolute GC fraction, absolute old-TE-boundary distance, row_id",
            "control_reuse_allowed": False,
            "algorithm": "deterministic greedy assignment in ascending FP row_id; not a maximum-cardinality matching",
            "seed": 42,
        },
        "selection_excludes": [
            "model score or probability",
            "new annotation support",
            "target annotation",
            "target sequence identity",
        ],
    }
    return selected, summary


def write_match_table(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty match table")
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--allowed-chromosomes", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_qualification(args.qualification, args.allowed_chromosomes)
    selected, summary = select_no_reuse(rows)
    args.output.mkdir(parents=True, exist_ok=False)
    write_match_table(args.output / "matched_controls_no_reuse.tsv", selected)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "STATUS").write_text(summary["status"] + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
