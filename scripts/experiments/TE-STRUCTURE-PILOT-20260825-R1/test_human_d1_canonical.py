#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("human_d1", HERE / "human_d1_canonical.py")
assert SPEC and SPEC.loader
human_d1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(human_d1)


def record(index: int, labels: list[int], chrom: str = "chr17", start: int | None = None):
    begin = index * human_d1.WINDOW if start is None else start
    return {
        "sequence": "A" * human_d1.WINDOW,
        "labels": labels,
        "chr": chrom,
        "start": begin,
        "end": begin + human_d1.WINDOW,
    }


class HumanD1CanonicalTest(unittest.TestCase):
    def _jsonl(self, root: Path, rows: list[dict]) -> Path:
        path = root / "test.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return path

    def test_prefix_coordinates_and_count_are_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            labels = [0] * human_d1.WINDOW
            path = self._jsonl(root, [record(0, labels)])
            with self.assertRaisesRegex(ValueError, "exactly 1200"):
                list(human_d1.iter_windows(path))
            bad = record(1, labels, start=human_d1.WINDOW + 1)
            with self.assertRaisesRegex(ValueError, "contiguous"):
                human_d1.validate_record(1, bad)

    def test_non_chr17_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            labels = [0] * human_d1.WINDOW
            bad = record(0, labels, chrom="chr19")
            with self.assertRaisesRegex(ValueError, "not chr17"):
                human_d1.validate_record(0, bad)

    def test_materialized_unknown_label_uses_minus_100(self):
        labels = [human_d1.UNKNOWN_LABEL] * human_d1.WINDOW
        human_d1.validate_record(0, record(0, labels))
        with self.assertRaisesRegex(ValueError, "labels"):
            human_d1.validate_record(0, record(0, [-1] * human_d1.WINDOW))

    def test_runs_are_zero_based_half_open_and_unknown_is_separate(self):
        values = [0, 1, 1, 0, human_d1.UNKNOWN_LABEL, human_d1.UNKNOWN_LABEL, 1]
        self.assertEqual(human_d1.runs(values, 1), [(1, 3), (6, 7)])
        self.assertEqual(human_d1.runs(values, human_d1.UNKNOWN_LABEL), [(4, 6)])
        rows = human_d1.canonical_rows(human_d1.runs(values, 1), "base_ce")
        self.assertEqual(rows[0]["seqid"], "chr17")
        self.assertEqual((rows[0]["start"], rows[0]["end"]), (1, 3))
        self.assertEqual(rows[0]["source"], "TE-STRUCTURE-D1")

    def test_canonical_header_is_exact(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.tsv"
            human_d1.write_canonical(path, human_d1.canonical_rows([(2, 5)], "truth"))
            self.assertEqual(path.read_text().splitlines()[0], "\t".join(human_d1.FIELDS))
            self.assertEqual(path.read_text().splitlines()[1].split("\t")[:3], ["chr17", "2", "5"])


if __name__ == "__main__":
    unittest.main()
