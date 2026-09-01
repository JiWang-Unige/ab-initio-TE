#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_gene_safety", HERE / "phase0_gene_safety.py")
assert SPEC is not None and SPEC.loader is not None
safety = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = safety
SPEC.loader.exec_module(safety)


class Phase0GeneSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.intervals = self.root / "selected.tsv"
        with self.intervals.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["seqid", "start", "end", "comparator_negative_bp", "comparator_unknown_bp"],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows([
                {"seqid": "chr19", "start": 98, "end": 102, "comparator_negative_bp": "0", "comparator_unknown_bp": "99"},
                {"seqid": "chr19", "start": 148, "end": 152, "comparator_negative_bp": "999", "comparator_unknown_bp": "0"},
                {"seqid": "chr19", "start": 298, "end": 302, "comparator_negative_bp": "0", "comparator_unknown_bp": "0"},
                {"seqid": "chr19", "start": 500, "end": 504, "comparator_negative_bp": "1", "comparator_unknown_bp": "999"},
            ])

        self.positive = self.root / "comparator-positive.bed"
        self.positive.write_text(
            "chr19\t98\t100\nchr19\t500\t502\nchr3\t0\t100\n",
            encoding="utf-8",
        )
        self.unknown = self.root / "comparator-unknown.bed"
        self.unknown.write_text(
            "chr19\t98\t101\nchr19\t300\t301\nchr5\t0\t100\n",
            encoding="utf-8",
        )

        self.refgene = self.root / "refGene.txt.gz"
        rows = [
            ["0", "txPlus", "chr19", "+", "90", "350", "100", "320", "2", "90,200,", "160,350,", "0", "GENE_PLUS", "cmpl", "cmpl", "0,0,"],
            ["0", "txMinus", "chr19", "-", "450", "650", "480", "620", "2", "450,550,", "520,650,", "0", "GENE_MINUS", "cmpl", "cmpl", "0,0,"],
        ]
        with gzip.open(self.refgene, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write("\t".join(row) + "\n")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _audit(
        self,
        intervals: Path | None = None,
        refgene: Path | None = None,
    ) -> dict[str, object]:
        return safety.audit_gene_safety(
            intervals or self.intervals,
            self.positive,
            self.unknown,
            refgene or self.refgene,
            self.root / "out.json",
            self.root / "out.tsv",
            "hg38-refGene-test",
            "https://example.invalid/refGene.txt.gz",
        )

    def test_exact_negative_projection_and_feature_intersections(self) -> None:
        result = self._audit()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selected_added_bp"], 16)
        self.assertEqual(result["added_comparator_negative_bp"], 10)
        self.assertEqual(
            result["added_comparator_negative_bp_status"],
            "EXACT_FROM_POSITIVE_AND_UNKNOWN_INTERVALS",
        )
        self.assertEqual(result["comparator_projection"]["positive_bp_chr19"], 4)
        self.assertEqual(result["comparator_projection"]["unknown_source_bp_chr19"], 4)
        self.assertEqual(result["comparator_projection"]["effective_unknown_bp_chr19"], 2)
        self.assertEqual(result["intersections"]["cds"]["feature_union_bp"], 290)
        self.assertEqual(result["intersections"]["cds"]["union_denominator_bp"], 290)
        self.assertAlmostEqual(result["intersections"]["cds"]["selected_added_fraction"], 14 / 290)
        self.assertEqual(result["intersections"]["coding_exon"]["feature_union_bp"], 390)
        self.assertAlmostEqual(result["intersections"]["coding_exon"]["selected_added_fraction"], 16 / 390)
        self.assertEqual(result["intersections"]["all_exon"]["feature_union_bp"], 390)
        self.assertAlmostEqual(result["intersections"]["all_exon"]["selected_added_fraction"], 16 / 390)
        self.assertEqual(result["intersections"]["splice_core_pm2"]["feature_union_bp"], 16)
        self.assertEqual(result["intersections"]["promoter_pm200"]["feature_union_bp"], 690)
        self.assertAlmostEqual(result["intersections"]["promoter_pm200"]["selected_added_fraction"], 12 / 690)
        self.assertEqual(result["intersections"]["cds"]["selected_added_bp"], 14)
        self.assertEqual(result["intersections"]["cds"]["added_comparator_negative_bp"], 10)
        self.assertEqual(result["intersections"]["coding_exon"]["selected_added_bp"], 16)
        self.assertEqual(result["intersections"]["coding_exon"]["added_comparator_negative_bp"], 10)
        self.assertEqual(result["intersections"]["all_exon"]["added_comparator_negative_bp"], 10)
        self.assertEqual(result["intersections"]["splice_core_pm2"]["added_comparator_negative_bp"], 0)
        self.assertEqual(result["intersections"]["promoter_pm200"]["added_comparator_negative_bp"], 7)

    def test_strand_tss_and_frozen_four_base_splice_definition(self) -> None:
        result = self._audit()
        self.assertEqual(result["intersections"]["promoter_pm200"]["selected_added_bp"], 12)
        self.assertIn("[boundary-2,boundary+2)", result["feature_definitions"]["splice_core_pm2"])
        self.assertNotIn("splice_core_pm2_inclusive", result["intersections"])
        self.assertNotIn("splice_core_pm2_inclusive", result["feature_definitions"])
        owners = [
            feature.owner
            for feature in safety._build_features(safety.load_refgene(self.refgene))["splice_core_pm2"]
        ]
        self.assertTrue(all("donor" not in owner and "acceptor" not in owner for owner in owners))
        self.assertTrue(all("internal_boundary" in owner for owner in owners))

    def test_gene_overlap_uses_feature_union_not_transcript_span(self) -> None:
        result = self._audit()
        self.assertEqual(result["gene_overlap_candidate_count"], 4)
        self.assertEqual(result["gene_overlap_selected_added_bp"], 16)
        self.assertEqual(result["gene_overlap_added_comparator_negative_bp"], 10)
        self.assertAlmostEqual(result["gene_overlap_added_bp_precision"], 6 / 16)
        self.assertEqual(result["affected_gene_count"], 2)
        self.assertEqual(result["affected_exon_count"], 3)
        self.assertEqual(result["annotated_cds_records"], [
            {"transcript_id": "txPlus", "gene_id": "GENE_PLUS", "cds_bp": 180, "comparator_negative_bp": 8},
            {"transcript_id": "txMinus", "gene_id": "GENE_MINUS", "cds_bp": 110, "comparator_negative_bp": 2},
        ])
        self.assertEqual(result["max_single_cds_comparator_negative_bp"], 8)
        self.assertEqual(result["max_single_annotated_cds_negative_bp"], 8)

        long_refgene = self.root / "long-refGene.txt"
        long_refgene.write_text(
            "0\ttxLong\tchr19\t+\t1000\t2010\t1000\t2010\t2\t1000,2000,\t1010,2010,\t0\tGENE_LONG\tcmpl\tcmpl\t0,0,\n",
            encoding="utf-8",
        )
        intron_only = self.root / "intron-only.tsv"
        intron_only.write_text("seqid\tstart\tend\nchr19\t1500\t1510\n", encoding="utf-8")
        intron_result = self._audit(intron_only, long_refgene)
        self.assertEqual(intron_result["gene_overlap_candidate_count"], 0)
        self.assertIsNone(intron_result["gene_overlap_added_bp_precision"])
        self.assertEqual(intron_result["affected_gene_count"], 0)

    def test_callable_cds_excludes_effective_unknown(self) -> None:
        result = self._audit()
        self.assertEqual(result["callable_cds_bp"], 288)
        self.assertEqual(result["callable_cds_negative_bp"], 10)
        self.assertAlmostEqual(result["callable_cds_negative_fill_rate"], 10 / 288)

    def test_selected_label_columns_are_ignored(self) -> None:
        altered = self.root / "altered-labels.tsv"
        altered.write_text(
            "seqid\tstart\tend\tcomparator_negative_bp\tcomparator_unknown_bp\n"
            "chr19\t98\t102\t9999\t0\n"
            "chr19\t148\t152\t0\t9999\n"
            "chr19\t298\t302\t9999\t9999\n"
            "chr19\t500\t504\t0\t0\n",
            encoding="utf-8",
        )
        result = self._audit(altered)
        self.assertEqual(result["added_comparator_negative_bp"], 10)

    def test_output_tsv_contains_gate_fields(self) -> None:
        self._audit()
        with (self.root / "out.tsv").open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        for field in (
            "cds_union_bp",
            "cds_selected_added_fraction",
            "cds_negative_bp",
            "coding_exon_union_bp",
            "coding_exon_selected_added_fraction",
            "coding_exon_negative_bp",
            "all_exon_union_bp",
            "all_exon_selected_added_fraction",
            "all_exon_negative_bp",
            "splice_core_pm2_union_bp",
            "splice_core_pm2_selected_added_fraction",
            "splice_core_pm2_negative_bp",
            "promoter_pm200_union_bp",
            "promoter_pm200_selected_added_fraction",
            "promoter_pm200_negative_bp",
            "callable_cds_negative_fill_rate",
            "max_single_cds_comparator_negative_bp",
            "gene_overlap_added_bp_precision",
        ):
            self.assertIn(field, row)

    def test_json_is_written_with_external_annotation_metadata(self) -> None:
        self._audit()
        result = json.loads((self.root / "out.json").read_text(encoding="utf-8"))
        self.assertEqual(result["annotation"]["version"], "hg38-refGene-test")
        self.assertEqual(result["annotation"]["url"], "https://example.invalid/refGene.txt.gz")


if __name__ == "__main__":
    unittest.main()
