#!/usr/bin/env python3
"""Pure contract tests for the native GLM extraction helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("extract_glm_embeddings", HERE / "extract_glm_embeddings.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class ExtractGlmContractTest(unittest.TestCase):
    def test_native_model_name_is_fixed(self):
        self.assertEqual(module.MODEL_ID, "nucleotide-transformer-v2-500m-multi-species")
        with self.assertRaises(ValueError):
            module.require_native_model(Path("/tmp/other-model"))

    def test_special_tokens_are_excluded_from_pool_mask(self):
        mask = module.non_special_mask(
            [3, 728, 3379, 1, 0],
            [1, 1, 1, 0, 1],
            [0, 1, 2, 3],
        )
        self.assertEqual(mask, [0, 1, 1, 0, 0])

    def test_long_sequences_split_at_content_token_boundaries(self):
        class TinyTokenizer:
            def __call__(self, sequence, add_special_tokens=False, truncation=False):
                return {"input_ids": list(range(len(sequence)))}

            def build_inputs_with_special_tokens(self, ids):
                return [99] + list(ids)

        parts = module.token_segments(TinyTokenizer(), "A" * 10, max_token_length=5)
        self.assertEqual(parts, [list(range(4)), list(range(4, 8)), [8, 9]])

    def test_segment_aggregation_is_content_token_weighted(self):
        pooled = module.weighted_segment_mean([[1.0, 3.0], [5.0, 7.0]], [1, 3])
        self.assertEqual(pooled, [4.0, 6.0])
        with self.assertRaises(ValueError):
            module.weighted_segment_mean([[1.0]], [0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
