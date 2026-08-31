#!/usr/bin/env python3
import csv
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("c5_hybrid_pilot.py")
SPEC = importlib.util.spec_from_file_location("c5_hybrid_pilot", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class A0RuleTest(unittest.TestCase):
    def test_scored_segments_use_raw_body_runs_and_mean_filter(self):
        probability = [0.1] * 500 + [0.9] * 600 + [0.1] * 10 + [0.85] * 500
        truth = [1] * len(probability)
        result = MODULE.scored_segments(probability, truth, 0.5, 500, 0.8)
        self.assertEqual([(row["start"], row["end"]) for row in result], [(500, 1100), (1110, 1610)])
        self.assertAlmostEqual(result[0]["mean_probability"], 0.9)

    def test_a0_tie_break_is_recall_then_threshold_then_length(self):
        rows = [
            {"segment_precision": 0.8, "segment_recall": 0.4, "mean_probability": 0.8, "min_length": 500},
            {"segment_precision": 0.8, "segment_recall": 0.4, "mean_probability": 0.9, "min_length": 500},
            {"segment_precision": 0.8, "segment_recall": 0.4, "mean_probability": 0.9, "min_length": 1000},
            {"segment_precision": 0.8, "segment_recall": 0.5, "mean_probability": 0.8, "min_length": 500},
        ]
        selected = max(rows, key=lambda row: (
            row["segment_precision"], row["segment_recall"],
            row["mean_probability"], row["min_length"],
        ))
        self.assertEqual(selected["segment_recall"], 0.5)

    def test_reciprocal_overlap_and_union_intervals(self):
        self.assertEqual(MODULE.reciprocal_overlap(100, 700, 100, 700), 1.0)
        self.assertAlmostEqual(MODULE.reciprocal_overlap(100, 700, 200, 800), 500 / 600)
        self.assertEqual(
            MODULE.union_intervals([
                ("chr17", 500, 700), ("chr17", 100, 300), ("chr17", 250, 550),
                ("chr17", 900, 1000),
            ]),
            [("chr17", 100, 700), ("chr17", 900, 1000)],
        )


class A1PafTest(unittest.TestCase):
    def test_filters_paf_hits_excludes_self_and_counts_unique_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seeds = root / "a0.seeds.tsv"
            seeds.write_text(
                "\t".join(MODULE.SEED_FIELDS) + "\n"
                "s1\tchr17\t100\t700\t600\t0.95\t0.5\t500\t0.8\n",
                encoding="utf-8",
            )
            fasta = root / "a0.seeds.fa"
            fasta.write_text(">s1\n" + "A" * 600 + "\n", encoding="ascii")
            assembly = root / "hs1.fa"
            output = root / "a1"
            paf_lines = [
                "s1\t600\t0\t600\t+\tchr17\t10000\t100\t700\t600\t600\t60\n",
                "s1\t600\t0\t600\t+\tchr17\t10000\t2000\t2600\t600\t600\t60\n",
                "s1\t600\t0\t600\t-\tchr1\t20000\t5000\t5600\t600\t600\t60\n",
                "s1\t600\t0\t400\t+\tchr2\t20000\t1000\t1600\t400\t400\t60\n",
                "s1\t600\t0\t600\t+\tchr3\t20000\t1000\t1600\t400\t600\t60\n",
                "s1\t600\t0\t600\t+\tchr4\t20000\t1000\t1450\t600\t600\t60\n",
            ]

            def fake_run(argv, stdout, check):
                self.assertEqual(argv[:3], ["minimap2", "-x", "asm20"])
                self.assertEqual(argv[-2:], [str(assembly), str(fasta)])
                stdout.write("".join(paf_lines))
                return SimpleNamespace(returncode=0)

            with patch.object(MODULE.subprocess, "run", side_effect=fake_run):
                result = MODULE.a1_run(SimpleNamespace(
                    seeds_tsv=seeds, seeds_fasta=fasta, assembly=assembly,
                    minimap2="minimap2", prefix_seqid="chr17", prefix_end=10000,
                    out_dir=output,
                ))

            self.assertEqual(result["seeds"], 1)
            self.assertEqual(result["paf_rows"], 6)
            self.assertEqual(result["qualified_nonself_hits"], 2)
            self.assertEqual(result["seeds_with_at_least_two_copies"], 1)
            self.assertEqual(result["emitted_chr17_prefix_hits"], 1)
            with (output / "a1.evidence.tsv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(rows[0]["self_hit"], "True")
            self.assertEqual(rows[0]["copy_evidence"], "False")
            self.assertEqual(rows[1]["emitted_to_chr17_prefix"], "True")
            self.assertEqual(
                (output / "a1.canonical.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")[:3],
                ["chr17", "100", "700"],
            )
            self.assertEqual(
                (output / "a1.canonical.tsv").read_text(encoding="utf-8").splitlines()[2].split("\t")[:3],
                ["chr17", "2000", "2600"],
            )
            manifest = json.loads((output / "a1.manifest.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(manifest["fraction_seeds_with_at_least_two_copies"], 1.0)


class HiTEA0Test(unittest.TestCase):
    def test_exports_tool_native_full_length_calls_without_truth_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gff = root / "HiTE.full_length.gff"
            gff.write_text(
                "##gff-version 3\n"
                "chr17\tHiTE\tSINE/Alu\t2\t5\t.\t+\t.\tid=te_intact_1;name=fam1;classification=SINE/Alu\n"
                "chr17\tHiTE\tLINE/L1\t8\t12\t.\t-\t.\tid=te_intact_2;name=fam2;classification=LINE/L1\n",
                encoding="utf-8",
            )
            assembly = root / "hs1.fa"
            assembly.write_text(">chr17\nACGTACGTACGTACGT\n", encoding="ascii")
            out = root / "out"
            result = MODULE.hite_a0_export(SimpleNamespace(
                full_length_gff=gff, assembly=assembly, prefix_seqid="chr17",
                prefix_end=16, out_dir=out,
            ))
            self.assertEqual(result["seeds"], 2)
            with (out / "a0.seeds.tsv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual((rows[0]["start"], rows[0]["end"]), ("1", "5"))
            self.assertIn(">te_intact_2\nTACGT\n", (out / "a0.seeds.fa").read_text())

    def test_union_combines_seed_queries_and_merges_a0_intervals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p3 = root / "p3.tsv"
            hite = root / "hite.tsv"
            p3.write_text("seed_id\tseqid\tstart\tend\np3\tchr17\t10\t20\n")
            hite.write_text("seed_id\tseqid\tstart\tend\nhite\tchr17\t15\t25\n")
            p3_fa = root / "p3.fa"
            hite_fa = root / "hite.fa"
            p3_fa.write_text(">p3\nAAAAAAAAAA\n")
            hite_fa.write_text(">hite\nCCCCCCCCCC\n")
            out = root / "out"
            result = MODULE.union_a0_export(SimpleNamespace(
                p3_seeds_tsv=p3, p3_seeds_fasta=p3_fa,
                hite_seeds_tsv=hite, hite_seeds_fasta=hite_fa, out_dir=out,
            ))
            self.assertEqual(result["union_queries"], 2)
            self.assertEqual(result["canonical_intervals"], 1)
            self.assertIn(">hite\nCCCCCCCCCC\n", (out / "a0.seeds.fa").read_text())


if __name__ == "__main__":
    unittest.main()
