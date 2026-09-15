#!/usr/bin/env python3
"""Focused contract tests for the label-free NTv2 experiment."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ntv2_label_free_cluster", HERE / "ntv2_label_free_cluster.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(record_id, start, family, homology, copy_id, chrom="chr1"):
    return {
        "record_id": "interval|hg38|%s|%d|%d|+|%s" % (chrom, start, start + 120, record_id),
        "host_id": "human:hg38",
        "source_copy_id": copy_id,
        "homology_component_id": homology,
        "host_locus": chrom,
        "family_id": family,
        "source_kind": "natural_copy",
        "sequence": "ACGT" * 40,
    }


class LabelFreeClusterContractTests(unittest.TestCase):
    def test_split_groups_do_not_cross_copy_homology_or_locus(self):
        rows = [
            row("a", 10, "Fam_A", "hc_a", "copy_a"),
            row("b", 20, "Fam_B", "hc_a", "copy_b"),
            row("c", 2_000_010, "Fam_C", "hc_c", "copy_c"),
            row("d", 4_000_010, "Fam_D", "hc_d", "copy_d"),
            row("e", 4_000_020, "Fam_E", "hc_e", "copy_e"),
        ]
        split_rows, audit = MODULE.build_isolated_split(rows, seed=42, locus_block_bp=2_000_000)
        self.assertEqual(audit["family_labels_used_for_assignment"], False)
        self.assertEqual(audit["family_labels_read_for_assignment_or_split_audit"], False)
        self.assertIsNone(audit["family_support_external_audit"])
        self.assertEqual(audit["cross_split_source_copy"]["count"], 0)
        self.assertEqual(audit["cross_split_homology_component"]["count"], 0)
        self.assertEqual(audit["cross_split_locus_block"]["count"], 0)
        by_record = {item["record_id"]: item["split"] for item in split_rows}
        self.assertEqual(by_record[split_rows[0]["record_id"]], by_record[split_rows[1]["record_id"]])
        self.assertEqual(by_record[split_rows[3]["record_id"]], by_record[split_rows[4]["record_id"]])

    def test_views_are_same_record_reverse_complement_pair(self):
        first, second = MODULE.make_label_free_views("ACGTACGT", 3, seed=42)
        self.assertEqual(len(first), len(second))
        self.assertEqual(MODULE.reverse_complement("ACGTACGT"), "ACGTACGT")
        self.assertEqual(first.count("N"), 1)
        self.assertEqual(second.count("N"), 1)

    def test_kmer_shape_and_parameter_matching(self):
        self.assertEqual(len(MODULE.kmer_vector("ACGT" * 20, 6)), 4096)
        kmer_params = MODULE.mlp_parameter_count(4096, 256, 128)
        capacity_params = MODULE.mlp_parameter_count(1024, 938, 128)
        self.assertEqual(kmer_params, 1_081_728)
        self.assertEqual(capacity_params, 1_081_642)
        self.assertLessEqual(abs(kmer_params - capacity_params), 100)

    def test_nt_xent_targets_pair_only_by_position(self):
        self.assertEqual(MODULE.nt_xent_positive_indices(3), [3, 4, 5, 0, 1, 2])
        with self.assertRaises(ValueError):
            MODULE.nt_xent_positive_indices(1)

    def test_prior_query_exclusion_removes_identity_homology_and_locus(self):
        rows = [
            row("query", 10, "Fam_A", "hc_query", "copy_query"),
            row("same_homology", 200_000, "Fam_B", "hc_query", "copy_other"),
            row("same_locus", 49_999, "Fam_C", "hc_other", "copy_other2"),
            row("kept", 100_000, "Fam_D", "hc_kept", "copy_kept"),
        ]
        kept, audit = MODULE.exclude_prior_query_neighborhood(
            rows, [rows[0]["record_id"]], locus_block_bp=50_000
        )
        self.assertEqual([item["record_id"] for item in kept], [rows[3]["record_id"]])
        self.assertEqual(audit["excluded_by_record_id"], 1)
        self.assertEqual(audit["excluded_by_homology_component_after_id"], 1)
        self.assertEqual(audit["excluded_by_locus_block_after_id_and_homology"], 1)
        self.assertFalse(audit["prior_query_labels_or_scores_read"])

    def test_query_loader_reads_only_record_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queries.tsv"
            path.write_text("record_id\tfamily\tscore\nabc\tSECRET\t0.99\nabc\tOTHER\t0.01\n", encoding="utf-8")
            self.assertEqual(MODULE.load_query_record_ids(path), ["abc"])


if __name__ == "__main__":
    unittest.main()
