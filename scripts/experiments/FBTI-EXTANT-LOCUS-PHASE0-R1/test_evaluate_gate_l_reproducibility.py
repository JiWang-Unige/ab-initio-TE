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

    @staticmethod
    def _bundle(
        topology_resolution: str,
        loci: list[tuple[str, int, int]],
        segments: list[tuple[str, str, int, int]],
        relations: list[tuple[str, str, str]] | None = None,
    ):
        return evaluator.Bundle(
            reviews={"pkg": evaluator.Review("resolved", topology_resolution)},
            loci={
                "pkg": [
                    evaluator.Locus(label, "resolved", "2L", start, end)
                    for label, start, end in loci
                ]
            },
            materials={
                "pkg": [
                    evaluator.Segment(segment, locus, "assigned", "2L", start, end)
                    for segment, locus, start, end in segments
                ]
            },
            boundaries={},
            relations={"pkg": relations or []},
        )

    def test_topology_audit_ignores_endpoint_edits_and_local_ids(self) -> None:
        left = self._bundle(
            "",
            [("left", 100, 200)],
            [("segment-left", "left", 100, 200)],
        )
        right = self._bundle(
            "",
            [("right", 110, 190)],
            [("segment-right", "right", 110, 190)],
        )
        result = evaluator._audit_topology_pair("pkg", left, right, "2L", "2L")
        self.assertIs(result["equivalent"], True)
        self.assertIs(result["common_material_partition_equal"], True)
        self.assertTrue(result["locus_matching_complete"])

    def test_topology_audit_detects_common_support_partition_change(self) -> None:
        left = self._bundle(
            "",
            [("left-a", 100, 200), ("left-b", 220, 320)],
            [("segment-a", "left-a", 100, 200), ("segment-b", "left-b", 220, 320)],
        )
        right = self._bundle(
            "",
            [("right-a", 100, 150), ("right-b", 150, 320)],
            [("segment-a", "right-a", 100, 150), ("segment-b", "right-b", 150, 320)],
        )
        result = evaluator._audit_topology_pair("pkg", left, right, "2L", "2L")
        self.assertTrue(result["locus_matching_complete"])
        self.assertIs(result["common_material_partition_equal"], False)
        self.assertIs(result["equivalent"], False)

    def test_topology_audit_respects_directed_and_symmetric_relations(self) -> None:
        left = self._bundle(
            "",
            [("left-child", 100, 200), ("left-parent", 300, 400)],
            [
                ("child-segment", "left-child", 100, 200),
                ("parent-segment", "left-parent", 300, 400),
            ],
            [
                ("nested_in", "left-child", "left-parent"),
                ("distinct_locus", "left-child", "left-parent"),
            ],
        )
        right = self._bundle(
            "",
            [("right-child", 100, 200), ("right-parent", 300, 400)],
            [
                ("child-segment", "right-child", 100, 200),
                ("parent-segment", "right-parent", 300, 400),
            ],
            [
                ("nested_in", "right-parent", "right-child"),
                ("distinct_locus", "right-parent", "right-child"),
            ],
        )
        result = evaluator._audit_topology_pair("pkg", left, right, "2L", "2L")
        self.assertIs(result["mapped_relation_graph_equal"], False)
        self.assertIs(result["equivalent"], False)

        left.relations["pkg"] = [("distinct_locus", "left-child", "left-parent")]
        right.relations["pkg"] = [("distinct_locus", "right-parent", "right-child")]
        result = evaluator._audit_topology_pair("pkg", left, right, "2L", "2L")
        self.assertIs(result["mapped_relation_graph_equal"], True)
        self.assertIs(result["equivalent"], True)

    def test_topology_audit_reports_nonunique_adjudication_source(self) -> None:
        a1 = self._bundle(
            "",
            [("a1", 100, 200)],
            [("a1-segment", "a1", 100, 200)],
        )
        a2 = self._bundle(
            "",
            [("a2", 100, 200)],
            [("a2-segment", "a2", 100, 200)],
        )
        adj = self._bundle(
            "accept_a1",
            [("adj", 105, 195)],
            [("adj-segment", "adj", 105, 195)],
        )
        audit = evaluator._topology_consistency_audit(("pkg",), a1, a2, adj)
        self.assertEqual(audit["status"], "source_choice_nonunique")
        self.assertEqual(audit["status_counts"], {"source_choice_nonunique": 1})
        self.assertEqual(
            audit["contingency"]["pair_equivalence"]["ADJ-A1"]["equivalent"], 1
        )
        self.assertEqual(
            audit["contingency"]["pair_equivalence"]["ADJ-A2"]["equivalent"], 1
        )
        self.assertEqual(audit["field_audit_discordance_count"], 0)
        self.assertEqual(
            audit["algorithmic_nonequivalence"],
            {"count": 0, "denominator": 1, "fraction": 0.0},
        )
        self.assertEqual(
            audit["packages"][0]["audit_reason"],
            "adjudication_equivalent_to_both_sources",
        )

    def test_minor_edit_requires_all_three_topologies_to_be_equivalent(self) -> None:
        self.assertEqual(
            evaluator._topology_audit_status(
                "same_topology_minor_edit", True, True, True
            ),
            "consistent",
        )
        self.assertEqual(
            evaluator._topology_audit_status(
                "same_topology_minor_edit", True, False, False
            ),
            "AUDIT_DISCORDANT",
        )
        self.assertEqual(
            evaluator._topology_audit_status(
                "same_topology_minor_edit", True, True, None
            ),
            "AUDIT_UNEVALUABLE",
        )

    def test_topology_audit_marks_absent_material_unevaluable(self) -> None:
        empty_a1 = self._bundle("", [], [])
        empty_a2 = self._bundle("", [], [])
        empty_adj = self._bundle("accept_a1", [], [])
        audit = evaluator._topology_consistency_audit(
            ("pkg",), empty_a1, empty_a2, empty_adj
        )
        self.assertEqual(audit["status"], "AUDIT_UNEVALUABLE")
        self.assertEqual(audit["status_counts"], {"AUDIT_UNEVALUABLE": 1})
        self.assertIsNone(
            audit["packages"][0]["pairwise"]["ADJ-A1"]["equivalent"]
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
