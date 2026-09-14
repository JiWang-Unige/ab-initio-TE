#!/usr/bin/env python3
"""Small local tests for natural-panel extraction and identity labels."""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("build_natural_panel", HERE / "build_natural_panel.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def write_fasta_with_fai(path: Path, name: str, sequence: str, line_bases: int = 10) -> None:
    with path.open("wb") as handle:
        offset = handle.tell()
        handle.write((">%s\n" % name).encode())
        sequence_offset = handle.tell()
        lines = [sequence[i:i + line_bases] for i in range(0, len(sequence), line_bases)]
        for line in lines:
            handle.write((line + "\n").encode())
    line_width = line_bases + 1
    path.with_name(path.name + ".fai").write_text(
        "%s\t%d\t%d\t%d\t%d\n" % (name, len(sequence), sequence_offset, line_bases, line_width),
        encoding="utf-8",
    )


class NaturalPanelTest(unittest.TestCase):
    def test_repeat_name_is_exact_family_and_rep_family_is_context(self):
        row = module.parse_bed_row(
            ["chr1", "10", "110", "AluY", "100", "+", "SINE", "Alu", "1", "100", "1"], 1
        )
        self.assertEqual(row["family_id"], "AluY")
        self.assertEqual(row["superfamily_id"], "Alu")

    def test_fetch_sequence_respects_half_open_interval_and_strand(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "x.fa"
            sequence = "AACCGGTTAACCGGTTAACC"
            write_fasta_with_fai(fasta, "chr1", sequence)
            fai = module.parse_fai(root / "x.fa.fai")
            with fasta.open("rb") as handle:
                self.assertEqual(module.fetch_sequence(handle, fai, "chr1", 2, 8, "+"), "CCGGTT")
                self.assertEqual(module.fetch_sequence(handle, fai, "chr1", 2, 8, "-"), "AACCGG")

    def test_consensus_rows_are_material_only_and_copy_ids_are_coordinate_derived(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "hg38.fa"
            write_fasta_with_fai(fasta, "chr1", "ACGT" * 1000)
            bed = root / "rmsk_te.bed.gz"
            rows = []
            for index, start in enumerate((10, 120, 230, 340, 450, 560), start=1):
                rows.append("chr1\t%d\t%d\tAluY\t100\t+\tSINE\tAlu\t1\t100\t1\n" % (start, start + 100))
            with gzip.open(bed, "wt", encoding="utf-8") as handle:
                handle.writelines(rows)
            consensus = root / "consensus.fa"
            consensus.write_text(">AluY#SINE/Alu\n%s\n" % ("ACGT" * 50), encoding="utf-8")
            args = type("Args", (), {
                "te_final_root": str(root),
                "assembly": "hg38",
                "species": "human",
                "chromosomes": ["chr1"],
                "bed": str(bed),
                "fasta": str(fasta),
                "fai": str(root / "hg38.fa.fai"),
                "consensus_fasta": str(consensus),
                "out_dir": str(root / "out"),
                "max_families": 1,
                "target_per_family": 6,
                "min_intervals": 3,
                "max_divergence": 20.0,
                "min_length": 80,
                "max_length": 1000,
                "kmer_size": 3,
                "homology_jaccard": 0.99,
                "nearby_distance": 25,
            })()
            status = module.run(args)
            self.assertEqual(status["natural_rows"], 6)
            self.assertEqual(status["consensus_rows"], 1)
            records = [json.loads(line) for line in (root / "out" / "identity_manifest.jsonl").read_text().splitlines()]
            natural = [row for row in records if row["source_kind"] == "natural_copy"]
            consensus_rows = [row for row in records if row["source_kind"] == "consensus"]
            self.assertTrue(all(row["source_copy_id"].startswith("coord|") for row in natural))
            self.assertTrue(all(row["biological_insertion_id"] == "" for row in natural))
            self.assertEqual(natural[0]["family_id"], "AluY")
            self.assertEqual(natural[0]["superfamily_id"], "Alu")
            self.assertEqual(consensus_rows[0]["source_copy_id"], "")
            self.assertEqual(consensus_rows[0]["homology_component_id"], "")

    def test_exact_consensus_lookup_keeps_ambiguity_and_missing_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "consensus.fa"
            path.write_text(
                ">AluY#SINE/Alu\nACGT\n>AluY#SINE/Alu\nTGCA\n",
                encoding="utf-8",
            )
            records, audit = module.read_consensus(path, {"AluY", "MIR"})
            self.assertEqual(records, [])
            self.assertEqual(audit["ambiguous_families"], ["AluY"])
            self.assertEqual(audit["missing_families"], ["MIR"])

    def test_homology_components_can_join_exact_names_by_sequence_or_locus(self):
        rows = [
            {"family_id": "AluY", "chrom": "chr1", "start": 10, "end": 110, "sequence": "ACGT" * 30},
            {"family_id": "AluSx", "chrom": "chr1", "start": 130, "end": 230, "sequence": "TGCA" * 30},
            {"family_id": "MIR", "chrom": "chr1", "start": 500, "end": 600, "sequence": "ACGT" * 30},
        ]
        components = module.homology_components(rows, jaccard_threshold=0.99, k=3, nearby_distance=25)
        self.assertEqual(components[0], components[1])  # nearby locus
        self.assertEqual(components[0], components[2])  # sequence evidence


if __name__ == "__main__":
    unittest.main(verbosity=2)
