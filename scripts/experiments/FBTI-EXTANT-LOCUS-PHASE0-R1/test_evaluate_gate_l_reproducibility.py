#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "evaluate_gate_l_reproducibility", HERE / "evaluate_gate_l_reproducibility.py"
)
assert SPEC is not None and SPEC.loader is not None
evaluator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluator
SPEC.loader.exec_module(evaluator)


class EvaluateGateLRTest(unittest.TestCase):
    @staticmethod
    def _coordinate(label: str, start: int):
        return SimpleNamespace(locus_id=label, coordinate_key=("2L", start, start + 10))

    def test_matching_prioritizes_cardinality_before_total_iou(self) -> None:
        left = [self._coordinate("left-a", 100), self._coordinate("left-b", 200)]
        right = [self._coordinate("right-a", 300), self._coordinate("right-b", 400)]
        pairs = evaluator._maximum_bipartite_matching(
            left,
            right,
            {
                (0, 0): 0.60,
                (0, 1): 0.95,
                (1, 0): 0.55,
            },
        )
        self.assertEqual(set(pairs), {(0, 1), (1, 0)})

    def test_matching_keeps_original_indices_when_sides_are_unequal(self) -> None:
        left = [self._coordinate("left-a", 100), self._coordinate("left-b", 200)]
        right = [self._coordinate("right-a", 300)]
        pairs = evaluator._maximum_bipartite_matching(
            left,
            right,
            {(0, 0): 0.60, (1, 0): 0.90},
        )
        self.assertEqual(pairs, [(1, 0)])

    def test_empty_unions_have_zero_iou(self) -> None:
        self.assertEqual(evaluator.interval_iou([], []), 0.0)

    def test_matching_does_not_depend_on_actor_local_ids(self) -> None:
        left_a = [self._coordinate("A1-local", 100)]
        right_a = [self._coordinate("A2-local", 200)]
        left_b = [self._coordinate("different-left-id", 100)]
        right_b = [self._coordinate("different-right-id", 200)]
        score = {(0, 0): 0.75}
        self.assertEqual(
            evaluator._maximum_bipartite_matching(left_a, right_a, score),
            evaluator._maximum_bipartite_matching(left_b, right_b, score),
        )

    def test_ac1_reports_boundary_rating_denominator(self) -> None:
        result = evaluator.compute_gwet_ac1(
            [("point", "point"), ("point", "interval"), ("unidentifiable", "interval")]
        )
        self.assertEqual(result["rating_count"], 3)
        self.assertEqual(result["denominator"], 3)
        self.assertEqual(result["agreement_count"], 1)
        self.assertIsNotNone(result["value"])

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is provided by the cluster runtime")
    def test_bootstrap_preserves_frozen_cell_mixture(self) -> None:
        cells = {
            cell: [index]
            for index, cell in enumerate(
                evaluator.S0_CELLS + evaluator.S1_CELLS
            )
        }
        samples = evaluator._bootstrap_samples(cells, replicates=3)
        expected_counts = {
            index: evaluator.BOOTSTRAP_CELL_QUOTAS[cell]
            for index, cell in enumerate(evaluator.S0_CELLS + evaluator.S1_CELLS)
        }
        for sample in samples:
            self.assertEqual(len(sample), 120)
            for index, expected in expected_counts.items():
                self.assertEqual(sample.count(index), expected)


if __name__ == "__main__":
    unittest.main()
