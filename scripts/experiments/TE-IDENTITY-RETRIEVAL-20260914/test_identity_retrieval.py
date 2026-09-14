#!/usr/bin/env python3
"""Contract tests for the identity-aware retrieval planner."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("identity_retrieval", HERE / "identity_retrieval.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def natural(record_id, host, copy, homology, split, family="Fam_A"):
    return {
        "record_id": record_id,
        "source_kind": "natural_copy",
        "assembly": host,
        "host_id": host,
        "source_copy_id": copy,
        "homology_component_id": homology,
        "family_id": family,
        "split": split,
        "sequence": "ACGT" * 32,
    }


class IdentityRetrievalContractTest(unittest.TestCase):
    def complete_rows(self):
        rows = [
            natural("tr0", "host-tr0", "copy0", "hom0", "train"),
            natural("tr1", "host-tr1", "copy1", "hom1", "train"),
            natural("tr2", "host-tr2", "copy2", "hom2", "train"),
            natural("tr3", "host-tr3", "copy3", "hom3", "train"),
            natural("cal", "host-cal", "copy-cal", "hom-cal", "cal"),
            natural("ev", "host-eval", "copy-eval", "hom-eval", "eval"),
            {
                "record_id": "consensus-A",
                "source_kind": "consensus",
                "family_id": "Fam_A",
                "family_level": "family",
                "sequence": "TGCA" * 32,
                "origin_id": "consensus-A",
            },
        ]
        return rows

    def test_complete_identity_is_ready_but_not_a_scientific_result(self):
        rows = self.complete_rows()
        audit = module.audit_manifest(rows)
        self.assertEqual(audit["status"], "PASS_AUDIT")
        self.assertEqual(audit["complete_natural_copy_rows"], 6)
        availability = module.protocol_availability(rows, audit)
        self.assertEqual(availability["protocols"]["single_consensus"]["status"], "READY_PROTOCOL")
        self.assertEqual(availability["protocols"]["single_train_medoid"]["status"], "READY_PROTOCOL")
        self.assertEqual(availability["protocols"]["k4_natural_prototypes"]["status"], "READY_PROTOCOL")
        self.assertEqual(availability["protocols"]["random4_natural_prototypes"]["status"], "READY_PROTOCOL")
        self.assertEqual(availability["protocols"]["basic_sequence_features"]["status"], "READY_PROTOCOL")
        self.assertEqual(availability["protocols"]["glm_embedding"]["status"], "NOTRUN")
        contract = module.protocol_contract()
        self.assertIn("single_train_medoid", contract["protocols"])
        self.assertIn("host is contextual", contract["identity_rules"]["split_rule"])

    def test_consensus_rows_never_supply_natural_copy_count(self):
        rows = [
            {
                "record_id": "c0",
                "source_kind": "consensus",
                "family_id": "Fam_A",
                "sequence": "ACGT" * 30,
                "origin_id": "consensus-A",
            },
            {
                "record_id": "c1",
                "source_kind": "consensus",
                "family_id": "Fam_A",
                "sequence": "CGTA" * 30,
                "origin_id": "consensus-A",
            },
        ]
        audit = module.audit_manifest(rows)
        self.assertEqual(audit["status"], "NOTRUN_NO_NATURAL_COPIES")
        self.assertEqual(audit["natural_copy_rows"], 0)
        self.assertEqual(audit["consensus_rows_with_identity_ids"], 0)
        self.assertTrue(audit["consensus_fragments_are_not_natural_copies"])

    def test_missing_ids_are_blocked_and_do_not_form_a_key(self):
        rows = [
            natural("a", "host-a", "", "hom-a", "train"),
            natural("b", "host-a", "", "hom-a", "train"),
        ]
        audit = module.audit_manifest(rows)
        self.assertEqual(audit["status"], "BLOCKED_IDENTITY_FIELDS")
        self.assertEqual(audit["missing_identity_counts"]["source_copy_id"], 2)
        self.assertIsNone(module.canonical_copy_key(module.normalize_row(rows[0], 0)))

    def test_split_overlap_is_detected_from_materialized_identity(self):
        rows = [
            natural("a", "host-a", "copy-a", "hom-a", "train"),
            natural("b", "host-a", "copy-a", "hom-a", "eval"),
        ]
        audit = module.audit_manifest(rows)
        self.assertEqual(audit["status"], "BLOCKED_IDENTITY_FIELDS")
        self.assertGreater(audit["cross_split_identity_overlap"]["source_copy_id"]["count"], 0)
        self.assertGreater(audit["cross_split_identity_overlap"]["homology_component_id"]["count"], 0)
        self.assertEqual(audit["host_roles"]["host-a"], ["eval", "train"])

    def test_fixed_calibration_rule_is_deterministic(self):
        scores = [0.95, 0.90, 0.60, 0.20, 0.10]
        labels = [1, 0, 1, 0, 0]
        threshold = module.calibrated_threshold(scores, labels, max_false_accept_rate=0.0)
        self.assertEqual(threshold, 0.95)
        self.assertEqual(threshold, module.calibrated_threshold(scores, labels, 0.0))

    def test_default_run_without_input_is_typed_notrun(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = module.run(None, Path(temporary) / "out")
            self.assertEqual(result["status"], "NOTRUN_INPUT_MISSING")
            self.assertFalse(result["scores_written"])
            self.assertTrue((Path(temporary) / "out" / "protocol_contract.json").is_file())
            self.assertTrue((Path(temporary) / "out" / "status.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
