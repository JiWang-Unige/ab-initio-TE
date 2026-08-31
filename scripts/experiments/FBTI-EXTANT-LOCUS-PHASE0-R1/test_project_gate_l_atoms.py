#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "project_gate_l_atoms", HERE / "project_gate_l_atoms.py"
)
assert SPEC is not None and SPEC.loader is not None
projector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projector)


class ProjectGateLAtomsTest(unittest.TestCase):
    @staticmethod
    def atom(
        atom_id: str = "P3:2L:100:200",
        start: str = "100",
        end: str = "200",
        censored: str = "0",
    ) -> dict[str, str]:
        return {
            "package_id": "MAIN-001",
            "atom_id": atom_id,
            "seqid": "2L",
            "start0": start,
            "end0": end,
            "package_censored": censored,
        }

    @staticmethod
    def material(
        segment_id: str,
        locus_id: str,
        start: str,
        end: str,
        status: str = "assigned",
    ) -> dict[str, str]:
        return {
            "package_id": "MAIN-001",
            "segment_id": segment_id,
            "locus_id": locus_id,
            "seqid": "2L",
            "start": start,
            "end": end,
            "locus_assignment_status": status,
        }

    def project(
        self,
        materials: list[dict[str, str]],
        atoms: list[dict[str, str]] | None = None,
    ) -> dict[str, str]:
        rows = projector.project_atoms(materials, atoms or [self.atom()])
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_package_censored_is_reported_and_excluded(self) -> None:
        row = self.project(
            [self.material("unresolved", "", "100", "200", "unresolved")],
            [self.atom(censored="1")],
        )
        self.assertEqual(row["projection_eligibility"], "package_censored")
        self.assertEqual(row["assignment"], "")
        self.assertEqual(row["assigned_segment_ids"], "")

    def test_one_percent_unresolved_support_keeps_unique_assignment(self) -> None:
        row = self.project(
            [
                self.material("s1", "L1", "100", "199"),
                self.material("u1", "", "199", "200", "unresolved"),
            ]
        )
        self.assertEqual(row["assignment"], "unique")
        self.assertEqual(row["assigned_locus_id"], "L1")
        self.assertEqual(row["assigned_segment_ids"], "s1")

    def test_fifteen_percent_unresolved_support_blocks_unique_assignment(self) -> None:
        row = self.project(
            [
                self.material("s1", "L1", "100", "160"),
                self.material("u1", "", "160", "175", "unresolved"),
            ]
        )
        self.assertEqual(row["assignment"], "unresolved")
        self.assertEqual(row["assigned_locus_id"], "")
        self.assertEqual(row["assigned_segment_ids"], "s1")

    def test_unique_assignment_uses_top_locus_and_sorted_segment_ids(self) -> None:
        row = self.project(
            [
                self.material("s2", "L1", "120", "170"),
                self.material("s1", "L1", "170", "200"),
            ]
        )
        self.assertEqual(row["assignment"], "unique")
        self.assertEqual(row["assigned_locus_id"], "L1")
        self.assertEqual(row["assigned_segment_ids"], "s1,s2")

    def test_mixed_assignment_requires_two_loci_at_twenty_percent(self) -> None:
        row = self.project(
            [
                self.material("s1", "L1", "100", "130"),
                self.material("s2", "L2", "160", "190"),
            ]
        )
        self.assertEqual(row["assignment"], "mixed")
        self.assertEqual(row["assigned_locus_id"], "")
        self.assertEqual(row["assigned_segment_ids"], "s1,s2")

    def test_one_percent_unresolved_support_is_unassigned(self) -> None:
        row = self.project([self.material("u1", "", "100", "101", "unresolved")])
        self.assertEqual(row["assignment"], "unassigned")
        self.assertEqual(row["assigned_locus_id"], "")
        self.assertEqual(row["assigned_segment_ids"], "")


if __name__ == "__main__":
    unittest.main()
