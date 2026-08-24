#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("lemmi_adapter", Path(__file__).with_name("adapter.py"))
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class AdapterTest(unittest.TestCase):
    def test_synthetic_fixture_matches_fm_strict_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.smoke(Path(tmp))
            self.assertTrue(result["pass"])
            self.assertEqual(result["coordinate_convention"], "zero_based_half_open")
            self.assertEqual(result["metrics"]["bp_tp"], 30)
            self.assertEqual(result["metrics"]["true_segments"], 2)

    def test_repeatmasker_coordinates_are_one_to_zero_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "x.out"; output = Path(tmp) / "x.tsv"
            source.write_text("  10  1.0  0.0  0.0 chr1 11 20 (0) + AluY  SINE/Alu 1 10 (0) 1\n", encoding="utf-8")
            self.assertEqual(adapter.convert(source, output, "repeatmasker_out"), 1)
            self.assertEqual(adapter.read_canonical(output), [("chr1", 10, 20)])

    def test_missing_contig_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            truth = Path(tmp) / "t.bed"; pred = Path(tmp) / "p.bed"
            truth.write_text("chrX\t0\t1\tx\n", encoding="utf-8"); pred.write_text("chrX\t0\t1\tx\n", encoding="utf-8")
            tc = Path(tmp) / "t.tsv"; pc = Path(tmp) / "p.tsv"
            adapter.convert(truth, tc, "bed"); adapter.convert(pred, pc, "bed")
            with self.assertRaisesRegex(ValueError, "missing"):
                adapter.evaluate(tc, pc, {"chr1": 10})

    def test_overlapping_truth_uses_flat_union_and_can_report_topology_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            truth = Path(tmp) / "t.bed"; pred = Path(tmp) / "p.bed"
            truth.write_text("chr1\t0\t5\ta\nchr1\t4\t8\tb\n", encoding="utf-8")
            pred.write_text("chr1\t0\t8\tp\n", encoding="utf-8")
            tc = Path(tmp) / "t.tsv"; pc = Path(tmp) / "p.tsv"
            adapter.convert(truth, tc, "bed"); adapter.convert(pred, pc, "bed")
            result = adapter.evaluate(tc, pc, {"chr1": 10}, truth_tier="T1")
            self.assertEqual(result["truth_raw_interval_count"], 2)
            self.assertEqual(result["truth_overlap_count"], 1)
            self.assertEqual(result["truth_union_run_count"], 1)
            self.assertIsNone(result["bp_fp"])
            self.assertIsNone(result["segment_f1"])
            with self.assertRaisesRegex(ValueError, "truth overlap"):
                adapter.evaluate(tc, pc, {"chr1": 10}, overlap_policy="require_nonoverlap")

    def test_overlap_audit_counts_pairs_and_participating_intervals(self):
        audit = adapter._interval_audit([
            ("chr1", 0, 10), ("chr1", 1, 9), ("chr1", 2, 8), ("chr1", 20, 30)
        ])
        self.assertEqual(audit["overlap_count"], 3)
        self.assertEqual(audit["overlap_interval_count"], 3)
        self.assertEqual(audit["union_run_count"], 2)

    def test_union_audit_merges_adjacent_intervals_like_flat_mask(self):
        audit = adapter._interval_audit([("chr1", 0, 5), ("chr1", 5, 8)])
        self.assertEqual(audit["overlap_count"], 0)
        self.assertEqual(audit["overlap_interval_count"], 0)
        self.assertEqual(audit["union_run_count"], 1)

    def test_cli_has_explicit_subcommands_and_evaluate_t1(self):
        script = str(Path(__file__).with_name("adapter.py"))
        help_result = subprocess.run([sys.executable, script, "-h"], check=True, capture_output=True, text=True)
        self.assertIn("convert", help_result.stdout)
        self.assertIn("evaluate", help_result.stdout)
        self.assertIn("self-test", help_result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); truth = root / "truth.bed"; pred = root / "pred.bed"; lengths = root / "lengths.json"
            truth.write_text("chr1\t0\t5\tt\n", encoding="utf-8"); pred.write_text("chr1\t0\t5\tp\n", encoding="utf-8")
            tc = root / "truth.tsv"; pc = root / "pred.tsv"; adapter.convert(truth, tc, "bed"); adapter.convert(pred, pc, "bed")
            lengths.write_text(json.dumps({"chr1": 10}), encoding="utf-8")
            run = subprocess.run([sys.executable, script, "evaluate", "--truth", str(tc), "--prediction", str(pc), "--lengths", str(lengths), "--truth-tier", "T1"], check=True, capture_output=True, text=True)
            result = json.loads(run.stdout)
            self.assertEqual(result["truth_tier"], "T1")
            self.assertIsNone(result["bp_precision"])
            self.assertEqual(result["bp_recall"], 1.0)

    def test_claim_screen_uses_allocation_threads_and_positive_only_scope(self):
        script = Path(__file__).resolve().parents[3] / "sbatch" / "LEMMI-TE-BENCH-20260824-hite-claim-screen.sbatch"
        text = script.read_text(encoding="utf-8")
        self.assertIn("THREADS=${SLURM_CPUS_PER_TASK:-}", text)
        self.assertIn('--thread "$THREADS"', text)
        self.assertIn('--plant 0 --annotate 1', text)
        self.assertNotIn("--thread 2", text)
        self.assertIn("PROJECT_ROOT=${PROJECT_ROOT:-/home/users/j/jwang/ab-initio-TE}", text)
        self.assertNotIn("BASH_SOURCE", text)
        self.assertIn('"claim_scope": "T1_positive_only_recall_boundary_fragmentation"', text)
        self.assertIn('"whole_genome_precision_f1_claim": False', text)
        preflight = script.with_name("LEMMI-TE-BENCH-20260824-preflight.sbatch").read_text(encoding="utf-8")
        self.assertIn("PROJECT_ROOT=${PROJECT_ROOT:-/home/users/j/jwang/ab-initio-TE}", preflight)
        self.assertNotIn("BASH_SOURCE", preflight)


if __name__ == "__main__":
    unittest.main()
