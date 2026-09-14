import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('revision',Path(__file__).with_name('qualify_mm10.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class IntervalTest(unittest.TestCase):
    def test_added_deleted_and_shared_material_are_separate(self):
        # Overlapping records must not double-count bp. A new annotation can
        # simultaneously remove old positives and add different positives.
        a=r.union([(0,5),(3,8),(10,12)])
        b=r.union([(0,5),(6,9),(11,13)])
        self.assertEqual(r.bp(a),10)
        self.assertEqual(r.bp(b),10)
        self.assertEqual(r.shared(a,b),8)
        self.assertEqual(r.bp(a)-r.shared(a,b),2)
        self.assertEqual(r.bp(b)-r.shared(a,b),2)
    def test_bookended_half_open_coordinates(self):
        self.assertEqual(r.shared([(0,5)],[(5,10)]),0)
        self.assertEqual(r.union([(0,5),(5,10)]),[(0,10)])

if __name__=='__main__':unittest.main()
