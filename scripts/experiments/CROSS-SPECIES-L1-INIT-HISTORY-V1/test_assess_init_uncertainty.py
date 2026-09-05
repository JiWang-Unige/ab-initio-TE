import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

SPEC = importlib.util.spec_from_file_location("assess_init_uncertainty", Path(__file__).with_name("assess_init_uncertainty.py"))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def panel(margin=None, truth=None, callable_mask=None):
    margin = np.array([[1., -1.], [1., .5]], dtype=np.float32) if margin is None else np.array(margin, dtype=np.float32)
    truth = np.array([[1, 0], [1, 0]], dtype=bool) if truth is None else np.array(truth, dtype=bool)
    callable_mask = np.ones_like(truth) if callable_mask is None else np.array(callable_mask, dtype=bool)
    point, _ = module.core._metric_values(margin, truth, callable_mask, 1., 0., .5)
    return {"margin": margin, "truth": truth, "callable": callable_mask,
            "hard_negative": ~truth & callable_mask, "tile_id": [f"t{i}" for i in range(len(margin))],
            "chrom": ["chrI"] * len(margin), "start": np.arange(len(margin)) * module.BLOCK_BP,
            "calibration": {"platt_slope": 1., "platt_intercept": 0., "threshold": .5},
            "metadata": {"per_species": {"c_elegans": point}}, "metrics_path": Path("synthetic.json"), "inputs": {}}


def arms(value, seeds=(42,)):
    return {f"seed{seed}_{arm}": copy.deepcopy(value) for seed in seeds for arm in module.ARMS}


def write_inputs(root, seed, arm, value):
    directory = root / f"seed{seed}_{arm}"
    directory.mkdir()
    model = directory / "model"
    calibration_path = directory / "calibration.json"
    calibration_path.write_text(json.dumps({
        **value["calibration"], "arm": arm, "seed": seed, "model_dir": str(model),
        "calibration_scope": "six-species-shared", "fit_split": "CAL", "species": list(module.decision.SPECIES)}))
    report = {"protocol": module.EXPERIMENT_ID, "stage": "J0-A", "seed": seed,
              "mode": "apply-only", "status": "COMPLETED", "model_dir": str(model),
              "calibration_json": str(calibration_path), "panels": {}}
    for split in module.PANELS:
        cache_dir = directory / "margins" / split
        cache_dir.mkdir(parents=True)
        np.savez_compressed(cache_dir / "c_elegans.npz", **{key: value[key] for key in module.CACHE_KEYS})
        species = ["c_elegans"] if split == "SCREEN" else list(module.decision.SPECIES)
        old = arm == "D"
        artifact = {
            "experiment": module.decision.OLD_EXPERIMENT if old else module.EXPERIMENT_ID,
            "protocol": module.decision.OLD_EXPERIMENT + "-V1" if old else module.EXPERIMENT_ID,
            "run_role": "upstream_coverage_pilot" if old else module.decision.RUN_ROLE,
            "arm": arm, "seed": seed, "split": split, "species": species, "conf_evaluated": False,
            "calibration_scope": "six-species-shared", "model_dir": str(model), "calibration_json": str(calibration_path),
            "per_species": {sp: value["metadata"]["per_species"]["c_elegans"] for sp in species}}
        metric_path = directory / f"{split.lower()}_metrics.json"
        metric_path.write_text(json.dumps(artifact))
        report["panels"][split] = {"expected_metrics_path": str(metric_path)}
    if arm == "D":
        (directory / "diagnostic.json").write_text(json.dumps(report))
    return directory


