from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("downstream_c_build_masks", HERE / "build_masks.py")
assert SPEC is not None and SPEC.loader is not None
build_masks = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_masks
SPEC.loader.exec_module(build_masks)


MANIFEST_FIELDS = [
    "candidate_id", "seqid", "role", "chr13_block_index", "gap_start", "gap_end",
    "gap_length", "comparator_known", "positive_bp", "negative_bp", "unknown_bp",
]


def read_fasta(path: Path) -> dict[str, str]:
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


class BuildMasksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        # Keep the fixture small while exercising the frozen block/halo logic.
        self.block_patch = mock.patch.object(build_masks, "SUPERBLOCK_BP", 20)
        self.block_patch.start()
        self.sequence = "ACGT" * 50
        self.region = self.root / "region.jsonl.gz"
        with gzip.open(self.region, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps({"chr": "chr13", "start": 0, "end": 100, "sequence": self.sequence[:100].lower()}) + "\n")
            handle.write(json.dumps({"chr": "chr13", "start": 100, "end": 200, "sequence": self.sequence[100:]}) + "\n")
        self.stage0 = self.root / "stage0.json"
        self.stage0.write_text(json.dumps({"chr13_split": [
            {"block_index": block, "start": block * 20, "end": (block + 1) * 20,
             "role": "DEV" if block < 9 else "CAL_GATE"}
            for block in range(10)
        ]}), encoding="utf-8")

        self.p3 = self.root / "p3.canonical.tsv"
        self.p3.write_text("chr13\t0\t4\nchr13\t27\t29\nchr19\t0\t3\n", encoding="utf-8")

        self.positive = self.root / "comparator-positive.tsv"
        self.positive.write_text("seqid\tstart\tend\nchr13\t10\t14\nchr13\t20\t22\n", encoding="utf-8")

        self.manifest = self.root / "candidate_manifest.tsv"
        rows = [
            # All four bases are known positive: MW and MP both add 10-14.
            {
                "candidate_id": "dev-a", "seqid": "chr13", "role": "DEV",
                "chr13_block_index": "0", "gap_start": "10", "gap_end": "14",
                "gap_length": "4", "comparator_known": "1", "positive_bp": "4",
                "negative_bp": "0", "unknown_bp": "0",
            },
            # P covers only 20-22; the final two bases stay uppercase in MP.
            {
                "candidate_id": "dev-b", "seqid": "chr13", "role": "DEV",
                "chr13_block_index": "1", "gap_start": "20", "gap_end": "24",
                "gap_length": "4", "comparator_known": "0", "positive_bp": "2",
                "negative_bp": "1", "unknown_bp": "1",
            },
            # Non-DEV rows are out of scope and must not create a record/mask.
            {
                "candidate_id": "cal", "seqid": "chr13", "role": "CAL_FIT",
                "chr13_block_index": "2", "gap_start": "50", "gap_end": "51",
                "gap_length": "1", "comparator_known": "1", "positive_bp": "1",
                "negative_bp": "0", "unknown_bp": "0",
            },
        ]
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self) -> None:
        self.block_patch.stop()
        self.tempdir.cleanup()

    def test_three_modes_share_letters_and_keep_additions_in_core(self) -> None:
        output = self.root / "bundle"
        summary = build_masks.build(
            region=self.region,
            p3_canonical=self.p3,
            candidate_manifest=self.manifest,
            comparator_positive=self.positive,
            output_dir=output,
            halo_bp=2,
            stage0_json=self.stage0,
        )

        self.assertEqual(summary["dev_core_count"], 9)
        self.assertEqual(summary["candidate_count"], 2)
        self.assertEqual(summary["known_complete_positive_candidate_count"], 1)
        self.assertEqual(summary["masks"]["MW"]["added_mask_bp_in_halos"], 4)
        self.assertEqual(summary["masks"]["MP"]["added_mask_bp_in_halos"], 6)

        records = {mode: read_fasta(output / f"{mode}.fasta") for mode in build_masks.MODES}
        self.assertEqual(set(records["M0"]), set(records["MW"]))
        self.assertEqual(set(records["M0"]), set(records["MP"]))
        for name in records["M0"]:
            self.assertEqual(records["M0"][name].upper(), records["MW"][name].upper())
            self.assertEqual(records["M0"][name].upper(), records["MP"][name].upper())

        by_header = {name: records["M0"][name] for name in records["M0"]}
        block0 = next(name for name in by_header if "dev_block=0" in name)
        block1 = next(name for name in by_header if "dev_block=1" in name)
        # Halo 0-22: M0 is P3 0-4, and MW/MP add only the core gap 10-14.
        self.assertTrue(records["M0"][block0][0:4].islower())
        self.assertTrue(records["MW"][block0][10:14].islower())
        self.assertTrue(records["MP"][block0][10:14].islower())
        # Halo 18-42: P3 27-29 remains in all modes; MP adds only P 20-22.
        self.assertTrue(records["M0"][block1][9:11].islower())
        self.assertTrue(records["MP"][block1][2:4].islower())
        self.assertTrue(records["MP"][block1][4:6].isupper())
        self.assertTrue(records["MW"][block1][2:6].isupper())
        # Block 0's halo ends at 22 and must not inherit block 1's additions.
        self.assertTrue(records["MP"][block0][20:22].isupper())
        for name in records['M0']:
            if name not in (block0, block1):
                self.assertEqual(records['M0'][name], records['MW'][name])
                self.assertEqual(records['M0'][name], records['MP'][name])

        geometry = (output / "geometry.tsv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(geometry), 10)
        self.assertIn("block_index\tcore_start\tcore_end", geometry[0])
        self.assertTrue((output / "STATUS").read_text(encoding="utf-8") == "PASS\n")

    def test_positive_sweep_crosses_multiple_intervals(self) -> None:
        """Detect a sweep that loses partial overlaps or advances past the next gap."""
        candidates = [SimpleNamespace(candidate_id='a', gap_start=2, gap_end=12, positive_bp=5),
                      SimpleNamespace(candidate_id='b', gap_start=15, gap_end=18, positive_bp=1),
                      SimpleNamespace(candidate_id='c', gap_start=30, gap_end=32, positive_bp=0)]
        build_masks.validate_positive_projection(candidates, [(0, 3), (5, 7), (10, 16), (40, 50)])

    def test_positive_asset_mismatch_is_rejected_before_output(self) -> None:
        self.positive.write_text("chr13\t10\t13\nchr13\t20\t22\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "dev-a.*manifest=4, observed=3"):
            build_masks.build(
                region=self.region,
                p3_canonical=self.p3,
                candidate_manifest=self.manifest,
                comparator_positive=self.positive,
                output_dir=self.root / "bundle",
                halo_bp=2,
                stage0_json=self.stage0,
            )
        self.assertFalse((self.root / "bundle").exists())

    def test_more_than_nine_dev_cores_is_rejected(self) -> None:
        sequence = "ACGT" * 110
        region = self.root / "many.region.jsonl"
        region.write_text(json.dumps({"chr": "chr13", "start": 0, "end": len(sequence), "sequence": sequence}) + "\n", encoding="utf-8")
        manifest = self.root / "many.tsv"
        rows = []
        positive_lines = []
        for block in range(10):
            start = block * 20 + 1
            rows.append({
                "candidate_id": f"c{block}", "seqid": "chr13", "role": "DEV",
                "chr13_block_index": str(block), "gap_start": str(start), "gap_end": str(start + 1),
                "gap_length": "1", "comparator_known": "1", "positive_bp": "1",
                "negative_bp": "0", "unknown_bp": "0",
            })
            positive_lines.append(f"chr13\t{start}\t{start + 1}")
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        positive = self.root / "many-positive.tsv"
        positive.write_text("\n".join(positive_lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "more than the frozen 9 DEV cores"):
            build_masks.read_manifest(manifest, len(sequence))


if __name__ == "__main__":
    unittest.main()
