import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import numpy as np
    import evaluate_conf as module
except ModuleNotFoundError as exc:
    if exc.name not in {"numpy", "scipy"}:
        raise
    np = None
    module = None


def calibration(model_dir: Path, code_dir: Path) -> dict:
    return {
        "experiment": module.EXPERIMENT_ID,
        "protocol": module.PROTOCOL,
        "run_role": module.RUN_ROLE,
        "arm": "L",
        "seed": 17,
        "calibration_protocol": module.CALIBRATION_PROTOCOL,
        "calibration_scope": "six-species-shared",
        "fit_split": "CAL",
        "species": list(module.SPECIES),
        "model_dir": str(model_dir.resolve()),
        "tokenizer_dir": str(model_dir.resolve()),
        "model_code_dir": str(code_dir.resolve()),
        "platt_slope": 1.0,
        "platt_intercept": 0.0,
        "threshold": 0.5,
        "evaluation_contract": {
            "dev_split": "DEV",
            "screen_split": "SCREEN",
            "forbidden_split": "CONF",
            "conf_status": "sealed_not_evaluated",
        },
    }


def panel(split="CONF"):
    tiles = []
    for index in range(module.CONF_TILES):
        truth = np.array([index % 2, 0, 1, 0], dtype=bool)
        tiles.append(
            {
                "species": module.WORM,
                "assembly": "ce11",
                "split": split,
                "tile_id": f"tile-{index}",
                "chrom": "chrIV",
                "start": index * 8192,
                "end": index * 8192 + 4,
                "margin": np.array([1.0, -1.0, 1.0, -1.0], dtype=np.float32),
                "truth": truth,
                "callable": np.ones(4, dtype=bool),
                "hard_negative": np.zeros(4, dtype=bool),
            }
        )
    return {module.WORM: tiles}


@unittest.skipIf(module is None, "legacy evaluation dependencies are unavailable")
class ConfEvaluateTest(unittest.TestCase):
    def args(self, root: Path, model_dir: Path, code_dir: Path, output: Path):
        return type(
            "Args",
            (),
            {
                "arm": "L",
                "seed": 17,
                "model_dir": model_dir,
                "calibration_json": root / "calibration.json",
                "data_root": root / "materialization",
                "model_code_dir": code_dir,
                "output_dir": output,
                "batch_size": 12,
                "cpu": True,
            },
        )()

    def test_rejects_calibration_bound_to_other_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_dir, code_dir = root / "model", root / "code"
            calibration_path = root / "calibration.json"
            value = calibration(model_dir / "other", code_dir)
            calibration_path.write_text(json.dumps(value))
            args = self.args(root, model_dir, code_dir, root / "out")
            with mock.patch.object(
                module.upstream.legacy,
                "load_final_model",
                side_effect=AssertionError("model must not load"),
            ):
                with self.assertRaisesRegex(ValueError, "different final_model"):
                    module.evaluate_conf(args)

    def test_rejects_non_conf_input_before_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_dir, code_dir = root / "model", root / "code"
            value = calibration(model_dir, code_dir)
            (root / "calibration.json").write_text(json.dumps(value))
            args = self.args(root, model_dir, code_dir, root / "out")
            with mock.patch.object(
                module.upstream.legacy,
                "load_final_model",
                return_value=("model", "tokenizer", "cpu"),
            ), mock.patch.object(
                module.upstream.legacy,
                "infer_inputs",
                return_value=panel("DEV"),
            ), mock.patch.object(
                module.upstream.legacy,
                "evaluate",
                side_effect=AssertionError("wrong split must not score"),
            ):
                with self.assertRaisesRegex(ValueError, "expected CONF records"):
                    module.evaluate_conf(args)

    def test_applies_frozen_calibration_without_fitting_or_rethresholding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_dir, code_dir = root / "model", root / "code"
            value = calibration(model_dir, code_dir)
            (root / "calibration.json").write_text(json.dumps(value))
            args = self.args(root, model_dir, code_dir, root / "out")
            with mock.patch.object(
                module.upstream.legacy,
                "load_final_model",
                return_value=("model", "tokenizer", "cpu"),
            ), mock.patch.object(
                module.upstream.legacy,
                "infer_inputs",
                return_value=panel(),
            ), mock.patch.object(
                module.upstream.legacy,
                "fit_platt",
                side_effect=AssertionError("CONF must not fit calibration"),
            ), mock.patch.object(
                module.upstream.legacy,
                "select_global_threshold",
                side_effect=AssertionError("CONF must not rethreshold"),
            ):
                result = module.evaluate_conf(args)

            self.assertTrue(result["conf_evaluated"])
            self.assertEqual(result["split"], "CONF")
            self.assertEqual(result["species"], [module.WORM])
            self.assertTrue((root / "out" / "conf_metrics.json").exists())
            self.assertTrue((root / "out" / "CONF_margins.npz").exists())
            with np.load(root / "out" / "CONF_margins.npz", allow_pickle=False) as cache:
                self.assertEqual(
                    set(cache.files),
                    {"margin", "truth", "callable", "hard_negative", "tile_id", "chrom", "start"},
                )
                self.assertEqual(cache["margin"].shape[0], module.CONF_TILES)


if __name__ == "__main__":
    unittest.main()
