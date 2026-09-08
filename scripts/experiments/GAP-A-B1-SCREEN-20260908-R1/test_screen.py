import unittest
import numpy as np
import torch
import screen


class ScreenTest(unittest.TestCase):
    def test_sampling_fixed_coordinate_universe(self):
        universe = {"chr3": set(range(19)), "chr5": set(range(27))}
        a = screen.sample_blocks(universe)
        self.assertEqual(a, screen.sample_blocks(universe))
        self.assertEqual(len(a["chr3"]), 3)
        self.assertEqual(len(a["chr5"]), 4)
        self.assertEqual(screen.block_id(524000, 524032), 0)
        self.assertEqual(screen.block_id(524000, 524033), 1)

    def test_actual_head_capacity_and_paired_init(self):
        heads, _ = screen.new_heads("cpu")
        self.assertEqual(heads["HN-O__seed17"].readout.in_channels, 144)
        self.assertEqual(heads["HN-O__seed17"].mlp[0].in_features, 202)
        x, g = torch.randn(2, 144, 32), torch.randn(2, 10)
        x[:, 9] = 1
        x[:, 4:7] = 1
        x0, g0 = screen.prepared(x, g, "H0-O")
        self.assertTrue(torch.equal(x0[:, :143], x[:, :143]))
        self.assertTrue(torch.equal(g0[:, :7], g[:, :7]))
        self.assertEqual(int(torch.count_nonzero(x0[:, 143])), 0)
        self.assertEqual(int(torch.count_nonzero(g0[:, 7:])), 0)
        self.assertTrue(torch.equal(screen.prepared(x, g, "H0-S")[0], x0))
        self.assertTrue(torch.equal(screen.prepared(x, g, "HN-O")[0], x))
        self.assertTrue(torch.isfinite(heads["HN-O__seed17"].forward_prepared(x, g)).all())

    def test_ap_ties_matches_frozen_metric(self):
        metric = screen.pair.load_module(screen.ROOT / "scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_metrics.py", "test_old_metrics")
        p, n, score = np.array([1., 2., 0., 7.]), np.array([2., 0., 9., 3.]), np.array([.2, .2, .8, .8])
        self.assertAlmostEqual(screen.action_ap(score, p, n), metric.weighted_action_ap(score, p, n), places=14)
        self.assertAlmostEqual(screen.action_ap(score[::-1], p[::-1], n[::-1]), screen.action_ap(score, p, n), places=14)

    def test_brier_decomposition_and_gate(self):
        m = screen.metrics([0., 1.], [1, 2], [3, 4])
        self.assertAlmostEqual(m["fraction_mse"]+m["irreducible"], m["pseudo_base_brier"], places=14)
        control = {"fraction_mse": 1., "action_ap": .5}
        self.assertEqual(screen.decision(control, {"fraction_mse": .94, "action_ap": .5})["status"], "SCREEN_POSITIVE")
        self.assertEqual(screen.decision(control, {"fraction_mse": .94, "action_ap": .49})["status"], "SCREEN_GATE_FAIL")
        self.assertEqual(screen.decision(control, control)["status"], "SCREEN_GATE_FAIL")
        self.assertEqual(screen.decision({"fraction_mse": 0., "action_ap": .5}, control)["status"], "UNDETERMINED")
        with self.assertRaises(ValueError):
            screen.metrics([float("nan")], [1], [1])


if __name__ == "__main__":
    torch.set_num_threads(2)
    unittest.main()
