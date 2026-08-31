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
AUDIT_SPEC = importlib.util.spec_from_file_location("gap_topology_audit", HERE / "gap_topology_audit.py")
assert AUDIT_SPEC is not None and AUDIT_SPEC.loader is not None
audit = importlib.util.module_from_spec(AUDIT_SPEC)
sys.modules[AUDIT_SPEC.name] = audit
AUDIT_SPEC.loader.exec_module(audit)

SUMMARY_SPEC = importlib.util.spec_from_file_location("summarize_gap_audits", HERE / "summarize_gap_audits.py")
assert SUMMARY_SPEC is not None and SUMMARY_SPEC.loader is not None
summary = importlib.util.module_from_spec(SUMMARY_SPEC)
sys.modules[SUMMARY_SPEC.name] = summary
SUMMARY_SPEC.loader.exec_module(summary)


class GapSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.truth = self.root / "truth.tsv"
        self.prediction = self.root / "prediction.bed"
        self.calibration = self.root / "calibration.tsv"
        self.truth.write_text(
            "seqid\tstart\tend\tname\n"
            "chrA\t0\t10\tt1\n"
            "chrA\t20\t100\tt2\n",
            encoding="utf-8",
        )
        self.prediction.write_text(
            "chrA\t2\t4\n"
            "chrA\t6\t8\n"
            "chrA\t22\t30\n"
            "chrA\t35\t40\n"
            "chrA\t80\t90\n",
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

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _audit(self) -> Path:
        output = self.root / "audit"
        audit.audit(self.truth, self.prediction, self.calibration, None, output)
        return output

    def test_overall_and_length_strata_metrics(self) -> None:
        rows = summary.summarize("human_p3", self._audit(), "material-comparator")
        overall = rows[0]
        short = rows[1]
        medium = rows[2]
        self.assertEqual([row["stratum"] for row in rows], ["overall", "<80", "80-499"])
        self.assertEqual(overall["truth_intervals"], 2)
        self.assertEqual(overall["truth_bp"], 90)
        self.assertEqual(overall["observed_internal_gaps"], 3)
        self.assertEqual(overall["terminal_gap_records"], 4)
        self.assertEqual(
            overall["left_terminal_gap_bp"] + overall["right_terminal_gap_bp"],
            overall["terminal_gap_bp"],
        )
        self.assertEqual(overall["observed_fragments"], 5)
        self.assertAlmostEqual(overall["fragments_per_truth"], 2.5)
        self.assertEqual(overall["internal_gap_length_count"], 3)
        self.assertAlmostEqual(overall["internal_gap_length_p50"], 5)
        self.assertAlmostEqual(overall["internal_gap_length_p90"], 33)
        self.assertEqual(overall["internal_gap_length_max"], 40)
        self.assertEqual(overall["between_gap_spacing_count"], 1)
        self.assertEqual(overall["between_gap_spacing_p50"], 5)
        self.assertEqual(overall["seam_observed_count"], 0)
        self.assertIsNone(overall["seam_le_0_fraction"])
        self.assertEqual(overall["relative_0_10_0_25_count"], 1)
        self.assertEqual(overall["relative_0_50_0_75_count"], 2)
        self.assertEqual(short["truth_intervals"], 1)
        self.assertEqual(short["internal_gap_bp"], 2)
        self.assertEqual(medium["observed_internal_gaps"], 2)

    def test_positive_only_is_explicit_and_tsv_uses_na_for_missing_seams(self) -> None:
        output = self._audit()
        rows = summary.summarize("fly_p3", output, "positive-only")
        self.assertEqual(rows[0]["truth_interpretation"], "positive-only")
        self.assertEqual(rows[0]["precision_f1_reportable"], "0")
        tsv = self.root / "summary.tsv"
        summary._write_tsv(tsv, rows)
        with tsv.open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(row["seam_le_0_fraction"], "NA")
        self.assertEqual(row["truth_interpretation"], "positive-only")

    def test_manifest_and_json_output(self) -> None:
        audit_dir = self._audit()
        manifest = self.root / "manifest.tsv"
        manifest.write_text(
            "label\tpath\tinterpretation\n"
            f"mouse_p3\t{audit_dir}\tuntuned-material-comparator\n",
            encoding="utf-8",
        )
        self.assertEqual(summary._manifest(manifest), [("mouse_p3", audit_dir, "untuned-material-comparator")])
        tsv = self.root / "result.tsv"
        js = self.root / "result.json"
        old_argv = sys.argv
        try:
            sys.argv = [
                "summarize_gap_audits.py", "--manifest", str(manifest),
                "--output-tsv", str(tsv), "--output-json", str(js),
            ]
            self.assertEqual(summary.main(), 0)
        finally:
            sys.argv = old_argv
        payload = json.loads(js.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "fragment_gap_topology_summary_v1")
        self.assertEqual(len(payload["rows"]), 3)
        self.assertEqual(payload["rows"][0]["label"], "mouse_p3")


if __name__ == "__main__":
    unittest.main()
