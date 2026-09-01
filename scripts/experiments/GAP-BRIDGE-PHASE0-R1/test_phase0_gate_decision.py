#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_gate_decision", HERE / "phase0_gate_decision.py")
assert SPEC is not None and SPEC.loader is not None
decision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decision)


def passing_candidate() -> dict[str, object]:
    return {
        "status": "PARTIAL_EVALUATION_UNAVAILABLE_ASSETS",
        "prospective_denominator": {
            "status": "PASS",
            "eligible_clean_bridge_candidates": 1200,
            "eligible_clean_separation_candidates": 1300,
            "eligible_bridge_longer_than_5bp": 250,
            "independent_1mb_blocks_with_both_clean_classes": 25,
        },
        "comparison": {
            "best_ranking_baseline": "G0_LENGTH",
            "best_operating_baseline": "G1_GEOMETRY_LOGITS",
            "g2_minus_best_baseline_average_precision": 0.06,
        },
        "bootstrap_ap_difference": {"status": "PASS", "lower_95": 0.01},
        "purged_challenge": {
            "status": "EVALUATED",
            "g2_minus_best_baseline_average_precision": 0.02,
        },
        "group_metrics": {
            "G2_FULL_LIBRARY_FREE": {"candidate_metrics": {"average_precision": 0.80}},
            "G1_GEOMETRY_LOGITS": {"candidate_metrics": {"average_precision": 0.76}},
        },
    }


def passing_mask() -> dict[str, object]:
    return {
        "status": "PARTIAL_GATE_NO_GENE_SAFETY",
        "all_original_p3_positive_bases_retained": True,
        "metrics": {
            "added_bp": {
                "precision": 0.98,
                "added_positive_bp": 125,
                "added_negative_bp": 15,
                "precision_bootstrap": {"status": "PASS", "lower_95": 0.96},
            },
            "internal_gap_recovery": {
                "internal_gap_positive_bp_recall": 0.25,
                "internal_gap_gt5_positive_bp_recall": 0.11,
            },
            "fragmentation": {
                "raw": {"split_rate": 0.40, "fragments_per_truth": 1.40, "missed_rate": 0.10},
                "refined": {"split_rate": 0.30, "fragments_per_truth": 1.10, "missed_rate": 0.10},
            },
            "whole_mask": {
                "raw": {"precision": 0.9900, "f1": 0.8000},
                "refined": {"precision": 0.9895, "f1": 0.8100},
            },
            "baseline": {
                "status": "EVALUATED",
                "best_ranking_baseline": "G0_LENGTH",
                "best_operating_baseline": "G1_GEOMETRY_LOGITS",
                "added_bp": {"added_positive_bp": 100, "added_negative_bp": 20},
                "fragmentation": {"refined": {"split_rate": 0.35}},
            },
        },
    }


def passing_gene() -> dict[str, object]:
    return {
        "status": "PASS",
        "intersections": {"splice_core_pm2": {"added_comparator_negative_bp": 0}},
        "callable_cds_negative_fill_rate": 5e-6,
        "gene_overlap_added_bp_precision": 0.999,
        "max_single_annotated_cds_negative_bp": 10,
    }


class Phase0GateDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.candidate = self.root / "candidate.json"
        self.mask = self.root / "mask.json"
        self.gene = self.root / "gene.json"
        self.output = self.root / "decision.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_decision(
        self, candidate: dict[str, object] | None = None,
        mask: dict[str, object] | None = None, gene: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.candidate.write_text(json.dumps(candidate or passing_candidate()), encoding="utf-8")
        self.mask.write_text(json.dumps(mask or passing_mask()), encoding="utf-8")
        self.gene.write_text(json.dumps(gene or passing_gene()), encoding="utf-8")
        return decision.decide_phase0(self.candidate, self.mask, self.gene, self.output)

    def test_all_eight_gates_and_frozen_operating_comparison_pass(self) -> None:
        result = self.run_decision()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["pass_count"], 8)
        self.assertEqual(result["relative_operating_comparison"]["status"], "PASS")
        self.assertEqual(
            result["relative_operating_comparison"]["best_operating_baseline"],
            "G1_GEOMETRY_LOGITS",
        )
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), result)

    def test_known_gate_failure_makes_overall_fail(self) -> None:
        mask = passing_mask()
        mask["metrics"]["added_bp"]["precision"] = 0.96
        result = self.run_decision(mask=mask)
        self.assertEqual(result["gates"]["4_added_bp_precision"]["status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_explicit_insufficient_denominator_is_fail(self) -> None:
        candidate = passing_candidate()
        candidate["prospective_denominator"]["status"] = "TEST_DENOMINATOR_INSUFFICIENT"
        candidate["prospective_denominator"]["eligible_clean_bridge_candidates"] = 999
        result = self.run_decision(candidate=candidate)
        self.assertEqual(result["gates"]["1_test_denominator"]["status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_fixed_operating_comparison_failure_closes_route(self) -> None:
        mask = passing_mask()
        mask["metrics"]["added_bp"]["added_positive_bp"] = 110
        mask["metrics"]["added_bp"]["added_negative_bp"] = 19
        mask["metrics"]["baseline"]["fragmentation"]["refined"]["split_rate"] = 0.15
        result = self.run_decision(mask=mask)
        self.assertEqual(result["pass_count"], 8)
        self.assertEqual(result["relative_operating_comparison"]["status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_missing_or_not_evaluated_required_evidence_blocks_pass(self) -> None:
        candidate = passing_candidate()
        candidate["bootstrap_ap_difference"] = {"status": "NOT_EVALUATED", "lower_95": None}
        gene = passing_gene()
        del gene["max_single_annotated_cds_negative_bp"]
        result = self.run_decision(candidate=candidate, gene=gene)
        self.assertEqual(result["gates"]["2_candidate_information_gain"]["status"], "BLOCKED")
        self.assertEqual(result["gates"]["8_gene_feature_safety"]["status"], "BLOCKED")
        self.assertEqual(result["status"], "BLOCKED")

    def test_no_frozen_safe_baseline_is_reported_not_selected_on_chr19(self) -> None:
        candidate = passing_candidate()
        candidate["comparison"]["best_operating_baseline"] = None
        mask = passing_mask()
        mask["metrics"]["baseline"] = {
            "status": "NO_BASELINE_OPERATING_POINT",
            "best_ranking_baseline": "G0_LENGTH",
            "best_operating_baseline": None,
            "reason": "no frozen PASS precision-floor threshold",
        }
        result = self.run_decision(candidate=candidate, mask=mask)
        self.assertEqual(result["pass_count"], 8)
        self.assertEqual(result["relative_operating_comparison"]["status"], "BASELINE_UNAVAILABLE")
        self.assertEqual(result["status"], "BLOCKED")

    def test_gene_audit_not_evaluable_blocks_instead_of_failing_safety(self) -> None:
        gene = passing_gene()
        gene["status"] = "NOT_EVALUATED"
        result = self.run_decision(gene=gene)
        self.assertEqual(result["gates"]["8_gene_feature_safety"]["status"], "BLOCKED")
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
