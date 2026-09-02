#!/usr/bin/env python3
"""CPU tests for the frozen Stage 1 evaluator state and input joins."""
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stage1_evaluate", HERE / "stage1_evaluate.py")
assert SPEC is not None and SPEC.loader is not None
evaluate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluate
SPEC.loader.exec_module(evaluate)


class Stage1EvaluateTest(unittest.TestCase):
    def _candidate(self, candidate_id: str, gap_start: int, gap_end: int, positive: int, negative: int, unknown: int = 0):
        base = evaluate.stage0.BaseCandidate(
            candidate_id, "chr13", gap_start - 10, gap_start,
            gap_start, gap_end, gap_end, gap_end + 10,
        )
        return evaluate.EvalCandidate(
            candidate_id, "CAL_GATE", 0, base, "COMPARATOR_BRIDGE_SUPPORTED",
            positive, negative, unknown,
        )

    def _data(self, candidates):
        return evaluate.stage0.ChromData(
            "chr13", 100, [(0, 100)], [(0, 100)], [(0, 100)],
            [(0, 50)], [], [(0, 10), (15, 25), (40, 50)],
            [evaluate.stage0.Candidate(c.base, c.relation, c.positive_bp, c.negative_bp, c.unknown_bp) for c in candidates],
        )

    def test_fragment_state_matches_stage0_after_complete_gap_actions(self):
        candidates = [self._candidate("a", 10, 15, 5, 0), self._candidate("b", 25, 40, 15, 0)]
        data = self._data(candidates)
        state = evaluate.PolicyState(data, candidates)
        state.add(candidates[0])
        state.add(candidates[1])
        expected = evaluate.stage0.evaluate_dataset([data], {"a", "b"})
        self.assertEqual(state.summary()["fragmentation"], expected["fragmentation"])
        self.assertEqual(state.summary()["whole_mask"], expected["whole_mask"])
        self.assertEqual(state.summary()["selected_positive_bp"], expected["selected_positive_bp"])

    def test_fragment_state_counts_a_truth_run_that_is_only_in_the_selected_gap(self):
        candidate = self._candidate("gap_only", 10, 15, 5, 0)
        data = evaluate.stage0.ChromData(
            "chr13", 100, [(0, 100)], [(0, 100)], [(0, 100)],
            [(10, 15)], [], [(0, 10), (15, 25)],
            [evaluate.stage0.Candidate(candidate.base, candidate.relation, 5, 0, 0)],
        )
        state = evaluate.PolicyState(data, [candidate])
        state.add(candidate)
        expected = evaluate.stage0.evaluate_dataset([data], {"gap_only"})
        self.assertEqual(state.summary()["fragmentation"], expected["fragmentation"])

    def test_manifest_score_and_purge_joins_reject_missing_denominators(self):
        fields = [
            "candidate_id", "seqid", "role", "chr13_block_index", "left_run_start", "left_run_end",
            "gap_start", "gap_end", "right_run_start", "right_run_end", "crop_start", "crop_end",
            "gap_length", "length_stratum", "comparator_known", "positive_bp", "negative_bp", "unknown_bp",
            "target_negative_fraction", "comparator_relation",
        ]
        row = {
            "candidate_id": "c", "seqid": "chr13", "role": "DEV", "chr13_block_index": "0",
            "left_run_start": "290", "left_run_end": "300", "gap_start": "300", "gap_end": "305",
            "right_run_start": "305", "right_run_end": "315", "crop_start": "44", "crop_end": "561",
            "gap_length": "5", "length_stratum": "3-5", "comparator_known": "1", "positive_bp": "5",
            "negative_bp": "0", "unknown_bp": "0", "target_negative_fraction": "0", "comparator_relation": "COMPARATOR_BRIDGE_SUPPORTED",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.tsv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
                writer.writeheader()
                writer.writerow(row)
            candidates = evaluate.read_manifest(manifest)
            purge = root / "purge.tsv"
            with purge.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=("candidate_id", "seqid", "purged"), delimiter="\t")
                writer.writeheader()
                writer.writerow({"candidate_id": "c", "seqid": "chr13", "purged": "0"})
            self.assertEqual(evaluate.read_purge(purge, candidates), {"c": False})
            with purge.open("a", newline="", encoding="utf-8") as handle:
                handle.write("extra\tchr13\t0\n")
            with self.assertRaises(ValueError):
                evaluate.read_purge(purge, candidates)

    def test_budget_utility_counts_partially_resolved_internal_gap(self):
        result = {
            "selected_evaluation": {
                "incremental_state": {
                    "selected_positive_bp": 7,
                    "fragmentation": {
                        "raw": {"internal_gap_count": 2, "split_truth_runs": 1},
                        "refined": {"internal_gap_count": 1, "split_truth_runs": 1},
                    },
                },
            },
        }
        self.assertEqual(evaluate._budget_utility_values(result), (7.0, 1.0))


if __name__ == "__main__":
    unittest.main()
