#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("length_stratified_eval.py")
SPEC = importlib.util.spec_from_file_location("length_stratified_eval", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def rows(intervals):
    return [("chr1", start, end) for start, end in intervals]


class LengthStratifiedEvalTest(unittest.TestCase):
    def test_global_matching_then_truth_length_bins_and_fragment_denominators(self):
        truth = rows([(0, 50), (100, 600), (1000, 2200)])
        prediction = rows([(0, 50), (100, 500), (520, 600), (3000, 3050)])
        result = MODULE.evaluate(truth, prediction, {"chr1": 4000}, truth_tier="T0")

        self.assertEqual(result["truth_runs"], 3)
        self.assertEqual(result["prediction_runs"], 4)
        self.assertEqual(result["unassigned_prediction_segments"], 1)

        small = result["bins"]["<80"]
        self.assertEqual(small["truth_segments"], 1)
        self.assertEqual(small["segment_tp"], 1)
        self.assertEqual(small["segment_recall"], 1.0)
        self.assertEqual(small["boundary_recall_5bp"], 1.0)
        self.assertEqual(small["mean_fragments_per_true"], 1.0)
        self.assertEqual(small["split_true_rate"], 0.0)
        self.assertEqual(small["missed_true_rate"], 0.0)

        medium = result["bins"]["500-999"]
        self.assertEqual(medium["truth_segments"], 1)
        self.assertEqual(medium["pred_segments"], 2)
        self.assertEqual(medium["segment_tp"], 1)
        self.assertEqual(medium["segment_fp"], 1)
        self.assertEqual(medium["segment_recall"], 1.0)
        self.assertAlmostEqual(medium["segment_f1"], 2 / 3)
        self.assertEqual(medium["mean_fragments_per_true"], 2.0)
        self.assertEqual(medium["split_true_rate"], 1.0)
        self.assertEqual(medium["missed_true_rate"], 0.0)

        long = result["bins"][">=1000"]
        self.assertEqual(long["truth_segments"], 1)
        self.assertEqual(long["segment_tp"], 0)
        self.assertEqual(long["segment_recall"], 0.0)
        self.assertEqual(long["mean_fragments_per_true"], 0.0)
        self.assertEqual(long["missed_true_rate"], 1.0)

    def test_t1_keeps_recall_but_removes_precision_and_f1(self):
        result = MODULE.evaluate(
            rows([(0, 50), (100, 600)]),
            rows([(0, 50), (100, 500), (520, 600), (3000, 3050)]),
            {"chr1": 4000},
            truth_tier="T1",
        )
        for summary in [result["overall"], *result["bins"].values()]:
            self.assertIsNone(summary["segment_precision"])
            self.assertIsNone(summary["segment_f1"])
            self.assertIsNone(summary["boundary_precision_5bp"])
            self.assertIsNone(summary["boundary_f1_5bp"])
            self.assertIsNone(summary["boundary_precision_25bp"])
            self.assertIsNone(summary["boundary_f1_25bp"])
        self.assertEqual(result["bins"]["<80"]["segment_recall"], 1.0)
        self.assertEqual(result["bins"]["500-999"]["segment_recall"], 1.0)

    def test_cli_reads_canonical_tsv_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = "\t".join(MODULE.FIELDS) + "\n"
            truth = root / "truth.tsv"
            pred = root / "pred.tsv"
            lengths = root / "lengths.json"
            output = root / "result.json"
            truth.write_text(header + "chr1\t0\t50\tt\t.\t.\t.\t.\n", encoding="utf-8")
            pred.write_text(header + "chr1\t0\t50\tp\t.\t.\t.\t.\n", encoding="utf-8")
            lengths.write_text(json.dumps({"chr1": 100}), encoding="utf-8")
            import subprocess
            subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--truth",
                    str(truth),
                    "--prediction",
                    str(pred),
                    "--lengths",
                    str(lengths),
                    "--out-json",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["bins"]["<80"]["segment_tp"], 1)


if __name__ == "__main__":
    unittest.main()
