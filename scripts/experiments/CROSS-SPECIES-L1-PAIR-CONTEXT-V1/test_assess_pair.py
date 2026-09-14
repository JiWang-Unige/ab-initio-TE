"""Decision-changing boundary tests for the newly approved release rule."""
import copy
import unittest

import assess_pair as decision


def panels(arm, seed=42, f1=0.85):
    old = arm == "D"
    row = {"bp_f1": f1, "bp_precision": 0.85, "bp_recall": 0.85,
           "bp_average_precision": 0.9, "segment_f1_iou_0_8": 0.8,
           "boundary_f1_5bp": 0.8, "fragments_per_truth": 1.0,
           "split_rate": 0.1, "missed_rate": 0.1, "hardN_fp_rate": 0.01}
    return {split: {
        "experiment": decision.helpers.OLD_EXPERIMENT if old else decision.PROTOCOL,
        "protocol": decision.helpers.OLD_EXPERIMENT + "-V1" if old else decision.PROTOCOL,
        "run_role": "upstream_coverage_pilot" if old else "pair_context_registered_evaluation",
        "arm": arm, "seed": seed, "split": split, "calibration_scope": "six-species-shared",
        "conf_evaluated": False,
        "species": list(decision.helpers.SPECIES) if split == "DEV" else [decision.helpers.WORM],
        "per_species": {s: copy.deepcopy(row) for s in (decision.helpers.SPECIES if split == "DEV" else [decision.helpers.WORM])},
        "summary": {"macro_bp_f1": f1, "macro_hardN_fp_rate": 0.01},
    } for split in ("DEV", "SCREEN")}


class PairDecisionTests(unittest.TestCase):
    def setUp(self):
        self.candidate, self.control, self.anchor = panels("PAIR8", f1=0.855), panels("BLOCK4"), panels("D")

    def run_gate(self):
        return decision.assess(self.candidate, self.control, self.anchor, 42)

    def test_exact_effect_bound_releases(self):
        self.assertTrue(self.run_gate()["release_seed17"])

    def test_each_worm_panel_and_reference_required(self):
        for reference in (self.control, self.anchor):
            for split in ("DEV", "SCREEN"):
                reference[split]["per_species"]["c_elegans"]["bp_f1"] = 0.850001
                self.assertFalse(self.run_gate()["release_seed17"])
                reference[split]["per_species"]["c_elegans"]["bp_f1"] = 0.85

    def test_absolute_readiness_blocks_seed17(self):
        self.candidate["DEV"]["per_species"]["human"]["bp_precision"] = 0.749
        self.assertFalse(self.run_gate()["release_seed17"])

    def test_each_guard_blocks(self):
        mutations = {"bp_average_precision": 0.8979, "segment_f1_iou_0_8": 0.7499,
                     "boundary_f1_5bp": 0.7499, "fragments_per_truth": 1.2501,
                     "split_rate": 0.12501, "missed_rate": 0.13001}
        for key, value in mutations.items():
            with self.subTest(key=key):
                row = self.candidate["SCREEN"]["per_species"]["c_elegans"]
                old = row[key]
                row[key] = value
                self.assertFalse(self.run_gate()["release_seed17"])
                row[key] = old
        self.candidate["DEV"]["summary"]["macro_hardN_fp_rate"] = 0.015001
        self.assertFalse(self.run_gate()["release_seed17"])

    def test_zero_reference_no_smoothing(self):
        for reference in (self.control, self.anchor):
            reference["SCREEN"]["per_species"]["c_elegans"]["split_rate"] = 0
        self.candidate["SCREEN"]["per_species"]["c_elegans"]["split_rate"] = 0
        self.assertTrue(self.run_gate()["release_seed17"])
        self.candidate["SCREEN"]["per_species"]["c_elegans"]["split_rate"] = 1e-12
        self.assertFalse(self.run_gate()["release_seed17"])

    def test_seed17_requires_release_and_strict_positive_both_panels(self):
        previous = self.run_gate()
        c, b, d = panels("PAIR8", 17, 0.850001), panels("BLOCK4", 17), panels("D", 17)
        with self.assertRaises(ValueError):
            decision.assess(c, b, d, 17)
        self.assertTrue(decision.assess(c, b, d, 17, previous)["two_seed_internal_candidate"])
        for split in ("DEV", "SCREEN"):
            c[split]["per_species"]["c_elegans"]["bp_f1"] = 0.85
            self.assertFalse(decision.assess(c, b, d, 17, previous)["scientific_gate_pass"])
            c[split]["per_species"]["c_elegans"]["bp_f1"] = 0.850001

    def test_wrong_seed_is_not_scientific_failure(self):
        self.anchor["DEV"]["seed"] = 17
        with self.assertRaises(ValueError):
            self.run_gate()


if __name__ == "__main__":
    unittest.main()