class UncertaintyTest(unittest.TestCase):
    def test_weighted_raw_ties_equal_explicit_bp_repetition(self):
        scores = np.array([.5, .5, .2, .1], dtype=np.float32)
        truth = np.array([1, 0, 1, 0], dtype=bool)
        weights = np.array([2, 3, 1, 4])
        weighted = module.core.average_precision_tied(truth, scores, weights)
        repeated = module.core.average_precision_tied(np.repeat(truth, weights), np.repeat(scores, weights))
        self.assertAlmostEqual(weighted, repeated, places=15)
        # First tied group contributes (2/3)*(2/5), next positive (1/3)*(3/6).
        self.assertAlmostEqual(weighted, 2 / 3 * 2 / 5 + 1 / 3 * 3 / 6, places=15)

    def test_zero_weight_group_does_not_affect_ap(self):
        scores = np.array([.9, .8, .7], dtype=np.float32)
        truth = np.array([0, 1, 0], dtype=bool)
        self.assertEqual(module.core.average_precision_tied(truth, scores, np.array([0, 1, 1])), 1.)
        self.assertIsNone(module.core.average_precision_tied(truth, scores, np.zeros(3)))

    def test_same_draws_cancel_identical_three_arms_and_both_seeds(self):
        result = module.assess_panel(arms(panel(), (42, 17)), (42, 17), replicates=30)
        for contrast in result["paired"].values():
            for seed in contrast.values():
                for metric in seed.values():
                    self.assertEqual(metric["point"], 0)
                    self.assertEqual(metric["ci95"], [0., 0.])
                    self.assertEqual(metric["valid_replicates"], 30)
        for contrast in result["two_seed_arithmetic_mean_effects"].values():
            for metric in contrast.values():
                self.assertEqual(metric["ci95"], [0., 0.])

    def test_points_pool_callable_bp_not_window_f1(self):
        value = panel([[1, -1, -1, -1], [-1, -1, -1, -1]],
                      [[1, 0, 0, 0], [1, 1, 1, 1]],
                      [[1, 0, 0, 0], [1, 1, 1, 1]])
        result = module.assess_panel(arms(value), (42,), replicates=10)
        self.assertAlmostEqual(result["absolute"]["seed42_P0R"]["bp_f1"]["point"], 1 / 3)
        self.assertNotEqual(result["absolute"]["seed42_P0R"]["bp_f1"]["point"], .5)
        self.assertEqual(result["point_counts"]["seed42_P0R"], {"tp_bp": 1, "fp_bp": 0, "fn_bp": 4, "positive_bp": 5})

    def test_undefined_draws_are_counted_and_never_removed(self):
        value = panel([[1., -1.], [-1., -1.]], [[1, 0], [0, 0]])
        result = module.assess_panel(arms(value), (42,), replicates=100)
        for metric in result["absolute"]["seed42_P0R"].values():
            self.assertIsNone(metric["ci95"])
            self.assertGreater(metric["undefined_replicates"], 0)
            self.assertEqual(metric["undefined_replicates"] + metric["valid_replicates"], 100)
        for metric in result["paired"]["P0R_minus_D_anchor"]["seed42"].values():
            self.assertIsNone(metric["ci95"])
            self.assertGreater(metric["undefined_replicates"], 0)

    def test_two_seed_effect_is_arithmetic_mean_not_score_ensemble(self):
        supplied = arms(panel(), (42, 17))
        supplied["seed42_P0R"] = panel([[1., -1.], [1., -1.]])
        supplied["seed17_P0R"] = panel([[1., 1.], [1., 1.]])
        result = module.assess_panel(supplied, (42, 17), replicates=20)
        for contrast in result["paired"]:
            for metric in module.METRICS:
                points = [result["paired"][contrast][f"seed{seed}"][metric]["point"] for seed in (42, 17)]
                self.assertAlmostEqual(result["two_seed_arithmetic_mean_effects"][contrast][metric]["point"], sum(points) / 2)

    def test_alignment_and_point_mismatch_stop_before_bootstrap(self):
        for key in ("truth", "callable", "hard_negative", "start"):
            with self.subTest(key=key):
                supplied = arms(panel())
                array = supplied["seed42_D"][key]
                array.flat[0] = 1 - array.flat[0]
                with self.assertRaisesRegex(ValueError, "alignment"):
                    module.assess_panel(supplied, (42,), replicates=2)
        supplied = arms(panel())
        supplied["seed42_P0R"]["metadata"]["per_species"]["c_elegans"]["bp_f1"] += .000002
        with self.assertRaisesRegex(ValueError, "differs from cache"):
            module.assess_panel(supplied, (42,), replicates=2)

    def test_loader_sorts_coordinates_and_never_accepts_conf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value = panel()
            directory = write_inputs(root, 42, "P0R", value)
            path = directory / "margins" / "SCREEN" / "c_elegans.npz"
            np.savez_compressed(path, **{key: np.asarray(value[key])[::-1] for key in module.CACHE_KEYS})
            loaded = module.load_panel(directory, 42, "P0R", "SCREEN")
            self.assertEqual(loaded["tile_id"], value["tile_id"])
            self.assertTrue(np.array_equal(loaded["margin"], value["margin"]))
            with self.assertRaisesRegex(ValueError, "CONF"):
                module.load_panel(Path("/does-not-exist"), 42, "P0R", "CONF")

    def test_end_to_end_registered_defaults_only_existing_cache_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directories = {42: {arm: write_inputs(root, 42, arm, panel()) for arm in module.ARMS}}
            result = module.run_assessment(directories, root / "uncertainty.json")
            self.assertEqual(set(result["panels"]), {"SCREEN", "DEV"})
            self.assertEqual(result["bootstrap"]["replicates"], 1000)
            self.assertEqual(result["bootstrap"]["seed"], 20260905)
            self.assertEqual(result["bootstrap"]["block_bp"], 524288)
            self.assertFalse(result["claim_boundary"]["ci_sign_gate"])
            self.assertFalse(result["claim_boundary"]["ensemble"])
            self.assertIsNone(result["panels"]["DEV"]["two_seed_arithmetic_mean_effects"])
            self.assertTrue((root / "uncertainty.json").exists())


if __name__ == "__main__":
    unittest.main()
