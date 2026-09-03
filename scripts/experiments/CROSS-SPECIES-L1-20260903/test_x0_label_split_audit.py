import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("x0_label_split_audit.py")
SPEC = importlib.util.spec_from_file_location("x0_label_split_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class X0AuditTest(unittest.TestCase):
    def test_repeatmasker_classes_and_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.out"
            path.write_text(
                "  100  1.0 0.0 0.0 chr1 2 5 (95) + r1 LINE/L1 1 4 (0) 1\n"
                "  100  1.0 0.0 0.0 chr1 6 8 (92) + r2 Unknown/Unknown 1 3 (0) 2\n"
                "  100  1.0 0.0 0.0 chr1 9 12 (88) + r3 Simple_repeat 1 4 (0) 3\n"
            )
            packed, stats = MODULE.parse_repeatmasker(path, {"chr1": 100}, {"chr1"})
            self.assertEqual(stats["records"], 3)
            self.assertEqual(packed["positive"]["chr1"][0], [(1, 5)])
            self.assertEqual(packed["unknown"]["chr1"][0], [(5, 8)])
            self.assertEqual(packed["hard_negative"]["chr1"][0], [(8, 12)])

    def test_label_priority(self):
        intervals = {
            "positive": {"chr1": ([(2, 6)], [6])},
            "unknown": {"chr1": ([(0, 4)], [4])},
            "hard_negative": {"chr1": ([(4, 8)], [8])},
        }
        labels = bytearray(8)
        MODULE.paint(labels, "chr1", 0, intervals["hard_negative"], 3)
        MODULE.paint(labels, "chr1", 0, intervals["unknown"], 2)
        MODULE.paint(labels, "chr1", 0, intervals["positive"], 1)
        self.assertEqual(list(labels), [2, 2, 1, 1, 1, 1, 3, 3])

    def test_quota_bounds(self):
        quotas = MODULE.allocate_quotas({f"chr{i}": 1000 for i in range(5)}, 1500, 0.10, 0.30)
        self.assertEqual(sum(quotas.values()), 1500)
        self.assertTrue(all(150 <= value <= 450 for value in quotas.values()))

    def test_split_overlap_is_rejected(self):
        rows = [
            {"species_code": "s", "split": "TRAIN", "chrom": "chr1", "start": 0, "end": 8192},
            {"species_code": "s", "split": "CAL", "chrom": "chr1", "start": 4096, "end": 12288},
        ]
        with self.assertRaisesRegex(ValueError, "coordinate overlap"):
            MODULE.assert_no_split_overlap(rows)

    def test_single_chromosome_validation_uses_disjoint_blocks(self):
        candidates = {"chrI": [index * MODULE.TILE_BP for index in range(1280)]}
        selected = MODULE.split_validation_tiles("worm", "ce11", candidates)
        self.assertEqual(len(selected), MODULE.CAL_TILES + MODULE.DEV_TILES)
        cal_blocks = {start // MODULE.BLOCK_BP for _, start, split in selected if split == "CAL"}
        dev_blocks = {start // MODULE.BLOCK_BP for _, start, split in selected if split == "DEV"}
        self.assertFalse(cal_blocks & dev_blocks)


if __name__ == "__main__":
    unittest.main()
