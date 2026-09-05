"""Synthetic CPU tests for J0-A; no genomic panel or model is accessed."""
import itertools
import json
from argparse import Namespace
import tempfile
import unittest
from pathlib import Path

import numpy as np

import diagnose_anchor_scores as diag


def tile(truth, callable_mask=None, margin=None):
    truth = np.asarray(truth, bool)
    return {"truth": truth, "callable": np.ones(truth.size, bool) if callable_mask is None else np.asarray(callable_mask, bool),
            "hard_negative": np.zeros(truth.size, bool),
            "margin": np.zeros(truth.size, np.float32) if margin is None else np.asarray(margin, np.float32)}


class ScoreTests(unittest.TestCase):
    def test_ties_are_indivisible_and_no_threshold_export(self):
        result = diag.exact_score_summary(np.array([1, 1], np.float32), [True, False])
        self.assertEqual(result["tie_groups"], 1)
        self.assertIsNone(result["constrained_max_f1"])
        self.assertIsNone(result["recall_at_precision_0_80"])
        self.assertTrue(result["constrained_reason"])
        self.assertNotIn("threshold", result)

    def test_known_feasible_tied_curve(self):
        result = diag.exact_score_summary(np.array([3, 3, 2, 2, 1], np.float32), [1, 1, 1, 0, 0])
        self.assertEqual(result["constrained_max_f1"], {"f1": 6 / 7, "precision": .75, "recall": 1.0})
        self.assertEqual(result["recall_at_precision_0_80"], 2 / 3)

    def test_no_positive_or_no_callable(self):
        for margin, truth, reason in (([], [], "no_callable_bp"), ([1, 2], [0, 0], "no_positive_bp")):
            result = diag.exact_score_summary(np.asarray(margin, np.float32), truth)
            self.assertIsNone(result["constrained_max_f1"])
            self.assertIsNone(result["recall_at_precision_0_80"])
            self.assertEqual(result["constrained_reason"], reason)

    def test_curve_matches_brute_force_reachable_thresholds(self):
        scores = np.array([3, 3, 2, 1, 1], np.float32)
        for truth in itertools.product((False, True), repeat=len(scores)):
            if not any(truth):
                continue
            actual = diag.exact_score_summary(scores, truth)
            rows = []
            for cutoff in np.unique(scores):
                predicted = scores >= cutoff
                tp = np.sum(predicted & truth)
                rows.append((tp / predicted.sum(), tp / sum(truth), 2 * tp / (sum(truth) + predicted.sum())))
            allowed = [f for p, r, f in rows if p >= .75 and r >= .75]
            recall = [r for p, r, f in rows if p >= .80]
            self.assertEqual(actual["constrained_max_f1"]["f1"] if allowed else actual["constrained_max_f1"], max(allowed) if allowed else None)
            self.assertEqual(actual["recall_at_precision_0_80"], max(recall) if recall else None)


class PartitionTests(unittest.TestCase):
    def test_three_categories_and_fully_hit(self):
        tiles = [tile([1] * 4), tile([1] * 8), tile([1] * 3)]
        result = diag.fn_partition(tiles, [np.zeros(4, bool), np.array([0, 1, 0, 0, 1, 0, 0, 0], bool), np.ones(3, bool)])
        self.assertEqual(result["complete_miss_bp"], 4)
        self.assertEqual(result["internal_gap_bp"], 2)
        self.assertEqual(result["terminal_missing_bp"], 4)
        self.assertEqual(result["fn_bp"], 10)
        self.assertEqual(result["fully_hit_runs"], 1)
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_unknown_break_is_evaluation_boundary(self):
        result = diag.fn_partition([tile([1] * 7, [1, 1, 1, 0, 1, 1, 1])], [np.array([1, 0, 0, 0, 0, 0, 1], bool)])
        self.assertEqual(result["truth_runs"], 2)
        self.assertEqual(result["internal_gap_bp"], 0)
        self.assertEqual(result["terminal_missing_bp"], 4)
        self.assertEqual(result["fn_bp"], 4)

    def test_exhaustive_fn_for_all_short_labels_and_predictions(self):
        # 0=N, 1=P, 2=U; 3^5 * 2^5 possible label/prediction combinations.
        for labels in itertools.product(range(3), repeat=5):
            labels = np.array(labels)
            t = tile(labels == 1, labels != 2)
            for prediction in itertools.product((False, True), repeat=5):
                prediction = np.array(prediction)
                result = diag.fn_partition([t], [prediction])
                expected = int(np.sum((labels == 1) & ~prediction))
                self.assertEqual(result["fn_bp"], expected)
                self.assertEqual(sum(result[k] for k in ("complete_miss_bp", "internal_gap_bp", "terminal_missing_bp")), expected)


