#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("hite_contract", ROOT / "hite_chr17_pilot.py")
assert SPEC and SPEC.loader
hite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hite)


class HiTEContractTest(unittest.TestCase):
    def test_same_prefix_truth_mask_and_comparator_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lengths = root / "lengths.json"
            lengths.write_text(json.dumps({"chr17": 20_000_000}), encoding="utf-8")
            result = hite.build_contract(
                root / "hg38.fa.gz",
                root / "repeatmasker.bed",
                root / "unknown.bed",
                lengths,
                root / "hite.sif",
                root / "pilot",
                model_prediction=root / "base.prediction.tsv",
            )

            self.assertEqual(result["status"], "CONTRACT_ONLY")
            self.assertFalse(result["truth_is_independent_biological_gold"])
            self.assertEqual(result["claim_scope"], "RepeatMasker-comparator agreement only")
            self.assertEqual(result["prefix"]["seqid"], "chr17")
            self.assertEqual(result["prefix"]["start"], 0)
            self.assertEqual(result["prefix"]["end"], 9_830_400)
            crop_ids = [command["id"] for command in result["commands"]]
            self.assertEqual(crop_ids[:4], ["crop_assembly", "crop_truth", "crop_unknown_mask", "project_contig_lengths"])
            self.assertIn("sed '1c\\>chr17'", result["commands"][0]["shell"])
            for command in result["commands"][1:3]:
                self.assertEqual(command["interval"], ["chr17", 0, 9_830_400])
            evaluation = result["evaluation_contract"]
            self.assertTrue(evaluation["same_truth_and_mask_for_all_methods"])
            self.assertEqual(evaluation["methods"]["model"], str(root / "base.prediction.tsv"))
            self.assertIn("bp_f1_agreement", evaluation["metrics"])

    def test_short_chr17_rejects_fixed_prefix_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lengths = root / "lengths.json"
            lengths.write_text(json.dumps({"chr17": hite.PREFIX_BP - 1}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "shorter than the fixed"):
                hite.build_contract(
                    root / "assembly.fa",
                    root / "truth.bed",
                    root / "unknown.bed",
                    lengths,
                    root / "hite.sif",
                    root / "pilot",
                )


if __name__ == "__main__":
    unittest.main()
