#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gap_topology_audit", HERE / "gap_topology_audit.py")
assert SPEC is not None and SPEC.loader is not None
gap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gap
SPEC.loader.exec_module(gap)


class GapTopologyAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.truth = self.root / "truth.tsv"
        self.prediction = self.root / "prediction.bed"
        self.calibration = self.root / "calibration.tsv"
        self.windows = self.root / "windows.tsv"
        self.truth.write_text(
            "seqid\tstart\tend\tname\n"
            "chrA\t0\t10\tt1\n"
            "chrA\t20\t100\tt2\n"
            "chrA\t200\t1200\tt3\n",
            encoding="utf-8",
        )
        self.prediction.write_text(
            "chrA\t2\t4\n"
            "chrA\t6\t8\n"
            "chrA\t22\t30\n"
            "chrA\t35\t40\n"
            "chrA\t205\t210\n"
            "chrA\t500\t510\n"
            "chrA\t800\t801\n"
            "chrA\t800\t805\n",
            encoding="utf-8",
        )
        self.calibration.write_text(
            "seqid\tstart\tend\tstate\n"
            "cal\t0\t2\t0\n"
            "cal\t2\t3\t1\n"
            "cal\t3\t5\t0\n"
            "cal\t5\t7\t1\n"
            "cal\t7\t9\t0\n",
            encoding="utf-8",
        )
        self.windows.write_text(
            "seqid\tstart\tend\tname\n"
            "chrA\t0\t5\tw1\n"
            "chrA\t5\t10\tw2\n"
            "chrA\t20\t35\tw3\n"
            "chrA\t0\t250\tw4\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_internal_gap_records_and_window_edges(self) -> None:
        output = self.root / "audit"
        gap.audit(self.truth, self.prediction, self.calibration, self.windows, output)
        records = self._rows(output / "gap_records.tsv")
        self.assertEqual(len(records), 10)
        internal = [row for row in records if row["event_type"] == "internal"]
        self.assertEqual(len(internal), 4)
        first = internal[0]
        self.assertEqual(first["truth_id"], "t1")
        self.assertEqual((first["gap_start"], first["gap_end"], first["gap_length"]), ("4", "6", "2"))
        self.assertEqual(first["before_positive_run_length"], "2")
        self.assertEqual(first["after_positive_run_length"], "2")
        self.assertEqual(first["relative_mid"], "0.5")
        self.assertEqual(first["touches_window_edge"], "1")
        self.assertEqual(first["window_edge_side"], "left,right")
        self.assertEqual(first["nearest_window_seam_signed_distance"], "0")
        self.assertEqual(first["nearest_window_seam_abs_distance"], "0")
        terminal = [row for row in records if row["event_type"] == "left_terminal"]
        self.assertEqual((terminal[0]["gap_start"], terminal[0]["gap_end"]), ("0", "2"))
        self.assertEqual(terminal[0]["before_positive_run_length"], "")
        truth_rows = self._rows(output / "truth_summary.tsv")
        self.assertEqual([row["internal_gap_count"] for row in truth_rows], ["1", "1", "2"])
        self.assertEqual([row["positive_runs_overlapping"] for row in truth_rows], ["2", "2", "3"])

    def test_bins_and_observed_run_totals(self) -> None:
        output = self.root / "audit"
        gap.audit(self.truth, self.prediction, self.calibration, None, output)
        summary = self._rows(output / "summary.tsv")
        self.assertEqual([row["truth_length_bin"] for row in summary], ["<80", "80-499", ">=1000"])
        self.assertEqual(summary[0]["truth_intervals"], "1")
        self.assertEqual(summary[0]["observed_fragments"], "2")
        self.assertEqual(summary[1]["observed_internal_gaps"], "1")
        self.assertEqual(summary[2]["observed_internal_gaps"], "2")
        self.assertIn("iid_expected_any_positive_rate", summary[0])
        self.assertIn("iid_expected_split_rate", summary[0])
        self.assertIn("markov_expected_any_positive_rate", summary[0])
        self.assertIn("markov_expected_split_rate", summary[0])
        run_summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(run_summary["global"]["observed_prediction_runs_total"], 7)
        self.assertEqual(run_summary["global"]["internal_gap_records"], 4)
        self.assertEqual(run_summary["global"]["terminal_gap_records"], 6)

    def test_nearest_window_seam_distance_is_signed_from_gap(self) -> None:
        windows = {
            "chrA": [gap.Interval("chrA", 0, 8192, "w8192")],
        }
        before = gap._edge_info((9000, 9010), windows, "chrA")
        self.assertEqual(before[3:], ("-808", "808"))
        after = gap._edge_info((100, 110), {"chrA": [gap.Interval("chrA", 8192, 16384, "w2")]}, "chrA")
        self.assertEqual(after[3:], ("8082", "8082"))
        absent = gap._edge_info((100, 110), {"other": windows["chrA"]}, "chrA")
        self.assertEqual(absent[3:], ("NA", "NA"))

    def test_merge_groups_each_sequence_once(self) -> None:
        merged = gap._merge([
            gap.Interval("chrB", 5, 8, "b2"),
            gap.Interval("chrA", 10, 20, "a2"),
            gap.Interval("chrB", 0, 6, "b1"),
            gap.Interval("chrA", 0, 10, "a1"),
        ])
        self.assertEqual(
            [(row.start, row.end) for row in merged["chrA"]],
            [(0, 20)],
        )
        self.assertEqual(
            [(row.start, row.end) for row in merged["chrB"]],
            [(0, 8)],
        )

    def test_null_parameters_are_from_calibration_track(self) -> None:
        calibration = gap._calibration(self.calibration)
        self.assertAlmostEqual(calibration["positive_probability"], 1 / 3)
        self.assertEqual(calibration["initial_positive_probability"], 0.0)
        self.assertAlmostEqual(calibration["p_positive_given_negative"], 0.4)
        self.assertAlmostEqual(calibration["p_negative_given_positive"], 2 / 3)
        iid = gap._iid(10, calibration["positive_probability"])
        self.assertAlmostEqual(iid["expected_positive_runs"], 1 / 3 + 9 * (2 / 3) * (1 / 3))
        markov = gap._markov(1, calibration["initial_positive_probability"], calibration["p_positive_given_negative"], calibration["p_negative_given_positive"])
        self.assertEqual(markov["expected_positive_runs"], 0.0)
        self.assertEqual(markov["expected_internal_gaps"], 0.0)
        self.assertAlmostEqual(gap._iid(3, 0.5)["expected_split"], 1 / 8)
        self.assertAlmostEqual(gap._markov(3, 0.5, 0.5, 0.5)["expected_split"], 1 / 8)
        self.assertGreater(gap._iid(10000, 0.99)["expected_split"], 0.0)

    def test_rejects_overlapping_truth_and_incomplete_calibration(self) -> None:
        overlap = self.root / "overlap.tsv"
        overlap.write_text("seqid\tstart\tend\nchrA\t0\t5\nchrA\t4\t8\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "truth intervals overlap"):
            gap._intervals(overlap, truth=True)
        union = gap._load_truth(overlap, True)
        self.assertEqual([(row.start, row.end) for row in union], [(0, 8)])
        incomplete = self.root / "incomplete.tsv"
        incomplete.write_text("seqid\tstart\tend\tstate\ncal\t1\t3\t0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not start at zero"):
            gap._calibration(incomplete)

    def test_missed_truth_has_no_terminal_events_and_exclusions_leave_denominator(self) -> None:
        truth = self.root / "missed_truth.tsv"
        truth.write_text(
            "seqid\tstart\tend\nchrA\t0\t10\nchrA\t20\t30\nchrA\t40\t50\n",
            encoding="utf-8",
        )
        prediction = self.root / "partial_prediction.tsv"
        prediction.write_text("seqid\tstart\tend\nchrA\t2\t8\n", encoding="utf-8")
        exclusion = self.root / "exclude.tsv"
        exclusion.write_text("seqid\tstart\tend\nchrA\t19\t21\n", encoding="utf-8")
        output = self.root / "missed_audit"
        gap.audit(truth, prediction, self.calibration, None, output, exclusion)
        records = self._rows(output / "gap_records.tsv")
        self.assertEqual([row["event_type"] for row in records], ["left_terminal", "right_terminal"])
        summary = self._rows(output / "summary.tsv")
        self.assertEqual(summary[0]["truth_intervals"], "2")
        self.assertEqual(summary[0]["terminal_gap_records"], "2")
        truth_rows = self._rows(output / "truth_summary.tsv")
        self.assertEqual([row["missed"] for row in truth_rows], ["0", "1"])
        run_summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(run_summary["global"]["truth_intervals_before_exclusion"], 3)
        self.assertEqual(run_summary["global"]["excluded_truth_intervals"], 1)
        self.assertEqual(run_summary["global"]["excluded_truth_bp"], 10)


if __name__ == "__main__":
    unittest.main()
