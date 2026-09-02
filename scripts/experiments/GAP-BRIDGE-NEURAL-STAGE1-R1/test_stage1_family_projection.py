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


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stage1_family_projection", HERE / "stage1_family_projection.py")
assert SPEC is not None and SPEC.loader is not None
projection = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = projection
SPEC.loader.exec_module(projection)


class Stage1FamilyProjectionTest(unittest.TestCase):
    def _write_manifest(self, path: Path) -> None:
        rows = [
            {"candidate_id": "same", "seqid": "chr13", "role": "DEV", "gap_start": 10, "gap_end": 12},
            {"candidate_id": "different", "seqid": "chr13", "role": "CAL_FIT", "gap_start": 20, "gap_end": 21},
            {"candidate_id": "unsupported", "seqid": "chr13", "role": "CAL_GATE", "gap_start": 30, "gap_end": 31},
            {"candidate_id": "multiple", "seqid": "chr13", "role": "DEV", "gap_start": 40, "gap_end": 41},
            {"candidate_id": "ignored-role", "seqid": "chr13", "role": "TRAIN", "gap_start": 50, "gap_end": 51},
            {"candidate_id": "ignored-chromosome", "seqid": "chr19", "role": "DEV", "gap_start": 60, "gap_end": 61},
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=projection.MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _write_bed(self, path: Path) -> None:
        rows = [
            ("chr13", 9, 10, "same-left", "0", ".", "LINE", "L1", "LINE/L1"),
            ("chr13", 12, 13, "same-right", "0", ".", "LINE", "L1", "LINE/L1"),
            ("chr13", 19, 20, "different-left", "0", ".", "LINE", "L1", "LINE/L1"),
            ("chr13", 21, 22, "different-right", "0", ".", "SINE", "Alu", "SINE/Alu"),
            ("chr13", 39, 40, "multiple-a", "0", ".", "LINE", "L1", "LINE/L1"),
            ("chr13", 39, 40, "multiple-b", "0", ".", "SINE", "Alu", "SINE/Alu"),
            ("chr13", 41, 42, "multiple-right", "0", ".", "LINE", "L1", "LINE/L1"),
            # The first interval ends at 50 and must not cover position 50;
            # the second starts at 50 and does cover it.
            ("chr13", 49, 50, "half-open-end", "0", ".", "LTR", "ERV", "LTR/ERV"),
            ("chr13", 50, 51, "half-open-start", "0", ".", "DNA", "hAT", "DNA/hAT"),
            ("chr19", 9, 100, "ignored", "0", ".", "LINE", "L1", "LINE/L1"),
        ]
        with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
            for row in rows:
                handle.write("\t".join(map(str, row)) + "\n")

    def test_half_open_boundary_and_unique_label_collection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "strict.bed.gz"
            self._write_bed(path)
            intervals = projection.read_intervals(path)
            self.assertEqual(projection.labels_at(intervals, [49, 50, 51]), [
                ("LTR/ERV",), ("DNA/hAT",), (),
            ])

    def test_statuses_and_manifest_without_label_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "candidate_manifest.tsv"
            bed = root / "strict.bed.gz"
            self._write_manifest(manifest)
            self._write_bed(bed)
            output = root / "projection"
            census = projection.project(manifest, bed, output)
            with (output / "chr13_family_projection.tsv").open(newline="", encoding="utf-8") as handle:
                rows = {row["candidate_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
            self.assertEqual(set(rows), {"same", "different", "unsupported", "multiple"})
            self.assertEqual(rows["same"]["status"], "SAME_UNIQUE")
            self.assertEqual(rows["same"]["family_stratum"], "LINE/L1")
            self.assertEqual(rows["same"]["left_labels"], "LINE/L1")
            self.assertEqual(rows["different"]["status"], "DIFFERENT")
            self.assertEqual(rows["unsupported"]["status"], "UNSUPPORTED")
            self.assertEqual(rows["multiple"]["status"], "MULTIPLE")
            self.assertEqual(census["processed_candidates"], 4)
            self.assertEqual(census["status_counts"], {
                "DIFFERENT": 1, "MULTIPLE": 1, "SAME_UNIQUE": 1, "UNSUPPORTED": 1,
            })
            self.assertEqual(json.loads((output / "family_projection_census.json").read_text())["status"], "PASS")
            self.assertEqual((output / "STATUS").read_text(), "PASS\n")

    def test_class_family_fallback_when_combined_column_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "strict.bed.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write("chr13\t1\t2\tname\t0\t.\tLTR\tERV\n")
            intervals = projection.read_intervals(path)
            self.assertEqual(intervals[0].label, "LTR/ERV")
            self.assertEqual(intervals[0].repeat_class, "LTR")
            self.assertEqual(intervals[0].family, "ERV")

if __name__ == "__main__":
    unittest.main()
