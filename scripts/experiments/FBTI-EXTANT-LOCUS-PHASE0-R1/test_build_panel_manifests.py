#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_panel_manifests", HERE / "build_panel_manifests.py"
)
assert SPEC is not None and SPEC.loader is not None
sidecars = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sidecars)


class BuildPanelManifestsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.packages = self.root / "packages.tsv"
        self.truth = self.root / "truth.tsv"
        self.atoms = self.root / "p3.tsv"
        with self.truth.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(
                ["feature_id", "seqid", "start0", "end0", "strand", "label"]
            )
            writer.writerows(
                [
                    ["FBti1", "2L", 100, 200, "+", "component-a"],
                    ["FBti2", "2L", 150, 180, "+", "component-b"],
                    ["FBti3", "2L", 500, 550, "-", "singleton"],
                    ["FBti4", "2L", 700, 760, "+", "other-singleton"],
                ]
            )
        with self.packages.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(
                [
                    "package_id",
                    "role",
                    "unit_type",
                    "seqid",
                    "core_start0",
                    "core_end0",
                    "package_start0",
                    "package_end0",
                    "feature_ids",
                ]
            )
            writer.writerows(
                [
                    ["P-S1", "main", "S1", "2L", 100, 200, 90, 240, "FBti1,FBti2"],
                    ["P-S0", "main", "S0", "2L", 500, 550, 480, 570, "FBti3"],
                ]
            )
        with self.atoms.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["seqid", "start", "end", "score"])
            writer.writerows(
                [
                    ["2L", 95, 120, "a"],
                    ["2L", 80, 110, "b"],
                    ["2L", 230, 250, "c"],
                    ["2L", 80, 260, "d"],
                    ["2L", 500, 530, "e"],
                    ["2L", 470, 490, "f"],
                    ["2L", 560, 590, "g"],
                    ["2L", 230, 500, "crosses-two-packages"],
                    ["2L", 300, 310, "outside"],
                ]
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_context_and_atom_sidecars(self) -> None:
        context_fields, context_rows, atom_fields, atom_rows = sidecars.build_sidecars(
            self.packages, self.truth, self.atoms
        )
        self.assertEqual(context_fields, ["package_id", "feature_id", "seqid", "start0", "end0", "strand", "label"])
        context_by_package = {}
        for row in context_rows:
            context_by_package.setdefault(row["package_id"], []).append(row)
        self.assertEqual(
            [row["feature_id"] for row in context_by_package["P-S1"]],
            ["FBti1", "FBti2"],
        )
        self.assertEqual(context_by_package["P-S1"][0]["label"], "component-a")
        self.assertEqual(
            {row["feature_id"] for row in context_by_package["P-S0"]}, {"FBti3"}
        )

        self.assertEqual(
            set(atom_fields),
            {"package_id", "atom_id", "seqid", "start0", "end0", "overlap_role", "package_censored", "score"},
        )
        atom_by_id = {row["atom_id"]: row for row in atom_rows}
        self.assertEqual(atom_by_id["P3:2L:95:120"]["overlap_role"], "contained")
        self.assertEqual(atom_by_id["P3:2L:95:120"]["package_censored"], "0")
        self.assertEqual(atom_by_id["P3:2L:80:110"]["overlap_role"], "left_censored")
        self.assertEqual(atom_by_id["P3:2L:230:250"]["overlap_role"], "right_censored")
        self.assertEqual(atom_by_id["P3:2L:80:260"]["overlap_role"], "both_censored")
        self.assertEqual(atom_by_id["P3:2L:80:260"]["package_censored"], "1")
        self.assertNotIn("P3:2L:300:310", atom_by_id)

        cross_package = [
            row for row in atom_rows if row["atom_id"] == "P3:2L:230:500"
        ]
        self.assertEqual(
            {(row["package_id"], row["package_censored"]) for row in cross_package},
            {("P-S1", "1"), ("P-S0", "1")},
        )

    def test_rejects_incomplete_s1_component(self) -> None:
        text = self.packages.read_text(encoding="utf-8").replace("FBti1,FBti2", "FBti1")
        self.packages.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "complete truth component"):
            sidecars.build_sidecars(self.packages, self.truth, self.atoms)

    def test_rejects_duplicate_canonical_coordinates(self) -> None:
        with self.atoms.open("a", encoding="utf-8") as handle:
            handle.write("2L\t95\t120\tduplicate\n")
        with self.assertRaisesRegex(ValueError, "duplicate canonical P3 coordinates"):
            sidecars.build_sidecars(self.packages, self.truth, self.atoms)

    def test_rejects_overlapping_selected_packages(self) -> None:
        text = self.packages.read_text(encoding="utf-8").replace("480\t570", "200\t570")
        self.packages.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "selected packages overlap"):
            sidecars.build_sidecars(self.packages, self.truth, self.atoms)

    def test_rejects_truth_context_shared_by_two_packages(self) -> None:
        with self.truth.open("a", encoding="utf-8") as handle:
            handle.write("FBti5\t2L\t230\t500\t+\tshared-context\n")
        with self.assertRaisesRegex(ValueError, "truth context feature enters multiple packages"):
            sidecars.build_sidecars(self.packages, self.truth, self.atoms)

    def test_writes_only_the_two_sidecars(self) -> None:
        output = self.root / "sidecars"
        sidecars.build_panel_manifests(self.packages, self.truth, self.atoms, output)
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"context_features.tsv", "package_atoms.tsv"},
        )
        with (output / "package_atoms.tsv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 9)


if __name__ == "__main__":
    unittest.main()
