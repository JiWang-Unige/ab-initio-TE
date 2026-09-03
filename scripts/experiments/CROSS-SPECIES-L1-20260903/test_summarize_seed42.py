#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "summarize_seed42", HERE / "summarize_seed42.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


SPECIES = list(MODULE.SPECIES)
PER_SPECIES = (
    "bp_precision",
    "bp_recall",
    "bp_f1",
    "segment_f1_iou_0_8",
    "boundary_f1_5bp",
    "boundary_f1_25bp",
    "short_prediction_rate",
    "fragments_per_truth",
    "split_rate",
    "missed_rate",
    "hardN_fp_rate",
)
SUMMARY = (
    "macro_bp_precision",
    "macro_bp_recall",
    "macro_bp_f1",
    "macro_segment_f1_iou_0_8",
    "macro_boundary_f1_5bp",
    "macro_boundary_f1_25bp",
    "macro_short_prediction_rate",
    "macro_fragments_per_truth",
    "macro_split_rate",
    "macro_missed_rate",
    "macro_hardN_fp_rate",
    "minimum_species_bp_f1",
)


def metrics(bp_f1: list[float], fragments: list[float], split: list[float]) -> dict:
    per_species = {}
    for index, species in enumerate(SPECIES):
        row = {metric: 0.2 for metric in PER_SPECIES}
        row.update(
            {
                "bp_f1": bp_f1[index],
                "segment_f1_iou_0_8": 0.70,
                "boundary_f1_5bp": 0.60,
                "fragments_per_truth": fragments[index],
                "split_rate": split[index],
                "missed_rate": 0.10,
            }
        )
        per_species[species] = row
    summary = {metric: 0.2 for metric in SUMMARY}
    summary.update(
        {
            "macro_bp_f1": sum(bp_f1) / len(bp_f1),
            "macro_segment_f1_iou_0_8": 0.70,
            "macro_boundary_f1_5bp": 0.60,
            "macro_fragments_per_truth": sum(fragments) / len(fragments),
            "macro_split_rate": sum(split) / len(split),
            "macro_missed_rate": 0.10,
            "minimum_species_bp_f1": min(bp_f1),
        }
    )
    return {
        "mode": "apply-only",
        "seed": 42,
        "observed_splits": ["DEV"],
        "per_species": per_species,
        "summary": summary,
    }


class SummarizeSeed42Test(unittest.TestCase):
    def write_inputs(self, payloads: dict[str, dict]) -> tuple[Path, dict]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = {}
        for name, payload in payloads.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload))
            paths[name] = path
        return root, paths

    def test_all_frozen_checks_pass_selects_b2_and_reports_attribution(self):
        base = metrics([0.80, 0.82] * 3, [1.00, 1.00] * 3, [0.10, 0.20] * 3)
        payloads = {
            "I0": metrics([0.70, 0.72] * 3, [1.10, 1.20] * 3, [0.10, 0.20] * 3),
            "H1": metrics([0.75, 0.77] * 3, [1.05, 1.10] * 3, [0.10, 0.20] * 3),
            "B1": base,
            "B2": metrics([0.83, 0.85] * 3, [1.20, 1.20] * 3, [0.11, 0.21] * 3),
        }
        _, paths = self.write_inputs(payloads)
        result = MODULE.summarize(
            paths["I0"], paths["H1"], paths["B1"], paths["B2"]
        )
        self.assertTrue(result["gate"]["all_pass"])
        self.assertEqual(result["selected_arm"], "B2")
        self.assertTrue(result["seed42_engineering_only"])
        self.assertTrue(result["three_seed_gate_required"])
        self.assertFalse(result["three_seed_gate_replaced"])
        self.assertAlmostEqual(
            result["attribution"]["I0_to_H1"]["per_species"]["human"]["bp_f1"],
            0.05,
        )
        self.assertAlmostEqual(
            result["attribution"]["H1_to_B1"]["summary"]["macro_bp_f1"],
            0.05,
        )
        self.assertEqual(len(result["gate"]["checks"]), 9)

    def test_any_failed_check_keeps_b1_and_zero_baseline_relative_increase_fails(self):
        payloads = {
            "I0": metrics([0.70, 0.72] * 3, [1.10, 1.20] * 3, [0.10, 0.20] * 3),
            "H1": metrics([0.75, 0.77] * 3, [1.05, 1.10] * 3, [0.10, 0.20] * 3),
            "B1": metrics([0.80, 0.82] * 3, [1.00, 1.00] * 3, [0.00, 0.20] * 3),
            "B2": metrics([0.81, 0.83] * 3, [1.20, 1.20] * 3, [0.01, 0.21] * 3),
        }
        _, paths = self.write_inputs(payloads)
        result = MODULE.summarize(
            paths["I0"], paths["H1"], paths["B1"], paths["B2"]
        )
        self.assertFalse(result["gate"]["all_pass"])
        self.assertEqual(result["selected_arm"], "B1")
        split_check = next(
            item
            for item in result["gate"]["checks"]
            if item["name"] == "per_species_split_rate_relative_increase"
        )
        self.assertFalse(split_check["pass"])
        self.assertIsNone(
            split_check["evidence"]["relative_increase_by_species"]["human"]
        )

    def test_mismatched_species_are_rejected(self):
        payloads = {
            "I0": metrics([0.70, 0.72] * 3, [1.10, 1.20] * 3, [0.10, 0.20] * 3),
            "H1": metrics([0.75, 0.77] * 3, [1.05, 1.10] * 3, [0.10, 0.20] * 3),
            "B1": metrics([0.80, 0.82] * 3, [1.00, 1.00] * 3, [0.10, 0.20] * 3),
            "B2": metrics([0.81, 0.83] * 3, [1.00, 1.00] * 3, [0.10, 0.20] * 3),
        }
        payloads["B2"]["per_species"]["horse"] = payloads["B2"][
            "per_species"
        ].pop("mouse")
        _, paths = self.write_inputs(payloads)
        with self.assertRaisesRegex(ValueError, "frozen six species"):
            MODULE.summarize(
                paths["I0"], paths["H1"], paths["B1"], paths["B2"]
            )


if __name__ == "__main__":
    unittest.main()
