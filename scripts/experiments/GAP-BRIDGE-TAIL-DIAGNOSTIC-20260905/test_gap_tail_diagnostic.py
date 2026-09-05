#!/usr/bin/env python3
"""Small standard-library tests for the frozen DEV tail diagnostic."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gap_tail_diagnostic", HERE / "gap_tail_diagnostic.py")
assert SPEC is not None and SPEC.loader is not None
diagnostic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diagnostic
SPEC.loader.exec_module(diagnostic)


MANIFEST_FIELDS = (
    "row_id", "candidate_id", "seqid", "role", "chr13_block_index",
    "left_run_start", "left_run_end", "gap_start", "gap_end",
    "right_run_start", "right_run_end", "crop_start", "crop_end",
    "gap_length", "length_stratum", "comparator_known", "positive_bp",
    "negative_bp", "unknown_bp", "target_negative_fraction",
    "comparator_relation",
)
SCORE_FIELDS = (
    "candidate_id", "seqid", "role", "chr13_block_index", "gap_start",
    "gap_end", "gap_length", "length_stratum", *diagnostic.HEAD_COLUMNS,
)


class GapTailDiagnosticTest(unittest.TestCase):
    def _manifest_row(
        self, row_id, candidate_id, role, start, length, positive, negative,
        unknown, relation, block=0, seqid="chr13",
    ):
        end = start + length
        known = int(unknown == 0)
        return {
            "row_id": row_id,
            "candidate_id": candidate_id,
            "seqid": seqid,
            "role": role,
            "chr13_block_index": str(block),
            "left_run_start": str(start - 10),
            "left_run_end": str(start),
            "gap_start": str(start),
            "gap_end": str(end),
            "right_run_start": str(end),
            "right_run_end": str(end + 10),
            "crop_start": str(start - 256),
            "crop_end": str(end + 256),
            "gap_length": str(length),
            "length_stratum": diagnostic.length_stratum(length),
            "comparator_known": str(known),
            "positive_bp": str(positive),
            "negative_bp": str(negative),
            "unknown_bp": str(unknown),
            "target_negative_fraction": "" if not known else str(negative / length),
            "comparator_relation": relation,
        }

    def _score_row(self, candidate, logits_by_arm):
        row = {
            "candidate_id": candidate["candidate_id"],
            "seqid": candidate["seqid"],
            "role": candidate["role"],
            "chr13_block_index": candidate["chr13_block_index"],
            "gap_start": candidate["gap_start"],
            "gap_end": candidate["gap_end"],
            "gap_length": candidate["gap_length"],
            "length_stratum": candidate["length_stratum"],
        }
        for arm in diagnostic.ARMS:
            value = logits_by_arm[arm]
            for seed in diagnostic.SEEDS:
                row[f"{arm}__seed{seed}__raw_risk_logit"] = str(value)
        return row

    def _fixture(self, root):
        rows = [
            self._manifest_row(0, "c_pos", "DEV", 300, 1, 1, 0, 0, "BRIDGE", 0),
            self._manifest_row(1, "c_mix", "DEV", 8190, 4, 2, 2, 0, "NON_BRIDGE", 0),
            self._manifest_row(2, "c_neg", "DEV", 1_000_000, 3, 0, 3, 0, "BRIDGE", 1),
            self._manifest_row(3, "c_unknown", "DEV", 2_000, 2, 1, 0, 1, "UNKNOWN", 0),
            # The diagnostic must skip CAL-GATE before interpreting its fields.
            {"candidate_id": "cal_row", "seqid": "chr13", "role": "CAL_GATE"},
        ]
        manifest = root / "candidate_manifest.tsv"
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        dev_rows = rows[:4]
        score_values = {
            "c_pos": {arm: -3.0 for arm in diagnostic.ARMS},
            "c_mix": {
                "G_GEOMETRY_LOGITS": -2.0,
                "R_RAW_LOCAL": -1.0,
                "H_P3_LATENT": -4.0,
            },
            "c_neg": {
                "G_GEOMETRY_LOGITS": -1.0,
                "R_RAW_LOCAL": -3.0,
                "H_P3_LATENT": 0.0,
            },
            "c_unknown": {arm: -4.0 for arm in diagnostic.ARMS},
        }
        scores = root / "chr13_stage1_raw_logits.tsv"
        with scores.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SCORE_FIELDS, delimiter="\t")
            writer.writeheader()
            for row in dev_rows:
                writer.writerow(self._score_row(row, score_values[row["candidate_id"]]))
            # Full Stage 1 score files contain CAL rows; they are out of scope.
            writer.writerow({field: "" for field in SCORE_FIELDS} | {
                "candidate_id": "cal_row", "seqid": "chr13", "role": "CAL_GATE",
            })

        threshold = diagnostic._sigmoid(-2.0)
        summary = {
            "schema": "gap_bridge_neural_stage1_evaluation_v1",
            "status": "PASS",
            "role_counts": {"DEV": 4},
            "calibrators": {
                arm: {"success": True, "intercept": 0.0, "slope": 1.0}
                for arm in diagnostic.ARMS
            },
            diagnostic.MECHANISM_BUDGET_KEY: {
                "G_GEOMETRY_LOGITS": {
                    "threshold": threshold, "selected_candidates": 3,
                    "selected_positive_bp": 4, "selected_known_negative_bp": 2,
                    "selected_unknown_bp": 1, "worst_case_negative_bp": 3,
                },
                "R_RAW_LOCAL": {
                    "threshold": threshold, "selected_candidates": 3,
                    "selected_positive_bp": 2, "selected_known_negative_bp": 3,
                    "selected_unknown_bp": 1, "worst_case_negative_bp": 4,
                },
                "H_P3_LATENT": {
                    "threshold": threshold, "selected_candidates": 3,
                    "selected_positive_bp": 4, "selected_known_negative_bp": 2,
                    "selected_unknown_bp": 1, "worst_case_negative_bp": 3,
                },
            },
            "role_metrics": {
                "DEV": {
                    arm: {"known_candidates": 3, "known_gap_bp": 8}
                    for arm in diagnostic.ARMS
                },
            },
        }
        summary_path = root / "evaluation_summary.json"
        summary_path.write_text(json.dumps(summary), encoding="utf-8")
        return manifest, scores, summary_path

    def test_dev_tail_is_reconstructed_without_reading_cal_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, scores, summary = self._fixture(root)
            output = root / "output"
            result = diagnostic.analyze(manifest, scores, summary, output)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["arms"]["G_GEOMETRY_LOGITS"]["tail"]["candidate_count"], 3)
            composition = result["arms"]["G_GEOMETRY_LOGITS"]["tail"]["composition"]
            self.assertEqual(composition["all_positive"]["candidate_count"], 1)
            self.assertEqual(composition["mixed"]["candidate_count"], 1)
            self.assertEqual(composition["all_negative"]["candidate_count"], 0)
            self.assertEqual(composition["unknown"]["candidate_count"], 1)
            self.assertEqual(result["pairwise_selected"]["G_GEOMETRY_LOGITS_vs_R_RAW_LOCAL"]["overlap"]["candidate_count"], 2)
            self.assertEqual(result["pairwise_selected"]["G_GEOMETRY_LOGITS_vs_R_RAW_LOCAL"]["arm_a_exclusive"]["negative_bp"], 2)
            known = result["dev_known"]
            self.assertEqual(known["mixed"]["positive_bp"], 2)
            self.assertEqual(known["mixed"]["negative_bp"], 2)
            self.assertAlmostEqual(known["within_gap_irreducible_brier"]["value"], 1.0 / 8.0)
            denominator = result["dev_denominator"]
            self.assertEqual(denominator["known"]["candidate_count"], 3)
            self.assertEqual(denominator["unknown"]["candidate_count"], 1)
            self.assertEqual(
                denominator["known"]["by_seam"]["crop_crosses_seam"]["seam"]["candidate_count"],
                1,
            )
            self.assertEqual(
                denominator["known"]["by_seam"]["gap_internal_crosses_seam"]["true"]["candidate_count"],
                1,
            )
            self.assertEqual(denominator["unknown"]["by_length_stratum"]["2"]["unknown_bp"], 1)
            stratum_brier = known["length_stratum_brier"]["3-5"]
            self.assertAlmostEqual(stratum_brier["within_gap_irreducible_brier"]["value"], 1.0 / 7.0)
            self.assertIn("candidate_fraction_mse", stratum_brier["arms"]["G_GEOMETRY_LOGITS"])

            def candidate(start, end):
                return diagnostic.Candidate("test", 0, start, end, end - start, diagnostic.length_stratum(end - start), "", 0, 0, end - start)

            internal = candidate(8189, 8195)
            endpoint = candidate(8192, 8194)
            flank_only = candidate(8000, 8002)
            self.assertTrue(internal.gap_internal_crosses_seam)
            self.assertFalse(internal.gap_endpoint_at_seam)
            self.assertTrue(endpoint.gap_endpoint_at_seam)
            self.assertFalse(endpoint.gap_internal_crosses_seam)
            self.assertTrue(flank_only.flank_only_crop_crosses_seam)
            self.assertEqual(
                result["arms"]["G_GEOMETRY_LOGITS"]["tail"]["negative_contributors"]["top_k"]["1"]["share_of_selected_negative_bp"],
                1.0,
            )
            self.assertNotIn("c_pos", json.dumps(result))
            self.assertTrue((output / "gap_tail_diagnostic.json").exists())

    def test_summary_mismatch_blocks_scientific_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, scores, summary_path = self._fixture(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary[diagnostic.MECHANISM_BUDGET_KEY]["G_GEOMETRY_LOGITS"]["selected_positive_bp"] = 99
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaises(ValueError):
                diagnostic.analyze(manifest, scores, summary_path, root / "output")
            self.assertFalse((root / "output").exists())

    def test_module_uses_no_numpy_or_torch(self):
        source = (HERE / "gap_tail_diagnostic.py").read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("import torch", source)


if __name__ == "__main__":
    unittest.main()
