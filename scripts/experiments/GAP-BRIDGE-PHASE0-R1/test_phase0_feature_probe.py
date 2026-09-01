#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_feature_probe", HERE / "phase0_feature_probe.py")
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class FeatureContractTest(unittest.TestCase):
    def test_feature_groups_are_strictly_nested_and_label_free(self):
        self.assertEqual(probe.G0, ["log1p_gap_length"])
        self.assertTrue(set(probe.G0) < set(probe.G1) < set(probe.G2))
        forbidden = {"clean_target", "comparator_relation", "gap_comparator_positive_bp"}
        self.assertFalse(forbidden & set(probe.G2))

    def test_feature_values_apply_only_frozen_scalar_transforms(self):
        row = {field: "1" for field in probe.G2}
        row.update({
            "gap_length": "9", "left_run_length": "99", "right_run_length": "199",
            "span_length": "307", "nearest_window_seam_abs_distance": "8192",
            "gap_max_homopolymer": "4", "microhomology_bp": "2",
        })
        values = probe.feature_values(row)
        self.assertEqual(set(values), set(probe.G2))
        self.assertAlmostEqual(values["log1p_gap_length"], np.log1p(9))
        self.assertAlmostEqual(values["log1p_microhomology_bp"], np.log1p(2))


class ThresholdContractTest(unittest.TestCase):
    def test_most_permissive_precision_passing_threshold_respects_score_ties(self):
        result = probe.choose_added_bp_threshold(
            np.asarray([0.9, 0.8, 0.8, 0.7]),
            np.asarray([10, 9, 0, 10]),
            np.asarray([0, 0, 1, 5]),
            0.95,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["threshold"], 0.8)
        self.assertEqual(result["selected_candidates"], 3)
        self.assertEqual(result["added_bp_precision"], 0.95)

    def test_no_nonempty_precision_passing_threshold_abstains(self):
        result = probe.choose_added_bp_threshold(
            np.asarray([0.9, 0.8]), np.asarray([0, 1]), np.asarray([10, 10]), 0.98,
        )
        self.assertEqual(result["status"], "NO_NONEMPTY_THRESHOLD")
        self.assertEqual(result["selected_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
