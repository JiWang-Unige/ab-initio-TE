#!/usr/bin/env python3
"""Focused tests for the Phase 1 bounded association baseline."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fragment_linking_phase1", HERE / "fragment_linking_phase1.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class FragmentLinkingPhase1Test(unittest.TestCase):
    def setUp(self):
        self.fragments = module.make_fixture()
        module.validate_fragments(self.fragments)

    def test_fixture_is_independent_insertion_data(self):
        self.assertTrue(all(fragment.sequence_origin == "independent_insertion_semisim" for fragment in self.fragments))
        self.assertTrue(all(fragment.annotation_provenance == module.ENGINEERING_ONLY for fragment in self.fragments))
        self.assertFalse(any("consensus" in fragment.sequence_origin for fragment in self.fragments))

    def test_role_partition_is_materialized_and_leakage_is_detected(self):
        partition = module.validate_role_partition(self.fragments)
        self.assertTrue(partition["pass"])
        first = self.fragments[0]
        leaked = dataclasses.replace(first, role="eval")
        mutated = [leaked] + self.fragments[1:]
        self.assertFalse(module.validate_role_partition(mutated)["pass"])
        self.assertGreater(module.validate_role_partition(mutated)["cross_role_overlap"]["source_copy_id"]["count"], 0)

    def test_host_is_a_pair_gate_and_empty_truth_is_unresolved(self):
        pairs = module.build_pairs(self.fragments, max_distance=25)
        self.assertFalse(any({pair["left_id"], pair["right_id"]} == {"ev_regular_left", "host2_near"} for pair in pairs))
        unresolved = [pair for pair in pairs if pair["truth_pair_status"] == module.UNRESOLVED]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["truth_same_insertion"], None)

    def test_b1_abstains_on_missing_orientation_without_relabeling_truth(self):
        pairs = module.build_pairs(self.fragments, max_distance=25)
        target = next(
            pair for pair in pairs
            if {pair["left_id"], pair["right_id"]} == {"ev_unknown_left", "ev_unknown_right"}
        )
        self.assertEqual(target["truth_pair_status"], module.KNOWN)
        self.assertEqual(target["truth_same_insertion"], 1)
        self.assertEqual(target["pred_orientation_match"], 0)
        self.assertEqual(target["b1_link"], 0)

    def test_bounded_baseline_is_calibrated_and_does_not_fill_gaps(self):
        with tempfile.TemporaryDirectory() as temporary:
            metrics = module.run(Path(temporary) / "out")
            self.assertEqual(metrics["status"], module.ENGINEERING_ONLY)
            self.assertTrue(metrics["invariants"]["intervals_unchanged"])
            self.assertFalse(metrics["invariants"]["gap_filling_applied"])
            self.assertFalse(metrics["invariants"]["material_mask_changed"])
            self.assertEqual(metrics["known_truth_policy"]["unresolved_as_negative"], 0)
            self.assertTrue((Path(temporary) / "out" / "calibration.json").is_file())
            status = json.loads((Path(temporary) / "out" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["scientific_claim_status"], "NOTRUN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
