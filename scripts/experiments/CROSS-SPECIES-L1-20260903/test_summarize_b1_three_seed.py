#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "summarize_b1_three_seed", HERE / "summarize_b1_three_seed.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


SPECIES = list(MODULE.SPECIES)
PER_SPECIES = list(MODULE.PER_SPECIES_METRICS)
SUMMARY = list(MODULE.SUMMARY_METRICS)


def metrics(seed: int, bp_f1: float = 0.84, precision: float = 0.80, recall: float = 0.79) -> dict:
    per_species = {}
    for index, species in enumerate(SPECIES):
        row = {metric: 0.20 + index / 100 for metric in PER_SPECIES}
        row.update(
            {
                "bp_f1": bp_f1 + index / 1000,
                "bp_precision": precision + index / 1000,
                "bp_recall": recall + index / 1000,
                "segment_f1_iou_0_8": 0.70 + index / 1000,
                "boundary_f1_5bp": 0.60 + index / 1000,
                "boundary_f1_25bp": 0.65 + index / 1000,
                "short_prediction_rate": 0.10 + index / 1000,
                "fragments_per_truth": 1.00 + index / 1000,
                "split_rate": 0.20 + index / 1000,
                "missed_rate": 0.10 + index / 1000,
                "hardN_fp_rate": 0.02 + index / 1000,
            }
        )
        per_species[species] = row
    summary = {metric: 0.20 for metric in SUMMARY}
    summary.update(
        {
            "macro_bp_precision": precision + 0.0025,
            "macro_bp_recall": recall + 0.0025,
            "macro_bp_f1": bp_f1 + 0.0025,
            "macro_segment_f1_iou_0_8": 0.7025,
            "macro_boundary_f1_5bp": 0.6025,
            "macro_boundary_f1_25bp": 0.6525,
            "macro_short_prediction_rate": 0.1025,
            "macro_fragments_per_truth": 1.0025,
            "macro_split_rate": 0.2025,
            "macro_missed_rate": 0.1025,
            "macro_hardN_fp_rate": 0.0225,
            "minimum_species_bp_f1": bp_f1,
        }
    )
    return {
        "mode": "apply-only",
        "seed": seed,
        "observed_splits": ["DEV"],
        "per_species": per_species,
        "summary": summary,
    }


class SummarizeB1ThreeSeedTest(unittest.TestCase):
    def write_inputs(self, payloads: dict[int, dict]) -> tuple[tempfile.TemporaryDirectory, dict[int, Path]]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = {}
        for seed, payload in payloads.items():
            path = root / f"seed{seed}.json"
            path.write_text(json.dumps(payload))
            paths[seed] = path
        return temporary, paths

    def test_three_seed_gate_passes_and_topology_is_report_only(self):
        _, paths = self.write_inputs({seed: metrics(seed) for seed in MODULE.SEEDS})
        result = MODULE.summarize(paths)
        self.assertTrue(result["gate"]["all_pass"])
        self.assertEqual(result["failed_species"], [])
        self.assertEqual(result["decision"], "OPEN_E1_PREPARATION")
        self.assertTrue(result["initialization"]["all_seeds_from_same_h0_seed42_initialization"])
        self.assertEqual(result["initialization"]["claim_scope"], "continuation robustness only")
        self.assertFalse(result["topology_summary"]["gate_applied"])
        self.assertAlmostEqual(result["per_species_mean"]["human"]["bp_f1"], 0.84)
        self.assertAlmostEqual(result["three_seed_macro_species_bp_f1_mean"], 0.8425)

    def test_failed_species_selects_b0(self):
        payloads = {seed: metrics(seed) for seed in MODULE.SEEDS}
        payloads[17]["per_species"]["human"]["bp_recall"] = 0.60
        _, paths = self.write_inputs(payloads)
        result = MODULE.summarize(paths)
        self.assertFalse(result["gate"]["all_pass"])
        self.assertEqual(result["failed_species"], ["human"])
        self.assertEqual(result["decision"], "RUN_B0_FOR_FAILED_SPECIES")

    def test_macro_only_failure_has_no_b0_target(self):
        payloads = {
            seed: metrics(seed, bp_f1=0.81) for seed in MODULE.SEEDS
        }
        _, paths = self.write_inputs(payloads)
        result = MODULE.summarize(paths)
        self.assertFalse(result["gate"]["all_pass"])
        self.assertEqual(result["failed_species"], [])
        self.assertEqual(result["decision"], "INTERNAL_GATE_FAIL_NO_B0_TARGET")

    def test_wrong_seed_species_and_nonfinite_are_rejected(self):
        payloads = {seed: metrics(seed) for seed in MODULE.SEEDS}
        payloads[42]["seed"] = 17
        _, paths = self.write_inputs(payloads)
        with self.assertRaisesRegex(ValueError, "wrong seed"):
            MODULE.summarize(paths)

        payloads = {seed: metrics(seed) for seed in MODULE.SEEDS}
        payloads[20260903]["per_species"]["horse"] = payloads[20260903]["per_species"].pop("mouse")
        _, paths = self.write_inputs(payloads)
        with self.assertRaisesRegex(ValueError, "frozen six species"):
            MODULE.summarize(paths)

        payloads = {seed: metrics(seed) for seed in MODULE.SEEDS}
        payloads[17]["summary"]["macro_bp_f1"] = "NaN"
        _, paths = self.write_inputs(payloads)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            MODULE.summarize(paths)


if __name__ == "__main__":
    unittest.main()
