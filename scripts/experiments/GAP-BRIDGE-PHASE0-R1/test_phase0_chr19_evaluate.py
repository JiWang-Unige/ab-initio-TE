#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_chr19_evaluate", HERE / "phase0_chr19_evaluate.py")
assert SPEC and SPEC.loader
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)


class Chr19EvaluatorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.lock = self.root / "feature_lock.json"
        self.labeled = self.root / "labeled.tsv"
        self.output = self.root / "evaluation.json"
        self.purge = self.root / "purge-membership.tsv"
        self._write_lock()
        self._write_labeled()
        self._write_purge()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_lock(self, coefficient_delta: float = 0.0) -> None:
        groups = {}
        for index, (name, fields) in enumerate(evaluate.FEATURE_GROUPS.items()):
            size = len(fields)
            groups[name] = {
                "features": fields,
                "regularization_c": 1.0,
                "imputation_median": [0.0] * size,
                "standardization_mean": [0.0] * size,
                "standardization_scale": [1.0] * size,
                "coefficient": [0.0] * size,
                "intercept": coefficient_delta if name == "G2_FULL_LIBRARY_FREE" else 0.0,
                "validation": {
                    "average_precision": 0.5 + index / 100,
                    "operating_threshold": {"status": "PASS", "threshold": 0.5},
                },
            }
        groups["G2_FULL_LIBRARY_FREE"]["coefficient"][0] = 1.0
        self.lock.write_text(json.dumps({
            "schema": "gap_bridge_phase0_feature_lock_v1",
            "status": "PASS_TO_TEST",
            "selection_locked": True,
            "test_labels_read": False,
            "test_label_release_allowed": True,
            "selected_deployment_group": "G2_FULL_LIBRARY_FREE",
            "baselines": {
                "simple_gap_length_cutoff": {
                    "status": "PASS", "maximum_gap_length": 4,
                    "validation_average_precision": 0.51,
                },
                "A0_consensus_alignment": {
                    "status": "ASSET_BLOCKED_PRETEST",
                    "reason": "no frozen per-candidate alignment evidence",
                },
            },
            "groups": groups,
        }), encoding="utf-8")

    def _write_labeled(self, seqid: str = "chr19", include_unknown: bool = False) -> None:
        fields = [
            "candidate_id", "seqid", "gap_start", "gap_length", "eligible_main", "clean_target",
            "comparator_relation", "gap_comparator_positive_bp", "gap_comparator_negative_bp",
            "gap_comparator_unknown_bp",
        ] + list(evaluate.FEATURE_GROUPS["G2_FULL_LIBRARY_FREE"])
        with self.labeled.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            values = [(1, evaluate.BRIDGE, "0"), (0, evaluate.SEPARATION, "0"), (1, evaluate.BRIDGE, "0")]
            if include_unknown:
                values.append(("", evaluate.AMBIGUOUS, "2"))
            for index, (target, relation, unknown_bp) in enumerate(values):
                row = {field: "1" for field in fields}
                row.update({
                    "candidate_id": f"chr19:{index * 1_000_000}-{index * 1_000_000 + 4}",
                    "seqid": seqid, "gap_start": str(index * 1_000_000), "gap_length": "4",
                    "eligible_main": "1", "clean_target": target if target == "" else str(target), "comparator_relation": relation,
                    "gap_comparator_positive_bp": "4" if target == 1 else "0",
                    "gap_comparator_negative_bp": "0" if target == 1 else "4", "gap_comparator_unknown_bp": unknown_bp,
                })
                writer.writerow(row)

    def _write_purge(self) -> None:
        with self.labeled.open(newline="", encoding="utf-8") as handle:
            candidate_ids = [
                row["candidate_id"] for row in csv.DictReader(handle, delimiter="\t")
            ]
        with self.purge.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["candidate_id", "purged"], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for index, candidate_id in enumerate(candidate_ids):
                writer.writerow({"candidate_id": candidate_id, "purged": str(index % 2)})

    def test_rejects_unlocked_or_test_consumed_lock(self) -> None:
        value = json.loads(self.lock.read_text(encoding="utf-8"))
        value["status"] = "NO_VALIDATION_OPERATING_POINT"
        self.lock.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "status=PASS_TO_TEST"):
            evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)

        value["status"] = "PASS_TO_TEST"
        value["selection_locked"] = False
        self.lock.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "selection_locked"):
            evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)

        value["selection_locked"] = True
        value["test_labels_read"] = True
        self.lock.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "test_labels_read"):
            evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)

        value["test_labels_read"] = False
        value["status"] = "PASS_TO_TEST"
        value["test_label_release_allowed"] = False
        self.lock.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "test_label_release_allowed"):
            evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)

    def test_unknown_candidates_are_excluded_and_unsafe_group_reports_ranking_only(self) -> None:
        self._write_labeled(include_unknown=True)
        self._write_purge()
        value = json.loads(self.lock.read_text(encoding="utf-8"))
        value["groups"]["G0_LENGTH"]["validation"]["operating_threshold"] = {
            "status": "NO_NONEMPTY_THRESHOLD", "threshold": None,
        }
        self.lock.write_text(json.dumps(value), encoding="utf-8")
        result = evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)
        self.assertEqual(result["excluded_unknown_candidates"], 1)
        self.assertEqual(result["candidate_count"], 3)
        self.assertNotIn("selected_candidates", result["group_metrics"]["G0_LENGTH"]["candidate_metrics"])
        self.assertIsNone(result["group_metrics"]["G0_LENGTH"]["added_bp_metrics"])

    def test_applies_locked_parameters_without_refit_and_reports_unavailable_full_gate(self) -> None:
        result = evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)
        self.assertEqual(result["status"], "PARTIAL_EVALUATION_UNAVAILABLE_ASSETS")
        self.assertEqual(result["comparison"]["best_ranking_baseline"], "SIMPLE_LENGTH")
        self.assertEqual(result["comparison"]["best_operating_baseline"], "SIMPLE_LENGTH")
        self.assertEqual(result["prospective_gate"]["status"], "NOT_EVALUATED")
        self.assertIn("fragments_per_truth", result["prospective_gate"]["unavailable_metrics"])
        self.assertEqual(result["bootstrap_ap_difference"]["unit"], "1Mb block")
        self.assertEqual(len(result["block_summaries"]), 3)
        self.assertEqual(result["purged_challenge"]["purged_candidates"], 1)
        self.assertEqual(result["purged_challenge"]["unpurged_challenge_candidates"], 2)
        self.assertFalse(result["a0_consensus_alignment"]["superiority_claim_allowed"])

        g2 = result["group_metrics"]["G2_FULL_LIBRARY_FREE"]
        self.assertEqual(g2["candidate_metrics"]["threshold"], 0.5)
        self.assertEqual(g2["added_bp_metrics"]["added_bp_recall"], 1.0)
        self.assertEqual(result["group_metrics"]["SIMPLE_LENGTH"]["candidate_metrics"]["threshold"], 4)
        self.assertEqual(result["group_metrics"]["SIMPLE_LENGTH"]["added_bp_metrics"]["threshold"], 4)
        self.assertIsNone(result["group_metrics"]["SIMPLE_LENGTH"]["candidate_metrics"]["brier"])
        self.assertEqual(
            result["purged_challenge"]["ranking_metrics_only"]["G2_FULL_LIBRARY_FREE"]["clean_candidates"],
            2,
        )

        self._write_lock(coefficient_delta=1.0)
        shifted = evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)
        self.assertNotEqual(
            shifted["group_metrics"]["G2_FULL_LIBRARY_FREE"]["candidate_metrics"]["brier"],
            g2["candidate_metrics"]["brier"],
        )

    def test_rejects_non_chr19_rows_and_never_projects_labels(self) -> None:
        self._write_labeled(seqid="chr13")
        with self.assertRaisesRegex(ValueError, "non-chr19"):
            evaluate.evaluate_chr19(self.lock, self.labeled, self.purge, self.output)
        self.assertNotIn("project", evaluate.__dict__)


if __name__ == "__main__":
    unittest.main()
