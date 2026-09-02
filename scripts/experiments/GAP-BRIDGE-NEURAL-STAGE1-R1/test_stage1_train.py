#!/usr/bin/env python3
"""CPU-only contract tests for the frozen Stage 1 training data path."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    import numpy as np
except ModuleNotFoundError:
    np = None


if np is not None:
    SPEC = importlib.util.spec_from_file_location("stage1_train_test_module", ROOT / "stage1_train.py")
    assert SPEC is not None and SPEC.loader is not None
    train = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = train
    SPEC.loader.exec_module(train)
else:
    train = None


def candidate(
    candidate_id: str,
    gap_start: int,
    gap_length: int,
    left_length: int = 300,
    right_length: int = 300,
) -> object:
    gap_end = gap_start + gap_length
    return train.CandidateRow(
        candidate_id=candidate_id,
        seqid="chr3",
        gap_start=gap_start,
        gap_end=gap_end,
        gap_length=gap_length,
        left_run_length=left_length,
        right_run_length=right_length,
        span_length=left_length + gap_length + right_length,
        target=0.0,
        stratum=train.length_stratum(gap_length),
    )


@unittest.skipUnless(np is not None, "NumPy is unavailable in this interpreter")
class Stage1TrainTest(unittest.TestCase):
    def test_cross_window_crop_uses_only_previous_carry(self) -> None:
        previous = train.WindowFeatures(
            start=0,
            end=train.WINDOW,
            sequence="A" * train.WINDOW,
            logits=np.arange(train.WINDOW * 4, dtype=np.float32).reshape(train.WINDOW, 4),
            latent=np.arange(train.LATENT_WIDTH * train.WINDOW, dtype=np.float32).reshape(
                train.LATENT_WIDTH, train.WINDOW,
            ),
        )
        current = train.WindowFeatures(
            start=train.WINDOW,
            end=2 * train.WINDOW,
            sequence="C" * train.WINDOW,
            logits=np.arange(train.WINDOW * 4, dtype=np.float32).reshape(train.WINDOW, 4) + 1_000_000,
            latent=np.arange(train.LATENT_WIDTH * train.WINDOW, dtype=np.float32).reshape(
                train.LATENT_WIDTH, train.WINDOW,
            ) + 2_000_000,
        )
        crop_start, crop_end = train.WINDOW - 248, train.WINDOW + 269
        sequence, logits, latent = train.assemble_crop(previous, current, crop_start, crop_end)
        self.assertEqual(sequence, "A" * 248 + "C" * 269)
        np.testing.assert_array_equal(logits[:248], previous.logits[-248:])
        np.testing.assert_array_equal(logits[248:], current.logits[:269])
        np.testing.assert_array_equal(latent[:, :248], previous.latent[:, -248:])
        np.testing.assert_array_equal(latent[:, 248:], current.latent[:, :269])

    def test_channels_encode_geometry_sequence_and_right_padding(self) -> None:
        row = candidate("channel", 100_000_003, 5)
        sequence = ("ACGT" * 130)[: row.crop_end - row.crop_start]
        logits = np.zeros((len(sequence), 4), dtype=np.float32)
        logits[0] = [0.0, 2.0, -1.0, -1.0]
        logits[1] = [2.0, -2.0, -2.0, -2.0]
        latent = np.arange(train.LATENT_WIDTH * len(sequence), dtype=np.float32).reshape(
            train.LATENT_WIDTH, len(sequence),
        )
        channels = train.build_channels(sequence, logits, latent, row)
        length = len(sequence)
        self.assertEqual(channels.shape, (train.CHANNELS, train.MAX_INPUT_BP))
        np.testing.assert_array_equal(channels[:3, 0], logits[0, 1:] - logits[0, :1])
        self.assertEqual(channels[3, 0], 1.0)
        self.assertEqual(channels[3, 1], 0.0)
        self.assertEqual(channels[4, 0], 1.0)
        self.assertEqual(channels[5, train.FLANK_BP], 1.0)
        self.assertEqual(channels[6, train.FLANK_BP + row.gap_length], 1.0)
        self.assertAlmostEqual(float(channels[7, 0]), (row.crop_start - row.gap_start) / 512.0)
        self.assertAlmostEqual(float(channels[8, 0]), (row.crop_start - row.gap_end) / 512.0)
        self.assertTrue(np.all(channels[9, :length] == 1.0))
        self.assertTrue(np.all(channels[9, length:] == 0.0))
        for offset, base in enumerate(train.BASES):
            self.assertTrue(np.all(channels[10 + offset, :length] == [char == base for char in sequence]))
        self.assertTrue(np.all(channels[14, :length] == 0.0))
        self.assertTrue(np.all(channels[14, length:] == 1.0))
        np.testing.assert_array_equal(channels[15:, :length], latent)
        self.assertTrue(np.all(channels[:, length:][np.arange(train.CHANNELS) != 14] == 0.0))

    def test_candidate_anchor_sort_and_scalar_stats(self) -> None:
        late = candidate("late", 8_300, 1)
        early = candidate("early", 8_200, 1)
        anchors = train._candidate_anchors([late, early])
        self.assertEqual([row.candidate_id for row in anchors["chr3"][1]], ["early", "late"])

        rows = [
            candidate("l1", 300, 1, 10, 20),
            candidate("l2", 1_000, 2, 20, 30),
            candidate("l3", 4_095, 3, 30, 40),
            candidate("l4", 8_180, 6, 40, 50),
            candidate("l5", 12_000, 21, 50, 60),
            candidate("l6", 16_380, 101, 60, 70),
        ]
        stats = train.scalar_stats(rows)
        raw = np.asarray([train.scalar_values(row) for row in rows], dtype=np.float64)
        self.assertEqual(stats["count"], len(rows))
        np.testing.assert_allclose(stats["mean"], raw.mean(axis=0))
        np.testing.assert_allclose(stats["scale"], raw.std(axis=0))
        tie = train.scalar_values(candidate("tie", 4_095, 2))
        self.assertEqual(float(tie[-1]), -1.0)
        with self.assertRaisesRegex(ValueError, "zero-variance"):
            train.scalar_stats([candidate("one", 300, 1)])

    def test_final_partial_batch_is_not_dropped_when_strata_are_unbalanced(self) -> None:
        samples = [
            train.Sample(
                channels=np.zeros((train.CHANNELS, train.MAX_INPUT_BP), dtype=np.float32),
                geometry=np.zeros(train.GEOMETRY_SCALARS, dtype=np.float32),
                target=0.0,
                length=1,
                stratum="1",
                candidate_id=f"candidate-{index}",
            )
            for index in range(3)
        ]
        pending = list(samples)
        self.assertIsNone(train._pop_ready_batch(pending))
        self.assertEqual(train._pop_ready_batch(pending, final=True), samples)
        self.assertEqual(pending, [])

    def test_manifest_loader_uses_only_known_train_chr3_chr5_rows(self) -> None:
        fields = [
            "row_id", "candidate_id", "seqid", "role", "chr13_block_index",
            "left_run_start", "left_run_end", "gap_start", "gap_end",
            "right_run_start", "right_run_end", "crop_start", "crop_end",
            "gap_length", "length_stratum", "comparator_known", "positive_bp",
            "negative_bp", "unknown_bp", "target_negative_fraction", "comparator_relation",
        ]
        rows = []
        lengths = [1, 2, 3, 6, 21, 101]
        for index, length in enumerate(lengths):
            gap_start = 300 + index * 1_000
            gap_end = gap_start + length
            rows.append({
                "row_id": index, "candidate_id": f"chr3:{gap_start}-{gap_end}", "seqid": "chr3",
                "role": "TRAIN", "chr13_block_index": "",
                "left_run_start": gap_start - 10, "left_run_end": gap_start,
                "gap_start": gap_start, "gap_end": gap_end,
                "right_run_start": gap_end, "right_run_end": gap_end + 10,
                "crop_start": gap_start - 256, "crop_end": gap_end + 256,
                "gap_length": length, "length_stratum": train.length_stratum(length),
                "comparator_known": 1, "positive_bp": length, "negative_bp": 0, "unknown_bp": 0,
                "target_negative_fraction": "0", "comparator_relation": "relation",
            })
        rows.append({**rows[0], "row_id": 6, "candidate_id": "chr13:300-301", "seqid": "chr13", "role": "DEV"})
        rows.append({**rows[0], "row_id": 7, "candidate_id": "chr3:9300-9301", "seqid": "chr3", "role": "TRAIN", "comparator_known": 0, "target_negative_fraction": ""})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate_manifest.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            loaded = train.load_training_candidates(path)
        self.assertEqual(len(loaded), 6)
        self.assertEqual({row.seqid for row in loaded}, {"chr3"})
        self.assertEqual({row.stratum for row in loaded}, set(train.LENGTH_STRATA))


if __name__ == "__main__":
    unittest.main()
