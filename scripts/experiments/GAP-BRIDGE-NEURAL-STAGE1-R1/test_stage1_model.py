#!/usr/bin/env python3
"""Contract tests for the frozen Stage 1 gap head."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest


try:
    import torch
except ModuleNotFoundError:  # The model is exercised on the Baobab runtime.
    torch = None


ROOT = pathlib.Path(__file__).resolve().parent


def load_model_module():
    spec = importlib.util.spec_from_file_location("stage1_model", ROOT / "stage1_model.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load stage1_model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(torch is not None, "PyTorch is unavailable in this interpreter")
class Stage1ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_model_module()

    def test_arm_channel_masks_are_exact_and_non_mutating(self):
        x = torch.randn(2, 143, 9)
        original = x.clone()
        g = self.module.build_arm_input(x, self.module.ARMS[0])
        r = self.module.apply_arm_input(x, self.module.ARMS[1])
        h = self.module.build_arm_input(x, self.module.ARMS[2])
        self.assertTrue(torch.equal(x, original))
        self.assertTrue(torch.equal(g[:, :10], x[:, :10]))
        self.assertTrue(torch.equal(g[:, 10:], torch.zeros_like(g[:, 10:])))
        self.assertTrue(torch.equal(r[:, :15], x[:, :15]))
        self.assertTrue(torch.equal(r[:, 15:], torch.zeros_like(r[:, 15:])))
        self.assertTrue(torch.equal(h, x))

    def test_forward_prepared_matches_forward_without_second_mask(self):
        torch.manual_seed(20260902)
        head = self.module.GapHead(self.module.ARMS[1]).eval()
        features = torch.randn(3, 143, 17)
        geometry = torch.randn(3, 7)
        prepared = self.module.build_arm_input(features, self.module.ARMS[1])
        with torch.no_grad():
            direct = head(features, geometry)
            prepared_output = head.forward_prepared(prepared, geometry)
        self.assertTrue(torch.equal(direct, prepared_output))

    def test_padding_is_excluded_from_region_pool_and_model_output(self):
        hidden = torch.arange(32 * 6, dtype=torch.float32).reshape(1, 32, 6)
        tags = torch.zeros(1, 3, 6)
        tags[:, 0, :2] = 1
        tags[:, 1, 2:4] = 1
        tags[:, 2, 4:6] = 1
        valid = torch.tensor([[[1, 1, 1, 1, 0, 0]]], dtype=torch.float32)
        pooled_a = self.module.masked_region_pool(hidden, tags, valid)
        hidden_changed = hidden.clone()
        hidden_changed[:, :, 4:] = 10_000
        pooled_b = self.module.masked_region_pool(hidden_changed, tags, valid)
        self.assertTrue(torch.equal(pooled_a, pooled_b))

        features = torch.randn(1, 143, 6)
        features[:, 4:7, :] = tags
        features[:, 9:10, :] = valid
        features_changed = features.clone()
        features_changed[:, :, 4:] = torch.randn_like(features_changed[:, :, 4:]) * 10_000
        features_changed[:, 4:7, :] = tags
        features_changed[:, 9:10, :] = valid
        head = self.module.GapHead(self.module.ARMS[2]).eval()
        geometry = torch.zeros(1, 7)
        with torch.no_grad():
            output_a = head(features, geometry)
            output_b = head(features_changed, geometry)
        self.assertTrue(torch.equal(output_a, output_b))

    def test_arms_are_parameter_isomorphic(self):
        heads = [self.module.GapHead(arm) for arm in self.module.ARMS]
        counts = [sum(parameter.numel() for parameter in head.parameters()) for head in heads]
        self.assertEqual(len(set(counts)), 1)
        parameter_signatures = [
            [(name, tuple(parameter.shape)) for name, parameter in head.named_parameters()]
            for head in heads
        ]
        self.assertEqual(parameter_signatures[0], parameter_signatures[1])
        self.assertEqual(parameter_signatures[1], parameter_signatures[2])
        for head in heads:
            self.assertEqual(head.readout.in_channels, 143)
            self.assertEqual(head.readout.out_channels, 32)
            self.assertEqual([block.depthwise.dilation[0] for block in head.blocks], [1, 2, 4, 8])
            self.assertTrue(all(block.depthwise.groups == 32 for block in head.blocks))
            self.assertTrue(all(block.depthwise.kernel_size[0] == 5 for block in head.blocks))

    def test_weights_equalize_strata_and_bad_normalization_stops_bce(self):
        lengths = torch.tensor([1, 2, 3, 6, 21, 101, 2], dtype=torch.float32)
        strata = ["1", "1", "3-5", "6-20", "21-100", "101-512", "2"]
        weights = self.module.stratum_sample_weights(lengths, strata)
        self.assertAlmostEqual(float(weights.mean()), 1.0, places=6)
        for stratum in self.module.LENGTH_STRATA:
            selected = weights[[value == stratum for value in strata]]
            self.assertAlmostEqual(float(selected.sum()), float(weights.sum() / 6), places=6)
        self.assertAlmostEqual(float(weights[1] / weights[0]), 2.0, places=6)

        logits = torch.zeros(7)
        targets = torch.full((7,), 0.25)
        with self.assertRaisesRegex(ValueError, "normalized to mean one"):
            self.module.soft_target_bce(logits, targets, torch.ones(7) * 2)
        with self.assertRaisesRegex(ValueError, "all six"):
            self.module.stratum_sample_weights(torch.ones(5), strata[:5])


if __name__ == "__main__":
    unittest.main()
