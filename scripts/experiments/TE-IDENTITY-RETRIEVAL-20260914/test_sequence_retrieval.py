#!/usr/bin/env python3
"""Contract tests for the k-mer retrieval runner."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sequence_retrieval", HERE / "sequence_retrieval.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def row(record_id, split, family="Fam_A", component=None, sequence="ACGT" * 80):
    component = component or ("hc|%s" % record_id)
    return {
        "record_id": record_id,
        "source_kind": "natural_copy",
        "assembly": "hg38",
        "host_id": "human:hg38",
        "host_locus": "chr1",
        "source_copy_id": "coord|%s" % record_id,
        "homology_component_id": component,
        "family_id": family,
        "family_level": "repeat_family",
        "split": split,
        "sequence": sequence,
    }


class SequenceRetrievalTest(unittest.TestCase):
    def test_scores_only_matched_families_and_reports_annotation_level(self):
        rows = [row("tr%d" % index, "train", component="hc|tr%d" % index) for index in range(4)]
        rows += [row("cal", "cal", component="hc|cal"), row("eval", "eval", component="hc|eval")]
        rows.append({
            "record_id": "consensus-A",
            "source_kind": "consensus",
            "family_id": "Fam_A",
            "family_level": "family",
            "sequence": "ACGT" * 80,
            "origin_id": "consensus-A",
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.jsonl"
            manifest.write_text("\n".join(json.dumps(item) for item in rows) + "\n", encoding="utf-8")
            status = module.run(manifest, root / "out")
            self.assertEqual(status["status"], "PASS_NUMERIC_ANNOTATION_LEVEL")
            self.assertEqual(status["families"], 1)
            metrics = json.loads((root / "out" / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["scientific_claim_status"], "ANNOTATION_LEVEL_ONLY")
            self.assertIn("single_consensus", metrics["methods"])
            self.assertIn("single_train_medoid", metrics["methods"])
            self.assertEqual(
                len(metrics["methods"]["single_train_medoid"]["prototype_record_ids"]["Fam_A"]),
                1,
            )
            self.assertFalse(status["real_glm_embedding"])

    def test_non_identity_manifest_fails_closed(self):
        rows = [row("x", "train", component="")]
        rows[0]["source_copy_id"] = ""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            status = module.run(manifest, root / "out")
            self.assertEqual(status["status"], "NOTRUN_IDENTITY_AUDIT")
            self.assertFalse((root / "out" / "metrics.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
