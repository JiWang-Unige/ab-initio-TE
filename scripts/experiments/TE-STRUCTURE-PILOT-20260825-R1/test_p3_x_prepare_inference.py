#!/usr/bin/env python3
import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p3_x_prepare", ROOT / "p3_x_prepare_inference.py")
assert SPEC and SPEC.loader
p3_x_prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p3_x_prepare)


class P3XPrepareInferenceTest(unittest.TestCase):
    def test_emits_full_windows_and_tail_with_zero_dummy_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = root / "assembly.fa.gz"
            output = root / "input.jsonl.gz"
            manifest = root / "input.manifest.json"
            with gzip.open(assembly, "wt", encoding="ascii") as handle:
                handle.write(">chrA description\n")
                handle.write("a" * 8192 + "c\n")
                handle.write(">chrB\nNNNNN\n")

            result = p3_x_prepare.write_inference_jsonl(assembly, output, manifest)
            self.assertEqual(result["contigs"], 2)
            self.assertEqual(result["total_bp"], 8198)
            self.assertEqual(result["windows"], 3)
            self.assertEqual(result["tail_windows"], 2)
            self.assertEqual(result["label_mode"], "all_zero_dummy_for_p3_r1_evaluator_only")
            self.assertFalse(result["truth_read"])

            with gzip.open(output, "rt", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle]
            self.assertEqual(
                [(row["chr"], row["start"], row["end"]) for row in rows],
                [("chrA", 0, 8192), ("chrA", 8192, 8193), ("chrB", 0, 5)],
            )
            for row in rows:
                self.assertEqual(len(row["sequence"]), len(row["labels"]))
                self.assertTrue(all(label == 0 for label in row["labels"]))

            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), result)

    def test_duplicate_contig_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            assembly = Path(tmp) / "duplicate.fa"
            assembly.write_text(">same\nAC\n>same\nGT\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "duplicate FASTA contig"):
                list(p3_x_prepare.iter_inference_rows(assembly))

    def test_geometry_is_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            assembly = Path(tmp) / "assembly.fa"
            output = Path(tmp) / "input.jsonl.gz"
            manifest = Path(tmp) / "manifest.json"
            assembly.write_text(">chrA\nACGT\n", encoding="ascii")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "p3_x_prepare_inference.py"),
                    "--assembly",
                    str(assembly),
                    "--output-jsonl",
                    str(output),
                    "--manifest",
                    str(manifest),
                    "--window",
                    "4096",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("requires --window 8192", completed.stderr)


if __name__ == "__main__":
    unittest.main()
