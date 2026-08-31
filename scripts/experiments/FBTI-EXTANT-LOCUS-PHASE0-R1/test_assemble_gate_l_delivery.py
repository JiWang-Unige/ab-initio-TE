#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "assemble_gate_l_delivery", HERE / "assemble_gate_l_delivery.py"
)
assert SPEC is not None and SPEC.loader is not None
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


PACKET_FIELDS = [
    "packet_id",
    "assembly_id",
    "seqid",
    "core_start0",
    "core_end0",
    "package_start0",
    "package_end0",
]
RESPONSE_FIELDS = {
    "package_reviews.tsv": ["package_id", "actor_id", "package_status"],
    "loci.tsv": ["package_id", "actor_id", "locus_id"],
    "material_segments.tsv": ["package_id", "actor_id", "segment_id"],
    "boundaries.tsv": ["package_id", "actor_id", "locus_id"],
    "interruptions.tsv": ["package_id", "actor_id", "interruption_id"],
    "relations.tsv": ["package_id", "actor_id", "relation_id"],
}


class AssembleGateLDeliveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bundle = self.root / "bundle"
        self.kit = self.root / "kit"
        self.handbook = self.root / "handbook.md"
        self.registry = self.root / "evidence_registry.tsv"
        self._write_bundle()
        self._write_kit()
        self.handbook.write_text("handbook\n", encoding="utf-8")
        self.registry.write_text("evidence_code\nCODE\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_bundle(self) -> None:
        packet_ids = ["MAIN-01", "MAIN-02", "MAIN-03"]
        packet_root = self.bundle / "packets"
        packet_root.mkdir(parents=True)
        with (self.bundle / "packet_manifest.tsv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["packet_id", "package_id", "role"])
            for index, packet_id in enumerate(packet_ids, start=1):
                writer.writerow([packet_id, f"S0-{index:05d}", "main"])
                packet_dir = packet_root / packet_id
                packet_dir.mkdir()
                with (packet_dir / "packet.tsv").open(
                    "w", newline="", encoding="utf-8"
                ) as packet_handle:
                    writer2 = csv.DictWriter(
                        packet_handle,
                        fieldnames=PACKET_FIELDS,
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    writer2.writeheader()
                    writer2.writerow(
                        {
                            "packet_id": packet_id,
                            "assembly_id": "asm",
                            "seqid": "chr1",
                            "core_start0": str(index * 10),
                            "core_end0": str(index * 10 + 5),
                            "package_start0": str(index * 10 - 2),
                            "package_end0": str(index * 10 + 7),
                        }
                    )
                for filename, text in {
                    "sequence.fa": f">{packet_id}\nACGT\n",
                    "context_features.tsv": f"packet_id\tfeature_id\n{packet_id}\tFB{index}\n",
                    "raw_flybase_features.gff3": f"chr1\tFlyBase\tTE\t1\t5\t.\t+\t.\tID=FB{index}\n",
                }.items():
                    (packet_dir / filename).write_text(text, encoding="utf-8")

    def _write_kit(self) -> None:
        packet_ids = ["MAIN-01", "MAIN-02", "MAIN-03"]
        for actor, order in {
            "A1": ["MAIN-03", "MAIN-01", "MAIN-02"],
            "A2": ["MAIN-02", "MAIN-03", "MAIN-01"],
        }.items():
            actor_dir = self.kit / f"annotator_{actor}"
            response_dir = actor_dir / "responses"
            response_dir.mkdir(parents=True)
            with (actor_dir / "assignment.tsv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "actor_id",
                        "assignment_order",
                        "packet_id",
                        "packet_relpath",
                        "response_dir",
                    ],
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writeheader()
                for position, packet_id in enumerate(order, start=1):
                    writer.writerow(
                        {
                            "actor_id": actor,
                            "assignment_order": str(position),
                            "packet_id": packet_id,
                            "packet_relpath": f"packets/{packet_id}",
                            "response_dir": f"annotator_{actor}/responses",
                        }
                    )
            for filename, fields in RESPONSE_FIELDS.items():
                with (response_dir / filename).open(
                    "w", newline="", encoding="utf-8"
                ) as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=fields,
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    if filename == "package_reviews.tsv":
                        for packet_id in packet_ids:
                            writer.writerow(
                                {
                                    "package_id": packet_id,
                                    "actor_id": actor,
                                    "package_status": "",
                                }
                            )

    @staticmethod
    def _read_bytes(path: Path) -> bytes:
        return path.read_bytes()

    def test_delivers_one_actor_and_copies_only_allowed_assets(self) -> None:
        output = self.root / "delivery-A1"
        delivery.assemble_gate_l_delivery(
            self.bundle,
            self.kit,
            self.handbook,
            self.registry,
            "A1",
            output,
        )

        expected_order = ["MAIN-03", "MAIN-01", "MAIN-02"]
        assignment_lines = (output / "assignment.tsv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            [line.split("\t")[2] for line in assignment_lines[1:]], expected_order
        )
        self.assertEqual(
            {line.split("\t")[4] for line in assignment_lines[1:]}, {"responses"}
        )
        self.assertEqual(
            sorted(path.name for path in (output / "responses").iterdir()),
            sorted(RESPONSE_FIELDS),
        )
        self.assertEqual(
            sorted(path.name for path in (output / "packets").iterdir()),
            ["MAIN-01", "MAIN-02", "MAIN-03"],
        )
        for packet_id in ("MAIN-01", "MAIN-02", "MAIN-03"):
            packet_dir = output / "packets" / packet_id
            self.assertEqual(
                sorted(path.name for path in packet_dir.iterdir()),
                sorted(delivery.PACKET_FILES),
            )
        self.assertEqual(
            self._read_bytes(output / "annotator_handbook.md"),
            self._read_bytes(self.handbook),
        )
        self.assertEqual(
            self._read_bytes(output / "evidence_registry.tsv"),
            self._read_bytes(self.registry),
        )
        all_paths = [path.relative_to(output).as_posix() for path in output.rglob("*")]
        self.assertNotIn("packet_manifest.tsv", all_paths)
        self.assertFalse(any("annotator_A2" in path for path in all_paths))
        self.assertFalse(any("adjudicator" in path for path in all_paths))
        self.assertFalse(any("atom" in path or "prediction" in path for path in all_paths))

    def test_packet_id_mismatch_fails_before_creating_output(self) -> None:
        assignment = self.kit / "annotator_A1" / "assignment.tsv"
        text = assignment.read_text(encoding="utf-8").replace("MAIN-03", "MAIN-99")
        assignment.write_text(text, encoding="utf-8")
        output = self.root / "invalid-delivery"
        with self.assertRaisesRegex(ValueError, "packet_id"):
            delivery.assemble_gate_l_delivery(
                self.bundle,
                self.kit,
                self.handbook,
                self.registry,
                "A1",
                output,
            )
        self.assertFalse(output.exists())

    def test_unknown_response_packet_id_fails_before_creating_output(self) -> None:
        response = self.kit / "annotator_A1" / "responses" / "package_reviews.tsv"
        response.write_text(
            "package_id\tactor_id\tpackage_status\nMAIN-99\tA1\tresolved\n",
            encoding="utf-8",
        )
        output = self.root / "invalid-response-delivery"
        with self.assertRaisesRegex(ValueError, "response packet_id"):
            delivery.assemble_gate_l_delivery(
                self.bundle,
                self.kit,
                self.handbook,
                self.registry,
                "A1",
                output,
            )
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
