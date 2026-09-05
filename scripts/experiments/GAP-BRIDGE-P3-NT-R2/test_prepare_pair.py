"""Each test targets a reachable native-grid/paired-input failure, not model quality."""
import csv
import ast
from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

spec = importlib.util.spec_from_file_location("r2_prepare_pair", Path(__file__).with_name("prepare_pair.py"))
pair = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pair
spec.loader.exec_module(pair)


def geometry(start=8192, end=8194, seqid="chr3", role="TRAIN"):
    return pair.Geometry("candidate", seqid, role, start, end, 700, 800, end - start + 1500)


class Tensor:
    """Minimal numpy-backed torch boundary for executing the real adapter in CPU tests."""
    def __init__(self, data):
        self.data = np.asarray(data)
        self.shape = self.data.shape

    def __getitem__(self, key):
        return Tensor(self.data[key])

    def to(self, *_args):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.data


def real_strict_adapter():
    # Execute the exact production function, not a test reimplementation of
    # infer_probs_for_label_mode; mock only unavailable torch/model dependencies.
    path = pair.ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py"
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "infer_probs_for_label_mode")

    def softmax(value, dim):
        exponents = np.exp(value.data - value.data.max(axis=dim, keepdims=True))
        return Tensor(exponents / exponents.sum(axis=dim, keepdims=True))

    namespace = {"np": np, "torch": SimpleNamespace(device=object, no_grad=nullcontext, softmax=softmax)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(infer_probs_for_label_mode=namespace["infer_probs_for_label_mode"])


class KmerTokenizer:
    """Six-base ACGT tokens and singleton N tokens, with the real 688-token cap."""
    def __init__(self, offsets=True):
        self.offsets = offsets
        self.calls = []

    def tokenize(self, sequence):
        tokens = []
        position = 0
        while position < len(sequence):
            end = position + 1
            if sequence[position] != "N":
                while end < min(position + 6, len(sequence)) and sequence[end] != "N":
                    end += 1
            tokens.append(sequence[position:end])
            position = end
        return tokens

    def __call__(self, sequence, **kwargs):
        self.calls.append((sequence, kwargs))
        if kwargs.get("return_offsets_mapping") and not self.offsets:
            raise NotImplementedError("slow tokenizer has no offsets")
        length = kwargs["max_length"]
        mapping, position = [(0, 0)], 0
        for token in self.tokenize(sequence)[:length - 2]:
            mapping.append((position, position + len(token)))
            position += len(token)
        mapping.extend([(0, 0)] * (length - len(mapping)))
        encoded = {"input_ids": Tensor(np.zeros((1, length), dtype=int)),
                   "attention_mask": Tensor(np.ones((1, length), dtype=int))}
        if kwargs.get("return_offsets_mapping"):
            encoded["offset_mapping"] = Tensor([mapping])
        return encoded


def token_model(**inputs):
    length = inputs["input_ids"].shape[1]
    return SimpleNamespace(logits=Tensor(np.tile([0., 1.], (1, length, 1))))


class PairTests(unittest.TestCase):
    def test_nearest_tie_and_native_seam(self):
        """Catch seam sign/tie drift; fix feature geometry before any pairing run."""
        tie = geometry(6143, 6145)
        np.testing.assert_allclose(pair.nt_scalars(tie), [0, np.log1p(2048), 1])
        seam = geometry(8191, 8193)
        np.testing.assert_array_equal(pair.nt_scalars(seam), [1, 0, 0])

    def test_h0_zero_slots_and_hn_continuous_channel(self):
        """Catch accidental capacity/input differences or clipping/padding errors."""
        c = geometry()
        base = np.arange(143 * 1024, dtype=np.float32).reshape(143, 1024) / 10000
        old_scalars = np.arange(7, dtype=np.float32)
        probability = np.linspace(0, 1, c.crop_end - c.crop_start)
        stats = {"mean": [0.2, 3, 0.1], "scale": [0.5, 2, 0.7]}
        h0, hn, g0, gn = pair.pair_inputs(base, old_scalars, probability, c, stats)
        self.assertEqual(h0.shape, (144, 1024))
        self.assertEqual(g0.shape, (10,))
        np.testing.assert_array_equal(h0[:143], base)
        np.testing.assert_array_equal(hn[:143], base)
        np.testing.assert_array_equal(g0[:7], old_scalars)
        np.testing.assert_array_equal(gn[:7], old_scalars)
        self.assertFalse(h0[143].any())
        self.assertFalse(g0[7:].any())
        self.assertEqual(hn[143, 0], -12)
        self.assertEqual(hn[143, len(probability) - 1], 12)
        self.assertFalse(hn[143, len(probability):].any())
        self.assertGreater(len(np.unique(hn[143, :len(probability)])), 100)

    def test_native_terminal_and_unknown_coordinates(self):
        """Catch trim/compression and DNA-padding mistakes at a real terminal window."""
        tokenizer = KmerTokenizer()
        got, covered = pair.native_nt_window(real_strict_adapter(), token_model, tokenizer, "ACNTA", None, "nt_kmer")
        self.assertEqual(got.shape, (5,))
        self.assertTrue(covered.all())
        self.assertTrue((got > 0).all())
        self.assertEqual(tokenizer.calls[0][0], "ACNTA")

    def test_real_adapter_n_context_truncation_is_not_negative_evidence(self):
        """Catch shape-preserving 688-token truncation despite an all-ACGT candidate crop."""
        sequence = "N" * 800 + "A" * (4096 - 800)
        candidate = geometry(1300, 1302)
        self.assertEqual(set(sequence[candidate.crop_start:candidate.crop_end]), {"A"})
        for offset_support in (True, False):
            with self.subTest(offset_support=offset_support):
                tokenizer = KmerTokenizer(offset_support)
                got, covered = pair.native_nt_window(real_strict_adapter(), token_model, tokenizer,
                                                     sequence, None, "nt_kmer")
                self.assertEqual(got.shape, (4096,))
                self.assertTrue(np.isfinite(got).all())
                self.assertEqual(int(covered.sum()), 686)
                self.assertTrue((got[~covered] == 0).all())
                with self.assertRaisesRegex(ValueError, "NT_TOKEN_COVERAGE_FAILED"):
                    pair.require_crop_coverage(covered[candidate.crop_start:candidate.crop_end], candidate)
                self.assertEqual([call[1]["max_length"] for call in tokenizer.calls],
                                 [688] if offset_support else [688, 688])

    def test_real_adapter_coverage_obeys_actual_model_token_count(self):
        """Catch assuming all tokenizer offsets were consumed when model output is shorter."""
        def short_model(**inputs):
            return SimpleNamespace(logits=Tensor(np.tile([0., 1.], (1, 3, 1))))
        got, covered = pair.native_nt_window(real_strict_adapter(), short_model, KmerTokenizer(),
                                             "A" * 30, None, "nt_kmer")
        self.assertEqual(int(covered.sum()), 12)
        self.assertTrue((got[12:] == 0).all())

    def test_sequence_projection_does_not_access_labels(self):
        """Catch reusing Stage1 region reader's labels check in blind inference."""
        class ForbiddenLabels(dict):
            def __getitem__(self, key):
                if key == "labels":
                    raise AssertionError("labels accessed")
                return super().__getitem__(key)
            def get(self, key, default=None):
                if key == "labels":
                    raise AssertionError("labels accessed")
                return super().get(key, default)
        row = ForbiddenLabels(chr="chr3", start=8192, end=8197, sequence="acNta", labels=None)
        self.assertEqual(pair.sequence_record(row, "chr3"), (8192, 8197, "ACNTA"))

    def test_known_train_stats_and_scope(self):
        """Catch DEV/CAL/unknown eligibility leaking into fitted normalization."""
        fields = ["candidate_id", "seqid", "role", "gap_start", "gap_end", "left_run_start",
                  "left_run_end", "right_run_start", "right_run_end", "comparator_known"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.tsv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(fields)
                for seqid, role, known in [("chr3", "TRAIN", "1"), ("chr5", "TRAIN", "1"),
                                          ("chr3", "TRAIN", "0"), ("chr13", "DEV", "1"),
                                          ("chr13", "CAL-GATE", "1"), ("chr19", "TEST", "1")]:
                    writer.writerow([f"{seqid}-{role}-{known}", seqid, role, 8192, 8194,
                                     7500, 8192, 8194, 9000, known])
            train = list(pair.read_geometry(path, known_train_only=True))
            self.assertEqual([c.seqid for c in train], ["chr3", "chr5"])
            stats = pair.fit_nt_stats(train + [geometry(1234, 1240, "chr13", "DEV")])
            self.assertEqual(stats["count"], 2)
            self.assertEqual(stats["scale"], [1, 1, 1])
            self.assertEqual(len(list(pair.read_geometry(path))), 4)

    def test_cross_p3_window_crop_preserves_coordinates(self):
        """Catch previous/current carry offsets at the observed endpoint-seam shape."""
        c = geometry()
        windows = []
        for start in (0, 8192):
            coords = np.arange(start, start + 8192, dtype=np.float32)
            windows.append(pair.stage1.WindowFeatures(start, start + 8192, "A" * 8192,
                           np.repeat(coords[:, None], 4, axis=1), np.repeat(coords[None, :], 128, axis=0)))
        seq, logits, latent = pair.stage1.assemble_crop(*windows, c.crop_start, c.crop_end)
        expected = np.arange(c.crop_start, c.crop_end, dtype=np.float32)
        self.assertEqual(len(seq), len(expected))
        np.testing.assert_array_equal(logits[:, 0], expected)
        np.testing.assert_array_equal(latent[0], expected)


if __name__ == "__main__":
    unittest.main()
