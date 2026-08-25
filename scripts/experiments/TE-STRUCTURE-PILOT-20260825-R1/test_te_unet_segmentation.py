#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


MODULE = Path(__file__).with_name("te_unet_segmentation.py")
SPEC = importlib.util.spec_from_file_location("te_unet_segmentation", MODULE)
te_unet = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(te_unet)


class FourStateLabelTest(unittest.TestCase):
    def test_known_run_has_two_boundaries(self):
        self.assertEqual(te_unet.four_state_labels([0, 1, 1, 1, 0]), [0, 2, 1, 3, 0])

    def test_window_and_unknown_edges_are_not_boundaries(self):
        self.assertEqual(te_unet.four_state_labels([1, 1, 0, -1, 1, 1]), [1, 3, 0, -100, 1, 1])

    def test_separate_runs_remain_separate(self):
        self.assertEqual(te_unet.four_state_labels([0, 1, 0, 1, 1, 0]), [0, 3, 0, 2, 3, 0])


if __name__ == "__main__":
    unittest.main()
