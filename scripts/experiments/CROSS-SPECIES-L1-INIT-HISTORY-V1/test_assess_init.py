import argparse
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assess = load_module("assess_init")


def pair(arm, seed=42):
    result = {}
    for split in ("DEV", "SCREEN"):
        old = arm == "D"
        species = [assess.WORM] if split == "SCREEN" else list(assess.SPECIES)
        result[split] = {
            "experiment": assess.OLD_EXPERIMENT if old else assess.EXPERIMENT_ID,
            "protocol": assess.OLD_EXPERIMENT + "-V1" if old else assess.PROTOCOL,
            "run_role": "upstream_coverage_pilot" if old else assess.RUN_ROLE,
            "arm": arm, "seed": seed, "split": split, "species": species,
            "calibration_scope": "six-species-shared", "conf_evaluated": False,
            "per_species": {sp: {
                "bp_f1": .85 if arm == "P0R" or split == "DEV" else .83,
                "bp_precision": .85, "bp_recall": .85, "bp_average_precision": .9,
                "segment_f1_iou_0_8": .4, "boundary_f1_5bp": .3,
                "fragments_per_truth": 1., "split_rate": .2, "missed_rate": .1,
            } for sp in species},
            "summary": {"macro_bp_f1": .85, "macro_hardN_fp_rate": .05},
        }
    return result


class AssessmentTest(unittest.TestCase):
    def setUp(self):
        self.p, self.h, self.d = pair("P0R"), pair("H0R"), pair("D")

    def run_gate(self, seed=42, previous=None):
        return assess.assess_seed(self.p, self.h, self.d, seed, previous)

    def test_positive_releases_seed17_but_not_freeze_or_conf(self):
        result = self.run_gate()
        self.assertTrue(result["release_seed17"])
        self.assertTrue(result["absolute_readiness"]["pass"])
        self.assertFalse(result["freeze_ready"])
        self.assertFalse(result["conf_opening_authorized"])
        self.assertIn("historical", result["conf_status"])

    def test_beating_only_reset_control_does_not_release(self):
        self.d["SCREEN"]["per_species"][assess.WORM]["bp_f1"] = .85
        result = self.run_gate()
        self.assertTrue(result["contrasts"]["P0R_minus_H0R"]["pass"])
        self.assertFalse(result["scientific_gate_pass"])
        self.assertFalse(result["release_seed17"])

    def test_all_exact_additive_and_multiplicative_boundaries_pass(self):
        for reference in (self.h, self.d):
            reference["SCREEN"]["per_species"][assess.WORM]["bp_f1"] = .84
        for split in ("SCREEN", "DEV"):
            for sp, row in self.p[split]["per_species"].items():
                row.update(segment_f1_iou_0_8=.35, boundary_f1_5bp=.25,
                           fragments_per_truth=1.25, split_rate=.25, missed_rate=.13)
                if sp == assess.WORM:
                    row["bp_average_precision"] = .898
                elif split == "DEV":
                    row["bp_f1"] = .84
        self.p["DEV"]["summary"]["macro_hardN_fp_rate"] = .055
        self.assertTrue(self.run_gate()["scientific_gate_pass"])

    def test_each_preregistered_guard_can_stop(self):
        mutations = [
            ("SCREEN", assess.WORM, "bp_f1", .839999),
            ("DEV", assess.WORM, "bp_f1", .849999),
            ("SCREEN", assess.WORM, "bp_average_precision", .897999),
            ("DEV", assess.WORM, "bp_average_precision", .897999),
            ("DEV", "human", "bp_f1", .839999),
            ("DEV", "mouse", "segment_f1_iou_0_8", .349999),
            ("SCREEN", assess.WORM, "boundary_f1_5bp", .249999),
            ("DEV", "chicken", "fragments_per_truth", 1.250001),
            ("SCREEN", assess.WORM, "split_rate", .250001),
            ("DEV", "pig", "missed_rate", .130001),
        ]
        for split, species, key, value in mutations:
            with self.subTest(split=split, species=species, key=key):
                candidate = copy.deepcopy(self.p)
                candidate[split]["per_species"][species][key] = value
                self.assertFalse(assess.assess_seed(candidate, self.h, self.d, 42)["scientific_gate_pass"])
        self.p["DEV"]["summary"]["macro_hardN_fp_rate"] = .055001
        self.assertFalse(self.run_gate()["scientific_gate_pass"])

    def test_zero_reference_geometry_is_not_discarded_or_divided(self):
        for key in ("split_rate", "fragments_per_truth"):
            with self.subTest(key=key):
                for arm in (self.p, self.h, self.d):
                    arm["SCREEN"]["per_species"][assess.WORM][key] = 0
                self.assertTrue(self.run_gate()["scientific_gate_pass"])
                self.p["SCREEN"]["per_species"][assess.WORM][key] = 1e-20
                self.assertFalse(self.run_gate()["scientific_gate_pass"])
                self.p["SCREEN"]["per_species"][assess.WORM][key] = 0

    def test_seed17_only_requires_positive_screen_gain_and_same_guards(self):
        previous = self.run_gate()
        self.p, self.h, self.d = pair("P0R", 17), pair("H0R", 17), pair("D", 17)
        for arm in (self.h, self.d):
            arm["SCREEN"]["per_species"][assess.WORM]["bp_f1"] = .849999
        self.assertTrue(self.run_gate(17, previous)["freeze_ready"])
        self.d["SCREEN"]["per_species"][assess.WORM]["bp_f1"] = .85
        self.assertFalse(self.run_gate(17, previous)["scientific_gate_pass"])

    def test_absolute_readiness_does_not_replace_relative_gate(self):
        self.p["DEV"]["summary"]["macro_bp_f1"] = .829999
        result = self.run_gate()
        self.assertTrue(result["release_seed17"])
        self.assertFalse(result["absolute_readiness"]["pass"])
        previous = result
        self.p, self.h, self.d = pair("P0R", 17), pair("H0R", 17), pair("D", 17)
        result = self.run_gate(17, previous)
        self.assertTrue(result["scientific_gate_pass"])
        self.assertFalse(result["freeze_ready"])
        self.assertEqual(result["decision"], "CLOSE_TRAINING_EXPANSION_BELOW_ABSOLUTE_READINESS")

    def test_absolute_targets_include_every_panel_precision_recall_and_macro(self):
        for split, sp, key, value in (("DEV", "pig", "bp_f1", .799999),
                                    ("DEV", "mouse", "bp_precision", .749999),
                                    ("SCREEN", assess.WORM, "bp_recall", .749999)):
            candidate = copy.deepcopy(self.p)
            candidate[split]["per_species"][sp][key] = value
            self.assertFalse(assess.absolute_readiness(candidate)["pass"])
        for panel in self.p.values():
            for row in panel["per_species"].values():
                row.update(bp_f1=.8, bp_precision=.75, bp_recall=.75)
        self.p["DEV"]["summary"]["macro_bp_f1"] = .83
        self.assertTrue(assess.absolute_readiness(self.p)["pass"])

    def test_all_species_ap_effects_retained(self):
        result = self.run_gate()
        for row in result["contrasts"].values():
            self.assertEqual(set(row["effects"]["DEV"]), set(assess.SPECIES))
            self.assertIn("bp_average_precision", row["effects"]["DEV"]["human"])

    def test_wrong_seed_or_reference_and_nonfinite_values_rejected(self):
        self.d["DEV"]["seed"] = 17
        with self.assertRaises(ValueError):
            self.run_gate()
        self.d = pair("D")
        self.d["SCREEN"]["arm"] = "L"
        with self.assertRaises(ValueError):
            self.run_gate()
        self.d = pair("D")
        self.p["SCREEN"]["per_species"][assess.WORM]["bp_average_precision"] = float("nan")
        with self.assertRaises(ValueError):
            self.run_gate()

    def test_cli_reads_only_dev_screen_and_writes_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, data in (("p", self.p), ("h", self.h), ("d", self.d)):
                (root / name).mkdir()
                for split, artifact in data.items():
                    (root / name / f"{split.lower()}_metrics.json").write_text(json.dumps(artifact))
            args = assess.build_parser().parse_args([
                "--p0r-dir", str(root / "p"), "--h0r-dir", str(root / "h"),
                "--d-anchor-dir", str(root / "d"), "--seed", "42", "--output", str(root / "decision.json")])
            result = assess.run_assessment(args)
            self.assertTrue(result["release_seed17"])
            self.assertEqual(len(result["inputs"]), 6)


