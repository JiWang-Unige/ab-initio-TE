#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_gap_table", HERE / "phase0_gap_table.py")
assert SPEC is not None and SPEC.loader is not None
gap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gap)


class Phase0GapTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        sequence = list("A" * 1500)
        sequence[1212] = "N"
        self.sequence = "".join(sequence)
        self.regions = self.root / "region.jsonl.gz"
        with gzip.open(self.regions, "wt", encoding="utf-8") as handle:
            for start, end in ((0, 12), (12, 1500)):
                handle.write(json.dumps({
                    "chr": "chrA", "start": start, "end": end,
                    "sequence": self.sequence[start:end], "labels": [0] * (end - start),
                }) + "\n")

        self.p3 = self.root / "p3.canonical.tsv"
        self.runs = [
            (0, 10), (15, 20),
            (30, 40), (552, 560),
            (600, 610), (1123, 1130),
            (1200, 1210), (1215, 1220),
            (1300, 1310), (1315, 1320),
            (1350, 1360), (1365, 1370),
        ]
        self._write_canonical(self.p3, self.runs)
        probability = np.full(1500, 0.1, dtype=np.float32)
        for start, end in self.runs:
            probability[start:end] = 0.9
        self.probability = self.root / "pte.npy"
        np.save(self.probability, probability, allow_pickle=False)
        states = np.zeros((1500, 4), dtype=np.float32)
        states[:, 0] = 0.8
        states[:, 1] = 0.1
        states[:, 2] = 0.05
        states[:, 3] = 0.05
        self.states = self.root / "states.npy"
        np.save(self.states, states, allow_pickle=False)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def _write_canonical(path: Path, intervals: list[tuple[int, int]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["seqid", "start", "end", "name"], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for start, end in intervals:
                writer.writerow({"seqid": "chrA", "start": start, "end": end, "name": "."})

    @staticmethod
    def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return list(reader.fieldnames or []), list(reader)

    def test_label_blind_export_covers_seam_512_513_n_and_probability(self) -> None:
        output = self.root / "candidates.tsv"
        self.assertEqual(
            gap.main([
                "candidates", "--p3-canonical", str(self.p3),
                "--data-jsonl", str(self.regions), "--pte-npy", str(self.probability),
                "--state-probabilities-npy", str(self.states), "--output", str(output),
            ]),
            0,
        )
        fields, rows = self._rows(output)
        self.assertEqual(len(rows), len(self.runs) - 1)
        self.assertFalse(any("comparator" in field for field in fields))
        by_gap = {(int(row["gap_start"]), int(row["gap_end"])): row for row in rows}

        seam = by_gap[(10, 15)]
        self.assertEqual(seam["touches_window_seam"], "1")
        self.assertEqual(seam["nearest_window_seam_signed_distance"], "0")
        self.assertAlmostEqual(float(seam["pte_gap_mean"]), 0.1)
        self.assertAlmostEqual(float(seam["pte_left_run_mean"]), 0.9, places=6)
        self.assertAlmostEqual(float(seam["state_background_gap_mean"]), 0.8)

        self.assertEqual(by_gap[(40, 552)]["gap_length"], "512")
        self.assertEqual(by_gap[(40, 552)]["eligible_main"], "1")
        self.assertEqual(by_gap[(610, 1123)]["gap_length"], "513")
        self.assertEqual(by_gap[(610, 1123)]["eligible_main"], "0")
        self.assertEqual(by_gap[(1210, 1215)]["n_bp"], "1")
        self.assertEqual(by_gap[(1210, 1215)]["callable"], "0")
        self.assertEqual(by_gap[(1210, 1215)]["eligible_main"], "0")

    def test_projection_assigns_bridge_separation_and_ambiguous_without_dropping_rows(self) -> None:
        candidates = self.root / "candidates.tsv"
        gap.export_candidates(self.p3, self.regions, candidates, self.probability, self.states)
        comparator = self.root / "comparator.tsv"
        self._write_canonical(comparator, [
            (0, 20),                         # 10-15: one comparator run
            (30, 40), (552, 560),            # 40-552: clean separation
            (600, 620), (1123, 1130),        # 610-1123: mixed gap
            (1200, 1220),                    # N keeps 1210-1215 ambiguous
            (1300, 1315),                    # right flank at 1315 unsupported
            (1350, 1360), (1365, 1370),      # unknown gap below
        ])
        unknown = self.root / "unknown.tsv"
        self._write_canonical(unknown, [(1360, 1365)])
        labeled = self.root / "labeled.tsv"
        self.assertEqual(gap.main([
            "project-labels", "--candidates", str(candidates),
            "--comparator-positive", str(comparator),
            "--comparator-unknown", str(unknown), "--output", str(labeled),
        ]), 0)
        fields, rows = self._rows(labeled)
        self.assertIn("comparator_relation", fields)
        by_gap = {(int(row["gap_start"]), int(row["gap_end"])): row for row in rows}

        self.assertEqual(by_gap[(10, 15)]["comparator_relation"], gap.BRIDGE)
        self.assertEqual(by_gap[(10, 15)]["clean_target"], "1")
        self.assertEqual(by_gap[(10, 15)]["gap_comparator_positive_bp"], "5")

        self.assertEqual(by_gap[(40, 552)]["comparator_relation"], gap.SEPARATION)
        self.assertEqual(by_gap[(40, 552)]["clean_target"], "0")
        self.assertEqual(by_gap[(40, 552)]["gap_comparator_negative_bp"], "512")

        self.assertEqual(by_gap[(610, 1123)]["comparator_relation"], gap.AMBIGUOUS)
        self.assertGreater(int(by_gap[(610, 1123)]["gap_comparator_positive_bp"]), 0)
        self.assertGreater(int(by_gap[(610, 1123)]["gap_comparator_negative_bp"]), 0)
        self.assertEqual(by_gap[(1210, 1215)]["comparator_relation"], gap.AMBIGUOUS)
        self.assertEqual(by_gap[(1310, 1315)]["comparator_relation"], gap.AMBIGUOUS)
        self.assertEqual(by_gap[(1360, 1365)]["comparator_relation"], gap.AMBIGUOUS)
        self.assertEqual(by_gap[(1360, 1365)]["gap_comparator_unknown_bp"], "5")

        census = gap.write_census(labeled, self.root / "census.json")
        self.assertEqual(census["candidates"], len(self.runs) - 1)
        self.assertEqual(census["relations"][gap.BRIDGE], 1)
        self.assertGreaterEqual(census["relations"][gap.SEPARATION], 1)
        self.assertFalse(census["scientific_metrics_computed"])

    def test_reads_actual_gzipped_headerless_comparator_contract(self) -> None:
        comparator = self.root / "comparator.bed.gz"
        with gzip.open(comparator, "wt", encoding="utf-8") as handle:
            handle.write("chrA\t10\t20\tL1\t1\t-\tLINE\n")
            handle.write("chrA\t18\t25\tL1\t1\t-\tLINE\n")
        self.assertEqual(gap.read_intervals(comparator), {"chrA": [(10, 25)]})


if __name__ == "__main__":
    unittest.main()
