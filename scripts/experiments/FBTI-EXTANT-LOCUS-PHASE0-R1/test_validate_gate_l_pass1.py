#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "validate_gate_l_pass1", HERE / "validate_gate_l_pass1.py"
)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidateGateLPass1Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest = self.root / "packet_manifest.tsv"
        self.evidence_registry = self.root / "evidence_registry.tsv"
        self.responses = self.root / "responses"
        self._write_manifest()
        self.evidence_registry.write_text(
            "evidence_code\tevidence_class\tsource_version\tindependent_of_fbti_endpoint\tused_by_gate_e\n"
            "FLYBASE_FEATURE_RECORD\tprovenance\tr6.68\t0\t0\n",
            encoding="utf-8",
        )
        self._write_response(
            package_status="resolved",
            loci=[self._locus("L1", "resolved", 120, 220)],
            materials=[self._material("M1", "L1", 120, 220, "assigned")],
            boundaries=self._boundaries("L1", 120, 220),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_manifest(self) -> None:
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted(validator.MANIFEST_REQUIRED_FIELDS)
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow(
                {
                    "packet_id": "CALIB-01",
                    "package_id": "S0-00001",
                    "role": "calibration",
                    "role_rank": "1",
                    "unit_type": "S0",
                    "hard_cell": "S0-L1",
                    "assembly_id": "dmel_r6.68",
                    "seqid": "2L",
                    "core_start0": "120",
                    "core_end0": "220",
                    "package_start0": "100",
                    "package_end0": "300",
                    "feature_ids": "FBti0000001",
                }
            )

    @staticmethod
    def _locus(locus_id: str, status: str, start: int, end: int) -> dict[str, str]:
        return {
            "package_id": "CALIB-01",
            "actor_id": "A1",
            "locus_id": locus_id,
            "locus_status": status,
            "locus_envelope_start": str(start),
            "locus_envelope_end": str(end),
        }

    @staticmethod
    def _material(
        segment_id: str,
        locus_id: str,
        start: int,
        end: int,
        assignment: str,
    ) -> dict[str, str]:
        return {
            "package_id": "CALIB-01",
            "actor_id": "A1",
            "segment_id": segment_id,
            "locus_id": locus_id,
            "seqid": "2L",
            "start": str(start),
            "end": str(end),
            "evidence_codes": "",
            "locus_assignment_status": assignment,
        }

    @staticmethod
    def _boundaries(locus_id: str, left: int, right: int) -> list[dict[str, str]]:
        rows = []
        for side, position in (("left", left), ("right", right)):
            rows.append(
                {
                    "package_id": "CALIB-01",
                    "actor_id": "A1",
                    "locus_id": locus_id,
                    "side": side,
                    "identifiability": "point",
                    "lower_pos": str(position),
                    "upper_pos": str(position),
                    "evidence_codes": "",
                }
            )
        return rows

    def _write_response(
        self,
        package_status: str,
        loci: list[dict[str, str]],
        materials: list[dict[str, str]],
        boundaries: list[dict[str, str]],
        interruptions: list[dict[str, str]] | None = None,
        relations: list[dict[str, str]] | None = None,
    ) -> None:
        self.responses.mkdir(parents=True, exist_ok=True)
        rows = {
            "package_reviews.tsv": [
                {
                    "package_id": "CALIB-01",
                    "actor_id": "A1",
                    "package_status": package_status,
                    "topology_resolution": "",
                    "topology_reason": "",
                }
            ],
            "loci.tsv": loci,
            "material_segments.tsv": materials,
            "boundaries.tsv": boundaries,
            "interruptions.tsv": interruptions or [],
            "relations.tsv": relations or [],
        }
        for filename, fields in validator.TABLE_FIELDS.items():
            with (self.responses / filename).open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(rows[filename])

    def test_valid_minimal_package_maps_opaque_id_and_writes_normalized_bundle(self) -> None:
        output = self.root / "normalized"
        validator.validate_and_normalize(
            self.manifest, self.evidence_registry, self.responses, "A1", output
        )

        with (output / "package_reviews.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            reviews = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(reviews[0]["package_id"], "S0-00001")
        self.assertEqual(reviews[0]["actor_id"], "A1")
        with (output / "loci.tsv").open(newline="", encoding="utf-8") as handle:
            loci = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(loci[0]["package_id"], "S0-00001")
        self.assertEqual(loci[0]["locus_id"], "L1")
        self.assertEqual(set(path.name for path in output.iterdir()), set(validator.TABLE_FIELDS))

    def test_rejects_abstained_locus_status(self) -> None:
        self._write_response(
            package_status="resolved",
            loci=[self._locus("L1", "abstained", 120, 220)],
            materials=[self._material("M1", "L1", 120, 220, "assigned")],
            boundaries=self._boundaries("L1", 120, 220),
        )
        with self.assertRaisesRegex(ValueError, "invalid locus_status"):
            validator.validate_and_normalize(
                self.manifest,
                self.evidence_registry,
                self.responses,
                "A1",
                self.root / "invalid-locus",
            )

    def test_rejects_missing_relation_for_two_declared_loci(self) -> None:
        self._write_response(
            package_status="resolved",
            loci=[
                self._locus("L1", "resolved", 120, 160),
                self._locus("L2", "resolved", 180, 220),
            ],
            materials=[
                self._material("M1", "L1", 120, 160, "assigned"),
                self._material("M2", "L2", 180, 220, "assigned"),
            ],
            boundaries=self._boundaries("L1", 120, 160)
            + self._boundaries("L2", 180, 220),
        )
        with self.assertRaisesRegex(ValueError, "each pair of declared loci"):
            validator.validate_and_normalize(
                self.manifest,
                self.evidence_registry,
                self.responses,
                "A1",
                self.root / "missing-relation",
            )

    def test_rejects_material_outside_package(self) -> None:
        self._write_response(
            package_status="resolved",
            loci=[self._locus("L1", "resolved", 120, 220)],
            materials=[self._material("M1", "L1", 90, 220, "assigned")],
            boundaries=self._boundaries("L1", 120, 220),
        )
        with self.assertRaisesRegex(ValueError, "material segment outside package"):
            validator.validate_and_normalize(
                self.manifest,
                self.evidence_registry,
                self.responses,
                "A1",
                self.root / "out-of-bounds",
            )

    def test_rejects_assigned_and_unresolved_material_overlap(self) -> None:
        self._write_response(
            package_status="partially_resolved",
            loci=[self._locus("L1", "partially_resolved", 120, 220)],
            materials=[
                self._material("M1", "L1", 120, 180, "assigned"),
                self._material("U1", "", 150, 200, "unresolved"),
            ],
            boundaries=self._boundaries("L1", 120, 220),
        )
        with self.assertRaisesRegex(ValueError, "assigned and unresolved material overlap"):
            validator.validate_and_normalize(
                self.manifest,
                self.evidence_registry,
                self.responses,
                "A1",
                self.root / "overlapping-assignment-status",
            )

    def test_rejects_nested_interruption_without_matching_edge(self) -> None:
        self._write_response(
            package_status="resolved",
            loci=[
                self._locus("L1", "resolved", 120, 220),
                self._locus("L2", "resolved", 150, 180),
            ],
            materials=[
                self._material("M1", "L1", 120, 145, "assigned"),
                self._material("M1b", "L1", 185, 220, "assigned"),
                self._material("M2", "L2", 150, 180, "assigned"),
            ],
            boundaries=self._boundaries("L1", 120, 220)
            + self._boundaries("L2", 150, 180),
            interruptions=[
                {
                    "package_id": "CALIB-01",
                    "actor_id": "A1",
                    "interruption_id": "I1",
                    "locus_id": "L1",
                    "child_locus_id": "L2",
                    "seqid": "2L",
                    "start": "150",
                    "end": "180",
                    "interruption_type": "nested_locus_occupied",
                    "evidence_codes": "",
                }
            ],
            relations=[
                {
                    "package_id": "CALIB-01",
                    "actor_id": "A1",
                    "relation_id": "R1",
                    "relation_type": "distinct_locus",
                    "subject_locus_id": "L1",
                    "object_locus_id": "L2",
                    "evidence_codes": "",
                }
            ],
        )
        with self.assertRaisesRegex(ValueError, "nested interruption lacks"):
            validator.validate_and_normalize(
                self.manifest,
                self.evidence_registry,
                self.responses,
                "A1",
                self.root / "bad-nested",
            )


if __name__ == "__main__":
    unittest.main()
