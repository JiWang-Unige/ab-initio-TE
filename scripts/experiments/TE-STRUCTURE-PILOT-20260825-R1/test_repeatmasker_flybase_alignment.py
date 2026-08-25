#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("d2", ROOT / "repeatmasker_flybase_alignment.py")
assert SPEC and SPEC.loader
d2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d2)


class D2AlignmentTest(unittest.TestCase):
    def test_t1_output_contains_only_recall_and_fragmentation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth = root / "flybase.bed"
            prediction = root / "repeatmasker.bed"
            lengths = root / "lengths.json"
            truth.write_text("chr2\t10\t20\nchr2\t30\t40\n", encoding="utf-8")
            prediction.write_text("chr2\t10\t20\nchr2\t29\t41\n", encoding="utf-8")
            lengths.write_text(json.dumps({"chr2": 100}), encoding="utf-8")

            result = d2.run(truth, prediction, lengths)

            self.assertEqual(result["truth_tier"], "T1")
            self.assertEqual(result["metrics"]["bp_recall"], 1.0)
            self.assertEqual(result["metrics"]["boundary_recall_5bp"], 1.0)
            self.assertEqual(result["metrics"]["boundary_recall_25bp"], 1.0)
            self.assertEqual(result["metrics"]["mean_fragments_per_truth"], 1.0)
            self.assertTrue(all("precision" not in key and "f1" not in key for key in result["metrics"]))

    def test_same_declared_lengths_reject_out_of_range_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth = root / "flybase.bed"
            prediction = root / "repeatmasker.bed"
            lengths = root / "lengths.json"
            truth.write_text("chr2\t10\t20\n", encoding="utf-8")
            prediction.write_text("chr2\t10\t101\n", encoding="utf-8")
            lengths.write_text(json.dumps({"chr2": 100}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exceeds declared contig length"):
                d2.run(truth, prediction, lengths)


if __name__ == "__main__":
    unittest.main()
