#!/usr/bin/env python3
"""Focused tests for post-selection support joining."""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from summarize_matched_support import CATEGORIES, LAYERS, run


def _write_support(path: Path) -> None:
    fields = ["mapping_id"]
    fields.extend(
        field
        for category in CATEGORIES
        for layer in LAYERS
        for field in (f"{category}_{layer}_supported", f"{category}_{layer}_overlap_bp")
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for mapping_id, te_any in (("fp1", "True"), ("fp2", "False"), ("tn1", "False")):
            row = {field: "0" for field in fields}
            row["mapping_id"] = mapping_id
            for category in CATEGORIES:
                for layer in LAYERS:
                    row[f"{category}_{layer}_supported"] = (
                        te_any if category == "TE" and layer == "any" else "False"
                    )
            writer.writerow(row)


def _write_matches(path: Path) -> None:
    fields = [
        "fp_mapping_id",
        "control_mapping_id",
        "match_status",
        "fp_old_te_relation",
        "control_reused",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow(
            {
                "fp_mapping_id": "fp1",
                "control_mapping_id": "tn1",
                "match_status": "MATCHED_TN",
                "fp_old_te_relation": "ADJACENT",
                "control_reused": "False",
            }
        )
        writer.writerow(
            {
                "fp_mapping_id": "fp2",
                "control_mapping_id": "",
                "match_status": "UNMATCHED_FP",
                "fp_old_te_relation": "ISOLATED",
                "control_reused": "False",
            }
        )


def _write_qualification(path: Path) -> None:
    fields = [
        "state",
        "eligible_for_matching",
        "chain_stratum",
        "sequence_status",
        "mismatch_bp",
    ]
    rows = [
        ("TP", "True", "SINGLE_BLOCK", "SEQUENCE_EXACT", "0"),
        ("FP", "True", "SINGLE_BLOCK", "SEQUENCE_EXACT", "0"),
        ("FN", "False", "NOT_MAPPING_QUALIFIED", "NOT_MAPPING_QUALIFIED", ""),
        ("TN", "True", "SINGLE_BLOCK", "SEQUENCE_MISMATCH", "2"),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for state, eligible, chain, sequence, mismatch in rows:
            writer.writerow(
                {
                    "state": state,
                    "eligible_for_matching": eligible,
                    "chain_stratum": chain,
                    "sequence_status": sequence,
                    "mismatch_bp": mismatch,
                }
            )


def test_post_selection_join() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        matches = root / "matches.tsv"
        support = root / "support.tsv"
        summary = root / "qualification.json"
        qualification = root / "qualification.tsv"
        output = root / "out"
        _write_matches(matches)
        _write_support(support)
        _write_qualification(qualification)
        summary.write_text(
            json.dumps(
                {
                    "source_interval_count": 6,
                    "source_state_counts": {"TP": 2, "FP": 2, "FN": 1, "TN": 1},
                    "qualified_mapping_count": 2,
                    "qualified_count_by_state": {"FP": 2, "TN": 0},
                }
            ),
            encoding="utf-8",
        )
        result = run(
            type(
                "Args",
                (),
                {
                    "matched_controls": matches,
                    "overlap_table": support,
                    "qualification_summary": summary,
                    "qualification_table": qualification,
                    "output": output,
                },
            )()
        )
    assert result["matched_pair_n"] == 1
    assert result["unmatched_fp_n"] == 1
    te_any = result["support_by_category_layer"]["TE"]["any"]
    assert te_any["fp_supported_n"] == 1
    assert te_any["control_supported_n"] == 0
    assert te_any["fp_minus_control_fraction"] == 1.0


if __name__ == "__main__":
    test_post_selection_join()
    print("summarize_matched_support contract tests: PASS")
