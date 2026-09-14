#!/usr/bin/env python3
"""Focused tests for denominator and support-layer aggregation."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from summarize_annotation_overlap import CATEGORIES, LAYERS, aggregate


def _write_fixture(path: Path) -> None:
    fields = ["state", "source_chrom", "mapping_status"]
    fields.extend(
        f"{category}_{layer}_supported"
        for category in CATEGORIES
        for layer in LAYERS
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        base = {field: "" for field in fields}
        for state in ("TP", "FP", "FN", "TN"):
            row = dict(base, state=state, source_chrom="chr2", mapping_status="FAILED")
            writer.writerow(row)
        row = dict(base, state="TP", source_chrom="chr2", mapping_status="UNIQUE_RECIPROCAL_SAME_LENGTH")
        for category in CATEGORIES:
            for layer in LAYERS:
                row[f"{category}_{layer}_supported"] = "True" if category == "TE" else "False"
        writer.writerow(row)
        row = dict(base, state="FP", source_chrom="chr2", mapping_status="UNIQUE_RECIPROCAL_SAME_LENGTH")
        for category in CATEGORIES:
            for layer in LAYERS:
                row[f"{category}_{layer}_supported"] = "False"
        writer.writerow(row)


def test_full_denominator_and_qualified_support() -> None:
    with tempfile.TemporaryDirectory() as directory:
        table = Path(directory) / "fixture.tsv"
        _write_fixture(table)
        result = aggregate(table)
    assert result["source_interval_count"] == 6
    assert result["source_state_counts"] == {"TP": 2, "FP": 2, "FN": 1, "TN": 1}
    assert result["qualified_count_by_state"] == {"TP": 1, "FP": 1}
    te_any = result["support_by_category_layer_state"]["TE"]["any"]
    assert te_any["TP"]["source_n"] == 2
    assert te_any["TP"]["qualified_n"] == 1
    assert te_any["TP"]["supported_n"] == 1
    assert te_any["FP"]["supported_n"] == 0
    assert te_any["ALL_QUALIFIED"]["supported_n"] == 1


if __name__ == "__main__":
    test_full_denominator_and_qualified_support()
    print("summarize_annotation_overlap contract tests: PASS")
