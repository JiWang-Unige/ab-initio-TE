#!/usr/bin/env python3
"""Focused contracts for the source-only RepeatPeps evidence panel."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("protein_support.py")
SPEC = importlib.util.spec_from_file_location("protein_support", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTEIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTEIN)


class ProteinSupportTests(unittest.TestCase):
    def test_query_panel_deduplicates_reused_controls_and_preserves_unmatched_fp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fasta = root / "source.fa"
            fasta.write_text(">chr2\n" + "ACGT" * 30 + "\n>chr3\n" + "A" * 120 + "\n>chr4\n" + "C" * 120 + "\n", encoding="utf-8")
            matches = root / "matched.tsv"
            matches.write_text(
                "fp_mapping_id\tfp_source_chrom\tfp_source_start0\tfp_source_end\tfp_source_length\tfp_old_te_relation\tmatch_status\tcontrol_mapping_id\tcontrol_source_chrom\tcontrol_source_start0\tcontrol_source_end\tcontrol_source_length\tcontrol_old_te_relation\tcontrol_reused\n"
                "fp1\tchr2\t0\t20\t20\tADJACENT\tMATCHED_TN\ttn1\tchr2\t40\t60\t20\tADJACENT\tFalse\n"
                "fp2\tchr2\t4\t24\t20\tADJACENT\tUNMATCHED_FP\t\t\t\t\t\t\t\n",
                encoding="utf-8",
            )
            out = root / "queries"
            no_reuse = root / "no-reuse.tsv"
            no_reuse.write_text(
                "fp_mapping_id\tfp_source_chrom\tfp_source_start0\tfp_source_end\tfp_source_length\tfp_old_te_relation\tmatch_status\tcontrol_mapping_id\tcontrol_source_chrom\tcontrol_source_start0\tcontrol_source_end\tcontrol_source_length\tcontrol_old_te_relation\tcontrol_reused\n"
                "fp1\tchr2\t0\t20\t20\tADJACENT\tMATCHED_TN\ttn2\tchr2\t80\t100\t20\tADJACENT\tFalse\n",
                encoding="utf-8",
            )
            manifest = PROTEIN.build_queries(matches, fasta, out, no_reuse)
            self.assertEqual((manifest["fp_query_count"], manifest["tn_query_count"]), (2, 2))
            self.assertEqual(manifest["original_control_reuse_max"], 1)
            self.assertEqual(len((out / "query_manifest.tsv").read_text(encoding="utf-8").splitlines()), 5)

    def test_blastx_parser_retains_best_hit_and_rejects_unknown_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blast = root / "blast.tsv"
            blast.write_text(
                "q000\tsubjectB\t1e-3\t40\t10\t1\t30\t2\t31\t60\t50\n"
                "q000\tsubjectA\t1e-8\t55\t12\t1\t36\t2\t37\t60\t60\n",
                encoding="utf-8",
            )
            best = PROTEIN.parse_blast_hits(blast, ["q000"])
            self.assertEqual(best["q000"]["subject_id"], "subjectA")
            self.assertEqual(best["q000"]["qcovhsp"], 60.0)
            blast.write_text("q999\ts\t1e-3\t40\t10\t1\t30\t2\t31\t60\t50\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                PROTEIN.parse_blast_hits(blast, ["q000"])


if __name__ == "__main__":
    unittest.main()
