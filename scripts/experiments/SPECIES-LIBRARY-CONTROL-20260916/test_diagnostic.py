"""Coordinate clipping, overlapping classes, and complete confusion transitions."""
import itertools
import tempfile
from pathlib import Path
import unittest
import numpy as np
import diagnostic as d


class DiagnosticTest(unittest.TestCase):
    def test_rm_coordinate_conversion_and_core_clipping(self):
        text = '  300 2.0 0 0 query 101 104 (0) + A LINE/L1 1 4 (0) 1\n'
        text += '  300 2.0 0 0 query 104 108 (0) + B SINE/Alu 1 5 (0) 2\n'
        text += '  300 2.0 0 0 query 107 109 (0) + U Unknown 1 3 (0) 3\n'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'rm.out'; path.write_text(text)
            rows = d.raw_rows(path,{'query'})['query']
        bits, unknown = d.paint(rows,102,6)
        self.assertEqual(bits.tolist(),[1,3,2,2,2,2])
        self.assertEqual(unknown.tolist(),[False,False,False,False,True,True])
        # The shared endpoint is counted for both families but only once as material.
        self.assertEqual(int((bits>0).sum()),6)

    def test_all_truth_library_prediction_transitions(self):
        rows = list(itertools.product([False,True],repeat=4))
        old,new,p,callable_ = (np.array([r[i] for r in rows]) for i in range(4))
        before,after = d.count(old,p,callable_),d.count(new,p,callable_)
        adds = (~old)&new&callable_; losses=old&(~new)&callable_
        a=int(sum(adds&p)); b=int(sum(adds&~p))
        u=int(sum(losses&p)); v=int(sum(losses&~p))
        self.assertEqual(after['tp'],before['tp']+a-u)
        self.assertEqual(after['fp'],before['fp']-a+u)
        self.assertEqual(after['fn'],before['fn']+b-v)
        self.assertEqual(after['tn'],before['tn']-b+v)
        self.assertEqual(sum(after[k] for k in ('tp','fp','fn','tn')),8)


if __name__ == '__main__': unittest.main()
