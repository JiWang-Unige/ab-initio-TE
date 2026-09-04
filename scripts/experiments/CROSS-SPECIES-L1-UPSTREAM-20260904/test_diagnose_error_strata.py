import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).with_name("diagnose_error_strata.py")
SPEC = importlib.util.spec_from_file_location("diagnose_error_strata", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ErrorStrataTest(unittest.TestCase):
    def test_complete_panel_report_serializes(self):
        truth = np.zeros(8192, dtype=bool)
        truth[1:100] = True
        tile = {"truth": truth, "callable": np.ones(8192, dtype=bool),
                "margin": np.where(truth, 1.0, -1.0), "sequence": "A" * 8192,
                "chrom": "chr1", "start": 0}
        report = MODULE.panel_report([tile], {"platt_slope": 1, "platt_intercept": 0, "threshold": 0.5}, {})
        self.assertEqual(json.loads(json.dumps(report))["natural_metrics"]["f1"], 1.0)

    def test_nested_interval_starting_before_tile_is_retained(self):
        intervals = {"chr1": (((0, 100, 1), (2, 4, 4), (6, 8, 2)), (0, 2, 6))}
        mask = MODULE.class_mask_for_tile("chr1", 5, intervals, length=5)
        np.testing.assert_array_equal(mask, [1, 3, 3, 1, 1])

    def test_location_counts_include_positive_mass(self):
        truth = np.zeros(8192, dtype=bool)
        truth[1:4] = True
        tile = {"truth": truth, "callable": np.ones(8192, dtype=bool)}
        predicted = np.zeros(8192, dtype=bool)
        predicted[2:5] = True
        result = MODULE.error_location_strata([tile], [predicted])
        row = result["buckets"]["mixed_6bp_token"]
        self.assertEqual((row["positive_bp"], row["tp_bp"], row["fp_bp"], row["fn_bp"]), (3, 2, 1, 1))

    def test_raw_class_overlap_is_retained_as_mixed_bitmask(self):
        intervals = {
            "chr1": (
                ((0, 6, MODULE.BITS["LINE"]), (3, 9, MODULE.BITS["LTR"])),
                (0, 3),
            )
        }
        mask = MODULE.class_mask_for_tile("chr1", 0, intervals, length=12)
        np.testing.assert_array_equal(mask[:10], [1, 1, 1, 5, 5, 5, 4, 4, 4, 0])
        tile = {
            "truth": np.ones(12, dtype=bool),
            "callable": np.ones(12, dtype=bool),
        }
        result = MODULE.te_top_class_strata([tile], [np.ones(12, dtype=bool)], [mask])
        self.assertEqual(result["mixed_bitmasks"], [5])
        self.assertEqual(result["by_bitmask"]["5"]["label"], "mixed")
        self.assertEqual(result["by_bitmask"]["5"]["positive_bp"], 3)
        self.assertNotIn("fp_bp", result["by_bitmask"]["5"])

    def test_half_reset_does_not_join_tail_or_right_half_tokens(self):
        spans = MODULE.token_spans()
        self.assertEqual(spans[686], (4096, 4102))
        self.assertEqual(spans[682:686], [(4092, 4093), (4093, 4094), (4094, 4095), (4095, 4096)])
        self.assertEqual(spans[-4:], [(8188, 8189), (8189, 8190), (8190, 8191), (8191, 8192)])

        truth = np.zeros(8192, dtype=bool)
        callable_mask = np.ones(8192, dtype=bool)
        truth[4096] = True
        truth[4100] = False
        truth[4092] = True
        truth[8188] = True
        mixed = MODULE.mixed_6bp_token_mask(truth, callable_mask)
        self.assertTrue(np.all(mixed[4096:4102]))
        self.assertFalse(np.any(mixed[4092:4096]))
        self.assertFalse(np.any(mixed[8188:8192]))

    def test_length_strata_keep_false_positives_out_of_truth_bins(self):
        truth = np.zeros(8192, dtype=bool)
        truth[0:3] = True
        truth[100:180] = True
        truth[1000:2000] = True
        tile = {"truth": truth, "callable": np.ones(8192, dtype=bool)}
        predicted = np.zeros(8192, dtype=bool)
        predicted[0:3] = True
        predicted[100:150] = True
        predicted[7000:7010] = True
        rows = MODULE.truth_length_strata([tile], [predicted])
        self.assertEqual(rows["<80"]["positive_bp"], 3)
        self.assertEqual(rows["<80"]["recall"], 1.0)
        self.assertEqual(rows["80-499"]["positive_bp"], 80)
        self.assertEqual(rows["80-499"]["fn_bp"], 30)
        self.assertEqual(rows[">=1000"]["truth_runs"], 1)
        self.assertEqual(rows[">=1000"]["missed_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
