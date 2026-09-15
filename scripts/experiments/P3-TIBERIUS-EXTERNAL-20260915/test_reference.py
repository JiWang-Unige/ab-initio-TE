import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('external_prepare',Path(__file__).with_name('prepare.py'))
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class ReferenceCoordinates(unittest.TestCase):
    def test_strand_coordinate_partial_and_duplicate_locus_rules(self):
        core={'id':'c00','chrom':'NC_TEST.1','start':0,'end':100,'halo_start':0,'halo_end':120}
        seq=list('C'*120)
        seq[10:19]=list('ATGAAATAA')
        seq[50:59]=list('TTATTTCAT')
        seq[80:89]=list('ATGAAATAA')
        rows=[]
        for gid,tid,start,end,strand,extra in (
            ('g1','t1',11,19,'+',''),('g2','t2',51,59,'-',''),('g3','t3',81,89,'+',';partial=true')):
            rows.extend([
                f'NC_TEST.1\tRefSeq\tgene\t{start}\t{end}\t.\t{strand}\t.\tID={gid};Name={gid}',
                f'NC_TEST.1\tRefSeq\tmRNA\t{start}\t{end}\t.\t{strand}\t.\tID={tid};Parent={gid};transcript_id=NM_{tid}{extra}',
                f'NC_TEST.1\tRefSeq\tCDS\t{start}\t{end}\t.\t{strand}\t0\tParent={tid}',
            ])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ref.gff.gz'
            with gzip.open(path,'wt') as handle:handle.write('\n'.join(rows)+'\n')
            report=prepare.reference(path,[core],{'c00':''.join(seq)})
            self.assertEqual(report['unit_count'],2)
            self.assertEqual(report['excluded']['partial_or_exception'],1)
            by_id={u['unit_id']:u for u in report['units']}
            self.assertEqual(by_id['g1']['isoforms'][0]['intervals'],[(10,19)])
            self.assertEqual(by_id['g2']['isoforms'][0]['intervals'],[(50,59)])
            self.assertEqual(by_id['g2']['strand'],'-')
            # Two different gene IDs sharing one identical chain are ambiguous.
            duplicate=[r.replace('g1','g4').replace('t1','t4') for r in rows[:3]]
            with gzip.open(path,'wt') as handle:handle.write('\n'.join(rows+duplicate)+'\n')
            report=prepare.reference(path,[core],{'c00':''.join(seq)})
            self.assertEqual(report['unit_count'],1)
            self.assertEqual(report['excluded']['ambiguous_identical_chain_loci'],2)


if __name__=='__main__':unittest.main()
