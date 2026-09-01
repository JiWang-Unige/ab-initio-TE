#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase0_homology_purge", HERE / "phase0_homology_purge.py")
assert SPEC is not None and SPEC.loader is not None
purge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(purge)


class Phase0HomologyPurgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        sequence = ("ACGT" * 300)[:1000]
        self.region = self.root / "region.jsonl.gz"
        with gzip.open(self.region, "wt", encoding="utf-8") as handle:
            for start, end in ((100, 500), (500, 1100)):
                handle.write(json.dumps({
                    "chr": "chr19",
                    "start": start,
                    "end": end,
                    "sequence": sequence[start - 100:end - 100],
                    "labels": [999] * (end - start),
                }) + "\n")
        self.candidates = self.root / "candidates.tsv"
        self._write_candidates({
            "c_start": (100, 104, 1),
            "c_mid": (400, 404, 1),
            "c_end": (1096, 1100, 1),
            "c_skip": (600, 604, 0),
        })

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_candidates(self, values: dict[str, tuple[int, int, int]], extra: dict[str, str] | None = None) -> None:
        fields = [
            "candidate_id", "seqid", "gap_start", "gap_end", "eligible_main",
            "comparator_relation", "clean_target", "gap_comparator_positive_bp",
        ]
        with self.candidates.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for candidate_id, (start, end, eligible) in values.items():
                writer.writerow({
                    "candidate_id": candidate_id,
                    "seqid": "chr19",
                    "gap_start": start,
                    "gap_end": end,
                    "eligible_main": eligible,
                    "comparator_relation": (extra or {}).get(candidate_id, "bridge"),
                    "clean_target": (extra or {}).get(candidate_id, "1"),
                    "gap_comparator_positive_bp": (extra or {}).get(candidate_id, "4"),
                })

    @staticmethod
    def _fasta(path: Path) -> dict[str, str]:
        records: dict[str, str] = {}
        name = None
        sequence: list[str] = []
        for line in path.read_text(encoding="ascii").splitlines():
            if line.startswith(">"):
                if name is not None:
                    records[name] = "".join(sequence)
                name = line[1:]
                sequence = []
            else:
                sequence.append(line)
        if name is not None:
            records[name] = "".join(sequence)
        return records

    def test_extracts_at_most_256bp_and_handles_region_boundaries(self) -> None:
        output = self.root / "test.fa"
        self.assertEqual(purge.export_flanks(self.candidates, self.region, "test", output), 6)
        records = self._fasta(output)
        by_candidate_side = {
            (purge.parse_flank_name(name)["candidate_id"], purge.parse_flank_name(name)["side"]): sequence
            for name, sequence in records.items()
        }
        self.assertEqual(len(by_candidate_side[("c_start", "left")]), 0)
        self.assertEqual(len(by_candidate_side[("c_start", "right")]), 256)
        self.assertEqual(len(by_candidate_side[("c_mid", "left")]), 256)
        self.assertEqual(len(by_candidate_side[("c_mid", "right")]), 256)
        self.assertEqual(len(by_candidate_side[("c_end", "left")]), 256)
        self.assertEqual(len(by_candidate_side[("c_end", "right")]), 0)
        self.assertTrue(all("c_skip" not in name for name in records))

    def test_export_is_blind_to_extra_annotation_columns_and_region_metadata(self) -> None:
        first = self.root / "first.fa"
        second = self.root / "second.fa"
        purge.export_flanks(self.candidates, self.region, "test", first)
        self._write_candidates({
            "c_start": (100, 104, 1),
            "c_mid": (400, 404, 1),
            "c_end": (1096, 1100, 1),
            "c_skip": (600, 604, 0),
        }, {"c_start": "changed", "c_mid": "other", "c_end": "unknown"})
        purge.export_flanks(self.candidates, self.region, "test", second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def _paf_row(self, query: str, target: str, *, nmatch: int = 80, qend: int = 50, tend: int = 50) -> str:
        return "\t".join((query, "100", "0", str(qend), "+", target, "100", "0", str(tend), str(nmatch), "100", "60"))

    def test_exact_thresholds_and_any_flank_aggregate_to_candidate(self) -> None:
        test_fasta = self.root / "test.fa"
        train_fasta = self.root / "train.fa"
        purge.export_flanks(self.candidates, self.region, "test", test_fasta)
        train_candidates = self.root / "train_candidates.tsv"
        with train_candidates.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["candidate_id", "seqid", "gap_start", "gap_end", "eligible_main"], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow({"candidate_id": "tr1", "seqid": "chr3", "gap_start": 200, "gap_end": 204, "eligible_main": 1})
        train_region = self.root / "train_region.jsonl"
        train_region.write_text(json.dumps({"chr": "chr3", "start": 0, "end": 600, "sequence": "A" * 600}) + "\n", encoding="utf-8")
        purge.export_flanks(train_candidates, train_region, "train", train_fasta)
        query_left = purge.flank_name("test", "chr19", "c_start", "left")
        query_right = purge.flank_name("test", "chr19", "c_mid", "right")
        query_fail = purge.flank_name("test", "chr19", "c_end", "left")
        target = purge.flank_name("train", "chr3", "tr1", "left")
        paf = self.root / "hits.paf"
        paf.write_text("\n".join((
            self._paf_row(query_left, target),
            self._paf_row(query_right, target),
            self._paf_row(query_fail, target, nmatch=79),
        )) + "\n", encoding="utf-8")
        output_tsv = self.root / "purged.tsv"
        output_json = self.root / "purged.json"
        census = purge.summarize_paf(self.candidates, paf, output_tsv, output_json)
        self.assertEqual(census["candidates"], 3)
        self.assertEqual(census["purged_candidates"], 2)
        with output_tsv.open(newline="", encoding="utf-8") as handle:
            rows = {row["candidate_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(rows["c_start"]["purged"], "1")
        self.assertEqual(rows["c_mid"]["purged"], "1")
        self.assertEqual(rows["c_end"]["purged"], "0")
        self.assertEqual(list(rows["c_mid"]), ["candidate_id", "purged"])
        self.assertEqual(census["right_flank_hit_candidates"], 1)

    def test_empty_paf_covers_every_eligible_chr19_candidate_with_zero(self) -> None:
        paf = self.root / "empty.paf"
        paf.write_text("", encoding="utf-8")
        output_tsv = self.root / "empty.tsv"
        output_json = self.root / "empty.json"
        census = purge.summarize_paf(self.candidates, paf, output_tsv, output_json)
        self.assertTrue(census["paf_empty"])
        self.assertEqual(census["purged_candidates"], 0)
        with output_tsv.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["purged"] == "0" for row in rows))


if __name__ == "__main__":
    unittest.main()
