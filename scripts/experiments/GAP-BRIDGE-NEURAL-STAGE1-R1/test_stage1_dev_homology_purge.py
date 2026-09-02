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
SPEC = importlib.util.spec_from_file_location("stage1_dev_homology_purge", HERE / "stage1_dev_homology_purge.py")
assert SPEC is not None and SPEC.loader is not None
purge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = purge
SPEC.loader.exec_module(purge)


class Stage1DevHomologyPurgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest = self.root / "candidate_manifest.tsv"
        fields = [
            "candidate_id", "seqid", "role", "gap_start", "gap_end", "crop_start", "crop_end",
            "target_negative_fraction", "comparator_relation",
        ]
        rows = [
            {"candidate_id": "train|three", "seqid": "chr3", "role": "TRAIN", "gap_start": 300, "gap_end": 304, "crop_start": 44, "crop_end": 560},
            {"candidate_id": "train-five", "seqid": "chr5", "role": "TRAIN", "gap_start": 300, "gap_end": 304, "crop_start": 44, "crop_end": 560},
            {"candidate_id": "dev-left", "seqid": "chr13", "role": "DEV", "gap_start": 300, "gap_end": 304, "crop_start": 44, "crop_end": 560},
            {"candidate_id": "dev-right", "seqid": "chr13", "role": "DEV", "gap_start": 500, "gap_end": 502, "crop_start": 244, "crop_end": 758},
            {"candidate_id": "dev-none", "seqid": "chr13", "role": "DEV", "gap_start": 700, "gap_end": 703, "crop_start": 444, "crop_end": 959},
            {"candidate_id": "cal-fit", "seqid": "chr13", "role": "CAL_FIT", "gap_start": 850, "gap_end": 851, "crop_start": 594, "crop_end": 1107},
        ]
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        self.regions: dict[str, Path] = {}
        for seqid in ("chr3", "chr5", "chr13"):
            path = self.root / f"{seqid}.region.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                sequence = ("ACGT" * 400)[:1400]
                handle.write(json.dumps({"chr": seqid, "start": 0, "end": 700, "sequence": sequence[:700]}) + "\n")
                handle.write(json.dumps({"chr": seqid, "start": 700, "end": 1400, "sequence": sequence[700:]}) + "\n")
            self.regions[seqid] = path

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_flank_name_round_trip_and_rejects_wrong_qualifiers(self) -> None:
        name = purge.flank_name("DEV", "chr13", "dev|candidate%1", "left")
        self.assertEqual(
            purge.parse_flank_name(name),
            {"role": "DEV", "seqid": "chr13", "candidate_id": "dev|candidate%1", "side": "left"},
        )
        self.assertIsNone(purge.parse_flank_name(name.replace("role=DEV", "role=TRAIN")))
        self.assertIsNone(purge.parse_flank_name(name.replace("side=left", "side=middle")))
        self.assertIsNone(purge.parse_flank_name(name + "|side=right"))

    def test_qualifier_uses_frozen_inclusive_thresholds(self) -> None:
        row = ("q", 256, 0, 128, "t", 256, 0, 128, 80, 100)
        self.assertTrue(purge.qualifies(row))
        self.assertFalse(purge.qualifies(("q", 256, 0, 128, "t", 256, 0, 128, 79, 100)))
        self.assertFalse(purge.qualifies(("q", 256, 0, 127, "t", 256, 0, 128, 80, 100)))
        self.assertFalse(purge.qualifies(("q", 256, 0, 128, "t", 256, 0, 127, 80, 100)))
        self.assertFalse(purge.qualifies(("q", 256, 0, 128, "t", 256, 0, 128, 80, 99)))

    def test_export_and_summary_cover_every_dev_candidate_only(self) -> None:
        train_fasta = self.root / "train.fa"
        dev_fasta = self.root / "dev.fa"
        self.assertEqual(purge.export_flanks(self.manifest, self.regions["chr3"], "TRAIN", train_fasta), 2)
        self.assertEqual(purge.export_flanks(self.manifest, self.regions["chr5"], "TRAIN", self.root / "train5.fa"), 2)
        self.assertEqual(purge.export_flanks(self.manifest, self.regions["chr13"], "DEV", dev_fasta), 6)

        def fasta(path: Path) -> dict[str, str]:
            records: dict[str, str] = {}
            name: str | None = None
            sequence: list[str] = []
            for line in path.read_text(encoding="ascii").splitlines():
                if line.startswith(">"):
                    if name is not None:
                        records[name] = "".join(sequence)
                    name, sequence = line[1:], []
                else:
                    sequence.append(line)
            if name is not None:
                records[name] = "".join(sequence)
            return records

        train_records = fasta(train_fasta)
        dev_records = fasta(dev_fasta)
        self.assertTrue(all(len(sequence) == purge.FLANK_BP for sequence in train_records.values()))
        self.assertTrue(all(len(sequence) == purge.FLANK_BP for sequence in dev_records.values()))
        self.assertTrue(all(purge.parse_flank_name(name)["role"] == "DEV" for name in dev_records))
        query_left = purge.flank_name("DEV", "chr13", "dev-left", "left")
        query_right = purge.flank_name("DEV", "chr13", "dev-right", "right")
        query_none = purge.flank_name("DEV", "chr13", "dev-none", "left")
        target = purge.flank_name("TRAIN", "chr3", "train|three", "left")
        wrong_target = purge.flank_name("DEV", "chr13", "dev-left", "right")
        paf = self.root / "dev-to-train.paf"

        def paf_row(query: str, target_name: str, *, matches: int = 80, aligned: int = 100) -> str:
            return "\t".join((query, "256", "0", "128", "+", target_name, "256", "0", "128", str(matches), str(aligned), "60"))

        paf.write_text("\n".join((
            paf_row(query_left, target),
            paf_row(query_right, target),
            paf_row(query_none, target, matches=79),
            paf_row(query_left, wrong_target),
        )) + "\n", encoding="utf-8")
        membership = self.root / "membership.tsv"
        census_path = self.root / "census.json"
        census = purge.summarize_paf(self.manifest, paf, membership, census_path)
        self.assertEqual(census["dev_candidates"], 3)
        self.assertEqual(census["purged_candidates"], 2)
        with membership.open(newline="", encoding="utf-8") as handle:
            rows = {row["candidate_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(set(rows), {"dev-left", "dev-right", "dev-none"})
        self.assertEqual(rows["dev-left"]["purged"], "1")
        self.assertEqual(rows["dev-right"]["purged"], "1")
        self.assertEqual(rows["dev-none"]["purged"], "0")
        self.assertEqual(rows["dev-left"]["left_flank_hit"], "1")
        self.assertEqual(rows["dev-right"]["right_flank_hit"], "1")
        self.assertEqual(census["target_seqids"], ["chr3", "chr5"])


if __name__ == "__main__":
    unittest.main()
