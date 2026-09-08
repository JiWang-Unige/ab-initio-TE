"""Bounded tests: production projection equivalence and population preservation."""
import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


audit = load(Path(__file__).with_name("audit_coverage.py"), "audit")
fixture = load(audit.ROOT / "scripts/experiments/GAP-BRIDGE-P3-NT-R2/test_prepare_pair.py", "pair_fixture")


class CoverageTests(unittest.TestCase):
    def test_exact_production_adapter_trace(self):
        # Both reachable production branches: sentinels are finite even when
        # coverage truncates. Compare to actual nonzero projection, not finiteness.
        strict = fixture.real_strict_adapter()
        for offsets in (True, False):
            for sequence, expected in (("ACGT"*1024, 4096), ("N"*800+"A"*3296, 686), ("ACNTA", 5)):
                with self.subTest(offsets=offsets, length=len(sequence), expected=expected):
                    coverage = audit.audit_window(strict, fixture.token_model, fixture.KmerTokenizer(offsets), sequence)
                    probability = strict.infer_probs_for_label_mode(fixture.token_model, fixture.KmerTokenizer(offsets), sequence, 4096, "cpu", "nt_kmer")[:len(sequence)]
                    self.assertTrue(np.isfinite(probability).all())
                    self.assertEqual(int(coverage.sum()), expected)
                    np.testing.assert_array_equal(coverage, probability > 0)

    def test_cross_seam_gap_and_crop_denominators(self):
        row = {"gap_start": 4095, "gap_end": 4098, "crop_start": 3839, "crop_end": 4354}
        left, right = np.ones(4096, bool), np.zeros(4096, bool)
        right[:1] = True
        result = audit.summarize_candidate(row, {0: left, 4096: right})
        self.assertEqual(result["gap_covered_bp"], 2)
        self.assertEqual(result["gap_missing_bp"], 1)
        self.assertEqual(result["crop_covered_bp"], 258)
        self.assertEqual(result["crop_missing_bp"], 257)
        self.assertEqual(result["crop_status"], "partial")

    def test_all_known_unknown_cal_roles_without_target_use(self):
        fields = ["candidate_id", "seqid", "role", "chr13_block_index", "gap_start", "gap_end", "crop_start", "crop_end", "length_stratum", "comparator_known", "target_negative_fraction"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"c.tsv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
                writer.writeheader()
                for index, (chrom, role, known) in enumerate((("chr3", "TRAIN", "1"), ("chr5", "TRAIN", "0"), ("chr13", "DEV", "0"), ("chr13", "CAL_FIT", "1"), ("chr13", "CAL_GATE", "0"), ("chr19", "TEST", "1"))):
                    writer.writerow(dict(candidate_id=str(index), seqid=chrom, role=role, chr13_block_index="1", gap_start=1000, gap_end=1002, crop_start=744, crop_end=1258, length_stratum="2-5", comparator_known=known, target_negative_fraction="DO_NOT_PARSE"))
            rows = list(audit.candidate_rows(path))
            self.assertEqual(len(rows), 5)
            self.assertEqual({r["role"] for r in rows}, {"TRAIN", "DEV", "CAL_FIT", "CAL_GATE"})
            self.assertEqual(sum(r["known"] == "0" for r in rows), 3)

    def test_compact_intervals_keep_genomic_coordinates(self):
        self.assertEqual(audit.intervals(np.array([False, True, True, False, True]), 8192), [(8193, 8195), (8196, 8197)])


if __name__ == "__main__":
    unittest.main()
