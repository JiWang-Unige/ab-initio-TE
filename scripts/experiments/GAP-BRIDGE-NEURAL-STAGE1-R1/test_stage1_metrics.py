#!/usr/bin/env python3
"""Small-array tests for the frozen Stage 1 metric primitives."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest


try:
    import numpy as np
except ModuleNotFoundError:
    np = None


ROOT = pathlib.Path(__file__).resolve().parent


def load_metrics_module():
    spec = importlib.util.spec_from_file_location("stage1_metrics", ROOT / "stage1_metrics.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load stage1_metrics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(np is not None, "NumPy is unavailable in this interpreter")
class Stage1MetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_metrics_module()

    def test_weighted_ranking_groups_exact_ties_and_returns_normalized_ap(self):
        scores = np.asarray([0.5, 0.9, 0.9, -0.1])
        positive = np.asarray([3.0, 2.0, 1.0, 0.0])
        negative = np.asarray([0.0, 0.0, 2.0, 4.0])
        result = self.m.weighted_action_metrics(scores, positive, negative)
        self.assertAlmostEqual(result["ap"], 0.675, places=12)
        self.assertAlmostEqual(result["prevalence"], 6.0 / 12.0, places=12)
        self.assertAlmostEqual(result["normalized_ap"], 1.35, places=12)
        self.assertAlmostEqual(result["auroc"], 27.0 / 36.0, places=12)

        self.assertEqual(
            self.m.weighted_action_auroc([1.0, 0.0], [1.0, 0.0], [0.0, 1.0]),
            1.0,
        )

        permutation = np.asarray([2, 0, 3, 1])
        permuted = self.m.weighted_action_metrics(
            scores[permutation], positive[permutation], negative[permutation],
        )
        self.assertEqual(result, permuted)

    def test_risk_metrics_use_pseudo_base_mass_and_six_strata(self):
        p = np.asarray([0.25] * 6)
        positive = np.asarray([3.0] * 6)
        negative = np.asarray([1.0] * 6)
        strata = self.m.LENGTH_STRATA
        expected_brier = (1.0 * (1.0 - 0.25) ** 2 + 3.0 * 0.25**2) / 4.0
        self.assertAlmostEqual(self.m.pseudo_base_brier(p, positive, negative), expected_brier, places=12)
        self.assertAlmostEqual(self.m.natural_candidate_brier(p, positive, negative), (0.25 - 0.25) ** 2, places=12)
        self.assertAlmostEqual(self.m.six_stratum_macro_brier(p, positive, negative, strata), expected_brier, places=12)
        self.assertAlmostEqual(self.m.pseudo_base_log_loss(p, positive, negative), -(np.log(0.25) + 3.0 * np.log(0.75)) / 4.0, places=12)
        self.assertEqual(self.m.pseudo_base_log_loss([0.0], [4.0], [0.0]), 0.0)

    def test_platt_is_monotone_and_boundary_slope_zero_is_legal(self):
        if self.m.fit_monotone_platt([0.0, 1.0], [1.0, 1.0], [0.0, 2.0])["status"] == "SCIPY_UNAVAILABLE":
            self.skipTest("SciPy is unavailable in this interpreter")
        fit = self.m.fit_monotone_platt(
            np.asarray([-2.0, -1.0, 1.0, 2.0]),
            np.asarray([9.0, 8.0, 2.0, 1.0]),
            np.asarray([1.0, 2.0, 8.0, 9.0]),
        )
        self.assertTrue(fit["success"], fit["message"])
        self.assertGreaterEqual(fit["slope"], 0.0)
        probabilities = self.m.apply_monotone_platt(np.asarray([-2.0, 0.0, 2.0]), fit)
        self.assertTrue(np.all(np.diff(probabilities) >= 0))

        boundary = self.m.fit_monotone_platt(
            np.asarray([-2.0, 0.0, 2.0]),
            np.asarray([10.0, 10.0, 10.0]),
            np.asarray([0.0, 0.0, 0.0]),
        )
        self.assertTrue(boundary["success"], boundary["message"])
        self.assertAlmostEqual(boundary["slope"], 0.0, places=10)

    def test_equal_mass_ece_splits_candidate_and_tie_group_without_row_order(self):
        p = np.asarray([0.1, 0.1, 0.8, 0.9])
        positive = np.asarray([6.0, 4.0, 7.0, 3.0])
        negative = np.asarray([4.0, 6.0, 3.0, 7.0])
        result = self.m.equal_bp_mass_ece(p, positive, negative)
        self.assertEqual(len(result["bin_mass"]), 10)
        self.assertAlmostEqual(float(result["bin_mass"].sum()), 40.0, places=12)
        np.testing.assert_allclose(result["bin_mass"][:9], np.full(9, 4.0), atol=1e-12)
        self.assertAlmostEqual(float(result["bin_mass"][9]), 4.0, places=12)
        permutation = np.asarray([3, 1, 0, 2])
        permuted = self.m.equal_bp_mass_ece(p[permutation], positive[permutation], negative[permutation])
        np.testing.assert_allclose(result["bin_mass"], permuted["bin_mass"])
        np.testing.assert_allclose(result["bin_observed_negative_mass"], permuted["bin_observed_negative_mass"])
        np.testing.assert_allclose(result["bin_predicted_negative_mass"], permuted["bin_predicted_negative_mass"])
        self.assertAlmostEqual(result["citl"], -1.0 / 40.0, places=12)

    def test_budget_frontier_selects_complete_risk_ties_and_counts_unknown_as_negative(self):
        result = self.m.frozen_budget_frontier(
            p_neg=np.asarray([0.01, 0.01, 0.02, 0.03]),
            positive_bp=np.asarray([100.0, 100.0, 100.0, 100.0]),
            negative_bp=np.asarray([0.0, 0.0, 1.0, 0.0]),
            unknown_bp=np.asarray([0.0, 10.0, 0.0, 0.0]),
            callable_bp=1_000_000.0,
        )
        np.testing.assert_array_equal(result["selected_mask"], np.asarray([True, True, False, False]))
        self.assertEqual(result["threshold"], 0.01)
        self.assertEqual(result["selected_unknown_bp"], 10.0)
        self.assertEqual(result["worst_case_negative_bp"], 10.0)

    def test_utility_gate_is_registered_or(self):
        positive = self.m.utility_gate(11_000.0, 10_000.0, 90.0, 100.0)
        self.assertTrue(positive["positive_bp_pass"])
        self.assertTrue(positive["passed"])
        edges = self.m.utility_gate(10_100.0, 10_000.0, 220.0, 100.0)
        self.assertFalse(edges["positive_bp_pass"])
        self.assertTrue(edges["split_edge_pass"])
        self.assertTrue(edges["passed"])

    def test_absolute_blocks_and_paired_bootstrap_keep_zero_candidate_bins(self):
        self.assertEqual(self.m.absolute_mb_block_id("chr3", 999_999), "chr3:0")
        self.assertEqual(self.m.absolute_mb_block_id("chr3", 1_000_000), "chr3:1")
        blocks = self.m.absolute_mb_block_ids(["chr3", "chr3", "chr3"], [10.0, 1_000_001.0, 2_000_001.0])
        self.assertEqual(list(blocks), ["chr3:0", "chr3:1", "chr3:2"])
        result = self.m.bootstrap_action_ap_difference(
            action_scores_a=np.asarray([0.9, 0.1]),
            action_scores_b=np.asarray([0.1, 0.9]),
            positive_bp=np.asarray([100.0, 0.0]),
            negative_bp=np.asarray([0.0, 100.0]),
            candidate_block_ids=np.asarray(["chr3:0", "chr3:2"]),
            evaluated_block_universe=np.asarray(["chr3:0", "chr3:1", "chr3:2"]),
            n_replicates=1000,
            seed=20260902,
        )
        self.assertEqual(result["n_replicates"], 1000)
        self.assertEqual(result["evaluated_block_count"], 3)
        self.assertEqual(result["zero_candidate_block_count"], 1)
        self.assertEqual(result["percentile_method"], "linear")
        self.assertEqual(result["seed"], 20260902)
        self.assertAlmostEqual(result["observed_difference"], 0.5, places=12)
        self.assertEqual(len(result["replicates"]), 1000)


if __name__ == "__main__":
    unittest.main()
