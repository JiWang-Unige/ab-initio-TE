#!/usr/bin/env python3
"""CPU contract tests for label-blind Stage 1 chr13 scoring."""
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stage1_score", ROOT / "stage1_score.py")
assert SPEC is not None and SPEC.loader is not None
score = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = score
SPEC.loader.exec_module(score)


class Stage1ScoreTest(unittest.TestCase):
    def _row(self, candidate_id: str, seqid: str, role: str, block: str = "0") -> dict[str, str]:
        return {
            "candidate_id": candidate_id,
            "seqid": seqid,
            "role": role,
            "chr13_block_index": block,
            "left_run_start": "100",
            "left_run_end": "300",
            "gap_start": "300",
            "gap_end": "305",
            "right_run_start": "305",
            "right_run_end": "505",
            "crop_start": "44",
            "crop_end": "561",
            "gap_length": "5",
            "length_stratum": "3-5",
        }

    def test_label_columns_are_not_required_and_roles_are_retained(self) -> None:
        rows = [
            self._row("dev", "chr13", "DEV", "0"),
            self._row("fit", "chr13", "CAL_FIT", "1"),
            self._row("gate", "chr13", "CAL_GATE", "2"),
            self._row("train", "chr3", "TRAIN", ""),
            self._row("train13", "chr13", "TRAIN", "0"),
            self._row("quarantine", "chr13", "DEV", ""),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=score.MANIFEST_FIELDS, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            loaded, excluded = score.load_scoring_candidates(path)
        self.assertEqual([row.candidate_id for row in loaded], ["dev", "fit", "gate"])
        self.assertEqual([row.role for row in loaded], ["DEV", "CAL_FIT", "CAL_GATE"])
        self.assertEqual(excluded, {"non_chr13": 1, "non_scored_role": 1, "quarantined": 1})

    def test_generic_chr13_anchor_map_uses_crop_end_window(self) -> None:
        rows = []
        for candidate_id, gap_start in (("early", 300), ("seam", 8_190), ("late", 8_300)):
            gap_end = gap_start + 5
            row = self._row(candidate_id, "chr13", "DEV", "0")
            row.update({
                "left_run_start": str(gap_start - 200), "left_run_end": str(gap_start),
                "gap_start": str(gap_start), "gap_end": str(gap_end),
                "right_run_start": str(gap_end), "right_run_end": str(gap_end + 200),
                "crop_start": str(gap_start - 256), "crop_end": str(gap_end + 256),
            })
            rows.append(score._manifest_candidate(row))
        anchors = score.chr13_anchor_map(rows)
        self.assertEqual([row.candidate_id for row in anchors[0]], ["early"])
        self.assertEqual([row.candidate_id for row in anchors[8_192]], ["seam", "late"])

    def test_geometry_row_consumes_explicit_runs_and_crop(self) -> None:
        candidate = score._manifest_candidate(self._row("geometry", "chr13", "DEV", "7"))
        self.assertEqual(candidate.block_index, 7)
        self.assertEqual(candidate.geometry.left_run_length, 200)
        self.assertEqual(candidate.geometry.right_run_length, 200)
        self.assertEqual(candidate.crop_start, 44)
        self.assertEqual(candidate.crop_end, 561)
        self.assertEqual(candidate.gap_length, 5)

    def test_head_files_encode_arm_and_seed_without_state_dict_arm(self) -> None:
        self.assertEqual(len(score.head_specs()), 9)
        self.assertEqual(set(filename for _arm, _seed, filename, _column in score.head_specs()), set(score.HEAD_FILENAMES))
        self.assertEqual(
            [column for _arm, _seed, _filename, column in score.head_specs()],
            list(score.HEAD_COLUMNS),
        )
        self.assertEqual(score.head_specs()[0][:2], ("G_GEOMETRY_LOGITS", 17))
        self.assertEqual(score.head_specs()[-1][:2], ("H_P3_LATENT", 20260902))
        self.assertEqual(score.MANIFEST_FIELDS, (
            "candidate_id", "seqid", "role", "chr13_block_index",
            "left_run_start", "left_run_end", "gap_start", "gap_end",
            "right_run_start", "right_run_end", "crop_start", "crop_end",
            "gap_length", "length_stratum",
        ))


if __name__ == "__main__":
    unittest.main()
