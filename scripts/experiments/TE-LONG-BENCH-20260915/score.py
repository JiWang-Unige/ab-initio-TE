#!/usr/bin/env python3
"""Score known synthetic material separately from real reference-positive recovery."""
import argparse
from collections import defaultdict
import csv
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import numpy as np
from qualify_simulation import fasta, te_status

ROOT=Path(__file__).resolve().parents[3]


def job_states(jobs):
    """Slurm terminal failures must remain in the planned benchmark denominator."""
    output=subprocess.check_output(['sacct','-n','-P','-j',','.join(sorted(set(jobs))),
        '--format=JobID%40,State,ExitCode,Elapsed,MaxRSS'],text=True)
    rows={}
    for line in output.splitlines():
        fields=line.split('|')
        if len(fields)>=5 and fields[0] in jobs:
            rows[fields[0]]=dict(zip(('state','exit_code','elapsed','max_rss'),fields[1:5]))
    return rows


def reconcile(status,slurm):
    result=dict(status,slurm=slurm)
    state=slurm.get('state','UNKNOWN').split()[0].rstrip('+')
    if status.get('status')!='COMPLETED':
        if state in {'FAILED','TIMEOUT','OUT_OF_MEMORY','CANCELLED','NODE_FAIL','PREEMPTED','BOOT_FAIL'}:
            result.update(status=state,failure_reason=status.get('failure_reason',f'Slurm {state}'))
        elif state=='COMPLETED' and status.get('status') not in {'FAILED','TIMEOUT'}:
            result.update(status='FAILED_OUTPUT_MISSING',failure_reason='Slurm completed without qualified complete output')
    return result


def canonical(path):
    groups=defaultdict(list)
    with path.open() as handle:
        for row in csv.DictReader(handle,delimiter='\t'):
            # Binary TE calls retain unclassified candidates; hard non-TE
            # repeat/RNA classes are removed consistently where reported.
            match=re.search(r'(?:class_family|Classification|classification)=([^;]+)',row['attributes'])
            if match and te_status(match[1])=='NON_TE':continue
            groups[row['seqid']].append((int(row['start']),int(row['end'])))
    return groups


def truth(dataset,config):
    groups=defaultdict(list);excluded=defaultdict(list)
    if dataset=='sim100':
        with (ROOT/config['truth']).open() as handle:
            for row in csv.DictReader(handle,delimiter='\t'):
                pair=(int(row['start']),int(row['end']))
                if row['truth_status']=='TE':groups[row['seqid']].append(pair)
                elif row['truth_status']=='UNRESOLVED':excluded[row['seqid']].append(pair)
    else:
        spec=importlib.util.spec_from_file_location('long_score_adapter',ROOT/'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')
        adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
        for row in adapter.parse_repeatmasker_out(ROOT/config['label_out']):
            kind=row['attributes'].split('class_family=',1)[1]
            if '?' not in kind and te_status(kind)=='TE':
                groups[row['seqid']].append((row['start'],row['end']))
    return groups,excluded


def mask(intervals,length):
    values=np.zeros(length,dtype=bool)
    for left,right in intervals:
        if not 0<=left<right<=length:raise ValueError('interval outside common input coordinates')
        values[left:right]=True
    return values


