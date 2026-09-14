import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

native = load('native_panel', HERE / 'native.py')
adapter = load('adapter', ROOT / 'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')

class NativeCoordinates(unittest.TestCase):
    def test_inclusive_gff_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'x.gff').write_text('r01\tcaller\trepeat_region\t1\t10\t.\t-\t.\tID=x\n')
            n = native.canonicalize(adapter, p/'x.gff', 'gff3', p/'pred.tsv', [{'short_id':'r01','length_bp':10}])
            self.assertEqual(n, 1)
            self.assertIn('r01\t0\t10\tx\t.\t-', (p/'pred.tsv').read_text())

    def test_unmapped_query_is_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'x.bed').write_text('wrong\t0\t10\n')
            with self.assertRaisesRegex(ValueError, 'outside'):
                native.canonicalize(adapter, p/'x.bed', 'bed', p/'pred.tsv', [{'short_id':'r01','length_bp':10}])

    def test_empty_annotation_keeps_zero_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'x.out').write_text('There were no repetitive sequences detected\n')
            self.assertEqual(native.canonicalize(adapter, p/'x.out', 'repeatmasker_out', p/'pred.tsv', []), 0)

if __name__ == '__main__':
    unittest.main()
