#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("te_span_mlm", HERE / "te_span_mlm.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def masks(interior=(100, 1000), boundary=(1000, 1100), flank=(1100, 2200)):
    return {
        "interior": [interior[0] <= i < interior[1] for i in range(MODULE.WINDOW)],
        "boundary": [boundary[0] <= i < boundary[1] for i in range(MODULE.WINDOW)],
        "flank": [flank[0] <= i < flank[1] for i in range(MODULE.WINDOW)],
    }


class SpanMaskMechanismTests(unittest.TestCase):
    def test_spans_are_contiguous_and_stratum_pure(self):
        result = MODULE.sample_contiguous_spans(masks(), target_fraction=0.15, span_length=32, seed=7)
        selected = result["selected"]
        for row in result["spans"]:
            start, end = int(row["start"]), int(row["end"])
            self.assertEqual(end - start, 32)
            self.assertTrue(all(selected[start:end]))
            stratum = row["stratum"]
            for index in range(start, end):
                self.assertTrue(masks()[stratum][index])
        runs = MODULE._runs(selected)
        self.assertEqual(sum(end - start for start, end in runs), result["selected_bp"])
        self.assertEqual(len(runs), len(result["spans"]))

    def test_unknown_and_n_positions_are_not_selected(self):
        unknown = [500 <= i < 540 for i in range(MODULE.WINDOW)]
        n_mask = [1500 <= i < 1540 for i in range(MODULE.WINDOW)]
        result = MODULE.sample_contiguous_spans(
            masks(), unknown_mask=unknown, n_mask=n_mask, target_fraction=0.15, span_length=32, seed=7
        )
        self.assertFalse(any(selected and blocked for selected, blocked in zip(result["selected"], unknown)))
        self.assertFalse(any(selected and blocked for selected, blocked in zip(result["selected"], n_mask)))

    def test_mlm_labels_remain_original_nucleotide_targets(self):
        try:
            import torch
        except ModuleNotFoundError:
            self.skipTest("torch is available in the te_benchmark training environment")

        result = MODULE.sample_contiguous_spans(masks(), target_fraction=0.15, span_length=32, seed=7)
        input_ids = torch.ones((1, MODULE.WINDOW), dtype=torch.long)
        attention = torch.ones_like(input_ids)
        special = torch.zeros_like(input_ids)
        masked, labels, selected = MODULE.apply_span_mask(
            input_ids,
            attention,
            special,
            torch.tensor([result["selected"]], dtype=torch.bool),
            n_token_ids={4},
            pad_token_id=None,
            mask_token_id=9,
            acgt_token_ids=(1, 2, 3, 4),
            vocab_size=10,
            generator=torch.Generator().manual_seed(7),
        )
        self.assertGreater(int(selected.sum()), 0)
        self.assertTrue(torch.equal(labels[selected], input_ids[selected]))
        self.assertTrue(torch.equal(labels[~selected], torch.full_like(labels[~selected], -100)))
        self.assertTrue(torch.equal(masked[~selected], input_ids[~selected]))

    def test_overlapping_strata_are_rejected(self):
        bad = masks()
        bad["boundary"][150] = True
        with self.assertRaisesRegex(ValueError, "candidate strata overlap"):
            MODULE.sample_contiguous_spans(bad, target_fraction=0.15, span_length=32)

    def test_boundary_is_taken_from_explicit_mask_not_label_transition(self):
        candidate = masks(interior=(100, 1000), boundary=(3000, 3100), flank=(1100, 2200))
        result = MODULE.sample_contiguous_spans(candidate, target_fraction=0.15, span_length=32, seed=3)
        boundary_spans = [row for row in result["spans"] if row["stratum"] == "boundary"]
        self.assertTrue(boundary_spans)
        self.assertTrue(all(3000 <= int(row["start"]) and int(row["end"]) <= 3100 for row in boundary_spans))

    def test_wrong_window_length_is_rejected(self):
        bad = masks()
        bad["flank"] = bad["flank"][:-1]
        with self.assertRaisesRegex(ValueError, "flank length"):
            MODULE.sample_contiguous_spans(bad, target_fraction=0.15, span_length=32)

    def test_copy_level_gate(self):
        self.assertTrue(MODULE.metadata_allows_training({"copy_level": True}))
        self.assertTrue(MODULE.metadata_allows_training({"label_level": "copy_level"}))
        self.assertFalse(MODULE.metadata_allows_training({"copy_level": False}))
        self.assertFalse(MODULE.metadata_allows_training({"label_level": "reference_run"}))


if __name__ == "__main__":
    unittest.main()