class AlignmentTests(unittest.TestCase):
    def test_real_compact_archived_source_schema(self):
        # Compact, already-public-in-checkout metadata, not remote panel data.
        root = Path(__file__).resolve().parents[3]
        evidence = root / "docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D"
        calibration = json.loads((evidence / "calibration.json").read_text())
        expected = json.loads((evidence / "screen_metrics.json").read_text())
        args = Namespace(seed=42, model_dir=Path(calibration["model_dir"]),
                         tokenizer_dir=Path(calibration["tokenizer_dir"]),
                         model_code_dir=Path(calibration["model_code_dir"]),
                         calibration_json=Path(expected["calibration_json"]))
        diag.validate_sources(args, calibration, expected, "SCREEN")
        with self.assertRaisesRegex(ValueError, "split mismatch"):
            diag.validate_sources(args, calibration, expected, "DEV")
        with self.assertRaisesRegex(ValueError, "requires D"):
            diag.validate_sources(args, calibration, {**expected, "arm": "B0"}, "SCREEN")

    def test_point_metrics_equal_frozen_evaluator(self):
        tiles = [tile([1, 1, 0, 0, 1, 0], [1, 1, 1, 1, 0, 1], [1, -.2, .2, -.5, 2, -1])]
        calibration = {"platt_slope": .8123456789, "platt_intercept": -.173, "threshold": .48}
        observed, predictions, _, _ = diag.point_metrics(tiles, calibration)
        expected = diag.ev.evaluate_species_tiles(tiles, .8123456789, -.173, .48)
        for key in diag.POINT_KEYS:
            self.assertEqual(observed[key], expected[key])
        self.assertEqual(diag.fn_partition(tiles, predictions)["fn_bp"], expected["bp_fn"])

    def test_metric_mismatch_blocks_diagnostics(self):
        expected = dict.fromkeys(diag.POINT_KEYS, .8)
        self.assertEqual(diag.reproduce_metrics(expected, expected)["status"], "PASS")
        for value in (.800002, float("nan")):
            with self.assertRaisesRegex(ValueError, "repair inference/alignment"):
                diag.reproduce_metrics({**expected, "bp_f1": value}, expected)

    def test_cache_preserves_float32_and_checks_alignment(self):
        records = [{"tile_id": "worm:1:0", "half": half, "assembly": "ce11", "split": "SCREEN",
                    "species_code": "c_elegans", "chrom": "I", "start": half * 4096,
                    "end": (half + 1) * 4096, "sequence": "A" * 4096, "labels": "1" * 4096} for half in range(2)]
        tiles = diag.ev.assemble_tiles(diag.SPECIES, records, [np.ones(4096, np.float32), np.zeros(4096, np.float32)])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.npz"
            diag.save_cache(path, tiles)
            restored = diag.tiles_from_cache(path, records)
            self.assertEqual(restored[0]["margin"].dtype, np.float32)
            np.testing.assert_array_equal(restored[0]["margin"], tiles[0]["margin"])
            records[0]["labels"] = "0" * 4096
            with self.assertRaisesRegex(ValueError, "alignment mismatch"):
                diag.tiles_from_cache(path, records)


if __name__ == "__main__":
    unittest.main()
