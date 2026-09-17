#!/usr/bin/env python3
"""Paired context perturbation on exposed DEV, retaining frozen D calibration."""
import argparse
from collections import Counter, defaultdict
import gzip
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

SPECIES=('human','mouse','chicken','zebrafish','pig','c_elegans')


def runs(labels, value):
    start=None
    for i, char in enumerate(labels+'!'):
        if char==value and start is None: start=i
        elif char!=value and start is not None:
            yield start,i
            start=None


def dinuc(seq):
    return Counter(zip(seq,seq[1:]))


def shuffle_dinuc(seq, rng):
    if len(seq)<3: return seq
    graph=defaultdict(list)
    for left,right in zip(seq,seq[1:]): graph[left].append(right)
    for edges in graph.values(): rng.shuffle(edges)
    stack=[seq[0]]; path=[]
    while stack:
        if graph[stack[-1]]: stack.append(graph[stack[-1]].pop())
        else: path.append(stack.pop())
    output=''.join(reversed(path))
    if len(output)!=len(seq) or output[0]!=seq[0] or output[-1]!=seq[-1] or dinuc(output)!=dinuc(seq):
        raise ValueError('Dinucleotide shuffle broke the sequence contract')
    return output


def perturb(sequence, labels, value, seed):
    chars=list(sequence); rng=random.Random(seed)
    for start,end in runs(labels,value):
        if end-start>=16: chars[start:end]=shuffle_dinuc(sequence[start:end],rng)
    output=''.join(chars)
    if any(a!=b for a,b,label in zip(sequence,output,labels) if label!=value):
        raise ValueError('Perturbation changed a protected base')
    if Counter(output)!=Counter(sequence) or dinuc(output)!=dinuc(sequence):
        raise ValueError('Whole-window composition changed')
    return output


def interior_positions(labels):
    return [i for start,end in runs(labels,'1') for i in range(start+32,end-32)]


def select_records(path, species, count):
    selected=[]; seen=set(); scanned=0
    with gzip.open(path,'rt') as handle:
        for line in handle:
            scanned+=1; row=json.loads(line)
            seq,lab=row['sequence'].upper(),row['labels']
            if row['species_code']!=species or row['split']!='DEV':
                raise ValueError('Wrong source species or split')
            if len(seq)!=4096 or len(lab)!=4096: raise ValueError('Wrong window length')
            tile=row['tile_id']
            if tile in seen or set(seq)-set('ACGT'): continue
            if lab.count('1')<256 or lab.count('0')<256 or len(interior_positions(lab))<64: continue
            if sum(b-a for a,b in runs(lab,'0') if b-a>=16)<128: continue
            selected.append(row);seen.add(tile)
            if len(selected)==count: break
    if len(selected)!=count: raise ValueError(f'{species}: only {len(selected)} eligible windows')
    return selected,scanned


def module(path):
    spec=importlib.util.spec_from_file_location('context_fixed_D',path)
    value=importlib.util.module_from_spec(spec);sys.modules[spec.name]=value;spec.loader.exec_module(value)
    return value


def main(args):
    import numpy as np
    root=args.root.resolve(); out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((root/'scripts/experiments/D-EXTERNAL-RC0-20260914/config/panel.json').read_text())
    data=root/'outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV'
    records=[]; selection={}
    for species in SPECIES:
        rows,scanned=select_records(data/(species+'.jsonl.gz'),species,32)
        records.extend(rows);selection[species]={'scanned':scanned,'selected':len(rows),'tiles':[r['tile_id'] for r in rows]}
    (out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    rc0=module(root/'scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py')
    args.remote_root=root
    args.model_dir=args.tokenizer_dir=args.model_code_dir=args.calibration_json=None
    args.cpu=False
    started=time.monotonic()
    model,tokenizer,device,cal,load_seconds,paths=rc0._load_model(cfg,args)
    threshold=float(cal['threshold']); all_rows=[]
    for index,rec in enumerate(records):
        seq=rec['sequence'].upper(); labels=rec['labels']
        masks={'te':np.array([v=='1' for v in labels]),
               'te_interior':np.zeros(len(seq),dtype=bool),
               'bg':np.array([v=='0' for v in labels]),
               'hard_negative':np.array([v=='H' for v in labels])}
        masks['te_interior'][interior_positions(labels)]=True
        sequences={'native':seq,'bg_dinuc':perturb(seq,labels,'0',42+index*10),
                   'te_dinuc':perturb(seq,labels,'1',43+index*10)}
        # Concatenation retains exactly the existing 4096-bp inference boundaries.
        probs=rc0._infer_sequence(''.join(sequences.values()),model,tokenizer,device,3,
                                 float(cal['platt_slope']),float(cal['platt_intercept'])).reshape(3,4096)
        row={'species':rec['species_code'],'tile_id':rec['tile_id'],'half':rec.get('half'), 'arms':{}}
        for j,(name,altered) in enumerate(sequences.items()):
            p=probs[j]; stats={}
            for kind,mask in masks.items():
                n=int(mask.sum()); stats[kind]={'bp':n,'positive_bp':int((p[mask]>=threshold).sum()),
                    'mean_p':float(p[mask].mean()) if n else None,
                    'positive_fraction':float((p[mask]>=threshold).mean()) if n else None}
            row['arms'][name]={'changed_bp':sum(a!=b for a,b in zip(seq,altered)),'sites':stats}
        all_rows.append(row)
        if (index+1)%32==0: print(json.dumps({'completed_windows':index+1,'species':rec['species_code']}),flush=True)
    summary={}
    for species in SPECIES:
        items=[r for r in all_rows if r['species']==species]; result={}
        for arm in ('native','bg_dinuc','te_dinuc'):
            stats={}
            for kind in masks:
                n=sum(r['arms'][arm]['sites'][kind]['bp'] for r in items)
                positive=sum(r['arms'][arm]['sites'][kind]['positive_bp'] for r in items)
                weighted=sum((r['arms'][arm]['sites'][kind]['mean_p'] or 0)*r['arms'][arm]['sites'][kind]['bp'] for r in items)
                stats[kind]={'bp':n,'positive_fraction':positive/n if n else None,'mean_p':weighted/n if n else None}
            result[arm]=stats
        for arm in ('bg_dinuc','te_dinuc'):
            result[arm+'_minus_native']={kind:{metric:result[arm][kind][metric]-result['native'][kind][metric]
                for metric in ('positive_fraction','mean_p')} for kind in ('te','te_interior','bg')}
        summary[species]=result
    payload={'protocol':'D-CONTEXT-PAIR-20260917','status':'COMPLETED','model_paths':paths,'calibration':cal,
             'load_seconds':load_seconds,'wall_seconds':time.monotonic()-started,'windows':len(records),
             'no_training':True,'no_calibration_refit':True,'no_sealed_data':True,
             'interpretation':'Exposed DEV paired intervention, not independent generalization. TE-shuffled labels no longer establish biological truth.',
             'per_species':summary,'per_window':all_rows}
    (out/'result.json').write_text(json.dumps(payload,indent=2)+'\n')
    (out/'STATUS').write_text('COMPLETED\n')
    print(json.dumps({'status':'COMPLETED','output':str(out),'seconds':payload['wall_seconds']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
