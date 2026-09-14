#!/usr/bin/env python3
"""Aggregate the already-computed descriptive annotation-overlap table.

This is a reporting pass over ``annotation_overlap.tsv``.  It keeps the full
TP/FP/FN/TN source denominator and reports support only among qualified mapped
rows.  It does not read the target annotation again, recompute F1, or turn a
failed mapping into a negative annotation observation.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Sequence


VALID_STATES = ("TP", "FP", "FN", "TN")
CATEGORIES = ("TE", "UNKNOWN", "NONTE", "UNRECOGNIZED")
LAYERS = ("any", "ge50", "ge80")
QUALIFIED_STATUS = "UNIQUE_RECIPROCAL_SAME_LENGTH"
ALLOWED_SOURCE = {"chr2", "chr3", "chr4"}


def _nested_counts() -> Dict[str, Dict[str, Counter]]:
    return {
        category: {layer: Counter() for layer in LAYERS}
        for category in CATEGORIES
    }


def _bool_field(row: Mapping[str, str], field: str, row_number: int) -> bool:
    value = row.get(field, "")
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"row {row_number}: expected True/False in {field}, got {value!r}")


def aggregate(
    table_path: Path,
    source_summary: Optional[Path] = None,
    allowed_source: Iterable[str] = ALLOWED_SOURCE,
) -> dict:
    allowed_source_set = set(allowed_source)
    all_state_counts: Counter = Counter()
    qualified_by_state: Counter = Counter()
    supported = _nested_counts()
    rows = 0
    qualified = 0
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"overlap table has no header: {table_path}")
        required = {"state", "source_chrom", "mapping_status"}
        for category in CATEGORIES:
            for layer in LAYERS:
                required.add(f"{category}_{layer}_supported")
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"overlap table missing fields: {sorted(missing)}")
        for row_number, row in enumerate(reader, 2):
            rows += 1
            state = row.get("state", "")
            if state not in VALID_STATES:
                raise ValueError(f"row {row_number}: unexpected state {state!r}")
            all_state_counts[state] += 1
            if (
                row.get("source_chrom") in allowed_source_set
                and row.get("mapping_status") == QUALIFIED_STATUS
            ):
                qualified += 1
                qualified_by_state[state] += 1
                for category in CATEGORIES:
                    for layer in LAYERS:
                        field = f"{category}_{layer}_supported"
                        if _bool_field(row, field, row_number):
                            supported[category][layer][state] += 1

    if rows != sum(all_state_counts.values()):
        raise AssertionError("source denominator does not equal state counts")
    if qualified != sum(qualified_by_state.values()):
        raise AssertionError("qualified denominator does not equal state counts")

    support_by_state: MutableMapping[str, MutableMapping[str, dict]] = defaultdict(dict)
    for category in CATEGORIES:
        for layer in LAYERS:
            per_state = {}
            for state in VALID_STATES:
                q = qualified_by_state[state]
                n = supported[category][layer][state]
                per_state[state] = {
                    "source_n": all_state_counts[state],
                    "qualified_n": q,
                    "supported_n": n,
                    "not_supported_n": q - n,
                    "support_fraction_of_qualified": (n / q) if q else None,
                }
            total_q = qualified
            total_n = sum(supported[category][layer].values())
            per_state["ALL_QUALIFIED"] = {
                "source_n": rows,
                "qualified_n": total_q,
                "supported_n": total_n,
                "not_supported_n": total_q - total_n,
                "support_fraction_of_qualified": (total_n / total_q) if total_q else None,
            }
            support_by_state[category][layer] = per_state

    result = {
        "status": "CHM13_2022_DESCRIPTIVE_OVERLAP_AGGREGATED",
        "protocol": "HG19_CHM13V2_FIXED_2022_ANNOTATION_DESCRIPTIVE_OVERLAP",
        "table": str(table_path),
        "source_interval_count": rows,
        "source_state_counts": dict(all_state_counts),
        "qualified_unique_reciprocal_same_length_count": qualified,
        "qualified_count_by_state": dict(qualified_by_state),
        "support_by_category_layer_state": support_by_state,
        "support_denominator": (
            "source_n is the full TP/FP/FN/TN denominator; support_fraction_of_qualified "
            "is descriptive and uses only qualified unique reciprocal same-length rows"
        ),
        "claim_policy": {
            "same_base_f1_computed": False,
            "fp_rescue_claim": False,
            "failed_mapping_rows_as_support": False,
            "target_annotation_reparsed": False,
            "matched_control_analysis": False,
        },
    }
    if source_summary is not None:
        summary = json.loads(source_summary.read_text(encoding="utf-8"))
        result["annotation_rows_by_category_and_chromosome"] = summary[
            "annotation_rows_by_category_and_chromosome"
        ]
        result["annotation_union_bp_by_category_and_chromosome"] = summary[
            "annotation_union_bp_by_category_and_chromosome"
        ]
        result["annotation_release"] = summary["source"]["annotation_release"]
        result["annotation_source_url"] = summary["source"]["annotation_source_url"]
        result["mapping_outcome_counts"] = summary["mapping_outcome_counts"]

    return result


def run(args: argparse.Namespace) -> dict:
    result = aggregate(args.table, args.source_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--source-summary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
