#!/usr/bin/env python3
"""Stratify already-chosen pairs by strict exact ACGT sequence correspondence.

No rematching, model output selection or threshold fitting occurs. This adds
the necessary joint sequence-qualified view to the full descriptive result.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def read(path):
    with path.open() as handle:
        return list(csv.DictReader(handle,delimiter='\t'))

def exact(row,side):
    return row[f'{side}_sequence_status']=='SEQUENCE_EXACT' and int(row[f'{side}_source_non_acgt_count'])==0

def summarize(rows):
    n=len(rows)
    controls=Counter(r['control_mapping_id'] for r in rows)
    out={'pairs':n,'unique_controls':len(controls),'max_control_reuse':max(controls.values(),default=0),'support':{}}
    for category in ['TE','NONTE']:
        out['support'][category]={}
        for layer in ['any','ge50','ge80']:
            vals={side:sum(str(r[f'{side}_{category}_{layer}_supported']).lower() in ('true','1') for r in rows)
                  for side in ['fp','control']}
            out['support'][category][layer]={'fp_n':vals['fp'],'tn_n':vals['control'],
                'fp_fraction':vals['fp']/n if n else None,'tn_fraction':vals['control']/n if n else None,
                'difference':(vals['fp']-vals['control'])/n if n else None}
    return out

def run(root,output):
    base=root/'outputs/HG19-CHR1-REVISION-20260914-MATCHED'
    selected={r['fp_mapping_id']:r for r in read(base/'match-12708406/matched_controls.tsv') if r['match_status']=='MATCHED_TN'}
    joined=[r for r in read(base/'support-12708553/matched_support.tsv') if r['match_status']=='MATCHED_TN']
    strata={x:[] for x in ['both_exact_acgt','fp_only_exact_acgt','control_only_exact_acgt','neither_exact_acgt']}
    for row in joined:
        match=selected[row['fp_mapping_id']]
        if match['control_mapping_id']!=row['control_mapping_id']:
            raise ValueError('control changed after source-only selection')
        a,b=exact(match,'fp'),exact(match,'control')
        key='both_exact_acgt' if a and b else 'fp_only_exact_acgt' if a else 'control_only_exact_acgt' if b else 'neither_exact_acgt'
        strata[key].append(row)
    if len(joined)!=len(selected) or len(joined)!=18649:
        raise ValueError('matched-pair denominator changed')
    joint=strata['both_exact_acgt']
    result={'status':'COMPLETED_DESCRIPTIVE_SEQUENCE_STRATIFICATION','new_matching':False,
        'scope':'Same old source-only matched pairs; subset requires strict exact source-target ACGT sequences on both members.',
        'strata':{k:summarize(v) for k,v in strata.items()},
        'both_exact_by_relation':{k:summarize([r for r in joint if r['fp_old_te_relation']==k]) for k in ['ADJACENT','ISOLATED']},
        'enrichment_test':False,'corrected_f1':None,'biological_confirmation':False}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
