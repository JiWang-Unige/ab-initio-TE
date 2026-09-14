#!/usr/bin/env python3
"""Contract tests for embedding-only retrieval without a model dependency."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("glm_retrieval", HERE / "glm_retrieval.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def natural(record_id, family, split, index):
    return {
        "record_id": record_id,
        "source_kind": "natural_copy",
        "assembly": "hg38",
        "host_id": "human:hg38",
        "host_locus": "chr1",
        "source_copy_id": "coord|%s" % record_id,
        "homology_component_id": "hc|%s" % record_id,
        "family_id": family,
        "family_level": "repeat_family",
        "split": split,
        "sequence": ("ACGT" if family == "Fam_A" else "TGCA") * 80,
    }


class GlmRetrievalTest(unittest.TestCase):
    def test_embedding_table_retrieval_uses_real_vector_input_and_fixed_arms(self):
        rows = []
        vectors = {}
        for family, axis in (("Fam_A", [1.0, 0.0, 0.0]), ("Fam_B", [0.0, 1.0, 0.0])):
            for index in range(4):
                record_id = "%s-tr%d" % (family, index)
                rows.append(natural(record_id, family, "train", index))
                vectors[record_id] = axis
            for split, record_id in (("cal", "%s-cal" % family), ("eval", "%s-eval" % family)):
                rows.append(natural(record_id, family, split, 10))
                vectors[record_id] = axis
            consensus_id = "%s-consensus" % family
            rows.append({
                "record_id": consensus_id,
                "source_kind": "consensus",
                "family_id": family,
                "family_level": "family",
                "sequence": ("ACGT" if family == "Fam_A" else "TGCA") * 80,
            })
            vectors[consensus_id] = axis
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.jsonl"
            manifest.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            ids = [row["record_id"] for row in rows]
            ids_path = root / "embedding_ids.json"
            ids_path.write_text(json.dumps(ids) + "\n", encoding="utf-8")
            embedding_path = root / "embeddings.jsonl"
            embedding_path.write_text(
                "\n".join(json.dumps({"record_id": key, "embedding": vectors[key]}) for key in ids) + "\n",
                encoding="utf-8",
            )
            meta = root / "embedding_meta.json"
            meta.write_text(json.dumps({
                "model_id": module.MODEL_ID,
                "pooling": "mean",
                "special_tokens_excluded": True,
                "pretraining_exposure_status": "UNRESOLVED",
            }) + "\n", encoding="utf-8")
            status = module.run(manifest, embedding_path, ids_path, meta, root / "out")
            self.assertEqual(status["status"], "PASS_NUMERIC_ANNOTATION_LEVEL")
            self.assertTrue(status["real_glm_embedding"])
            metrics = json.loads((root / "out" / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["embedding_model_id"], module.MODEL_ID)
            self.assertIn("glm_single_train_medoid", metrics["methods"])
            self.assertIn("glm_k4_natural_prototypes", metrics["methods"])
            self.assertIn("glm_random4_natural_prototypes", metrics["methods"])
            self.assertIn("glm_train_centroid", metrics["methods"])
            self.assertTrue(metrics["exploratory_arm"])

    def test_embedding_ids_must_match_manifest_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ids = root / "ids.json"
            ids.write_text("[]\n", encoding="utf-8")
            emb = root / "embeddings.jsonl"
            emb.write_text("\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.load_embedding_table(emb, ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
