#!/usr/bin/env python3
"""Contract tests for source-only no-reuse matching."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("matching_sensitivity.py")
SPEC = importlib.util.spec_from_file_location("matching_sensitivity", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATCH)


def row(row_id: int, mapping_id: str, state: str, gc: float, relation: str = "ISOLATED") -> dict:
    return {
        "row_id": str(row_id),
        "mapping_id": mapping_id,
        "source_chrom": "chr2",
        "source_start0": str(row_id * 100),
        "source_end": str(row_id * 100 + 100),
        "source_length": "100",
        "state": state,
        "old_te_relation": relation,
        "old_te_distance_bp": "100",
        "old_te_distance_bin": "51_200",
        "source_gc_fraction": str(gc),
        "source_non_acgt_count": "0",
        "eligible_for_matching": "True",
    }


class NoReuseTests(unittest.TestCase):
    def test_control_is_consumed_and_exhaustion_is_reported(self) -> None:
        selected, summary = MATCH.select_no_reuse(
            [row(1, "fp1", "FP", 0.50), row(2, "fp2", "FP", 0.50), row(3, "tn1", "TN", 0.50)]
        )
        self.assertEqual([r["match_status"] for r in selected], ["MATCHED_TN", "UNMATCHED_FP"])
        self.assertEqual(selected[1]["unmatched_reason"], "CONTROL_EXHAUSTED")
        self.assertEqual(summary["matched_pairs_n"], 1)
        self.assertEqual(summary["unmatched_fp_n"], 1)
        self.assertEqual(summary["max_control_reuse"], 1)

    def test_incompatible_case_is_distinguished_from_exhaustion(self) -> None:
        selected, _ = MATCH.select_no_reuse([row(1, "fp1", "FP", 0.50, "ADJACENT"), row(2, "tn1", "TN", 0.50, "ISOLATED")])
        self.assertEqual(selected[0]["unmatched_reason"], "NO_COVARIATE_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
