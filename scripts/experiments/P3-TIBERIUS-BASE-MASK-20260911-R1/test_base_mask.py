import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("base_mask", HERE / "base_mask.py")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class BaseMaskUnitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.core = base.Core("chr16", 0, 100, 200, 80, 230)

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalize_and_intervals(self):
        self.assertEqual(base.normalize([(5, 8), (1, 3), (3, 5)]), ((1, 8),))
        mask = base.interval_mask([(90, 102), (105, 110), (108, 115)], 100, 120)
        self.assertEqual(mask.sum(), 12)
        self.assertTrue(mask[0])
        self.assertFalse(mask[4])

    def test_native_cds_gff_and_gtf_agree(self):
        gtf = self.root / "U.gtf"
        gff = self.root / "U.gff3"
        rows = [
            f'{self.core.record_id}\tT\tCDS\t26\t35\t.\t+\t0\ttranscript_id "a";',
            f'{self.core.record_id}\tT\tCDS\t46\t55\t.\t+\t0\ttranscript_id "a";',
            f'{self.core.record_id}\tT\tCDS\t66\t75\t.\t-\t0\ttranscript_id "b";',
        ]
        gtf.write_text("\n".join(rows) + "\n")
        gff.write_text("\n".join(
            row.replace('transcript_id "a";', "Parent=a").replace('transcript_id "b";', "Parent=b")
            for row in rows) + "\n")
        chains_a, content_a = base.parse_predictions(gtf, self.core, "gtf")
        chains_b, content_b = base.parse_predictions(gff, self.core, "gff3")
        self.assertEqual(chains_a, chains_b)
        self.assertEqual(content_a, content_b)
        self.assertEqual(len(chains_a), 2)
        self.assertIn(base.Chain("+", ((105, 115), (125, 135))), chains_a)

    def test_bootstrap_uses_count_fields_only(self):
        cfg = {"score": {"bootstrap_seed": 1, "bootstrap_replicates": 10}}
        row = {"modes": {"P": {"metric": base.metrics(4, 1, 2)},
                         "U": {"metric": base.metrics(3, 2, 3)}}}
        result = base.bootstrap([row, row], "P", "U", cfg)
        self.assertEqual(result["resamples"], 10)
        self.assertEqual(len(result["ci95"]), 2)


if __name__ == "__main__":
    unittest.main()
