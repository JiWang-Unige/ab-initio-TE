#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("infer_bridge", HERE / "infer_fasta_to_bed.py")
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class InferenceBridgeTests(unittest.TestCase):
    def test_all_contigs_and_tail_are_covered_without_overlap(self):
        lengths = [1, 8192, 8193, 16384, 16385]
        self.assertEqual([len(MOD.window_specs(x)) for x in lengths], [1, 1, 2, 2, 3])
        for length in lengths:
            audit = MOD.coverage_audit(length, MOD.window_specs(length))
            self.assertEqual(audit["covered_bp"], length)
            self.assertEqual(audit["missing_bp"], 0)
            self.assertEqual(audit["overlap_bp"], 0)
            self.assertTrue(audit["no_missing_bp"])
            self.assertTrue(audit["no_overlap"])

    def test_expected_count_includes_short_and_tail_windows(self):
        self.assertEqual(MOD.expected_window_count({"short": 1, "exact": 8192, "tail": 8193}), 4)

    def test_threshold_runs_are_zero_based_half_open(self):
        self.assertEqual(MOD.threshold_runs([0.1, 0.5, 0.9, 0.2]), [(1, 3)])
        self.assertEqual(MOD.threshold_runs([0.9, 0.9]), [(0, 2)])
        self.assertEqual(MOD.threshold_runs([0.1, 0.2]), [])

    def test_frozen_geometry_rejects_tuning(self):
        with self.assertRaises(ValueError):
            MOD.window_specs(8192, 4096, 4096)
        with self.assertRaises(ValueError):
            MOD.coverage_audit(10, [(0, 5), (6, 10)])


if __name__ == "__main__":
    unittest.main()
