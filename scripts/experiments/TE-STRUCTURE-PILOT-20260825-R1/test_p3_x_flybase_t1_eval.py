#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p3_x_flybase_t1", ROOT / "p3_x_flybase_t1_eval.py")
assert SPEC and SPEC.loader
p3_x_t1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p3_x_t1)


FIELDS = "seqid\tstart\tend\tname\tscore\tstrand\tsource\tattributes\n"


def canonical_row(seqid: str, start: int, end: int) -> str:
    return f"{seqid}\t{start}\t{end}\titem\t.\t.\ttest\t.\n"


class P3XFlyBaseT1EvalTest(unittest.TestCase):
    def test_t1_result_contains_no_forbidden_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth = root / "truth.tsv"
            prediction = root / "prediction.tsv"
            lengths = root / "lengths.json"
            truth.write_text(FIELDS + canonical_row("2L", 10, 20), encoding="utf-8")
            prediction.write_text(FIELDS + canonical_row("2L", 10, 20), encoding="utf-8")
            lengths.write_text(json.dumps({"2L": 100}), encoding="utf-8")

            result = p3_x_t1.evaluate_flybase_t1(truth, prediction, lengths)
            self.assertEqual(result["truth_tier"], "T1")
            self.assertEqual(result["overall"]["segment_recall"], 1.0)
            self.assertEqual(result["overall"]["boundary_recall_5bp"], 1.0)
            self.assertIn("claim_scope", result)

            def assert_clean(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        lower = key.lower()
                        self.assertNotIn("precision", lower)
                        self.assertNotIn("f1", lower)
                        self.assertFalse(lower.endswith("_fp") or lower.endswith("_tn"))
                        assert_clean(item)
                elif isinstance(value, list):
                    for item in value:
                        assert_clean(item)

            assert_clean(result)


if __name__ == "__main__":
    unittest.main()
