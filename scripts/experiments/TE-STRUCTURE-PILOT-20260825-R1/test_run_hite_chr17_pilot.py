#!/usr/bin/env python3
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("hite_run", HERE / "run_hite_chr17_pilot.py")
assert SPEC and SPEC.loader
hite_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hite_run)


class HiTERunTest(unittest.TestCase):
    def test_fasta_crop_preserves_chr17_prefix_and_coordinate_length(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "assembly.fa"
            source.write_text(">chr16\nAAAA\n>chr17\n" + "ACGT" * 4 + "\n>chr19\nCCCC\n")
            output = root / "prefix.fa"
            self.assertEqual(hite_run.crop_fasta(source, output, "chr17", 10), 10)
            self.assertEqual(list(hite_run.fasta_records(output)), [("chr17", "ACGTACGTAC")])

    def test_bed_crop_is_zero_based_half_open_and_clips_end(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bed"
            source.write_text(
                "chr19\t0\t20\tx\n"
                "chr17\t2\t12\ta\n"
                "chr17\t20\t30\tb\n"
            )
            output = root / "prefix.bed"
            self.assertEqual(hite_run.crop_bed(source, output, "chr17", 20), 1)
            self.assertEqual(output.read_text(), "chr17\t2\t12\ta\n")

    def test_bed_crop_normalizes_repeatmasker_complement_strand(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bed"
            source.write_text("chr17\t2\t12\ta\t1\tC\n")
            output = root / "prefix.bed"
            self.assertEqual(hite_run.crop_bed(source, output, "chr17", 20), 1)
            self.assertEqual(output.read_text(), "chr17\t2\t12\ta\t1\t-\n")

    def test_plus_unknown_difference_is_not_treated_as_all_te(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            strict = root / "strict.bed"
            plus = root / "plus.bed"
            strict.write_text("chr17\t2\t12\tTE\t1\t+\tLTR\tERV\tLTR/ERV\n")
            plus.write_text(
                strict.read_text()
                + "chr17\t20\t30\tUCON\t1\t+\tUnknown\tUnknown\tUnknown/Unknown\n"
            )
            self.assertEqual(len(hite_run.unknown_rows(strict, plus)), 1)
            self.assertEqual(hite_run.unknown_rows(strict, plus)[0][6], "Unknown")

    def test_hite_command_uses_pinned_direct_argv_and_positive_threads(self):
        command = hite_run.build_hite_command(Path("/x/hite.sif"), Path("/x/work"), 40)
        self.assertEqual(command[0:5], ["apptainer", "exec", "--cleanenv", "--bind", "/x/work:/work"])
        self.assertEqual(command[-12:], [
            "python", "/HiTE/main.py", "--genome", "/work/input/hite.fa",
            "--thread", "40", "--plant", "0", "--annotate", "1", "--out_dir", "/work/hite",
        ])
        with self.assertRaisesRegex(ValueError, "positive"):
            hite_run.build_hite_command(Path("/x/hite.sif"), Path("/x/work"), 0)

    def test_model_prediction_requires_unique_absolute_name_assignment(self):
        self.assertEqual(
            hite_run.parse_model_prediction(["base=/x/base.tsv", "dapt=/x/dapt.tsv"]),
            {"base": Path("/x/base.tsv"), "dapt": Path("/x/dapt.tsv")},
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            hite_run.parse_model_prediction(["base=/x/a.tsv", "base=/x/b.tsv"])
        with self.assertRaisesRegex(ValueError, "name=/absolute"):
            hite_run.parse_model_prediction(["base.tsv"])

    def test_scratch_workdir_uses_node_scratch_and_output_job_name(self):
        with tempfile.TemporaryDirectory() as td:
            scratch = Path(td) / "slurm-tmp"
            scratch.mkdir()
            output_root = Path(td) / "outputs" / "hite-chr17-123"
            with patch.dict(os.environ, {"HITE_NODE_SCRATCH": str(scratch)}, clear=False):
                self.assertEqual(
                    hite_run.scratch_workdir(output_root),
                    scratch / "hite-chr17-123",
                )

    def test_masked_evaluate_reports_boundary_at_5_and_25_bp(self):
        class Adapter:
            def __init__(self):
                self.tolerances = []

            @staticmethod
            def read_canonical(_path):
                return [("chr17", 10, 20)]

            def evaluate(self, _truth, _prediction, _lengths, **kwargs):
                tolerance = kwargs["boundary_tol_bp"]
                self.tolerances.append(tolerance)
                return {
                    "boundary_hits": tolerance,
                    "boundary_precision": tolerance / 100,
                    "boundary_recall": tolerance / 100,
                    "boundary_f1": tolerance / 100,
                }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adapter = Adapter()
            result = hite_run.masked_evaluate(
                adapter, root / "truth.tsv", root / "prediction.tsv",
                root / "unknown.tsv", {"chr17": 40}, root,
            )
            self.assertEqual(adapter.tolerances, [5, 25])
            self.assertEqual(result["boundary_f1"], 0.05)
            self.assertEqual(result["boundary_f1_at_25bp"], 0.25)


if __name__ == "__main__":
    unittest.main()
