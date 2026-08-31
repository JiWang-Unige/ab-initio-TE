#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("build_population", HERE / "build_population.py")
assert SPEC is not None and SPEC.loader is not None
build_population = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_population)


class BuildPopulationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.truth = self.root / "truth.tsv"
        self.overlaps = self.root / "overlaps.tsv"
        self.atoms = self.root / "atoms.tsv"
        self.lengths = self.root / "lengths.json"
        with self.truth.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(
                [
                    "feature_id", "seqid", "start0", "end0", "strand",
                    "flybase_name", "release", "species",
                ]
            )
            writer.writerows(
                [
                    ["FBti1", "2L", 100, 200, "+", "A{}1", "r6.68", "Dmel"],
                    ["FBti2", "2L", 150, 180, "+", "B{}2", "r6.68", "Dmel"],
                    ["FBti3", "2L", 40_000, 40_200, "-", "C{}3", "r6.68", "Dmel"],
                ]
            )
        with self.overlaps.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(
                [
                    "seqid", "left_id", "left_start0", "left_end0", "right_id",
                    "right_start0", "right_end0", "relationship",
                ]
            )
            writer.writerow(["2L", "FBti1", 100, 200, "FBti2", 150, 180, "strict_containment"])
        with self.atoms.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["seqid", "start", "end"])
            writer.writerows([["2L", 90, 110], ["2L", 160, 170], ["2L", 30_000, 30_010]])
        lengths = {f"aux-{index}": 1 for index in range(1869)}
        lengths["2L"] = 143_724_133
        self.lengths.write_text(json.dumps(lengths), encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_builds_s0_and_complete_s1_component(self) -> None:
        with mock.patch.object(
            build_population, "read_fasta_lengths", return_value=build_population.read_lengths(self.lengths)
        ):
            units, summary = build_population.build_population(
                self.truth, self.overlaps, self.atoms, self.lengths, self.root / "assembly.fa.gz"
            )
        by_type = {str(unit["unit_type"]): unit for unit in units}
        self.assertEqual(summary["S0_units"], 1)
        self.assertEqual(summary["S1_units"], 1)
        self.assertEqual(by_type["S1"]["feature_ids"], "FBti1,FBti2")
        self.assertEqual(by_type["S1"]["core_start0"], 100)
        self.assertEqual(by_type["S1"]["core_end0"], 200)
        self.assertEqual(by_type["S1"]["p3_atoms_core"], 2)
        self.assertEqual(by_type["S0"]["nearest_fbti_gap"], 39_800)

    def test_rejects_overlap_coordinate_mismatch(self) -> None:
        text = self.overlaps.read_text(encoding="utf-8").replace("\t150\t180\t", "\t151\t180\t")
        self.overlaps.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "overlap coordinate mismatch"):
            with mock.patch.object(
                build_population, "read_fasta_lengths", return_value=build_population.read_lengths(self.lengths)
            ):
                build_population.build_population(
                    self.truth, self.overlaps, self.atoms, self.lengths, self.root / "assembly.fa.gz"
                )

    def test_rejects_non_frozen_assembly_lengths(self) -> None:
        self.lengths.write_text(json.dumps({"2L": 1000}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "frozen exact r6.68 assembly"):
            build_population.build_population(
                self.truth, self.overlaps, self.atoms, self.lengths, self.root / "assembly.fa.gz"
            )

    def test_rejects_length_mapping_that_does_not_match_fasta(self) -> None:
        fasta_lengths = build_population.read_lengths(self.lengths)
        fasta_lengths["2L"] -= 1
        fasta_lengths["aux-0"] += 1
        with mock.patch.object(build_population, "read_fasta_lengths", return_value=fasta_lengths):
            with self.assertRaisesRegex(ValueError, "does not match the exact r6.68 FASTA"):
                build_population.build_population(
                    self.truth, self.overlaps, self.atoms, self.lengths, self.root / "assembly.fa.gz"
                )

    def test_reads_fasta_contig_length_mapping(self) -> None:
        assembly = self.root / "assembly.fa.gz"
        with gzip.open(assembly, "wt", encoding="utf-8") as handle:
            handle.write(">2L description\nACGT\n>3R\nAA\nA\n")
        self.assertEqual(build_population.read_fasta_lengths(assembly), {"2L": 4, "3R": 3})

    def test_output_freezes_the_consumed_tabular_inputs(self) -> None:
        output = self.root / "output"
        build_population.write_outputs(
            [],
            {"status": "PREFLIGHT_PASS"},
            output,
            self.truth,
            self.overlaps,
            self.atoms,
            self.lengths,
        )
        self.assertEqual((output / "truth_metadata.tsv").read_bytes(), self.truth.read_bytes())
        self.assertEqual((output / "overlap_pairs.tsv").read_bytes(), self.overlaps.read_bytes())
        self.assertEqual((output / "p3_atoms.tsv").read_bytes(), self.atoms.read_bytes())
        self.assertEqual((output / "contig_lengths.json").read_bytes(), self.lengths.read_bytes())

    def test_rejects_atom_outside_frozen_assembly(self) -> None:
        with self.atoms.open("a", encoding="utf-8") as handle:
            handle.write("missing-contig\t0\t1\n")
        with self.assertRaisesRegex(ValueError, "invalid P3 atom interval"):
            with mock.patch.object(
                build_population, "read_fasta_lengths", return_value=build_population.read_lengths(self.lengths)
            ):
                build_population.build_population(
                    self.truth, self.overlaps, self.atoms, self.lengths, self.root / "assembly.fa.gz"
                )

    def test_census_sbatch_is_cpu_only_and_attempt_scoped(self) -> None:
        text = (HERE / "submit_population_census.sbatch").read_text(encoding="utf-8")
        self.assertIn("#SBATCH --partition=private-teodoro-gpu", text)
        self.assertNotIn("#SBATCH --gres", text)
        self.assertIn("population-census-${ATTEMPT_TAG}", text)
        self.assertIn("population-census-%j.out", text)


if __name__ == "__main__":
    unittest.main()
