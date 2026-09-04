#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "summarize_b0_c_elegans", HERE / "summarize_b0_c_elegans.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload(seed: int, specialist: bool) -> dict:
    row = {
        "bp_precision": 0.82 if specialist else 0.79,
        "bp_recall": 0.91 if specialist else 0.73,
        "bp_f1": 0.86 if specialist else 0.76,
        "bp_average_precision": 0.84 if specialist else 0.80,
        "segment_f1_iou_0_8": 0.31 if specialist else 0.28,
        "boundary_f1_5bp": 0.12 if specialist else 0.11,
        "boundary_f1_25bp": 0.24 if specialist else 0.22,
        "short_prediction_rate": 0.50,
        "fragments_per_truth": 1.00,
        "split_rate": 0.12,
        "missed_rate": 0.18 if specialist else 0.29,
        "hardN_fp_rate": 0.06,
    }
    return {
        "mode": "apply-only",
        "seed": seed,
        "observed_splits": ["DEV"],
        "per_species": {"c_elegans": row},
    }


class SummarizeB0CElegansTest(unittest.TestCase):
    def write_inputs(self, specialist_ap: float = 0.84):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shared_paths = {}
        specialist_paths = {}
        for seed in MODULE.SEEDS:
            shared_path = root / f"shared_{seed}.json"
            specialist_path = root / f"specialist_{seed}.json"
            shared_path.write_text(json.dumps(payload(seed, False)))
            candidate = payload(seed, True)
            candidate["per_species"]["c_elegans"]["bp_average_precision"] = specialist_ap
            specialist_path.write_text(json.dumps(candidate))
            shared_paths[seed] = shared_path
            specialist_paths[seed] = specialist_path
        return shared_paths, specialist_paths

    def test_complete_recovery_gate_passes_but_does_not_admit_conditional_model(self):
        shared, specialist = self.write_inputs()
        result = MODULE.summarize(shared, specialist)
        self.assertTrue(result["gate"]["all_pass"])
        self.assertEqual(result["decision"], "B0_RECOVERABLE_SPECIALIST_GAP")
        self.assertFalse(result["conditional_model_admission"])
        self.assertTrue(result["external_remains_sealed"])

    def test_auprc_gain_failure_closes_recovery_gate(self):
        shared, specialist = self.write_inputs(specialist_ap=0.82)
        result = MODULE.summarize(shared, specialist)
        self.assertFalse(result["gate"]["all_pass"])
        self.assertEqual(result["decision"], "B0_RECOVERY_GATE_FAIL")
        failed = [item["name"] for item in result["gate"]["checks"] if not item["pass"]]
        self.assertEqual(
            failed,
            [
                "seed17_bp_average_precision_gain",
                "seed42_bp_average_precision_gain",
                "seed20260903_bp_average_precision_gain",
            ],
        )

    def test_wrong_species_is_rejected(self):
        shared, specialist = self.write_inputs()
        wrong = json.loads(shared[17].read_text())
        wrong["per_species"]["human"] = wrong["per_species"].pop("c_elegans")
        shared[17].write_text(json.dumps(wrong))
        with self.assertRaisesRegex(ValueError, "must contain only c_elegans"):
            MODULE.summarize(shared, specialist)


if __name__ == "__main__":
    unittest.main()
