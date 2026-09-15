#!/usr/bin/env python3
"""Recompute long-benchmark totals from validated per-block sufficient statistics.

Native annotations and coordinate-to-count extraction run on Slurm. Omni
recomputes these compact metric totals; its timing is never native runtime.
"""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def metrics(counts,synthetic):
    tp,fp,fn,tn=counts
    d={'reference_positive_bp':tp+fn,'predicted_bp':tp+fp,'overlap_bp':tp,
       'reference_positive_recall':tp/(tp+fn) if tp+fn else None,
       'prediction_outside_reference_bp':fp,'precision':None,'f1':None}
    if synthetic:
        d.update(tp=tp,fp=fp,fn=fn,tn=tn,recall=d['reference_positive_recall'],
                 precision=tp/(tp+fp) if tp+fp else None,
                 f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
    return d


def score(bundle):
    cells=[]
    for dataset,paths in bundle['attempts']['datasets'].items():
        observed=bundle['datasets'][dataset]
        for method,path in paths.items():
            status=observed['statuses'][method]
            values=None
            if status['status']=='COMPLETED':
                counts=[sum(block[method][i] for block in observed['blocks'].values()) for i in range(4)]
                if sum(counts)!=observed['callable_evaluation_bp']:
                    raise ValueError('per-block counts do not recover callable denominator')
                values=metrics(counts,dataset=='sim100')
                source=observed['metrics'][method]
                for key,value in values.items():
                    old=source[key]
                    if (value is None)!=(old is None) or (value is not None and not math.isclose(value,old,rel_tol=1e-12,abs_tol=1e-12)):
                        raise ValueError(f'native extraction/Omni total differs: {dataset}/{method}/{key}')
            cells.append({'cell_id':dataset+'|'+method,'dataset':dataset,'method':method,
                          'status':status['status'],'metrics':values,'source_attempt':path,
                          'native_wall_seconds':status.get('wall_seconds'),
                          'native_steps':status.get('steps'),'native_hardware':{
                              k:status.get(k) for k in ('hostname','cpu_model','accelerator','cpus','cpus_allocated')},
                          'failure_reason':status.get('failure_reason')})
    return {'protocol':'TE-LONG-BENCH-20260915','cells':cells,'expected_cells':14,
            'replay_scope':'Recompute metrics from Slurm-validated block counts, not native callers',
            'real_absolute_precision_f1':None,'L3_insertion_identity':None,
            'source_comparisons':{k:v.get('comparisons') for k,v in bundle['datasets'].items()},
            'source_engineering_attempts':bundle['attempts']['failed_engineering_attempts']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output_dir',type=Path,required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('--data.block_bundle',dest='bundle',type=Path)
    parser.add_argument('--metrics.score',dest='scores',type=Path,nargs='+')
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    if args.name=='bundle':
        path=Path(os.environ['TE_LONG_BENCH_RESULT'])
        bundle=json.loads(path.read_text())
        if bundle['protocol']!='TE-LONG-BENCH-20260915':raise ValueError('wrong benchmark bundle')
        write(args.output_dir/'block_bundle.json',bundle)
    elif args.name=='score':
        write(args.output_dir/'metrics.json',score(json.loads(args.bundle.read_text())))
    elif args.name=='summary':
        values=[json.loads(p.read_text()) for p in args.scores if p.is_file()]
        if len(values)!=1:raise ValueError('exactly one long-input metric collection required')
        result=values[0]
        if len(result['cells'])!=14:raise ValueError('incomplete planned cell denominator')
        result['status_counts']=dict(Counter(row['status'] for row in result['cells']))
        result['scored_cells']=sum(row['metrics'] is not None for row in result['cells'])
        write(args.output_dir/'collector_summary.json',result)
    else:raise ValueError('unknown Omni stage')


if __name__=='__main__':main()
