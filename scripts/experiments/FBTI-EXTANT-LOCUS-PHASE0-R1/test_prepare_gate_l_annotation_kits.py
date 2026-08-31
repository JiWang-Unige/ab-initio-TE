#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "prepare_gate_l_annotation_kits", HERE / "prepare_gate_l_annotation_kits.py"
)
assert SPEC is not None and SPEC.loader is not None
kits = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kits)


MANIFEST_FIELDS = [
    "packet_id",
    "package_id",
    "role",
    "role_rank",
    "unit_type",
    "hard_cell",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
    "feature_ids",
]
PACKET_FIELDS = [
    "packet_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
]


class PrepareGateLAnnotationKitsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bundle = self.root / "calibration-packets"
        self._write_bundle()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_bundle(self) -> None:
        (self.bundle / "packets").mkdir(parents=True)
        with (self.bundle / "packet_manifest.tsv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(MANIFEST_FIELDS)
            for index in range(1, 13):
                packet_id = f"CALIB-{index:02d}"
                packet_dir = self.bundle / "packets" / packet_id
                packet_dir.mkdir()
                writer.writerow(
                    [
                        packet_id,
                        f"S0-{index:05d}",
                        "calibration",
                        index,
                        "S0" if index <= 6 else "S1",
                        "S0-L1" if index <= 6 else "S1-C1",
                        "dmel_r6.68",
                        "2L",
                        100 * index,
                        100 * index + 40,
                        100 * index - 50,
                        100 * index + 90,
                        f"FBti{index:07d}",
                    ]
                )
                with (packet_dir / "packet.tsv").open(
                    "w", newline="", encoding="utf-8"
                ) as packet_handle:
                    packet_writer = csv.DictWriter(
                        packet_handle,
                        fieldnames=PACKET_FIELDS,
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    packet_writer.writeheader()
                    packet_writer.writerow(
                        {
                            "packet_id": packet_id,
                            "assembly_id": "dmel_r6.68",
                            "seqid": "2L",
                            "core_start0": str(100 * index),
                            "core_end0": str(100 * index + 40),
                            "package_start0": str(100 * index - 50),
                            "package_end0": str(100 * index + 90),
                        }
                    )
                (packet_dir / "sequence.fa").write_text(
                    f">{packet_id}\nACGT\n", encoding="utf-8"
                )
                (packet_dir / "context_features.tsv").write_text(
                    "packet_id\tfeature_id\tseqid\n"
                    f"{packet_id}\tFBti{index:07d}\t2L\n",
                    encoding="utf-8",
                )
                (packet_dir / "raw_flybase_features.gff3").write_text(
                    f"2L\tFlyBase\ttransposable_element\t{100 * index + 1}\t"
                    f"{100 * index + 40}\t.\t+\t.\tID=FBti{index:07d}\n",
                    encoding="utf-8",
                )

    @staticmethod
    def _rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_creates_two_same_denominator_blind_kits_and_adjudicator_input(self) -> None:
        output = self.root / "annotation-kits"
        kits.prepare_gate_l_annotation_kits(self.bundle, output)

        a1 = self._rows(output / "annotator_A1" / "assignment.tsv")
        a2 = self._rows(output / "annotator_A2" / "assignment.tsv")
        expected_ids = {f"CALIB-{index:02d}" for index in range(1, 13)}
        self.assertEqual(set(a1[0]), set(kits.ASSIGNMENT_FIELDS))
        self.assertEqual({row["packet_id"] for row in a1}, expected_ids)
        self.assertEqual({row["packet_id"] for row in a2}, expected_ids)
        self.assertEqual({row["actor_id"] for row in a1}, {"A1"})
        self.assertEqual({row["actor_id"] for row in a2}, {"A2"})
        self.assertNotEqual(
            [row["packet_id"] for row in a1], [row["packet_id"] for row in a2]
        )

        for actor in ("A1", "A2"):
            response_dir = output / f"annotator_{actor}" / "responses"
            review_rows = self._rows(response_dir / "package_reviews.tsv")
            self.assertEqual(len(review_rows), 12)
            self.assertEqual({row["package_id"] for row in review_rows}, expected_ids)
            self.assertEqual({row["actor_id"] for row in review_rows}, {actor})
            for filename, fields in kits.PASS1_RESPONSE_FIELDS.items():
                self.assertEqual(
                    self._rows(response_dir / filename), [], filename
                )
                with (response_dir / filename).open(
                    newline="", encoding="utf-8"
                ) as handle:
                    self.assertEqual(handle.readline().rstrip("\n").split("\t"), fields)

        adjudication = self._rows(output / "adjudicator" / "adjudication_input.tsv")
        self.assertEqual(len(adjudication), 12)
        self.assertEqual(
            {row["packet_id"] for row in adjudication}, expected_ids
        )
        self.assertEqual(
            {row["a1_response_dir"] for row in adjudication},
            {"annotator_A1/responses"},
        )
        self.assertEqual(
            {row["a2_response_dir"] for row in adjudication},
            {"annotator_A2/responses"},
        )
        adj_reviews = self._rows(
            output / "adjudicator" / "responses" / "package_reviews.tsv"
        )
        self.assertEqual({row["actor_id"] for row in adj_reviews}, {"ADJ"})

        generated_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in output.rglob("*.tsv")
        )
        self.assertNotIn("S0-", generated_text)
        self.assertNotIn("S1-", generated_text)

    def test_rejects_incomplete_frozen_bundle_before_output(self) -> None:
        (self.bundle / "packets" / "CALIB-12" / "sequence.fa").unlink()
        output = self.root / "invalid-output"
        with self.assertRaisesRegex(ValueError, "missing packet file"):
            kits.prepare_gate_l_annotation_kits(self.bundle, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
