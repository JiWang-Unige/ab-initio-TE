#!/usr/bin/env python3
"""Small contract tests for the fixed-panel library-control scorer."""

from __future__ import annotations

import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("control.py")
SPEC = importlib.util.spec_from_file_location("annotation_library_control", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


class ControlContractTests(unittest.TestCase):
    def test_cached_index_preserves_half_open_overlap(self) -> None:
        intervals = [(2, 5), (10, 15), (20, 22)]
        starts = [2, 10, 20]
        covered = {bp for left, right in intervals for bp in range(left, right)}
        for left in range(26):
            for right in range(left + 1, 27):
                expected = len(covered.intersection(range(left, right)))
                self.assertEqual(CONTROL.overlap_bp(intervals, left, right), expected)
                self.assertEqual(CONTROL.overlap_bp(intervals, left, right, starts), expected)

    def test_annotation_categories_keep_unknown_and_unrecognized_separate(self) -> None:
        self.assertEqual(CONTROL.annotation_category("SINE/Alu"), "TE")
        self.assertEqual(CONTROL.annotation_category("LINE/L1"), "TE")
        self.assertEqual(CONTROL.annotation_category("Simple_repeat"), "NONTE")
        self.assertEqual(CONTROL.annotation_category("Low_complexity"), "NONTE")
        self.assertEqual(CONTROL.annotation_category("Unknown"), "UNKNOWN")
        self.assertEqual(CONTROL.annotation_category("DNA/TcMar?"), "UNKNOWN")
        self.assertEqual(CONTROL.annotation_category("PLE/Other"), "UNRECOGNIZED")

    def test_fixed_tile_loader_filters_chromosomes_and_checks_tile_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bed = root / "fixed.bed"
            bed.write_text(
                "chr1\t0\t8\t.\t0\t+\thuman|hg19|chr1|0|8\n"
                "chr2\t9\t12\t.\t0\t.\thuman|hg19|chr2|8|16\n",
                encoding="utf-8",
            )
            config = {
                "allowed_chromosomes": ["chr2"],
                "tile_bp": 8,
                "expected_tile_count": 1,
            }
            rows = CONTROL.load_fixed_tiles(bed, config)
            self.assertEqual([row["tile_id"] for row in rows], ["human|hg19|chr2|8|16"])
            self.assertEqual((rows[0]["tile_start0"], rows[0]["tile_end"]), (8, 16))

            bad = root / "bad.bed"
            bad.write_text("chr2\t8\t16\t.\t0\t.\thuman|hg19|chr2|0|8\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                CONTROL.load_fixed_tiles(bad, config)

    def test_prepare_panel_preserves_center_and_halo_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.fa.gz"
            with gzip.open(source, "wt", encoding="utf-8") as handle:
                handle.write(">chr2\n" + "ACGT" * 10 + "\n")
            bed = root / "fixed.bed"
            bed.write_text("chr2\t8\t16\t.\t0\t.\thuman|hg19|chr2|8|16\n", encoding="utf-8")
            config = {
                "source_assembly": "hg19",
                "allowed_chromosomes": ["chr2"],
                "tile_bp": 8,
                "halo_bp": 4,
                "expected_tile_count": 1,
                "old_confusion_intervals": "fixed.bed",
                "source_fasta": "source.fa.gz",
            }
            out = root / "panel"
            manifest = CONTROL.prepare_panel(config, root, out)
            self.assertEqual(manifest["query_count"], 1)
            self.assertEqual(manifest["center_bp"], 8)
            self.assertEqual(manifest["panel_bp"], 16)
            table = CONTROL.read_panel(out / "panel.tsv")
            row = table["tile0000"]
            self.assertEqual((row["query_start0"], row["query_end"], row["center_offset0"]), ("4", "20", "4"))

    def test_repeatmasker_coordinates_are_clipped_to_center_and_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = {
                "tile0000": {
                    "query_id": "tile0000",
                    "center_offset0": "2",
                    "center_end_offset": "10",
                }
            }
            out = root / "panel.fa.out"
            out.write_text(
                "  100  0.0  0.0  0.0 tile0000 1 5 (0) + Alu SINE/Alu 1 5 (0) 1\n"
                "  100  0.0  0.0  0.0 tile0000 6 9 (0) + foo PLE/Other 1 4 (0) 2\n"
                "  100  0.0  0.0  0.0 tile0000 9 12 (0) + low Simple_repeat 1 4 (0) 3\n",
                encoding="utf-8",
            )
            annotations = CONTROL.parse_repeatmasker_out(out, panel)
            self.assertEqual(annotations["tile0000"]["TE"], [(2, 5)])
            self.assertEqual(annotations["tile0000"]["UNRECOGNIZED"], [(5, 9)])
            self.assertEqual(annotations["tile0000"]["NONTE"], [(8, 10)])

    def test_support_and_source_only_pair_keep_unmatched_fp(self) -> None:
        panel = {
            "human|hg19|chr2|0|8": {
                "query_id": "tile0000",
                "tile_id": "human|hg19|chr2|0|8",
                "tile_start0": "0",
                "center_offset0": "0",
                "center_end_offset": "8",
            }
        }
        annotations = {
            "tile0000": {
                "TE": [(0, 4)],
                "UNKNOWN": [],
                "NONTE": [],
                "UNRECOGNIZED": [],
            }
        }
        row = {
            "mapping_id": "m1",
            "state": "FP",
            "source_chrom": "chr2",
            "source_start0_int": "0",
            "source_end_int": "4",
            "tile_id": "human|hg19|chr2|0|8",
            "mapping_status": CONTROL.QUALIFIED_STATUS,
        }
        scored = CONTROL.support_record(row, panel, annotations, {"chr2": [(0, 4)]})
        self.assertTrue(scored["TE_any_supported"])
        self.assertTrue(scored["old_te_supported"])
        matches = [{"fp_mapping_id": "m1", "control_mapping_id": "missing", "match_status": "UNMATCHED_FP", "fp_old_te_relation": "ISOLATED"}]
        summary = CONTROL.aggregate_library([scored], matches, {"m1": scored}, "fixture")
        pair = summary["source_only_matched_pairs"]["TE:any"]
        self.assertEqual(pair["unmatched_fp"], 1)
        self.assertEqual(pair["fp_supported"], 1)
        self.assertEqual(pair["matched_pairs"], 0)

    def test_audit_library_cli_does_not_require_scoring_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "fixture.fa"
            library.write_text(">family_1#SINE/Alu\nACGT\n>family_2#LINE/L1\nACGTAC\n", encoding="utf-8")
            manifest = root / "audit.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "audit-library",
                    "--library",
                    str(library),
                    "--label",
                    "fixture",
                    "--output",
                    str(manifest),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(completed.stdout)["record_count"], 2)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["total_bp"], 10)


if __name__ == "__main__":
    unittest.main()
