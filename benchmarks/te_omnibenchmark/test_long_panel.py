"""Check endpoint separation and preserve failed cells during metric replay."""
import copy
import unittest
from long_panel import metrics, score


class LongPanelTests(unittest.TestCase):
    def bundle(self):
        counts=[60,20,40,80]
        paths={'D_gpu':'run/model','fixed_rm':'run/rm','edta':'run/failed'}
        statuses={m:{'status':'COMPLETED' if m!='edta' else 'TIMEOUT'} for m in paths}
        datasets={}
        for name,synthetic in [('sim100',True),('c_briggsae',False)]:
            datasets[name]={'statuses':statuses,'callable_evaluation_bp':200,
                'blocks':{'b1':{'D_gpu':counts,'fixed_rm':counts}},
                'metrics':{m:metrics(counts,synthetic) for m in ('D_gpu','fixed_rm')}}
        return {'attempts':{'datasets':{name:paths for name in datasets},'failed_engineering_attempts':[]},
                'datasets':datasets}

    def test_real_unknowns_and_timeouts_do_not_become_false_scores(self):
        rows=score(self.bundle())['cells']
        lookup={(r['dataset'],r['method']):r for r in rows}
        self.assertIsNone(lookup['c_briggsae','D_gpu']['metrics']['precision'])
        self.assertIsNone(lookup['c_briggsae','D_gpu']['metrics']['f1'])
        self.assertEqual(lookup['sim100','D_gpu']['metrics']['precision'],.75)
        self.assertAlmostEqual(lookup['sim100','D_gpu']['metrics']['f1'],2/3)
        self.assertIsNone(lookup['sim100','edta']['metrics'])
        self.assertEqual(lookup['sim100','edta']['status'],'TIMEOUT')

    def test_changed_counts_cannot_replay_as_valid(self):
        data=copy.deepcopy(self.bundle())
        data['datasets']['sim100']['blocks']['b1']['D_gpu']=[59,21,41,79]
        with self.assertRaisesRegex(ValueError,'differs'):score(data)


if __name__=='__main__':unittest.main()
