import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


SCRIPT = Path(__file__).with_name("calibrate_evaluate_x0.py")
SPEC = importlib.util.spec_from_file_location("calibrate_evaluate_x0", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def tile(tile_id: str, labels: str, margins: list[float], split: str = "DEV") -> dict:
    truth, callable_mask, hard_negative = MODULE.decode_labels(labels)
    return {
        "tile_id": tile_id,
        "split": split,
        "margin": np.asarray(margins, dtype=np.float64),
        "truth": truth,
        "callable": callable_mask,
        "hard_negative": hard_negative,
    }


class CalibrateEvaluateX0Test(unittest.TestCase):
    def test_token_margin_projection_matches_training_chunks(self):
        projected = MODULE.project_token_margins(
            np.asarray([99.0, -2.0, 3.0, 4.0, 5.0, 6.0, 99.0]),
            [1, 2, 3, 4, 5],
            10,
        )
        np.testing.assert_array_equal(
            projected, np.asarray([-2.0] * 6 + [3.0, 4.0, 5.0, 6.0], dtype=np.float32)
        )

    def test_platt_gives_each_species_equal_mass(self):
        base = {
            "a": (
                np.asarray([-2.0, -1.0, 1.0, 2.0]),
                np.asarray([0.0, 0.0, 1.0, 1.0]),
            ),
            "b": (
                np.asarray([-1.5, -0.5, 0.5, 1.5]),
                np.asarray([0.0, 1.0, 0.0, 1.0]),
            ),
        }
        duplicated = {
            "a": (np.tile(base["a"][0], 31), np.tile(base["a"][1], 31)),
            "b": base["b"],
        }
        slope_a, intercept_a, _ = MODULE.fit_platt(base)
        slope_b, intercept_b, _ = MODULE.fit_platt(duplicated)
        self.assertGreaterEqual(slope_a, 0.0)
        self.assertAlmostEqual(slope_a, slope_b, places=10)
        self.assertAlmostEqual(intercept_a, intercept_b, places=10)

    def test_threshold_rule_uses_tolerance_macro_and_final_ties(self):
        index = MODULE._choose_threshold_from_scores(
            np.asarray([0.2, 0.4]),
            np.asarray([0.8000, 0.7991]),
            np.asarray([0.81, 0.90]),
        )
        self.assertEqual(index, 1)
        index = MODULE._choose_threshold_from_scores(
            np.asarray([0.4, 0.6]),
            np.asarray([0.8, 0.8]),
            np.asarray([0.9, 0.9]),
        )
        self.assertEqual(index, 1)

    def test_adjacent_positive_edges_do_not_fuse_across_tiles(self):
        tiles = [
            tile("left", "0011", [-1.0, -1.0, 1.0, 1.0]),
            tile("right", "1100", [1.0, 1.0, -1.0, -1.0]),
        ]
        metrics = MODULE.evaluate_species_tiles(tiles, 1.0, 0.0, 0.5)
        self.assertEqual(metrics["truth_segments"], 2)
        self.assertEqual(metrics["predicted_segments"], 2)
        self.assertEqual(metrics["segment_f1_iou_0_8"], 1.0)
        self.assertEqual(metrics["fragments_per_truth"], 1.0)

    def test_apply_only_never_calls_fit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calibration = root / "calibration.json"
            metrics = root / "metrics.json"
            calibration.write_text(
                json.dumps(
                    {
                        "seed": 42,
                        "model_dir": str((root / "final_model").resolve()),
                        "platt_slope": 1.0,
                        "platt_intercept": 0.0,
                        "threshold": 0.5,
                    }
                )
            )
            args = SimpleNamespace(
                model_dir=root / "final_model",
                data=["human=fake.jsonl.gz"],
                calibration_json=calibration,
                metrics_json=metrics,
                batch_size=12,
                cpu=True,
            )
            inferred = {
                "human": [tile("one", "01H?", [-1.0, 1.0, -1.0, 5.0])]
            }
            with (
                mock.patch.object(MODULE, "load_final_model", return_value=(None, None, None)),
                mock.patch.object(MODULE, "infer_inputs", return_value=inferred),
                mock.patch.object(
                    MODULE, "fit_platt", side_effect=AssertionError("apply fitted CAL")
                ),
            ):
                output = MODULE.run_apply(args)
            self.assertEqual(output["mode"], "apply-only")
            self.assertEqual(json.loads(metrics.read_text())["mode"], "apply-only")


if __name__ == "__main__":
    unittest.main()
