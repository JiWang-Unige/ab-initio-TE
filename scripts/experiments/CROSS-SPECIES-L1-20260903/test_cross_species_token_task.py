#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

import torch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "cross_species_token_task", HERE / "cross_species_token_task.py"
)
task = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(task)


class CrossSpeciesTokenTaskTest(unittest.TestCase):
    def test_sampler_emits_one_tile_in_fixed_species_order(self) -> None:
        tile_ids = {
            species: [f"{species}:0", f"{species}:1"]
            for species in task.SPECIES
        }
        for arm in ("B1", "B2"):
            sampler = task.SpeciesTileSampler(tile_ids, seed=17, arm=arm)
            first = sampler.next_step()
            second = sampler.next_step()
            self.assertEqual([species for species, _ in first], list(task.SPECIES))
            self.assertEqual([species for species, _ in second], list(task.SPECIES))
            for species in task.SPECIES:
                observed = {
                    tile_id
                    for emitted_species, tile_id in first + second
                    if emitted_species == species
                }
                self.assertEqual(observed, set(tile_ids[species]))

    def test_h1_sampler_emits_six_human_tiles_per_step(self) -> None:
        human_tiles = [f"human:{index}" for index in range(12)]
        sampler = task.SpeciesTileSampler(
            {"human": human_tiles}, seed=17, arm="H1"
        )
        first = sampler.next_step()
        second = sampler.next_step()
        for step in (first, second):
            self.assertEqual(len(step), len(task.SPECIES))
            self.assertEqual(
                [species for species, _ in step], ["human"] * len(task.SPECIES)
            )
            self.assertEqual(len({tile_id for _, tile_id in step}), len(task.SPECIES))
            self.assertTrue({tile_id for _, tile_id in step} <= set(human_tiles))
        self.assertEqual(
            {tile_id for _, tile_id in first + second}, set(human_tiles)
        )

    def test_bp_loss_counts_p_n_ignores_question_and_treats_h_as_n(self) -> None:
        positive, negative = task.label_chunk_masses("10?H11", width=3)
        self.assertEqual(positive, [1, 2])
        self.assertEqual(negative, [1, 1])
        tail_positive, tail_negative = task.label_chunk_masses("1111110H?", width=6)
        self.assertEqual(tail_positive, [6, 0, 0, 0])
        self.assertEqual(tail_negative, [0, 1, 1, 0])

        logits = torch.tensor(
            [[[0.0, 0.0]], [[math.log(0.8), math.log(0.2)]]],
            dtype=torch.float32,
        )
        positive_bp = torch.tensor([[1.0], [0.0]])
        negative_bp = torch.tensor([[1.0], [2.0]])
        loss = task.bp_weighted_pair_loss(logits, positive_bp, negative_bp)
        expected = (math.log(2.0) - math.log(0.8)) / 2.0
        self.assertAlmostEqual(float(loss), expected, places=6)

    def test_b1_b2_weights_and_groupdro_update(self) -> None:
        initial = torch.full(
            (len(task.SPECIES),), -math.log(len(task.SPECIES)), dtype=torch.float64
        )
        b1 = task.arm_weights("B1", initial)
        b2 = task.arm_weights("B2", initial)
        h1 = task.arm_weights("H1", initial)
        torch.testing.assert_close(b1, torch.full_like(initial, 1.0 / 6.0))
        torch.testing.assert_close(b2, torch.full_like(initial, 1.0 / 6.0))
        torch.testing.assert_close(h1, torch.full_like(initial, 1.0 / 6.0))

        current_losses = torch.tensor([2.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        updated = task.update_groupdro_log_q(initial, current_losses, eta=0.01)
        expected = initial + 0.01 * current_losses.to(torch.float64)
        expected -= torch.logsumexp(expected, dim=0)
        self.assertEqual(updated.dtype, torch.float64)
        torch.testing.assert_close(updated, expected)
        self.assertGreater(float(torch.exp(updated[0])), float(torch.exp(updated[1])))
        torch.testing.assert_close(task.arm_weights("B2", updated).sum(), torch.tensor(1.0, dtype=torch.float64))


if __name__ == "__main__":
    unittest.main()
