"""Check exact prototype identity and union coverage used in exposure claims."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('exposure',Path(__file__).with_name('library_exposure.py'))
exposure=importlib.util.module_from_spec(spec)
spec.loader.exec_module(exposure)


class ExposureTests(unittest.TestCase):
    def test_exact_mapping_keeps_ambiguity_and_merges_by_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            q=root/'qualification.json';q.write_text(json.dumps({'families':{'A':3,'B':1,'C':1,'D':1}}))
            e=root/'source.embl'
            e.write_text('ID   DF000001;\nAC   DF000001;\nNM   A\n//\n'
                         'ID   DF000002;\nAC   DF000002;\nNM   B\n//\n'
                         'ID   DF000003;\nAC   DF000003;\nNM   B\n//\n'
                         'ID   DF000004;\nAC   DF000004;\nNM   C\n//\n')
            library=root/'library.fa';library.write_text('>DF000001.4#DNA name=A\nACGT\n')
            truth=root/'truth.tsv'
            truth.write_text('seqid\tstart\tend\tfamily\ttruth_status\n'
                             's1\t0\t10\tA\tTE\n'
                             's1\t5\t15\tA\tTE\n'
                             's2\t0\t4\tA\tNON_TE\n')
            exposure.run(q,e,library,truth,root/'out')
            result=json.loads((root/'out/library_exposure_summary.json').read_text())
            m=result['mapping']
            self.assertEqual(m['matched_family_count'],1)
            self.assertEqual(m['ambiguous_family_count'],1)
            self.assertEqual(m['unmatched_family_count'],1)
            self.assertEqual(m['dfam_exact_but_rm_missing_family_count'],1)
            self.assertEqual(m['matched_generated_raw_fragment_bp'],24)
            self.assertEqual(m['matched_generated_union_bp'],19)
            self.assertEqual(m['matched_generated_te_union_bp'],15)


if __name__=='__main__':unittest.main()
