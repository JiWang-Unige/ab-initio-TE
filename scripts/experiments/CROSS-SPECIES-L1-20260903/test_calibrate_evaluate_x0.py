import importlib.util
import json
import sys
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
    def test_sequence_tokens_keep_fixed_six_bp_alignment_across_n(self):
        self.assertEqual(
            MODULE.sequence_tokens("ACGTACAAANTTGTAC"),
            ["ACGTAC", "<unk>", "G", "T", "A", "C"],
        )

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
                        "tokenizer_dir": str((root / "final_model").resolve()),
                        "model_code_dir": None,
                        "platt_slope": 1.0,
                        "platt_intercept": 0.0,
                        "threshold": 0.5,
                    }
                )
            )
            args = SimpleNamespace(
                model_dir=root / "final_model",
                tokenizer_dir=None,
                model_code_dir=None,
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
                mock.patch.object(
                    MODULE, "load_final_model", return_value=(None, None, None)
                ) as load_model,
                mock.patch.object(MODULE, "infer_inputs", return_value=inferred),
                mock.patch.object(
                    MODULE, "fit_platt", side_effect=AssertionError("apply fitted CAL")
                ),
            ):
                output = MODULE.run_apply(args)
            self.assertEqual(output["mode"], "apply-only")
            self.assertEqual(json.loads(metrics.read_text())["mode"], "apply-only")
            load_model.assert_called_once_with(
                root / "final_model", None, True, None
            )

    def test_i0_loader_uses_checkpoint_state_and_model_code(self):
        import types

        model = mock.Mock()
        model_class = mock.Mock()
        model_class._from_config.return_value = model
        config = types.SimpleNamespace(
            auto_map={"AutoModelForTokenClassification": "modeling_esm.Fake"}
        )
        auto_config = mock.Mock(return_value=config)
        auto_tokenizer = mock.Mock(return_value=object())
        transformers = types.ModuleType("transformers")
        transformers.AutoConfig = types.SimpleNamespace(from_pretrained=auto_config)
        transformers.AutoTokenizer = types.SimpleNamespace(
            from_pretrained=auto_tokenizer
        )
        dynamic = types.ModuleType("transformers.dynamic_module_utils")
        dynamic_loader = mock.Mock(return_value=model_class)
        dynamic.get_class_from_dynamic_module = dynamic_loader
        torch = types.ModuleType("torch")
        torch.load = mock.Mock(return_value={"weight": 1})
        torch.device = mock.Mock(return_value="cpu")
        torch.cuda = types.SimpleNamespace(is_available=lambda: False)

        with mock.patch.dict(
            sys.modules,
            {
                "torch": torch,
                "transformers": transformers,
                "transformers.dynamic_module_utils": dynamic,
            },
        ):
            loaded, tokenizer, device = MODULE.load_final_model(
                Path("checkpoint"), Path("tokenizer"), True, Path("base-model")
            )

        self.assertIs(loaded, model)
        auto_config.assert_called_once_with(
            "checkpoint", trust_remote_code=True, local_files_only=True
        )
        torch.load.assert_called_once_with(
            Path("checkpoint") / "pytorch_model.bin", map_location="cpu"
        )
        dynamic_loader.assert_called_once_with(
            "modeling_esm.Fake", Path("base-model"), local_files_only=True
        )
        model_class._from_config.assert_called_once_with(config)
        model.load_state_dict.assert_called_once_with({"weight": 1}, strict=True)


if __name__ == "__main__":
    unittest.main()
