#!/usr/bin/env python3
"""Targeted tests for the Phase 0 fragment-linking contract."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from fragment_linking_phase0 import (
    ENGINEERING_ONLY,
    KNOWN,
    UNRESOLVED,
    assign_group_splits,
    build_candidate_pairs,
    build_split_role_records,
    evaluate,
    interval_snapshot,
    make_fixture,
    pair_row,
    run,
    validate_fragments,
    validate_group_split,
)


class FragmentLinkingPhase0Test(unittest.TestCase):
    def setUp(self) -> None:
        self.fragments = make_fixture()
        validate_fragments(self.fragments)
        self.before = interval_snapshot(self.fragments)
        self.source_splits = assign_group_splits(self.fragments, "source_copy_id", seed=42)
        self.family_splits = assign_group_splits(self.fragments, "family_group_id", seed=42)
        self.split_rows = build_split_role_records(self.fragments, self.source_splits, self.family_splits)
        self.pairs = build_candidate_pairs(self.fragments, max_distance_bp=25)
        self.rows = [
            pair_row(a, b, 25, 0.5, self.source_splits, self.family_splits)
            for a, b in self.pairs
        ]

    def row(self, pair_id: str) -> dict:
        return next(row for row in self.rows if row["pair_id"] == pair_id)

    def test_fixture_has_required_cases_and_separate_namespaces(self) -> None:
        cases = {fragment.case for fragment in self.fragments}
        self.assertTrue({
            "same_insertion",
            "adjacent_independent",
            "nested_outer",
            "nested_inner",
            "unknown_orientation",
            "transitive_chain",
            "far_same_insertion",
            "unresolved_truth",
        }.issubset(cases))
        self.assertTrue(all(fragment.annotation_provenance == ENGINEERING_ONLY for fragment in self.fragments))
        self.assertTrue(all(
            fragment.parent_insertion_id != fragment.source_copy_id
            for fragment in self.fragments
            if fragment.truth_status == KNOWN
        ))
        for fragment in self.fragments:
            record = fragment.to_record()
            self.assertIn("truth", record)
            self.assertIn("prediction", record)
            self.assertNotIn("predicted_family", record["truth"])
            self.assertNotIn("parent_insertion_id", record["prediction"])

    def test_half_open_intervals_and_group_split_no_leakage(self) -> None:
        self.assertTrue(all(fragment.end - fragment.start > 0 for fragment in self.fragments))
        validate_group_split(self.split_rows, "source_copy_id", "source_copy_split")
        validate_group_split(self.split_rows, "family_group_id", "family_group_split")
        same_copy_splits = {
            row["source_copy_split"] for row in self.split_rows if row["source_copy_id"] == "copy_same"
        }
        line_family_splits = {
            row["family_group_split"] for row in self.split_rows if row["family_group_id"] == "Fam_LINE_A"
        }
        self.assertEqual(len(same_copy_splits), 1)
        self.assertEqual(len(line_family_splits), 1)

    def test_split_validation_rejects_a_real_fragment_role_leak(self) -> None:
        bad_rows = [dict(row) for row in self.split_rows]
        bad_rows[0]["source_copy_split"] = "test"
        # The other same-copy fragment retains its original role, so this is a
        # genuine fragment->role violation rather than a self-consistent map.
        with self.assertRaises(AssertionError):
            validate_group_split(bad_rows, "source_copy_id", "source_copy_split")

    def test_candidate_recall_denominator_is_all_known_true_pairs(self) -> None:
        metrics = evaluate(self.fragments, self.rows, max_distance_bp=25)
        self.assertEqual(metrics["candidate_recall_denominator_all_known_same_insertion_pairs"], 4)
        self.assertEqual(metrics["candidate_recall_numerator_same_insertion_pairs_in_candidates"], 2)
        self.assertEqual(metrics["candidate_recall"], 0.5)
        self.assertEqual(metrics["unresolved_pairs_in_candidate_table"], 1)
        # The far_same_insertion pair is intentionally absent from candidates.
        self.assertFalse(any(row["pair_id"] == "far_a__far_b" for row in self.rows))

    def test_b0_and_b1_rules_keep_truth_separate(self) -> None:
        same = self.row("same_a__same_b")
        self.assertTrue(same["B0_distance_edge"])
        self.assertTrue(same["B1_rule_edge"])
        self.assertEqual(same["truth_pair_status"], "same_insertion")

        adjacent = self.row("adj_a__adj_b")
        self.assertTrue(adjacent["B0_distance_edge"])
        self.assertTrue(adjacent["B1_rule_edge"])
        self.assertEqual(adjacent["truth_pair_status"], "different_insertion")

        nested = self.row("outer_left__inner")
        self.assertTrue(nested["B0_distance_edge"])
        self.assertFalse(nested["B1_rule_edge"])
        self.assertEqual(nested["truth_pair_status"], "different_insertion")

        unknown = self.row("unknown_a__unknown_b")
        self.assertTrue(unknown["B0_distance_edge"])
        self.assertFalse(unknown["B1_rule_edge"])
        self.assertIn("orientation", unknown["B1_rule_reasons"])

    def test_unresolved_is_excluded_from_negative_counts(self) -> None:
        unresolved = self.row("unresolved_a__unresolved_b")
        self.assertEqual(unresolved["truth_pair_status"], "unresolved")
        self.assertIsNone(unresolved["truth_same_insertion"])
        self.assertTrue(unresolved["B0_distance_edge"])
        self.assertTrue(unresolved["B1_rule_edge"])
        metrics = evaluate(self.fragments, self.rows, max_distance_bp=25)
        for method in metrics["methods"].values():
            self.assertEqual(method["unresolved_candidate_pairs_excluded"], 1)
            self.assertEqual(method["unresolved_predicted_edges_excluded"], 1)
            self.assertTrue(method["unresolved_never_counted_as_negative"])

    def test_pair_rows_carry_endpoint_roles_and_cross_split_gate(self) -> None:
        self.assertTrue(all("left_source_copy_role" in row for row in self.rows))
        self.assertTrue(all("right_family_group_role" in row for row in self.rows))
        self.assertTrue(any(row["edge_split_gate"] == "EXCLUDED_CROSS_SPLIT" for row in self.rows))
        for row in self.rows:
            if row["source_copy_pair_gate"] == "EXCLUDED_CROSS_SPLIT":
                self.assertIsNone(row["source_copy_pair_role"])
            if row["family_group_pair_gate"] == "ELIGIBLE_SAME_ROLE":
                self.assertEqual(row["left_family_group_role"], row["right_family_group_role"])

    def test_transitive_chain_is_detected_and_intervals_are_unchanged(self) -> None:
        metrics = evaluate(self.fragments, self.rows, max_distance_bp=25)
        b1 = metrics["methods"]["B1_predicted_family_orientation_length"]
        self.assertTrue(b1["transitive_chain_false_merge_detected"])
        self.assertTrue(any(set(component) == {"chain_a", "chain_b", "chain_c"} for component in b1["components"]))
        self.assertTrue(metrics["intervals_unchanged"])
        self.assertFalse(metrics["gap_filling_applied"])
        self.assertFalse(metrics["material_mask_changed"])
        self.assertEqual(self.before, interval_snapshot(self.fragments))

    def test_cli_output_is_small_and_has_no_merged_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            summary = run(Path(temp), max_distance_bp=25, min_length_ratio=0.5, seed=42)
            self.assertTrue((Path(temp) / "contract.json").is_file())
            self.assertTrue((Path(temp) / "fixture_fragments.jsonl").is_file())
            self.assertTrue((Path(temp) / "edges_B0_distance.tsv").is_file())
            self.assertTrue((Path(temp) / "edges_B1_predicted_rules.tsv").is_file())
            self.assertEqual(summary["fixture_provenance"], ENGINEERING_ONLY)
            self.assertFalse(summary["gap_filling_applied"])
            self.assertFalse(summary["material_mask_changed"])
            for name in ("edges_B0_distance.tsv", "edges_B1_predicted_rules.tsv"):
                with (Path(temp) / name).open(encoding="utf-8", newline="") as handle:
                    gated_rows = list(csv.DictReader(handle, delimiter="\t"))
                self.assertTrue(all(row["edge_split_gate"] == "ELIGIBLE_SAME_ROLE" for row in gated_rows))
            with (Path(temp) / "pairs.tsv").open(encoding="utf-8", newline="") as handle:
                pair_rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertTrue(any(row["edge_split_gate"] == "EXCLUDED_CROSS_SPLIT" for row in pair_rows))
            cluster_text = (Path(temp) / "clusters_B1_predicted_rules.tsv").read_text(encoding="utf-8")
            self.assertNotIn("merged_start", cluster_text)
            self.assertNotIn("merged_end", cluster_text)


if __name__ == "__main__":
    unittest.main()
