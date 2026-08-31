#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_calibration_packets", HERE / "build_calibration_packets.py"
)
assert SPEC is not None and SPEC.loader is not None
packets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packets)


PACKAGE_FIELDS = [
    "package_id",
    "role",
    "role_rank",
    "reserve_pair_rank",
    "unit_type",
    "hard_cell",
    "selection_priority",
    "deep_audit_feature_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
    "core_length",
    "feature_count",
    "max_overlap_depth",
    "p3_atoms_core",
    "p3_atoms_package",
    "nearest_fbti_gap",
]
CONTEXT_FIELDS = [
    "package_id",
    "feature_id",
    "seqid",
    "start1",
    "end1",
    "start0",
    "end0",
    "strand",
    "length",
    "flybase_name",
    "release",
    "species",
]


class BuildCalibrationPacketsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.packages = self.root / "packages.tsv"
        self.context = self.root / "context_features.tsv"
        self.fasta = self.root / "dmel_r6.68.fa"
        self.flybase_gff = self.root / "flybase.gff3"
        self._write_inputs()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_inputs(self) -> None:
        s0_cells = ["S0-L1", "S0-L2", "S0-L2", "S0-L3", "S0-L4", "S0-L4"]
        s1_cells = ["S1-C1", "S1-C1", "S1-C2", "S1-C2", "S1-C3", "S1-C3"]
        package_rows: list[list[str | int]] = []
        context_rows: list[list[str | int]] = []
        gff_records: list[str] = []
        for rank in range(1, 13):
            package_id = f"S{'0' if rank <= 6 else '1'}-{rank:02d}"
            start = (rank - 1) * 200
            end = start + 100
            if rank <= 6:
                feature_id = f"FBti-S0-{rank:02d}"
                focal_ids = [feature_id]
                feature_intervals = [(feature_id, start + 20, start + 40)]
                hard_cell = s0_cells[rank - 1]
            else:
                first = f"FBti-S1-{rank:02d}-A"
                second = f"FBti-S1-{rank:02d}-B"
                focal_ids = [first, second]
                feature_intervals = [
                    (first, start + 20, start + 50),
                    (second, start + 40, start + 60),
                ]
                hard_cell = s1_cells[rank - 7]
            package_rows.append(
                [
                    package_id,
                    "calibration",
                    rank,
                    "",
                    "S0" if rank <= 6 else "S1",
                    hard_cell,
                    f"0.{rank:03d}",
                    "",
                    "dmel_r6.68",
                    "2L",
                    min(start0 for _, start0, _ in feature_intervals),
                    max(end0 for _, _, end0 in feature_intervals),
                    start,
                    end,
                    ",".join(focal_ids),
                    end - start,
                    len(focal_ids),
                    1,
                    0,
                    0,
                    100,
                ]
            )
            for feature_id, start0, end0 in feature_intervals:
                context_rows.append(
                    [
                        package_id,
                        feature_id,
                        "2L",
                        start0 + 1,
                        end0,
                        start0,
                        end0,
                        "+",
                        end0 - start0,
                        feature_id,
                        "r6.68",
                        "Drosophila melanogaster",
                    ]
                )
                gff_records.append(
                    f"2L\tFlyBase\ttransposable_element\t{start0 + 1}\t{end0}\t.\t+\t.\t"
                    f"ID={feature_id};Name={feature_id};Note=raw"
                )
            context_rows.append(
                [
                    package_id,
                    f"FBti-extra-{rank:02d}",
                    "2L",
                    start + 71,
                    start + 90,
                    start + 70,
                    start + 90,
                    "-",
                    20,
                    "extra-context",
                    "r6.68",
                    "Drosophila melanogaster",
                ]
            )
            gff_records.append(
                f"2L\tFlyBase\ttransposable_element\t{start + 71}\t{start + 90}\t.\t-\t.\t"
                f"ID=FBti-extra-{rank:02d};Name=extra-context"
            )

        gff_records.extend(
            [
                "2L\tsim4\tmatch\t1221\t1250\t.\t+\t.\tID=FBti-S1-07-A",
                "2L\tsim4\tmatch_part\t1221\t1230\t.\t+\t.\tID=FBti-S1-07-A",
            ]
        )

        with self.packages.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(PACKAGE_FIELDS)
            writer.writerows(package_rows)
        with self.context.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(CONTEXT_FIELDS)
            writer.writerows(context_rows)
        self.fasta.write_text(">2L\n" + ("ACGT" * 1000) + "\n", encoding="utf-8")
        self.flybase_gff.write_text("\n".join(gff_records) + "\n", encoding="utf-8")

    def _context_records(self) -> list[dict[str, str]]:
        with self.context.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def _rewrite_context(self, rows: list[dict[str, str]]) -> None:
        with self.context.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=CONTEXT_FIELDS, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_builds_blind_packets_and_preserves_raw_context(self) -> None:
        output = self.root / "calibration-packets"
        packets.build_calibration_packets(
            self.packages, self.context, self.fasta, self.flybase_gff, output
        )

        with (output / "packet_manifest.tsv").open(newline="", encoding="utf-8") as handle:
            manifest = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(manifest), 12)
        self.assertEqual(manifest[0]["packet_id"], "CALIB-01")
        self.assertEqual(manifest[0]["package_id"], "S0-01")
        self.assertEqual(manifest[-1]["packet_id"], "CALIB-12")
        self.assertEqual(
            {path.name for path in (output / "packets").iterdir()},
            {f"CALIB-{rank:02d}" for rank in range(1, 13)},
        )

        packet_dir = output / "packets" / "CALIB-07"
        with (packet_dir / "packet.tsv").open(newline="", encoding="utf-8") as handle:
            packet_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(packet_rows[0]["packet_id"], "CALIB-07")
        self.assertEqual(
            set(packet_rows[0]),
            set(packets.PACKET_FIELDS),
        )
        self.assertNotIn("package_id", packet_rows[0])
        self.assertNotIn("role", packet_rows[0])
        self.assertNotIn("hard_cell", packet_rows[0])

        with (packet_dir / "context_features.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            context_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(context_rows), 3)
        self.assertTrue(all(row["packet_id"] == "CALIB-07" for row in context_rows))
        self.assertEqual(
            {row["feature_id"] for row in context_rows},
            {"FBti-S1-07-A", "FBti-S1-07-B", "FBti-extra-07"},
        )
        self.assertNotIn("package_id", context_rows[0])
        self.assertNotIn("header_md5", context_rows[0])
        self.assertNotIn("atom_id", context_rows[0])

        fasta_lines = (packet_dir / "sequence.fa").read_text(encoding="utf-8").splitlines()
        self.assertTrue(fasta_lines[0].startswith(">CALIB-07 dmel_r6.68:2L:1200-1300"))
        self.assertEqual(len("".join(fasta_lines[1:])), 100)

        raw_lines = (packet_dir / "raw_flybase_features.gff3").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(raw_lines), 3)
        self.assertEqual(
            {line.split("\t")[8].split(";", 1)[0] for line in raw_lines},
            {"ID=FBti-S1-07-A", "ID=FBti-S1-07-B", "ID=FBti-extra-07"},
        )
        self.assertTrue(all(line.split("\t")[1:3] == ["FlyBase", "transposable_element"] for line in raw_lines))
        self.assertFalse(any("sim4" in line for line in raw_lines))

    def test_selects_frozen_main_and_reserve_roles(self) -> None:
        manifest = (
            HERE.parent.parent.parent
            / "docs"
            / "experiments"
            / "manifests"
            / "FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3"
            / "packages.tsv"
        )
        all_packages = packets.read_packages(manifest)
        main = packets.select_role(all_packages, "main")
        reserve = packets.select_role(all_packages, "reserve")

        self.assertEqual(len(main), 120)
        self.assertEqual(main[0]["role_rank"], 1)
        self.assertEqual(main[-1]["role_rank"], 120)
        self.assertEqual(len(reserve), 40)
        self.assertEqual(reserve[0]["role_rank"], 1)
        self.assertEqual(reserve[-1]["role_rank"], 40)

    def test_rejects_missing_focal_feature(self) -> None:
        rows = self._context_records()
        rows = [row for row in rows if row["feature_id"] != "FBti-S0-01"]
        self._rewrite_context(rows)
        with self.assertRaisesRegex(ValueError, "focal feature missing from context"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "missing-focal",
            )

    def test_rejects_nonoverlapping_context_feature(self) -> None:
        rows = self._context_records()
        rows[0]["start1"] = "1001"
        rows[0]["end1"] = "1010"
        rows[0]["start0"] = "1000"
        rows[0]["end0"] = "1010"
        self._rewrite_context(rows)
        with self.assertRaisesRegex(ValueError, "does not overlap package"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "bad-context",
            )

    def test_rejects_truth_feature_shared_by_packages(self) -> None:
        rows = self._context_records()
        rows.append(
            {
                "package_id": "S0-02",
                "feature_id": "FBti-S0-01",
                "seqid": "2L",
                "start0": "220",
                "end0": "230",
                "strand": "+",
                "length": "10",
                "flybase_name": "shared",
                "start1": "221",
                "end1": "230",
                "release": "r6.68",
                "species": "Drosophila melanogaster",
            }
        )
        self._rewrite_context(rows)
        with self.assertRaisesRegex(ValueError, "enters multiple packages"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "shared-feature",
            )

    def test_rejects_noncalibration_count(self) -> None:
        package_lines = self.packages.read_text(encoding="utf-8").splitlines()
        self.packages.write_text("\n".join(package_lines[:-1]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected 12 calibration packages"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "bad-count",
            )

    def test_accepts_gzipped_flybase_gff(self) -> None:
        gzipped = self.root / "flybase.gff3.gz"
        with gzip.open(gzipped, "wt", encoding="utf-8") as handle:
            handle.write(self.flybase_gff.read_text(encoding="utf-8"))
        output = self.root / "gzipped-packets"
        packets.build_calibration_packets(
            self.packages, self.context, self.fasta, gzipped, output
        )
        self.assertTrue(
            (output / "packets" / "CALIB-01" / "raw_flybase_features.gff3").exists()
        )

    def test_stops_at_gff_fasta_section(self) -> None:
        with self.flybase_gff.open("a", encoding="utf-8") as handle:
            handle.write("##FASTA\n>2L\nACGT\n")
        output = self.root / "gff-fasta-packets"
        packets.build_calibration_packets(
            self.packages, self.context, self.fasta, self.flybase_gff, output
        )
        self.assertTrue(
            (output / "packets" / "CALIB-01" / "raw_flybase_features.gff3").exists()
        )

    def test_rejects_duplicate_matching_flybase_gff_id(self) -> None:
        text = self.flybase_gff.read_text(encoding="utf-8")
        self.flybase_gff.write_text(text + text.splitlines()[0] + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate FlyBase GFF3 feature"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "duplicate-gff",
            )

    def test_rejects_gff_context_coordinate_mismatch(self) -> None:
        lines = self.flybase_gff.read_text(encoding="utf-8").splitlines()
        fields = lines[0].split("\t")
        fields[3] = str(int(fields[3]) + 1)
        lines[0] = "\t".join(fields)
        self.flybase_gff.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "coordinates/strand disagree"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "mismatch-gff",
            )

    def test_rejects_missing_matching_flybase_gff_id(self) -> None:
        lines = self.flybase_gff.read_text(encoding="utf-8").splitlines()
        self.flybase_gff.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing FlyBase GFF3 feature"):
            packets.build_calibration_packets(
                self.packages,
                self.context,
                self.fasta,
                self.flybase_gff,
                self.root / "missing-gff",
            )


if __name__ == "__main__":
    unittest.main()
