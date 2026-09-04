import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("materialize_upstream.py")
SPEC = importlib.util.spec_from_file_location("materialize_upstream", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def tile(chrom, start, split="TRAIN", source="old"):
    return (chrom, start, start + MODULE.TILE_BP, split, source)


class UpstreamMaterializeTest(unittest.TestCase):
    def test_buffer_boundary_and_touching_old_train(self):
        old = [tile("chrI", 0)]
        candidates = {"chrI": [0, MODULE.TILE_BP, 2 * MODULE.TILE_BP, 3 * MODULE.TILE_BP]}

        screened = MODULE.filter_pool(candidates, old, MODULE.BUFFER_BP)
        self.assertEqual(screened["chrI"], [2 * MODULE.TILE_BP, 3 * MODULE.TILE_BP])

        new_train = MODULE.filter_pool(candidates, old, 0, overlap_only=True)
        # The first adjacent tile touches the old half-open interval and is
        # deliberately allowed: no unnecessary old-TRAIN buffer is applied.
        self.assertEqual(new_train["chrI"], [MODULE.TILE_BP, 2 * MODULE.TILE_BP, 3 * MODULE.TILE_BP])

    def test_largest_remainder_is_seeded_and_proportional(self):
        available = {"chrI": 2, "chrII": 3, "chrIII": 5}
        first = MODULE.quotas(available, 7)
        second = MODULE.quotas(available, 7)
        self.assertEqual(first, second)
        self.assertEqual(sum(first.values()), 7)
        self.assertEqual(first, {"chrI": 1, "chrII": 2, "chrIII": 4})

    def test_cli_retains_old_train_and_does_not_materialize_infeasible_conf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = root / "outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
            for split in ("TRAIN", "CAL", "DEV"):
                (old_root / split).mkdir(parents=True)

            train_chroms = ["chrI", "chrII", "chrIII", "chrIV"]
            fasta = root / "ce11.fa"
            with fasta.open("w", encoding="utf-8") as handle:
                for chrom in train_chroms:
                    handle.write(f">{chrom}\n")
                    handle.write("A" * (8 * MODULE.TILE_BP) + "\n")
                handle.write(">chrV\n")
                handle.write("A" * (4 * MODULE.TILE_BP) + "\n")

            def write_old(split, tiles):
                path = old_root / split / "c_elegans.jsonl.gz"
                with gzip.open(path, "wt", encoding="utf-8") as handle:
                    for chrom, start in tiles:
                        for half in (0, 1):
                            half_start = start + half * MODULE.HALF_BP
                            record = {
                                "species_code": "c_elegans",
                                "assembly": "ce11",
                                "split": split,
                                "tile_id": f"c_elegans|ce11|{chrom}:{start}-{start + MODULE.TILE_BP}",
                                "half": half,
                                "chrom": chrom,
                                "start": half_start,
                                "end": half_start + MODULE.HALF_BP,
                                "sequence": "A" * MODULE.HALF_BP,
                                "labels": "0" * MODULE.HALF_BP,
                            }
                            handle.write(json.dumps(record, separators=(",", ":")) + "\n")

            write_old("TRAIN", [(chrom, 0) for chrom in train_chroms])
            write_old("CAL", [("chrV", 0)])
            write_old("DEV", [("chrV", MODULE.TILE_BP)])

            rm = root / "ce11.repeatmasker.out.gz"
            with gzip.open(rm, "wt", encoding="utf-8") as handle:
                handle.write("")
            table = root / "species.tsv"
            with table.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["species_code", "assembly", "fasta", "self_out"], delimiter="\t")
                writer.writeheader()
                writer.writerow({"species_code": "c_elegans", "assembly": "ce11", "fasta": str(fasta), "self_out": str(rm)})

            output = root / "upstream"
            with mock.patch.object(MODULE, "OLD_TRAIN", 4), mock.patch.object(MODULE, "NEW_TRAIN", 4), mock.patch.object(MODULE, "SCREEN", 2), mock.patch.object(MODULE, "CONF", 2):
                summary = MODULE.run(root, output, table)

            self.assertEqual(summary["status"], "CONF_NOT_FEASIBLE")
            self.assertEqual(summary["conf_status"], "CONF_NOT_FEASIBLE")
            self.assertTrue((output / "TRAIN/c_elegans.jsonl.gz").is_file())
            self.assertTrue((output / "SCREEN/c_elegans.jsonl.gz").is_file())
            self.assertFalse((output / "CONF").exists())
            with (output / "manifest.tsv").open(newline="", encoding="utf-8") as handle:
                manifest = list(csv.DictReader(handle, delimiter="\t"))
            self.assertNotIn("CONF", {row["role"] for row in manifest})
            self.assertEqual(len([row for row in manifest if row["role"] == "TRAIN1500"]), 4)
            self.assertEqual(len([row for row in manifest if row["role"] == "TRAIN3000"]), 8)

            with gzip.open(output / "TRAIN/c_elegans.jsonl.gz", "rt", encoding="utf-8") as handle:
                output_lines = [line.rstrip("\n") for line in handle]
            with gzip.open(old_root / "TRAIN/c_elegans.jsonl.gz", "rt", encoding="utf-8") as handle:
                old_lines = [line.rstrip("\n") for line in handle]
            self.assertEqual(output_lines[: len(old_lines)], old_lines)
            self.assertEqual(len(output_lines), 2 * (4 + 4))


if __name__ == "__main__":
    unittest.main()
