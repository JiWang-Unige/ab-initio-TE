import random
import sys
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch
import init_model
import train_init


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.esm = torch.nn.Linear(4, 4)
        self.classifier = torch.nn.Linear(4, 2)
        self.config = SimpleNamespace(initializer_range=0.02)


class InitModelTest(unittest.TestCase):
    def state(self, model, arm):
        result = {k: torch.full_like(v, 0.25) for k, v in model.state_dict().items() if k.startswith("esm.")}
        for key in (init_model.HEAD_KEYS if arm == "H0R" else init_model.LM_HEAD_KEYS):
            result[key] = torch.zeros(1)
        return result

    def test_both_sources_load_every_encoder_tensor_and_partition_heads(self):
        for arm in ("H0R", "P0R"):
            model = TinyModel()
            state = self.state(model, arm)
            report = init_model.load_encoder_state(model, state, arm)
            self.assertTrue(report["encoder_direct_tensor_equality"])
            for k, v in model.state_dict().items():
                if k.startswith("esm."):
                    self.assertTrue(torch.equal(v, state[k]))

    def test_missing_unknown_and_wrong_shape_encoder_block(self):
        model = TinyModel()
        for problem in ("missing", "unknown", "shape"):
            state = self.state(model, "P0R")
            if problem == "missing":
                del state["esm.weight"]
            elif problem == "unknown":
                state["unregistered.weight"] = torch.zeros(1)
            else:
                state["esm.weight"] = torch.zeros(1)
            with self.assertRaises(ValueError):
                init_model.load_encoder_state(model, state, "P0R")

    def test_head_is_matched_per_seed_and_preserves_rng(self):
        first, second = TinyModel(), TinyModel()
        for seed in (42, 17):
            before, python_before = torch.get_rng_state().clone(), random.getstate()
            init_model.reset_shared_head(first, seed)
            init_model.reset_shared_head(second, seed)
            self.assertTrue(torch.equal(before, torch.get_rng_state()))
            self.assertEqual(python_before, random.getstate())
            for key, value in first.classifier.state_dict().items():
                self.assertTrue(torch.equal(value, second.classifier.state_dict()[key]))
        seed17 = first.classifier.weight.clone()
        init_model.reset_shared_head(first, 42)
        self.assertFalse(torch.equal(seed17, first.classifier.weight))

    def test_wrapper_fixes_scientific_budget_and_separates_smoke(self):
        for smoke in (False, True):
            args = train_init.build_parser().parse_args([
                "--arm", "P0R", "--data-root", "/old", "--upstream-root", "/D",
                "--output-dir", "/output", *( ["--engineering-smoke"] if smoke else []),
            ])
            with tempfile.TemporaryDirectory() as tmp:
                args.output_dir = Path(tmp)
                if smoke:
                    (Path(tmp) / "train_log.jsonl").write_text('{"loss": {"human": 0.5}}\n' * 4)
                with mock.patch.object(train_init.legacy, "train") as train:
                    train_init.train(args)
            passed = train.call_args.args[0]
            self.assertEqual(passed.max_steps, 4 if smoke else 4000)
            self.assertEqual(passed.warmup_steps, 400)
            self.assertEqual(passed.arm, "B1")
            self.assertEqual(passed.experiment_arm, "P0R")
            self.assertTrue(passed.collect_exposure)
            self.assertEqual(passed.species_data, ["c_elegans=/D/TRAIN/c_elegans.jsonl.gz"])
            self.assertEqual(passed.run_role, "initialization_engineering_smoke" if smoke else "initialization_history_pilot")
            self.assertEqual(train.call_args.kwargs["model_loader"].keywords["base_model"], init_model.BASE_MODEL)

    def test_no_scientific_step_override_and_smoke_is_bounded(self):
        args = train_init.build_parser().parse_args([
            "--arm", "H0R", "--data-root", "/old", "--upstream-root", "/D",
            "--output-dir", "/output", "--engineering-smoke", "--smoke-steps", "5",
        ])
        with self.assertRaises(ValueError):
            train_init.train(args)


if __name__ == "__main__":
    unittest.main()
