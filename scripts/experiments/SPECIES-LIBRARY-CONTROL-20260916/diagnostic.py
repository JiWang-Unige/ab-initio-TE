#!/usr/bin/env python3
"""Finite reference-library diagnostic; preserves historical labels and scores."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'outputs/SPECIES-LIBRARY-CONTROL-20260916/run-r1'
DATA = ROOT / 'outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202'
HISTORY = ROOT / 'software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617'
EVAL = ROOT / 'outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1'
SPECIES = ('zebrafish', 'pig', 'chicken')
TAXA = (7955, 9823, 9031)
CLASSES = ('LINE', 'SINE', 'LTR', 'DNA', 'RC', 'Retroposon')
sys.path.insert(0, str(ROOT / 'scripts/experiments/CROSS-SPECIES-L1-20260903'))
import calibrate_evaluate_x0 as ev


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def count(y, p, c):
    return dict(tp=int(np.sum(y & p & c)), fp=int(np.sum(~y & p & c)),
                fn=int(np.sum(y & ~p & c)), tn=int(np.sum(~y & ~p & c)),
                callable_bp=int(c.sum()))


def metric(c):
    t, f, n = (c[k] for k in ('tp', 'fp', 'fn'))
    return {**c, 'precision': t/(t+f) if t+f else None,
            'recall': t/(t+n) if t+n else None,
            'f1': 2*t/(2*t+f+n) if 2*t+f+n else None}


def fasta(path):
    records = {}
    name = None
    with open(path) as handle:
        for line in handle:
            if line.startswith('>'):
                name = line[1:].split()[0]
                if name in records:
                    raise ValueError('Duplicate library ID: ' + name)
                records[name] = ''
            elif name is not None:
                records[name] += line.strip().upper()
    return records


def raw_rows(path, wanted):
    opener = gzip.open if str(path).endswith('.gz') else open
    rows = defaultdict(list)
    with opener(path, 'rt') as handle:
        for line in handle:
            f = line.split()
            if len(f) < 11 or not f[0].isdigit() or f[4] not in wanted:
                continue
            rows[f[4]].append((int(f[5])-1, int(f[6]), f[10].split('/')[0]))
    return rows


def paint(rows, start, length=8192):
    """Inclusive RM ends were converted to half-open intervals in raw_rows."""
    bits = np.zeros(length, dtype=np.uint8)
    unknown = np.zeros(length, dtype=bool)
    for left, right, cls in rows:
        a, b = max(left, start)-start, min(right, start+length)-start
        if a >= b:
            continue
        if cls in CLASSES:
            bits[a:b] |= 1 << CLASSES.index(cls)
        elif cls.lower().startswith(('unknown', 'unclassified')):
            unknown[a:b] = True
    return bits, unknown


def grouped_records(species, split):
    groups = defaultdict(dict)
    for r in ev.read_jsonl(DATA / split / (species+'.jsonl.gz')):
        if r['species_code'] != species or r['split'] != split:
            raise ValueError('Record species/split mismatch')
        groups[r['tile_id']][int(r['half'])] = r
    return groups


def prepare():
    out = BASE / 'prepared'
    out.mkdir(parents=True, exist_ok=False)
    with (ROOT/'scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv').open() as f:
        sources = {r['species_code']: r for r in csv.DictReader(f, delimiter='\t') if r['species_code'] in SPECIES}
    runtime = json.loads((ROOT/'configs/TE-LONG-BENCH-20260915.json').read_text())['runtimes']
    fm = [sys.executable, str(ROOT/runtime['famdb_cli']), '-i', str(ROOT/runtime['famdb3'])]
    records = []
    sys.path.insert(0, str(ROOT/'scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915'))
    from control import fasta_records
    for species, taxid in zip(SPECIES, TAXA):
        dest = out/species
        dest.mkdir()
        groups = grouped_records(species, 'DEV')
        if len(groups) != 500:
            raise ValueError('Expected 500 original DEV tiles')
        source = sources[species]
        genome = fasta_records(Path(source['fasta']), {h[0]['chrom'] for h in groups.values()})
        panel = []
        with (dest/'panel.fa').open('w') as fa:
            for i, (tile_id, halves) in enumerate(sorted(groups.items())):
                a, b = halves[0], halves[1]
                chrom, start, end = a['chrom'], int(a['start']), int(b['end'])
                left, right = max(0,start-4096), min(len(genome[chrom]),end+4096)
                seq = genome[chrom][left:right].upper()
                core = str(a['sequence']).upper()+str(b['sequence']).upper()
                if end-start != 8192 or seq[start-left:end-left] != core:
                    raise ValueError('Original sequence/coordinate mismatch: '+tile_id)
                q = f'tile{i:04d}'
                fa.write('>'+q+'\n'+seq+'\n')
                panel.append(dict(query=q,tile_id=tile_id,chrom=chrom,start=start,end=end,
                                  query_start=left,query_end=right,center_offset=start-left))
        del genome
        write(dest/'panel.json', panel)
        inventories = {}
        for arm in ('curated','combined'):
            cmd = fm+['families','-a','-d','-f','fasta_name','--include-class-in-name']
            if arm == 'curated':
                cmd += ['--curated']
            cmd += [str(taxid)]
            with (dest/(arm+'.fa')).open('w') as handle:
                p = subprocess.run(cmd,stdout=handle,stderr=subprocess.PIPE,text=True,check=True)
            (dest/(arm+'.stderr')).write_text(p.stderr)
            if 'absent related partitions' in p.stderr:
                raise ValueError('Missing target-related partitions')
            inventories[arm] = fasta(dest/(arm+'.fa'))
            if not inventories[arm]:
                raise ValueError('Empty library')
            write(dest/(arm+'-inventory.json'), dict(command=cmd,
                  records=[dict(id=k,length=len(v)) for k,v in inventories[arm].items()]))
        lo, hi = inventories['curated'], inventories['combined']
        if any(hi.get(k) != v for k,v in lo.items()):
            raise ValueError('Curated library is not an unchanged subset')
        identical = lo == hi
        if species == 'zebrafish' and not identical:
            raise ValueError('Expected empty zebrafish increment changed')
        probe = HISTORY/'specieslib_probe'/species/'repeatmasker_probe.log'
        (dest/'historical-probe-header.txt').write_text('\n'.join(probe.read_text().splitlines()[:25])+'\n')
        exposure = {}
        for split in ('TRAIN','CAL','DEV'):
            items = grouped_records(species,split)
            labels = ''.join(str(h[0]['labels'])+str(h[1]['labels']) for h in items.values())
            c = Counter(labels)
            exposure[split] = dict(tiles=len(items),positive_bp=c['1'],negative_bp=c['0']+c['H'],unknown_bp=c['?'])
        records.append(dict(species=species,taxid=taxid,tiles=len(panel),
                            curated_records=len(lo),combined_records=len(hi),
                            added_records=len(set(hi)-set(lo)),identical_libraries=identical,
                            exposure=exposure,source=source))
    write(out/'complete.json', dict(status='PREPARED',species=records,
          historical_invocation='species curated, multistage',new_invocation='explicit consensus libraries; both arms identical settings'))


def replay():
    out = BASE/'replay'
    out.mkdir(parents=True,exist_ok=False)
    modeldir = ROOT/'outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model'
    model, tokenizer, device = ev.load_final_model(modeldir,None,False,ROOT/'.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species')
    if device.type != 'cuda':
        raise RuntimeError('GPU replay requires CUDA')
    cal = json.loads((EVAL/'calibration.json').read_text())
    expected = json.loads((EVAL/'dev_metrics.json').read_text())['per_species']
    results = []
    for species in SPECIES:
        tiles = ev.infer_inputs(model,tokenizer,device,[(species,DATA/'DEV'/(species+'.jsonl.gz'))],12)[species]
        margins = np.stack([t['margin'] for t in tiles])
        y = np.stack([t['truth'] for t in tiles]); c = np.stack([t['callable'] for t in tiles])
        # Preserve the original evaluator's float32 affine operation, followed
        # by ev.sigmoid's float64 conversion; do not move that conversion.
        p = ev.sigmoid(cal['platt_slope']*margins+cal['platt_intercept']) >= cal['threshold']
        got = count(y,p,c)
        want = {k:expected[species]['bp_'+k] for k in ('tp','fp','fn')}
        ok = all(got[k] == v for k,v in want.items()) and got['callable_bp']==expected[species]['callable_bp']
        np.savez_compressed(out/(species+'.npz'),predicted=p,truth=y,callable=c,
                            tile_id=np.array([t['tile_id'] for t in tiles]))
        results.append(dict(species=species,counts=got,expected=want,exact_counts_match=ok))
        write(out/'progress.json',results)
        if not ok:
            raise ValueError('Historical count mismatch; scoring blocked: '+species)
    write(out/'complete.json', dict(status='COUNT_REPRODUCED',model_dir=str(modeldir),calibration=cal,
                                   pointwise_identity_unverifiable_without_original_cache=True,species=results))


def annotate(index):
    if not (BASE/'prepared/complete.json').exists():
        raise RuntimeError('Preparation incomplete')
    species = SPECIES[index//2]; arm = ('curated','combined')[index%2]
    out = BASE/'annotation'/species/arm
    out.mkdir(parents=True,exist_ok=False)
    source = BASE/'prepared'/species
    cmd = ['RepeatMasker','-pa','4','-xsmall','-gff','-lib',str(source/(arm+'.fa')),
           '-dir',str(out),str(source/'panel.fa')]
    started = time.monotonic()
    with (out/'stdout.log').open('w') as stdout, (out/'stderr.log').open('w') as stderr:
        p = subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=6900)
    record = dict(command=cmd,exit_code=p.returncode,seconds=time.monotonic()-started,
                  job_id=os.environ.get('SLURM_JOB_ID'))
    write(out/'attempt.json',record)
    p.check_returncode()
    if not (out/'panel.fa.out').exists() or 'RepeatMasker version 4.2.2' not in (out/'stdout.log').read_text():
        raise RuntimeError('Native output/version qualification failed')
    write(out/'complete.json',dict(status='COMPLETED',**record))


def score():
    replay_status = json.loads((BASE/'replay/complete.json').read_text())
    prep = json.loads((BASE/'prepared/complete.json').read_text())
    if replay_status['status'] != 'COUNT_REPRODUCED':
        raise RuntimeError('Unqualified replay')
    out = BASE/'score'; out.mkdir(exist_ok=False)
    results = []
    for source in prep['species']:
        s = source['species']; panel = json.loads((BASE/'prepared'/s/'panel.json').read_text())
        d = np.load(BASE/'replay'/(s+'.npz'),allow_pickle=False)
        if list(d['tile_id']) != [r['tile_id'] for r in panel]:
            raise ValueError('Prediction/query alignment mismatch')
        p, old, c = d['predicted'], d['truth'], d['callable']
        old_rows = raw_rows(source['source']['self_out'],{r['chrom'] for r in panel})
        old_bits = np.stack([paint(old_rows[r['chrom']],r['start'])[0] for r in panel])
        if not np.array_equal((old_bits>0)&c,old&c):
            raise ValueError('Old raw annotation does not reproduce original material labels')
        arms = {}; unknowns = {}; masks = {}; class_masks = {}
        for arm in ('curated','combined'):
            dest = BASE/'annotation'/s/arm
            status = json.loads((dest/'complete.json').read_text())
            if status['status'] != 'COMPLETED':
                raise ValueError('Native cell incomplete')
            table = (dest/'panel.fa.tbl').read_text()
            seq_match = re.search(r'sequences:\s*(\d+)',table)
            len_match = re.search(r'total length:\s*(\d+)',table)
            expected_bp = sum(r['query_end']-r['query_start'] for r in panel)
            if not seq_match or not len_match or int(seq_match[1]) != 500 or int(len_match[1]) != expected_bp:
                raise ValueError('Native RepeatMasker denominator incomplete')
            rows = raw_rows(dest/'panel.fa.out',{r['query'] for r in panel})
            painted = [paint(rows[r['query']],r['center_offset']) for r in panel]
            bits = np.stack([v[0] for v in painted]); u = np.stack([v[1] for v in painted])
            masks[arm] = bits>0; unknowns[arm] = u & (bits==0); class_masks[arm] = bits
            arms[arm] = metric(count(bits>0,p,c))
        lo, hi = masks['curated'], masks['combined']
        added, lost = ~lo & hi & c, lo & ~hi & c
        classes = {}
        for i,cl in enumerate(CLASSES):
            m = (old_bits==(1<<i))&c
            positive=int(m.sum()); tp=int((m&p).sum())
            classes[cl] = dict(positive_bp=positive,tp=tp,fn=positive-tp,recall=tp/positive if positive else None)
        mixed = (old_bits>0)&((old_bits & (old_bits-1))>0)&c
        code = class_masks['curated'].astype(np.uint16)*64+class_masks['combined']
        transitions = [dict(curated_classes=[cl for j,cl in enumerate(CLASSES) if (int(k)//64)&(1<<j)],
                            combined_classes=[cl for j,cl in enumerate(CLASSES) if (int(k)%64)&(1<<j)],bp=int(n))
                       for k,n in zip(*np.unique(code[c],return_counts=True))]
        tile_rows=[]
        for i,r in enumerate(panel):
            tile_rows.append(dict(tile_id=r['tile_id'],chrom=r['chrom'],block512kb=r['start']//524288,
                old=count(old[i],p[i],c[i]),curated=count(lo[i],p[i],c[i]),combined=count(hi[i],p[i],c[i]),
                added_predicted_positive=int((added[i]&p[i]).sum()),added_predicted_negative=int((added[i]&~p[i]).sum())))
        write(out/(s+'-blocks.json'),tile_rows)
        record=dict(species=s,old=metric(count(old,p,c)),arms=arms,
                    added_predicted_positive=int((added&p).sum()),added_predicted_negative=int((added&~p).sum()),
                    lost_predicted_positive=int((lost&p).sum()),lost_predicted_negative=int((lost&~p).sum()),
                    old_positive_missing_from_curated=int((old&~lo&c).sum()),new_curated_positive_vs_old=int((~old&lo&c).sum()),
                    unknown_bp={k:int((v&c).sum()) for k,v in unknowns.items()},
                    class_membership_transitions=transitions,
                    original_exclusive_class_recall=classes,mixed_class_positive_bp=int(mixed.sum()))
        if source['identical_libraries'] and not np.array_equal(lo,hi):
            raise ValueError('Identical-library control produced different strict labels')
        results.append(record)
    write(out/'result.json',dict(status='COMPLETED',scope='Retrospective comparator sensitivity, not biological truth',
                                original_scores_overwritten=False,protocol='SPECIES-LIBRARY-CONTROL-20260916',species=results))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','replay','annotate','score'])
    parser.add_argument('--index',type=int,choices=range(6))
    args=parser.parse_args()
    if args.stage=='annotate': annotate(args.index)
    else: globals()[args.stage]()
