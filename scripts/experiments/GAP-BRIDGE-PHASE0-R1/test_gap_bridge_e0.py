#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gap_bridge_e0", HERE / "gap_bridge_e0.py")
assert SPEC and SPEC.loader
e0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e0)


class RegionMaterializationTest(unittest.TestCase):
    def test_explicit_region_is_tail_safe_and_excludes_other_contigs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assembly = root / "assembly.fa"
            chr3 = "A" * 4097 + "C" * 4096 + "G" * 10
            chr5 = "T" * 9000
            assembly.write_text(
                ">chr3\n" + chr3[:5000] + "\n" + chr3[5000:] +
                "\n>chr5\n" + chr5 + "\n",
                encoding="ascii",
            )
            output = root / "chr3.jsonl.gz"
            manifest = root / "chr3.manifest.json"
            result = e0.write_region_jsonl(
                assembly, "chr3", 10, 8203, output, manifest,
            )
            self.assertEqual(result["windows"], 2)
            self.assertEqual(result["expected_windows"], 2)
            self.assertEqual(result["total_bp"], 8193)
            self.assertEqual(result["tail_windows"], 1)
            self.assertEqual(result["missing_bp"], 0)
            self.assertEqual(result["overlap_bp"], 0)
            with gzip.open(output, "rt", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle]
            self.assertEqual(
                [(row["chr"], row["start"], row["end"]) for row in rows],
                [("chr3", 10, 8202), ("chr3", 8202, 8203)],
            )
            self.assertEqual("".join(row["sequence"] for row in rows), chr3[10:8203])
            self.assertTrue(all(label == 0 for row in rows for label in row["labels"]))

    def test_fifty_megabase_shard_has_frozen_expected_window_count(self):
        self.assertEqual((50_000_000 + e0.WINDOW - 1) // e0.WINDOW, 6104)


class FrozenStitchTest(unittest.TestCase):
    def test_stitch_applies_known_mask_after_float32_threshold(self):
        rows = [
            {"chr": "chr17", "start": 0, "end": 4, "sequence": "AAAA", "labels": [0, -100, 0, 0]},
            {"chr": "chr17", "start": 4, "end": 6, "sequence": "CC", "labels": [0, 0]},
        ]
        values = iter([
            np.asarray([
                [0.6, 0.4, 0.0, 0.0],
                [0.4, 0.2, 0.2, 0.2],
                [0.5, 0.5, 0.0, 0.0],
                [0.1, 0.3, 0.3, 0.3],
            ], dtype=np.float32),
            np.asarray([
                [0.3, 0.7, 0.0, 0.0],
                [0.8, 0.2, 0.0, 0.0],
            ], dtype=np.float32),
        ])
        seqid, region_start, states, probability, known, windows = e0.stitch_track(
            rows, lambda _sequence: next(values), np.ones(e0.WINDOW, dtype=np.float32),
        )
        self.assertEqual(seqid, "chr17")
        self.assertEqual(region_start, 0)
        self.assertEqual(windows, 2)
        np.testing.assert_allclose(
            probability, np.asarray([0.4, 0.6, 0.5, 0.9, 0.7, 0.2], dtype=np.float32),
        )
        np.testing.assert_array_equal(
            probability, np.sum(states[:, 1:4], axis=1, dtype=np.float32),
        )
        np.testing.assert_array_equal(known, np.asarray([1, 0, 1, 1, 1, 1], dtype=bool))
        mask = (probability >= e0.THRESHOLD) & known
        self.assertEqual([(2, 5)], [(start, end) for start, end in _runs(mask)])

    def test_stitch_rejects_the_known_missing_coordinate_failure(self):
        rows = [
            {"chr": "chr3", "start": 0, "end": 2, "sequence": "AA", "labels": [0, 0]},
            {"chr": "chr3", "start": 3, "end": 4, "sequence": "C", "labels": [0]},
        ]
        with self.assertRaisesRegex(ValueError, "missing or overlapping"):
            e0.stitch_track(
                rows,
                lambda sequence: np.zeros((len(sequence), 4), dtype=np.float32),
                np.ones(e0.WINDOW, dtype=np.float32),
            )

    def test_stitch_supports_nonzero_aligned_region_start(self):
        rows = [
            {"chr": "chr3", "start": 8192, "end": 8194, "sequence": "AA", "labels": [0, 0]},
            {"chr": "chr3", "start": 8194, "end": 8195, "sequence": "C", "labels": [0]},
        ]
        values = iter([
            np.asarray([[0.8, 0.2, 0.0, 0.0], [0.4, 0.6, 0.0, 0.0]], dtype=np.float32),
            np.asarray([[0.3, 0.7, 0.0, 0.0]], dtype=np.float32),
        ])
        seqid, region_start, states, probability, known, windows = e0.stitch_track(
            rows, lambda _sequence: next(values), np.ones(e0.WINDOW, dtype=np.float32),
        )
        self.assertEqual((seqid, region_start, windows), ("chr3", 8192, 2))
        self.assertEqual(states.shape, (3, 4))
        np.testing.assert_allclose(probability, [0.2, 0.6, 0.7])
        np.testing.assert_array_equal(known, [True, True, True])

    def test_saved_state_track_is_float16_with_frozen_shape(self):
        states = np.asarray([
            [0.7, 0.1, 0.1, 0.1],
            [0.2, 0.5, 0.2, 0.1],
        ], dtype=np.float32)
        p_te = np.sum(states[:, 1:4], axis=1, dtype=np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            e0.write_probability_tracks(root / "pte.npy", root / "states.npy", p_te, states)
            saved_pte = np.load(root / "pte.npy", allow_pickle=False)
            saved_states = np.load(root / "states.npy", allow_pickle=False)
        self.assertEqual(saved_pte.dtype, np.float32)
        self.assertEqual(saved_states.dtype, np.float16)
        self.assertEqual(saved_states.shape, (2, 4))


class IdentityTest(unittest.TestCase):
    def test_identity_is_exact_tuple_and_length_equality(self):
        expected = [("chr17", 1, 3), ("chr17", 5, 8)]
        passed = e0.identity_result(expected, list(expected), {"chr17": 10}, "chr17", 10)
        self.assertEqual(passed["status"], "PASS")
        failed = e0.identity_result(
            expected, [("chr17", 1, 3), ("chr17", 5, 9)], {"chr17": 10}, "chr17", 10,
        )
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(failed["first_difference"]["index"], 1)
        self.assertFalse(failed["scientific_metrics_computed"])


class WholeChromosomeStitchTest(unittest.TestCase):
    def write_chunk(
        self, root: Path, start: int, end: int, sequence: str,
        probability: np.ndarray, runs: list[tuple[int, int]], tail: int,
    ) -> None:
        root.mkdir(parents=True)
        with gzip.open(root / "region.jsonl.gz", "wt", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "chr": "chr3", "start": start, "end": end,
                "sequence": sequence, "labels": [0] * (end - start),
            }) + "\n")
        region = {
            "status": "PASS", "seqid": "chr3", "region_start": start,
            "region_end": end, "windows": 1, "tail_windows": tail,
        }
        export = {
            "status": "PASS", "seqid": "chr3", "region_start": start,
            "region_end": end, "length": end - start, "windows": 1,
            "known_bp": end - start, "model_schema": "test_schema",
        }
        (root / "region.manifest.json").write_text(json.dumps(region), encoding="utf-8")
        (root / "export.manifest.json").write_text(json.dumps(export), encoding="utf-8")
        np.save(root / "p_te.npy", probability.astype(np.float32), allow_pickle=False)
        states = np.zeros((end - start, 4), dtype=np.float16)
        states[:, 0] = 1 - probability
        states[:, 1] = probability
        np.save(root / "states.npy", states, allow_pickle=False)
        e0.write_canonical(root / "prediction.canonical.tsv", "chr3", runs)

    def test_chunk_stitch_merges_a_positive_run_across_an_aligned_seam(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks = root / "chunks"
            self.write_chunk(
                chunks / "0-8192", 0, 8192, "A" * 8192,
                np.full(8192, 0.8), [(8189, 8192)], 0,
            )
            self.write_chunk(
                chunks / "8192-8195", 8192, 8195, "CCC",
                np.asarray([0.8, 0.8, 0.2]), [(8192, 8194)], 1,
            )
            whole = root / "whole"
            whole.mkdir()
            result = e0.stitch_chunk_exports(
                chunks, "chr3", 8195,
                whole / "region.jsonl.gz", whole / "region.manifest.json",
                whole / "p_te.npy", whole / "states.npy",
                whole / "prediction.canonical.tsv", whole / "export.manifest.json",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["windows"], 2)
            self.assertEqual(e0.canonical_tuples(whole / "prediction.canonical.tsv"), [("chr3", 8189, 8194)])
            self.assertEqual(np.load(whole / "p_te.npy", allow_pickle=False).shape, (8195,))
            self.assertEqual(np.load(whole / "states.npy", allow_pickle=False).shape, (8195, 4))
            with gzip.open(whole / "region.jsonl.gz", "rt", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle]
            self.assertEqual([(row["start"], row["end"]) for row in rows], [(0, 8192), (8192, 8195)])


def _runs(mask: np.ndarray):
    start = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            yield start, index
            start = None
    if start is not None:
        yield start, len(mask)


if __name__ == "__main__":
    unittest.main()
