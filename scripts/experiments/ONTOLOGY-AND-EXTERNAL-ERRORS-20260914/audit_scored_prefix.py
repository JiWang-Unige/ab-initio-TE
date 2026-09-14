#!/usr/bin/env python3
"""Identify the actual legacy scored population, without loading a model."""
from collections import Counter
from pathlib import Path
import argparse
import gzip
import json

LABELS = ['bg', 'sine', 'line', 'ltr', 'dna', 'unknown']

def prefix_counts(path, limit):
    species, classes, chromosomes = Counter(), Counter(), Counter()
    with gzip.open(path, 'rt') as handle:
        for i, line in enumerate(handle):
            if i >= limit:
                break
            row = json.loads(line)
            species[row['species_code']] += 1
            classes.update(map(int,row['labels'][:4096]))
            chrom = row.get('chrom',row.get('seqid','unrecorded'))
            chromosomes[f"{row['species_code']}:{chrom}"] += 1
    return {'windows':sum(species.values()),'species_windows':dict(species),
            'class_bp':{LABELS[k]:v for k,v in classes.items()},'chromosome_windows':dict(chromosomes)}

def run(root, output):
    data = root/'software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/data/animal_sf5_w4096'
    runs = root/'software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/runs'
    records={}
    for name in ['SF5_base_pretrained_seed42','SF5_binary_h0_seed42']:
        meta=json.loads((runs/name/'training_meta.json').read_text())
        metrics=json.loads((runs/name/'test_results.json').read_text())
        n=meta['max_eval_samples']
        test=prefix_counts(data/'test/data.jsonl.gz',n)
        val=prefix_counts(data/'val/data.jsonl.gz',n)
        test['legacy_support_matches'] = all(test['class_bp'].get(label,0)==metrics[label+'_support'] for label in LABELS)
        if not test['legacy_support_matches'] or test['windows']!=metrics['n_windows']:
            raise ValueError('legacy scored prefix cannot be reconstructed')
        records[name]={'limit':n,'val':val,'test':test}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'status':'EXACT_LEGACY_DENOMINATOR_REPLAY',
        'scope':'existing scored rows only; no prediction, threshold change, or new held-out evaluation',
        'runs':records},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
