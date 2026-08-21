#!/usr/bin/env python3
"""Executable counterexamples for denovoTE-eval commit f735c252.

These tests intentionally encode the claim-grade simulator contract. Failures
against unmodified upstream are evidence that it cannot be used as T0 truth
without a reviewed patch and an independent output verifier.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


UPSTREAM: Path
sequence_module = None
nest_module = None


def load_modules(path: Path) -> None:
    global UPSTREAM, sequence_module, nest_module
    UPSTREAM = path
    sys.path.insert(0, str(path))
    sequence_module = importlib.import_module("random_sequence_TEs")
    nest_module = importlib.import_module("random_nest_TEs")


class UpstreamSimulatorContractTests(unittest.TestCase):
    def test_deletion_occurs_at_declared_indel_position(self):
        with patch.object(sequence_module.random, "choice", return_value=0):
            observed = sequence_module.add_indels("ACGTA", [3])
        self.assertEqual(observed, "ACGA", "deletion must remove declared zero-based position 3")

    def test_non_tsd_element_does_not_inherit_previous_element_tsd(self):
        first = sequence_module.Repeat("first", "C", 1, 100, 0, 0, True, 0, 0)
        second = sequence_module.Repeat("second", "G", 1, 100, 0, 0, False, 0, 0)
        with (
            patch.object(sequence_module, "get_identity", return_value=100),
            patch.object(sequence_module, "generate_mismatches", return_value=([], [])),
            patch.object(sequence_module, "add_base_changes", side_effect=lambda seq, _: seq),
            patch.object(sequence_module, "add_indels", side_effect=lambda seq, _: seq),
            patch.object(sequence_module, "create_TSD", return_value=("TT", "TT")),
            patch.object(sequence_module.random, "choice", side_effect=lambda values: values[0]),
        ):
            observed, _ = sequence_module.generate_sequence(
                {"first": first, "second": second},
                [1, 3],
                "AAAA",
                [("first", 0), ("second", 0)],
            )
        expected_length = 4 + 1 + 1 + 2 + 2
        self.assertEqual(
            len(observed),
            expected_length,
            "only the first element is configured to receive the 2+2 bp TSD",
        )

    def test_identity_sampling_is_bounded_below_by_zero(self):
        with patch.object(sequence_module.numpy.random, "normal", return_value=-5):
            observed = sequence_module.get_identity(1, 100)
        self.assertGreaterEqual(observed, 0)

    def test_nested_outer_right_fragment_starts_after_nested_interval(self):
        repeat = sequence_module.Repeat("nested", "CC", 1, 100, 0, 0, False, 0, 100)
        original_gff = [["sequence", "script", "repeat_region", "1", "10", ".", "+", ".", "ID=host;identity=100"]]
        captured: dict[str, object] = {}

        def capture(_prefix, seq, gff):
            captured["sequence"] = seq
            captured["gff"] = gff

        def controlled_choice(values):
            if values == [1, 1, 0]:
                return 0
            return values[0]

        with (
            patch.object(nest_module.random, "shuffle", side_effect=lambda values: None),
            patch.object(nest_module.random, "sample", return_value=[0]),
            patch.object(nest_module.random, "randint", return_value=50),
            patch.object(nest_module.random, "choice", side_effect=controlled_choice),
            patch.object(nest_module, "get_identity", return_value=100),
            patch.object(nest_module, "generate_mismatches", return_value=([], [])),
            patch.object(nest_module, "add_base_changes", side_effect=lambda seq, _: seq),
            patch.object(nest_module, "add_indels", side_effect=lambda seq, _: seq),
            patch.object(nest_module, "print_data", side_effect=capture),
        ):
            nest_module.generate_nests({"nested": repeat}, original_gff, "A" * 10, "fixture")

        gff = captured["gff"]
        nested = gff[1]
        outer_right = gff[2]
        self.assertEqual(int(outer_right[3]), int(nested[4]) + 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    args, unittest_args = parser.parse_known_args()
    load_modules(args.upstream.resolve())
    unittest.main(argv=[sys.argv[0], *unittest_args], verbosity=2)


if __name__ == "__main__":
    main()
