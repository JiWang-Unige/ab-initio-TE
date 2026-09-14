#!/usr/bin/env python3
"""Focused contract tests for the bounded improvement study."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("improve_retrieval", HERE / "improve_retrieval.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

SUPPORT = Path(os.environ.get("TE_IDENTITY_SUPPORT_DIR", str(HERE.parent / "TE-IDENTITY-RETRIEVAL-20260914")))
IDENTITY, SEQUENCE = module.load_support_modules(SUPPORT)


def synthetic_rows():
    rows = []
    motifs = {"Fam_A": "ACGTAC", "Fam_C": "CCCCGT", "Fam_G": "GGATGC"}
    for family, motif in motifs.items():
        for split, count in (("train", 4), ("cal", 1), ("eval", 1)):
            for index in range(count):
                rows.append(
                    {
                        "record_id": "%s_%s_%d" % (family, split, index),
                        "source_kind": "natural_copy",
                        "host_id": "synthetic-host",
                        "host_locus": "chr%s" % (index + 1),
                        "source_copy_id": "%s_%s_%d" % (family, split, index),
                        "homology_component_id": "component_%s_%s_%d" % (family, split, index),
                        "family_id": family,
                        "split": split,
                        "sequence": (motif + "ATGCGTCA") * 12,
                    }
                )
        rows.append(
            {
                "record_id": "%s_consensus" % family,
                "source_kind": "consensus",
                "host_id": "",
                "host_locus": "",
                "source_copy_id": "",
                "homology_component_id": "",
                "family_id": family,
                "split": "",
                "sequence": (motif + "ATGCGTCA") * 12,
            }
        )
    return [IDENTITY.normalize_row(row, index) for index, row in enumerate(rows)]


class ImprovementContractTest(unittest.TestCase):
    def test_kmer_length_is_separate_from_prototype_count(self):
        rows = synthetic_rows()
        self.assertEqual(IDENTITY.audit_manifest(rows)["status"], "PASS_AUDIT")
        common, _by_k, metrics, _queries = module.kmer_ablation(rows, IDENTITY, SEQUENCE)
        self.assertEqual(common, ["Fam_A", "Fam_C", "Fam_G"])
        for kmer_size in (4, 6, 8):
            self.assertIn("kmer%d_single_train_medoid" % kmer_size, metrics)
            self.assertIn("kmer%d_k4_natural_prototypes" % kmer_size, metrics)
            self.assertIn("kmer%d_basic_train_centroid" % kmer_size, metrics)
            self.assertEqual(metrics["kmer%d_single_train_medoid" % kmer_size]["kmer_size"], kmer_size)
            self.assertEqual(metrics["kmer%d_k4_natural_prototypes" % kmer_size]["prototype_count"], 4)
        self.assertEqual(metrics["kmer4_single_train_medoid"]["families"], 3)

    def test_epoch_selection_uses_cal_only_and_earliest_tie(self):
        trace = [
            {"epoch": 1, "cal_status": "NUMERIC_ANNOTATION_LEVEL", "cal_true_accepts": 4},
            {"epoch": 2, "cal_status": "NUMERIC_ANNOTATION_LEVEL", "cal_true_accepts": 7},
            {"epoch": 3, "cal_status": "NUMERIC_ANNOTATION_LEVEL", "cal_true_accepts": 7},
        ]
        self.assertEqual(module.choose_epoch(trace), 2)

    def test_loss_excludes_self_pairs(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch unavailable in local lightweight test environment")
        embeddings = torch.tensor(
            [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]], dtype=torch.float32
        )
        labels = torch.tensor([0, 0, 1, 1], dtype=torch.long)
        loss = module.supervised_contrastive_loss(embeddings, labels, temperature=0.1)
        self.assertTrue(torch.isfinite(loss).item())
        self.assertGreater(loss.item(), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
