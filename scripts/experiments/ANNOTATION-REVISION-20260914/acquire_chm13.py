#!/usr/bin/env python3
"""Acquire documented annotation and chain assets; do not score or read label rows."""
import argparse
import json
from pathlib import Path
from qualify_mm10 import fetch

BASE='https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/'
FILES={
 'chm13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out': BASE+'annotation/chm13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out',
 'hg19-chm13v2.chain': BASE+'chain/v1_nflo/hg19-chm13v2.chain',
 'chm13v2-hg19.chain': BASE+'chain/v1_nflo/chm13v2-hg19.chain',
 'grch38-chm13v2.chain': BASE+'chain/v1_nflo/grch38-chm13v2.chain',
 'chm13v2-grch38.chain': BASE+'chain/v1_nflo/chm13v2-grch38.chain',
}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 evidence=[]
 for name,url in FILES.items():
  evidence.append(fetch(url,a.output/name))
  (a.output/'acquisition.json').write_text(json.dumps(evidence,indent=2)+'\n')
 result=dict(status='ASSETS_ACQUIRED_NOT_EVALUATED',sources=evidence,
             annotation_generation='RepeatMasker 4.1.2p1 2022Apr14 CHM13v2.0',
             library_engine_joint_change=True,label_rows_read=False,
             note='Future evaluation restricted to mapped allowed hg19 chr2/3/4 panel. Exclude mappings into chr19-22 counterparts. Acquisition is not FP validation.')
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