class EvaluationTest(unittest.TestCase):
    def test_once_only_cal_screen_dev_with_float32_coordinate_caches(self):
        import numpy as np
        evaluate = load_module("evaluate_init")
        calls = []

        def infer(model, tokenizer, device, specs, batch_size):
            split = specs[0][1].parent.name
            calls.append(split)
            return {sp: [{"species": sp, "assembly": "synthetic", "split": split,
                          "tile_id": "tiny", "chrom": "chr1", "start": 0, "end": 4,
                          "margin": np.array([1., -1., 0., -2.], dtype=np.float32),
                          "truth": np.array([True, False, False, False]),
                          "callable": np.array([True, True, False, True]),
                          "hard_negative": np.array([False, True, False, False])}]
                    for sp, _ in specs}

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(arm="P0R", seed=42, output_dir=Path(tmp) / "new", model_dir=Path(tmp) / "model",
                                      data_root=Path("/old"), upstream_root=Path("/upstream"), tokenizer_dir=None,
                                      model_code_dir=None, cpu=True, batch_size=12)
            with patch.object(evaluate.legacy, "load_final_model", return_value=(None, None, "cpu")), \
                 patch.object(evaluate.legacy, "infer_inputs", side_effect=infer), \
                 patch.object(evaluate.legacy, "fit_platt", return_value=(1., 0., .1)) as fit, \
                 patch.object(evaluate.legacy, "select_global_threshold", return_value={"threshold": .5}) as select:
                result = evaluate.evaluate_arm(args)
                self.assertEqual(calls, ["CAL", "SCREEN", "DEV"])
                self.assertEqual(fit.call_count, 1)
                self.assertEqual(select.call_count, 1)
                with self.assertRaises(FileExistsError):
                    evaluate.evaluate_arm(args)
            self.assertEqual(result["experiment"], assess.EXPERIMENT_ID)
            self.assertIn("historical", result["conf_status"])
            for split in ("SCREEN", "DEV"):
                metric = json.loads((args.output_dir / f"{split.lower()}_metrics.json").read_text())
                self.assertEqual(metric["arm"], "P0R")
                for path in result["margin_caches"][split].values():
                    with np.load(path, allow_pickle=False) as cache:
                        self.assertEqual(cache["margin"].dtype, np.dtype("float32"))
                        self.assertEqual(cache["start"].tolist(), [0])
                        self.assertEqual(cache["split"].tolist(), [split])
                        self.assertEqual(cache["hard_negative"].tolist(), [[False, True, False, False]])


if __name__ == "__main__":
    unittest.main()
