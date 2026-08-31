#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("prepare_p3_gap_inputs", HERE / "prepare_p3_gap_inputs.py")
assert SPEC is not None and SPEC.loader is not None
prepare = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prepare
SPEC.loader.exec_module(prepare)


class FakeC5:
    def __init__(self, probability: np.ndarray, truth: np.ndarray):
        self.probability = probability
        self.truth = truth

    def assemble_track(self, _data_jsonl, _model_dir, _max_windows, _weight_mode):
        return {"chr11": self.probability}, {"chr11": self.truth}

    @staticmethod
    def runs(mask: np.ndarray) -> list[tuple[int, int]]:
        output = []
        start = None
        for index, value in enumerate(mask):
            if value and start is None:
                start = index
            elif not value and start is not None:
                output.append((start, index))
                start = None
        if start is not None:
            output.append((start, len(mask)))
        return output


class PrepareP3GapInputsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_jsonl(self, path: Path, count: int = 2) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for index in range(count):
                start = index * prepare.WINDOW
                handle.write(json.dumps({
                    "chr": "chr11", "start": start, "end": start + prepare.WINDOW,
                    "sequence": "A" * prepare.WINDOW,
                }) + "\n")

    def _rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_windows_only_preserves_exact_coordinates(self) -> None:
        jsonl = self.root / "windows.jsonl.gz"
        self._write_jsonl(jsonl)
        output = self.root / "windows.tsv"
        result = prepare.windows_only(jsonl, output, None)
        self.assertEqual(result["windows"], 2)
        rows = self._rows(output)
        self.assertEqual(
            [(row["seqid"], row["start"], row["end"], row["length"]) for row in rows],
            [("chr11", "0", "8192", "8192"), ("chr11", "8192", "16384", "8192")],
        )

    def test_windows_only_accepts_frozen_tail_window(self) -> None:
        jsonl = self.root / "tail.jsonl.gz"
        with gzip.open(jsonl, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "chr": "tail", "start": 0, "end": 123,
                "sequence": "A" * 123, "labels": [0] * 123,
            }) + "\n")
        output = self.root / "tail.tsv"
        prepare.windows_only(jsonl, output, None)
        self.assertEqual(self._rows(output)[0]["length"], "123")

    def test_projected_canonical_tracks_are_independent_instances(self) -> None:
        truth = self.root / "truth.tsv"
        truth.write_text(
            "seqid\tstart\tend\tname\nchrA\t0\t5\tt1\nchrA\t10\t15\tt2\nchrA\t20\t25\tt3\n",
            encoding="utf-8",
        )
        prediction = self.root / "prediction.tsv"
        prediction.write_text(
            "seqid\tstart\tend\nchrA\t1\t3\nchrA\t12\t15\nchrA\t21\t24\n",
            encoding="utf-8",
        )
        exclude = self.root / "exclude.tsv"
        exclude.write_text("seqid\tstart\tend\nchrA\t22\t23\n", encoding="utf-8")
        output = self.root / "projected"
        result = prepare.project_canonical(truth, prediction, output, exclude)
        self.assertFalse(result["rule_selection_allowed"])
        self.assertEqual(result["truth_runs"], 2)
        self.assertEqual(result["excluded_truth_runs"], 1)
        records = self._rows(output / "in_sample.calibration.tsv")
        by_seq = {}
        for row in records:
            by_seq.setdefault(row["seqid"], []).append(row)
        self.assertEqual(set(by_seq), {"truth_run_000001", "truth_run_000002"})
        self.assertEqual(
            [(row["start"], row["end"], row["state"]) for row in by_seq["truth_run_000001"]],
            [("0", "1", "0"), ("1", "3", "1"), ("3", "5", "0")],
        )
        self.assertEqual(
            [(row["start"], row["end"], row["state"]) for row in by_seq["truth_run_000002"]],
            [("0", "2", "0"), ("2", "5", "1")],
        )
        manifest = self._rows(output / "in_sample.truth_runs.tsv")
        self.assertEqual([(row["source_start"], row["source_end"]) for row in manifest], [("0", "5"), ("10", "15")])
        self.assertEqual(json.loads((output / "in_sample.manifest.json").read_text())["diagnostic_scope"], "in-sample diagnostic only")

    def test_chr11_validation_writes_runs_without_cross_instance_transition(self) -> None:
        jsonl = self.root / "validation.jsonl.gz"
        self._write_jsonl(jsonl, 800)
        size = 800 * prepare.WINDOW
        truth = np.zeros(size, dtype=np.int8)
        probability = np.zeros(size, dtype=np.float32)
        truth[10:20] = 1
        probability[12:18] = 0.7
        truth[9000:9010] = 1
        probability[9002:9008] = 0.8
        original_loader = prepare._c5_module
        prepare._c5_module = lambda: FakeC5(probability, truth)
        try:
            output = self.root / "validation"
            result = prepare.chr11_validation(jsonl, self.root / "unused-model", output)
        finally:
            prepare._c5_module = original_loader
        self.assertEqual(result["windows"], 800)
        self.assertEqual(result["truth_runs"], 2)
        windows = self._rows(output / "validation.windows.tsv")
        self.assertEqual(len(windows), 800)
        self.assertEqual((windows[0]["start"], windows[-1]["end"]), ("0", str(size)))
        tracks = self._rows(output / "validation.calibration.tsv")
        by_seq = {}
        for row in tracks:
            by_seq.setdefault(row["seqid"], []).append(row)
        self.assertEqual(set(by_seq), {"truth_run_000001", "truth_run_000002"})
        for seqid, rows in by_seq.items():
            self.assertEqual(rows[0]["start"], "0")
            self.assertEqual(rows[-1]["end"], "10")
            for left, right in zip(rows, rows[1:]):
                self.assertEqual(left["end"], right["start"])


if __name__ == "__main__":
    unittest.main()
