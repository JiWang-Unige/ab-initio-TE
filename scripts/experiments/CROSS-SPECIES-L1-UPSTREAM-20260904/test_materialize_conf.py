import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("materialize_conf", HERE / "materialize_conf.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def manifest_row(chrom, start, *, coordinate_only="true", sequence_materialized="false", labels_materialized="false"):
    end = start + MODULE.upstream.TILE_BP
    return {
        "role": "CONF",
        "species_code": "c_elegans",
        "assembly": "ce11",
        "split": "CONF",
        "chrom": chrom,
        "start": str(start),
        "end": str(end),
        "tile_id": f"c_elegans|ce11|{chrom}:{start}-{end}",
        "source": "new_conf",
        "coordinate_only": coordinate_only,
        "sequence_materialized": sequence_materialized,
        "labels_materialized": labels_materialized,
    }


def write_manifest(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MODULE.upstream.MANIFEST_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


class ConfMaterializeTest(unittest.TestCase):
    def test_materializes_frozen_coordinates_and_preserves_label_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table_dir = root / "scripts/experiments/CROSS-SPECIES-L1-20260903"
            table_dir.mkdir(parents=True)
            upstream_root = root / "materialization/12306000"
            upstream_root.mkdir(parents=True)
            fasta = root / "ce11.fa"
            sequence = "A" * (256 * MODULE.upstream.TILE_BP)
            fasta.write_text(">chrIV\n" + sequence + "\n", encoding="utf-8")
            repeatmasker = root / "ce11.out.gz"
            with gzip.open(repeatmasker, "wt", encoding="utf-8") as handle:
                handle.write("1 0 0 0 chrIV 1 4 (0) 0 0 Simple_repeat\n")
                handle.write("1 0 0 0 chrIV 3 6 (0) 0 0 Unknown\n")
                handle.write("1 0 0 0 chrIV 5 8 (0) 0 0 LINE/L1\n")
            with (table_dir / "species_x0_r2.tsv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["species_code", "assembly", "cohort_role", "fasta", "self_out"],
                    delimiter="\t",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "species_code": "c_elegans",
                        "assembly": "ce11",
                        "cohort_role": "train",
                        "fasta": str(fasta),
                        "self_out": str(repeatmasker),
                    }
                )
            write_manifest(
                upstream_root / "manifest.tsv",
                [manifest_row("chrIV", index * MODULE.upstream.TILE_BP) for index in range(256)],
            )

            output = root / "conf/12370000"
            summary = MODULE.run(root, upstream_root, output)

            self.assertEqual(summary["tile_count"], 256)
            self.assertEqual(summary["record_count"], 512)
            self.assertEqual(summary["job_id"], "12370000")
            self.assertFalse(summary["selection"]["resampled"])
            self.assertFalse(summary["selection"]["new_coordinates"])
            with gzip.open(output / "CONF/c_elegans.jsonl.gz", "rt", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            self.assertEqual(len(records), 512)
            self.assertEqual(records[0]["split"], "CONF")
            self.assertTrue(records[0]["labels"].startswith("HH??1111"))
            self.assertEqual(records[0]["tile_id"], "c_elegans|ce11|chrIV:0-8192")
            self.assertEqual(summary["counts"]["positive_bp"], 4)
            self.assertEqual(summary["counts"]["unknown_bp"], 2)
            self.assertEqual(summary["counts"]["hard_negative_bp"], 2)

    def test_frozen_manifest_requires_exactly_256_conf_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.tsv"
            write_manifest(
                manifest,
                [manifest_row("chrIV", index * MODULE.upstream.TILE_BP) for index in range(255)],
            )
            with self.assertRaisesRegex(ValueError, "must contain 256"):
                MODULE.read_frozen_conf_tiles(manifest.parent)

    def test_frozen_manifest_must_remain_coordinate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.tsv"
            rows = [manifest_row("chrIV", index * MODULE.upstream.TILE_BP) for index in range(256)]
            rows[0]["labels_materialized"] = "true"
            write_manifest(manifest, rows)
            with self.assertRaisesRegex(ValueError, "must not already contain"):
                MODULE.read_frozen_conf_tiles(manifest.parent)


if __name__ == "__main__":
    unittest.main()
