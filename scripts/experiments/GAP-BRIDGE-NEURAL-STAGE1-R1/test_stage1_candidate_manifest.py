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


SPEC = importlib.util.spec_from_file_location(
    "stage1_candidate_manifest", Path(__file__).with_name("stage1_candidate_manifest.py"),
)
assert SPEC is not None and SPEC.loader is not None
manifest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = manifest
SPEC.loader.exec_module(manifest)


class Stage1CandidateManifestTest(unittest.TestCase):
    def test_tiny_manifest_uses_only_explicit_chromosomes(self) -> None:
        stage0 = manifest.load_stage0()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            for seqid in (*manifest.CHROMOSOMES, "chr19"):
                chromosome = source / seqid
                chromosome.mkdir(parents=True)
                with gzip.open(chromosome / "region.jsonl.gz", "wt", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "chr": seqid, "start": 0, "end": 1024,
                        "sequence": "A" * 1024, "labels": [0] * 1024,
                    }) + "\n")
                candidate = {
                    "candidate_id": f"{seqid}:300-301", "seqid": seqid,
                    "left_run_start": 100, "left_run_end": 300,
                    "gap_start": 300, "gap_end": 301,
                    "right_run_start": 301, "right_run_end": 500,
                }
                with (chromosome / "candidates.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(candidate), delimiter="\t")
                    writer.writeheader()
                    writer.writerow(candidate)
                labeled = {
                    **candidate, "comparator_relation": stage0.BRIDGE,
                    "gap_comparator_positive_bp": 1,
                    "gap_comparator_negative_bp": 0,
                    "gap_comparator_unknown_bp": 0,
                }
                with (chromosome / "labeled.tsv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(labeled), delimiter="\t")
                    writer.writeheader()
                    writer.writerow(labeled)
            _, split = stage0.chr13_split(1024)
            stage0_json = root / "stage0.json"
            stage0_json.write_text(json.dumps({
                "status": "PASS_TO_STAGE1",
                "chr13_split": split,
                "candidate_label_census": {
                    "train": {
                        "comparator_known_candidates": 2,
                        "comparator_unknown_candidates": 0,
                    },
                    "chr13_dev": {
                        "comparator_known_candidates": 1,
                        "comparator_unknown_candidates": 0,
                    },
                },
            }), encoding="utf-8")
            output = root / "output"
            result = manifest.run(source, stage0_json, output)
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["role_counts"]["TRAIN"]["known"], 2)
            self.assertEqual(result["role_counts"]["DEV"]["known"], 1)
            self.assertFalse(result["chr19_read"])
            with (output / "candidate_manifest.tsv").open(newline="", encoding="utf-8") as handle:
                self.assertEqual({row["seqid"] for row in csv.DictReader(handle, delimiter="\t")}, set(manifest.CHROMOSOMES))


if __name__ == "__main__":
    unittest.main()
