import csv
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("materialize_x0_windows.py")
SPEC = importlib.util.spec_from_file_location("materialize_x0_windows", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


TABLE_FIELDS = ["species_code", "assembly", "cohort_role", "fasta", "self_out"]
TILE_FIELDS = [
    "species_code",
    "assembly",
    "cohort_role",
    "split",
    "chrom",
    "start",
    "end",
    "positive_bp",
    "negative_bp",
    "unknown_bp",
    "hard_negative_bp",
    "callable_bp",
]


def rm_row(chrom, start, end, class_family):
    return f"100 1 0 0 {chrom} {start} {end} (0) + repeat {class_family} 1 1 (0) 1\n"


class MaterializeX0Test(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        fasta = root / "tiny.fa"
        first = "A" * MODULE.TILE_BP
        second = list("C" * MODULE.TILE_BP)
        second[10] = "N"
        second = "".join(second)
        third = "G" * MODULE.TILE_BP
        fasta.write_text(f">chrA\n{first}{second}{third}\n", encoding="utf-8")

        repeatmasker = root / "tiny.out"
        repeatmasker.write_text(
            rm_row("chrA", 1, 4, "LINE/L1")
            + rm_row("chrA", MODULE.TILE_BP + 11, MODULE.TILE_BP + 20, "Unknown/Unknown")
            + rm_row("chrA", 2 * MODULE.TILE_BP + 31, 2 * MODULE.TILE_BP + 40, "Simple_repeat"),
            encoding="utf-8",
        )

        table = root / "species.tsv"
        with table.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TABLE_FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerow(
                {
                    "species_code": "tiny_train",
                    "assembly": "tiny1",
                    "cohort_role": "train",
                    "fasta": str(fasta),
                    "self_out": str(repeatmasker),
                }
            )
            writer.writerow(
                {
                    "species_code": "sealed_primary",
                    "assembly": "sealed1",
                    "cohort_role": "primary",
                    "fasta": str(root / "not-materialized.fa"),
                    "self_out": str(root / "not-materialized.out"),
                }
            )

        tiles = root / "tiles.tsv"
        tile_counts = [
            ("TRAIN", 4, MODULE.TILE_BP - 4, 0, 0),
            ("CAL", 0, MODULE.TILE_BP - 10, 10, 0),
            ("DEV", 0, MODULE.TILE_BP, 0, 10),
        ]
        with tiles.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TILE_FIELDS, delimiter="\t")
            writer.writeheader()
            for index, (split, positive, negative, unknown, hard_negative) in enumerate(tile_counts):
                writer.writerow(
                    {
                        "species_code": "tiny_train",
                        "assembly": "tiny1",
                        "cohort_role": "train",
                        "split": split,
                        "chrom": "chrA",
                        "start": index * MODULE.TILE_BP,
                        "end": (index + 1) * MODULE.TILE_BP,
                        "positive_bp": positive,
                        "negative_bp": negative,
                        "unknown_bp": unknown,
                        "hard_negative_bp": hard_negative,
                        "callable_bp": positive + negative,
                    }
                )
        return table, tiles, fasta

    def test_role_filter_does_not_open_sealed_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            table, _, _ = self._fixture(Path(tmp))
            rows = MODULE.read_species_rows(table, "train")
            self.assertEqual([row["species_code"] for row in rows], ["tiny_train"])

    def test_materializes_two_halves_and_label_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table, tiles, _ = self._fixture(root)
            output = root / "materialized"
            small_counts = {"train": {"TRAIN": 1, "CAL": 1, "DEV": 1}}
            with mock.patch.object(MODULE, "ROLE_COUNTS", small_counts), mock.patch.object(
                sys, "argv",
                [
                    str(SCRIPT),
                    "--species-table",
                    str(table),
                    "--tiles-tsv",
                    str(tiles),
                    "--output-dir",
                    str(output),
                    "--cohort-role",
                    "train",
                ],
            ):
                MODULE.main()

            train_path = output / "TRAIN" / "tiny_train.jsonl.gz"
            cal_path = output / "CAL" / "tiny_train.jsonl.gz"
            dev_path = output / "DEV" / "tiny_train.jsonl.gz"
            for path in (train_path, cal_path, dev_path):
                self.assertTrue(path.is_file())
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    rows = [json.loads(line) for line in handle]
                self.assertEqual(len(rows), 2)
                self.assertEqual({row["half"] for row in rows}, {0, 1})
                for row in rows:
                    self.assertEqual(len(row["sequence"]), MODULE.HALF_BP)
                    self.assertEqual(len(row["labels"]), MODULE.HALF_BP)
                    self.assertEqual(row["end"] - row["start"], MODULE.HALF_BP)
                    self.assertEqual(
                        set(row),
                        {
                            "species_code",
                            "assembly",
                            "split",
                            "tile_id",
                            "half",
                            "chrom",
                            "start",
                            "end",
                            "sequence",
                            "labels",
                        },
                    )

            with gzip.open(train_path, "rt", encoding="utf-8") as handle:
                train_rows = [json.loads(line) for line in handle]
            self.assertTrue(train_rows[0]["labels"].startswith("1111"))
            self.assertEqual(train_rows[1]["labels"].count("1"), 0)

            with gzip.open(cal_path, "rt", encoding="utf-8") as handle:
                cal_rows = [json.loads(line) for line in handle]
            self.assertEqual(sum(row["labels"].count("?") for row in cal_rows), 10)

            with gzip.open(dev_path, "rt", encoding="utf-8") as handle:
                dev_rows = [json.loads(line) for line in handle]
            self.assertEqual(sum(row["labels"].count("H") for row in dev_rows), 10)

            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["tile_bp"], MODULE.TILE_BP)
            self.assertEqual(summary["half_bp"], MODULE.HALF_BP)
            self.assertEqual({row["split"] for row in summary["records"]}, {"TRAIN", "CAL", "DEV"})

            with (output / "summary.tsv").open(newline="", encoding="utf-8") as handle:
                summary_rows = list(csv.DictReader(handle, delimiter="\t"))
            by_split = {row["split"]: row for row in summary_rows}
            self.assertEqual(by_split["TRAIN"]["positive_bp"], "4")
            self.assertEqual(by_split["CAL"]["unknown_bp"], "10")
            self.assertEqual(by_split["DEV"]["hard_negative_bp"], "10")


if __name__ == "__main__":
    unittest.main()