def metric(counts,synthetic):
    tp,fp,fn,tn=map(int,counts)
    recall=tp/(tp+fn) if tp+fn else None
    result={'reference_positive_bp':tp+fn,'predicted_bp':tp+fp,'overlap_bp':tp,
            'reference_positive_recall':recall,'prediction_outside_reference_bp':fp}
    if synthetic:
        result.update(tp=tp,fp=fp,fn=fn,tn=tn,precision=tp/(tp+fp) if tp+fp else None,
                      recall=recall,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
    else:
        result.update(precision=None,f1=None,interpretation='reference-positive recovery; unlabelled sequence is not biological negative truth')
    return result


def interval_difference(blocks,left,right,synthetic):
    keys=sorted(blocks)
    a=np.array([blocks[k][left] for k in keys]);b=np.array([blocks[k][right] for k in keys])
    rng=np.random.default_rng(42);deltas=[]
    def value(c):
        tp,fp,fn,_=c
        denominator=(2*tp+fp+fn) if synthetic else (tp+fn)
        return (2*tp if synthetic else tp)/denominator if denominator else None
    for _ in range(10000):
        sample=rng.integers(0,len(keys),len(keys));x,y=value(a[sample].sum(axis=0)),value(b[sample].sum(axis=0))
        if x is not None and y is not None:deltas.append(x-y)
    x,y=value(a.sum(axis=0)),value(b.sum(axis=0))
    return {'metric':'synthetic_bp_f1' if synthetic else 'reference_positive_recall',
            'delta':x-y if x is not None and y is not None else None,
            'ci95':np.quantile(deltas,[.025,.975]).tolist() if deltas else None,
            'resampling_units':len(keys),'unit':'1Mb synthetic blocks' if synthetic else 'large assembly sequences; small scaffolds grouped',
            'replicates':10000,'valid_replicates':len(deltas),'seed':42,
            'scope':'within this input; no across-species uncertainty claim'}


def score(output):
    cfg=json.loads((ROOT/'configs/TE-LONG-BENCH-20260915.json').read_text())
    attempts=json.loads((ROOT/'configs/TE-LONG-BENCH-20260915-attempts.json').read_text())
    result={'protocol':cfg['protocol'],'status':'PARTIAL','datasets':{},'attempts':attempts,
            'L3_insertion_identity':None,'failed_cells_are_not_zero_scores':True}
    states_by_job=job_states([job for values in attempts['slurm_jobs'].values() for job in values.values()])
    all_complete=True;all_terminal=True
    for dataset,sources in attempts['datasets'].items():
        config=cfg['datasets'][dataset];synthetic=dataset=='sim100';states={};predictions={}
        for method,path in sources.items():
            p=ROOT/path/'status.json'
            status=json.loads(p.read_text()) if p.exists() else {'status':'NOT_AVAILABLE'}
            status=reconcile(status,states_by_job.get(attempts['slurm_jobs'][dataset][method],{}))
            states[method]=status
            if status.get('status')=='COMPLETED':
                predictions[method]=canonical(ROOT/path/'predictions.tsv')
            else:
                all_complete=False
                if status['status'] not in {'FAILED','TIMEOUT','OUT_OF_MEMORY','CANCELLED','NODE_FAIL',
                                            'PREEMPTED','BOOT_FAIL','FAILED_OUTPUT_MISSING'}:all_terminal=False
        if not predictions:
            result['datasets'][dataset]={'statuses':states,'scored_methods':0};continue
        known,excluded=truth(dataset,config)
        totals={m:np.zeros(4,dtype=np.int64) for m in predictions};blocks=defaultdict(dict)
        sequence_names=set();denominator=0
        for name,seq in fasta(ROOT/config['input']):
            sequence_names.add(name)
            valid=np.frombuffer(seq.encode('ascii'),dtype=np.uint8)!=ord('N')
            valid &= ~mask(excluded.get(name,[]),len(seq))
            reference=mask(known.get(name,[]),len(seq))
            denominator+=int(valid.sum())
            for method,groups in predictions.items():
                called=mask(groups.get(name,[]),len(seq))
                for start in range(0,len(seq),1000000 if synthetic else len(seq)):
                    end=min(start+1000000,len(seq)) if synthetic else len(seq)
                    v=valid[start:end];p=called[start:end];t=reference[start:end]
                    counts=np.array([np.count_nonzero(v&p&t),np.count_nonzero(v&p&~t),
                                     np.count_nonzero(v&~p&t),np.count_nonzero(v&~p&~t)],dtype=np.int64)
                    totals[method]+=counts
                    key=f'{name}:{start}' if synthetic else (name if len(seq)>=1000000 else 'small_scaffolds')
                    blocks[key].setdefault(method,np.zeros(4,dtype=np.int64));blocks[key][method]+=counts
        for groups in [known,excluded,*predictions.values()]:
            if set(groups)-sequence_names:raise ValueError('annotation seqids outside common input')
        comparisons={}
        if 'D_gpu' in predictions:
            for method in predictions:
                if method!='D_gpu':comparisons['D_gpu_minus_'+method]=interval_difference(blocks,'D_gpu',method,synthetic)
        result['datasets'][dataset]={'statuses':states,'scored_methods':len(predictions),'callable_evaluation_bp':denominator,
            'metrics':{m:metric(v,synthetic) for m,v in totals.items()},'comparisons':comparisons,
            'blocks':{k:{m:v.tolist() for m,v in d.items()} for k,d in blocks.items()},
            'scope':config['scope'],'truth_source':config.get('truth',config.get('label_out'))}
    if all_complete:result['status']='ALL_CELLS_COMPLETED'
    elif all_terminal:result['status']='ALL_CELLS_TERMINAL_WITH_FAILURES'
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'scored':{k:v['scored_methods'] for k,v in result['datasets'].items()}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);score(parser.parse_args().output)
