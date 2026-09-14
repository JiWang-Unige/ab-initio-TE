import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('prep',Path(__file__).with_name('prepare.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
spec=importlib.util.spec_from_file_location('eval_check',Path(__file__).with_name('evaluate.py'));ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
class SplitTest(unittest.TestCase):
    def test_label_blind_sampling_is_reproducible_and_excludes_n_tiles(self):
        seq='ACGT'*4096+'N'*8192+'ACGT'*4096
        a,n=p.selected_starts(seq,3,8192,42,0.01)
        self.assertEqual(n,4);self.assertNotIn(16384,a)
        self.assertEqual(a,p.selected_starts(seq,3,8192,42,0.01)[0])
        self.assertEqual(len(set(a)),3)
    def test_same_chromosome_cannot_cross_roles(self):
        cfg={'tiles_by_split':{'TRAIN':{'chr1':1},'CAL':{'chr1':1}},'forbidden':['chr19']}
        with self.assertRaises(ValueError):p.role_map(cfg)
    def test_sealed_chromosome_rejected(self):
        cfg={'tiles_by_split':{'TRAIN':{'chr1':1},'EVAL':{'chr19':1}},'forbidden':['chr19']}
        with self.assertRaises(ValueError):p.role_map(cfg)
    def test_eval_rejects_duplicate_and_nonadjacent_halves(self):
        records=[dict(chrom='chr2',split='EVAL',assembly='hg19',species_code='human',
                      tile_id='test',half=h,start=4096*h,end=4096*(h+1),
                      sequence='A'*4096,labels='0'*4096) for h in (0,1)]
        ev.check_records(records,'chr2','EVAL',1)
        with self.assertRaises(ValueError):ev.check_records(records+[records[0]],'chr2','EVAL',1)
        records[1].update(start=8192,end=12288)
        with self.assertRaises(ValueError):ev.check_records(records,'chr2','EVAL',1)
    def test_eval_rejects_cross_split_records(self):
        records=[dict(chrom='chr2',split='TRAIN',assembly='hg19',species_code='human',
                      tile_id='test',half=h,start=4096*h,end=4096*(h+1),
                      sequence='A'*4096,labels='0'*4096) for h in (0,1)]
        with self.assertRaises(ValueError):ev.check_records(records,'chr2','EVAL',1)
    def test_old_state_freeze_retains_ignore_holes_and_all_denominators(self):
        tile=dict(chrom='chr2',start=100,end=107,tile_id='a',
                  truth=[1,1,0,0,0,0,0],callable=[1,1,1,0,1,1,1])
        rows=ev.old_state_intervals(tile,[.9,.1,.8,.9,.8,.1,.1],.5)
        self.assertEqual(rows,[('chr2',100,101,'TP',0,'.','a'),('chr2',101,102,'FN',0,'.','a'),
                               ('chr2',102,103,'FP',0,'.','a'),('chr2',104,105,'FP',0,'.','a'),
                               ('chr2',105,107,'TN',0,'.','a')])
    def test_old_state_freeze_rejects_truncated_probabilities(self):
        tile=dict(chrom='chr2',start=10,end=12,tile_id='a',truth=[0,1],callable=[1,1])
        with self.assertRaises(ValueError):ev.old_state_intervals(tile,[.5],.5)
if __name__=='__main__':unittest.main()
