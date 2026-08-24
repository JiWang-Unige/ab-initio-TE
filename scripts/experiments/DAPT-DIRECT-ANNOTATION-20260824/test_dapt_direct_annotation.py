#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("dapt", HERE / "dapt_direct_annotation.py")
dapt = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(dapt)


class MaskingTests(unittest.TestCase):
    def test_matched_ce_array_uses_auto_token(self):
        sbatch = (HERE.parents[2] / "sbatch/DAPT-DIRECT-ANNOTATION-20260824-ce.sbatch").read_text(encoding="utf-8")
        self.assertIn("--kind auto_token", sbatch)
        self.assertNotIn("wrapper_auto", sbatch)

    def test_sequence_reader_never_requires_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train.jsonl"
            path.write_text(json.dumps({"sequence": "ACGT"}) + "\n", encoding="utf-8")
            self.assertEqual(list(dapt.iter_sequences(path, limit=1, window=4)), ["ACGT"])

    def test_frozen_recipe_constants(self):
        self.assertEqual(dapt.WINDOW, 8192)
        self.assertEqual(dapt.TRAIN_RECORDS, 3000)
        self.assertEqual(dapt.MASK_PROBABILITY, 0.15)
        self.assertEqual(dapt.OPTIMIZER_STEPS, 800)
        self.assertEqual(dapt.GRADIENT_ACCUMULATION, 16)

    def test_masking_deterministic_and_excludes_n_pad_special(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch is available in the training environment")
        ids = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])
        attention = torch.ones_like(ids)
        special = torch.tensor([[0, 0, 1, 0, 0, 0, 0, 0]])
        kwargs = dict(n_token_ids={5}, pad_token_id=6, mask_token_id=9,
                      acgt_token_ids=(1, 2, 3, 4), vocab_size=10)
        g1 = torch.Generator().manual_seed(42)
        g2 = torch.Generator().manual_seed(42)
        first = dapt.mask_inputs(ids, attention, special, generator=g1, **kwargs)
        second = dapt.mask_inputs(ids, attention, special, generator=g2, **kwargs)
        for left, right in zip(first, second):
            self.assertTrue(torch.equal(left, right))
        selected = first[2]
        self.assertFalse(bool(selected[0, 2]))
        self.assertFalse(bool(selected[0, 4]))
        self.assertFalse(bool(selected[0, 5]))
        self.assertFalse(bool(selected[0, 6]))
        self.assertTrue(torch.equal(first[1][~selected], torch.full_like(first[1][~selected], -100)))


if __name__ == "__main__":
    unittest.main()
