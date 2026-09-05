import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("assess_conf", ROOT / "assess_conf.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConfAssessmentTest(unittest.TestCase):
    def test_weighted_tie_ap_matches_direct_sample_pooled(self):
        scores = np.asarray([0.5, 0.5, 0.2, 0.1], dtype=np.float32)
        truth = np.asarray([True, False, True, False])
        weights = np.asarray([2, 3, 1, 4], dtype=np.float64)
        observed = MODULE.average_precision_tied(truth, scores, weights)
        direct = MODULE.average_precision_tied(
            np.repeat(truth, weights.astype(np.int64)),
            np.repeat(scores, weights.astype(np.int64)),
        )
        self.assertAlmostEqual(observed, direct, places=15)

    def test_zero_weight_score_groups_do_not_change_ap(self):
        scores = np.asarray([0.9, 0.8, 0.7], dtype=np.float32)
        truth = np.asarray([False, True, False])
        weights = np.asarray([0, 1, 1], dtype=np.float64)
        observed = MODULE.average_precision_tied(truth, scores, weights)
        direct = MODULE.average_precision_tied(
            truth[1:], scores[1:], np.ones(2, dtype=np.float64)
        )
        self.assertAlmostEqual(observed, direct, places=15)

    def test_shared_block_pairing_cancels_identical_arms(self):
        margin = np.asarray([[0.8, -0.2], [0.4, 0.1]], dtype=np.float32)
        truth = np.asarray([[1, 0], [1, 0]], dtype=bool)
        callable_mask = np.ones_like(truth, dtype=bool)
        panel = {
            "margin": margin,
            "truth": truth,
            "callable": callable_mask,
            "slope": 1.0,
            "intercept": 0.0,
            "threshold": 0.5,
        }
        blocks = [np.asarray([0]), np.asarray([1])]
        rng = np.random.default_rng(20260905)
        draws = rng.integers(0, len(blocks), size=(25, len(blocks)))
        for draw in draws:
            multiplicity = np.bincount(draw, minlength=len(blocks))
            weights = np.zeros(2, dtype=np.float64)
            for block, count in zip(blocks, multiplicity):
                weights[block] = count
            grid_weights = np.repeat(weights, 2)
            left, _ = MODULE._metric_values(
                margin, truth, callable_mask, 1.0, 0.0, 0.5, weights=grid_weights
            )
            right, _ = MODULE._metric_values(
                margin, truth, callable_mask, 1.0, 0.0, 0.5, weights=grid_weights
            )
            self.assertEqual(left, right)

    def test_targets_are_separate_from_improvement_direction(self):
        def row(ap, f1, precision, recall):
            return {
                "bp_average_precision": ap,
                "bp_f1": f1,
                "bp_precision": precision,
                "bp_recall": recall,
                "segment_f1_iou_0_8": 0.8,
                "boundary_f1_5bp": 0.8,
                "fragments_per_truth": 1.0,
                "split_rate": 0.1,
                "missed_rate": 0.1,
            }

        l = row(0.90, 0.90, 0.90, 0.90)
        d = row(0.89, 0.81, 0.81, 0.81)
        result = MODULE._conf_decisions({
            "seed42_L": {"per_species": {"c_elegans": l}},
            "seed42_D": {"per_species": {"c_elegans": d}},
            "seed17_L": {"per_species": {"c_elegans": l}},
            "seed17_D": {"per_species": {"c_elegans": d}},
        })
        self.assertFalse(result["42"]["direction"]["pass"])
        self.assertTrue(result["42"]["d_conf_absolute_targets"]["pass"])

    def test_degenerate_ap_is_undefined(self):
        result = MODULE.average_precision_tied(
            np.asarray([False, False]),
            np.asarray([0.2, 0.1], dtype=np.float32),
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
