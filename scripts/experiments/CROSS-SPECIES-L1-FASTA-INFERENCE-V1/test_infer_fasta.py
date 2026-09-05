import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

SPEC = importlib.util.spec_from_file_location("infer_fasta", Path(__file__).with_name("infer_fasta.py"))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FastaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = module.build_parser().parse_args([
            "--fasta", str(self.root / "input.fa"), "--model-dir", str(self.root / "model"),
            "--model-code-dir", str(self.root / "code"),
            "--calibration-json", str(self.root / "calibration.json"),
            "--output-dir", str(self.root / "out"), "--batch-size", "1", "--cpu"])
        self.calibration = {
            "model_dir": str(self.args.model_dir.resolve()),
            "tokenizer_dir": str(self.args.model_dir.resolve()),
            "model_code_dir": str(self.args.model_code_dir.resolve()),
            "calibration_protocol": "CROSS-SPECIES-L1-X0-PLATT-V1",
            "calibration_scope": "six-species-shared", "fit_split": "CAL",
            "species": list(module.core.CAL_SPECIES), "platt_slope": 1.,
            "platt_intercept": 0., "threshold": .5, "threshold_selection": {"threshold": .5}, "seed": 42,
        }
        self.write_calibration()

    def write_calibration(self):
        self.args.calibration_json.write_text(json.dumps(self.calibration))

    def infer(self, provider):
        with patch.object(module.core, "load_final_model", return_value=(None, None, "cpu")) as loader, \
                patch.object(module.core, "infer_half_margins", side_effect=provider):
            result = module.run(self.args)
            loader.assert_called_once_with(self.args.model_dir, None, True, self.args.model_code_dir)
            return result

    def rows(self, filename):
        path = self.args.output_dir / filename
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt") as handle:
            return [line.rstrip().split("\t") for line in handle]

    def test_coordinate_roundtrip_and_runs_cross_windows_batches(self):
        self.args.fasta.write_text(">chrA\n" + "a" * 4000 + "N" * 200 + "C" * 3994 + "\n>tiny\nry\n")
        lengths = []
        offset = 0
        def provider(model, tokenizer, device, sequences, batch_size):
            nonlocal offset
            output = []
            for seq in sequences:
                self.assertEqual(seq, seq.upper())
                lengths.append(len(seq))
                values = np.full(len(seq), -1, dtype=np.float32)
                if offset < 8194:
                    coords = offset + np.arange(len(seq))
                    values[(coords >= 4000) & (coords < 8193)] = 0  # >=, not >.
                else:
                    values[:] = 1
                offset += len(seq)
                output.append(values)
            return output
        report = self.infer(provider)
        self.assertEqual(lengths, [4096, 4096, 2, 2])
        self.assertEqual(self.rows("material_runs.bed"), [["chrA", "4000", "8193"], ["tiny", "0", "2"]])
        self.assertEqual(self.rows("ambiguity_qc.bed"), [["chrA", "4000", "4200"], ["tiny", "0", "2"]])
        rows = self.rows("material_probability.bedGraph.gz")
        self.assertEqual([(r[0], int(r[1]), int(r[2])) for r in rows],
                         [("chrA", 0, 4000), ("chrA", 4000, 8193), ("chrA", 8193, 8194), ("tiny", 0, 2)])
        self.assertEqual(float(rows[1][3]), .5)
        self.assertEqual(report["total_bp"], 8196)
        self.assertFalse(report["labels_used"])
        self.assertEqual(json.loads((self.args.output_dir / "summary.json").read_text()), report)

    def test_plain_and_gzip_multiple_contigs_and_all_short_tails(self):
        text = "".join(f">n{i} description\n{'ACGTN'[:i]}\n" for i in range(1, 6))
        self.args.fasta = self.root / "input.fa.gz"
        with gzip.open(self.args.fasta, "wt") as handle:
            handle.write(text.lower())
        self.assertEqual([len(seq) for _, seq in module.read_fasta(self.args.fasta)], [1, 2, 3, 4, 5])
        def provider(model, tokenizer, device, sequences, batch_size):
            return [np.ones(len(seq), np.float32) for seq in sequences]
        report = self.infer(provider)
        self.assertEqual(report["total_bp"], 15)
        self.assertEqual(self.rows("material_runs.bed"), [[f"n{i}", "0", str(i)] for i in range(1, 6)])
        self.assertEqual(self.rows("ambiguity_qc.bed"), [["n5", "4", "5"]])
        self.args.fasta = self.root / "plain.fa"
        self.args.fasta.write_text(text)
        self.assertEqual(list(module.read_fasta(self.args.fasta)), [(f"n{i}", "ACGTN"[:i]) for i in range(1, 6)])

    def test_existing_projection_helper_parity_at_native_boundaries(self):
        for length in [1, 2, 3, 4, 5, 4000, 4096]:
            seq = "A" * length
            tokens = module.core.sequence_tokens(seq)
            self.assertEqual(len(tokens), length // 6 + length % 6)
            positions = list(range(1, len(tokens) + 1))
            token_margin = np.arange(len(tokens) + 2, dtype=np.float32)
            observed = module.core.project_token_margins(token_margin, positions, length)
            expected = np.concatenate([np.repeat(np.arange(1, length // 6 + 1), 6),
                                       np.arange(length // 6 + 1, len(tokens) + 1)])
            np.testing.assert_array_equal(observed, expected)
        self.assertEqual(module.core.sequence_tokens("ACNTACN"), ["<unk>", "<unk>"])

    def test_contig_aligned_windows_and_one_to_five_bp_terminal_windows(self):
        lengths = [4000, 4096, 8192] + [4096 + tail for tail in range(1, 6)]
        self.args.fasta.write_text("".join(f">c{i}\n{'A' * n}\n" for i, n in enumerate(lengths)))
        self.args.batch_size = 2
        batches = []
        def provider(model, tokenizer, device, sequences, batch_size):
            batches.append([len(seq) for seq in sequences])
            self.assertLessEqual(len(sequences), 2)
            return [np.ones(len(seq), np.float32) for seq in sequences]
        self.infer(provider)
        self.assertEqual(batches, [[4000], [4096], [4096, 4096]] + [[4096, i] for i in range(1, 6)])
        self.assertEqual(self.rows("material_runs.bed"), [[f"c{i}", "0", str(n)] for i, n in enumerate(lengths)])

    def test_iupac_ambiguity_is_retained_without_censoring(self):
        self.args.fasta.write_text(">x\naCgTrYsWkMbDhVn\n")
        seen = []
        def provider(model, tokenizer, device, sequences, batch_size):
            seen.extend(sequences)
            return [np.ones(len(seq), np.float32) for seq in sequences]
        self.infer(provider)
        self.assertEqual(seen, ["ACGTRYSWKMBDHVN"])
        self.assertEqual(self.rows("material_runs.bed"), [["x", "0", "15"]])
        self.assertEqual(self.rows("ambiguity_qc.bed"), [["x", "4", "15"]])

    def test_invalid_fasta_rejected(self):
        for text in ["", "ACGT\n", ">\nACGT\n", ">x\n", ">x\n>x2\nA\n",
                     ">x\nA\n>x desc\nC\n", ">x\nAC-G\n", ">x\nACGU\n"]:
            with self.subTest(text=text):
                self.args.fasta.write_text(text)
                with self.assertRaises(ValueError):
                    list(module.read_fasta(self.args.fasta))

    def test_mismatched_paths_shared_cal_fields_and_nonfinite_rejected(self):
        for key, value in [("model_dir", "other"), ("tokenizer_dir", "other"),
                           ("model_code_dir", None), ("calibration_scope", "B0-species-specific"),
                           ("fit_split", "DEV"), ("species", ["human"]),
                           ("calibration_protocol", "unknown"), ("platt_slope", float("nan")),
                           ("platt_intercept", float("inf")), ("threshold", float("nan")),
                           ("threshold_selection", {"threshold": .6})]:
            with self.subTest(key=key):
                original = self.calibration[key]
                self.calibration[key] = value
                self.write_calibration()
                with self.assertRaises(ValueError):
                    module.load_calibration(self.args)
                self.calibration[key] = original

    def test_cli_has_no_labels_or_adjustable_threshold(self):
        options = module.build_parser()._option_string_actions
        for forbidden in ["--labels", "--data", "--threshold", "--gap", "--min-length", "--smooth"]:
            self.assertNotIn(forbidden, options)

    def test_invalid_model_margin_leaves_no_success_summary(self):
        self.args.fasta.write_text(">x\nACGT\n")
        with self.assertRaisesRegex(ValueError, "invalid projected"):
            self.infer(lambda *args: [np.full(4, np.nan, dtype=np.float32)])
        self.assertFalse((self.args.output_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
