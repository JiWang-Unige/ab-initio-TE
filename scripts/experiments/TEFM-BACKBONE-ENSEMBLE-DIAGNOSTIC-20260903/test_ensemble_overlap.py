#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ensemble_overlap", HERE / "ensemble_overlap.py")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class EnsembleOverlapTest(unittest.TestCase):
    def test_complete_gap_bridge_requires_full_donor_support(self):
        anchor = np.asarray([1, 1, 0, 0, 1, 1], dtype=bool)
        full = np.asarray([0, 0, 1, 1, 0, 0], dtype=bool)
        partial = np.asarray([0, 0, 1, 0, 0, 0], dtype=bool)
        np.testing.assert_array_equal(module.bridge_complete_gaps(anchor, full, 2), np.ones(6, dtype=bool))
        np.testing.assert_array_equal(module.bridge_complete_gaps(anchor, partial, 2), anchor)

    def test_internal_gap_mask_excludes_terminal_false_negatives(self):
        truth = np.asarray([1, 1, 1, 1, 1, 1], dtype=bool)
        prediction = np.asarray([0, 1, 0, 0, 1, 0], dtype=bool)
        np.testing.assert_array_equal(
            module.internal_gap_mask(truth, prediction),
            np.asarray([0, 0, 1, 1, 0, 0], dtype=bool),
        )


if __name__ == "__main__":
    unittest.main()
