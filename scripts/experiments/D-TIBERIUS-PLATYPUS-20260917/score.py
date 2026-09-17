#!/usr/bin/env python3
"""Score all fixed D cores with the qualified, identical historical controls."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from run_core import ROOT, OLD, BASE, module

MODES=('D','U_soft','U_nosm','R_TE','R_all','P')


def bootstrap(rows,control):
    chroms=sorted({r['chrom'] for r in rows})
    grouped={c:{m:Counter() for m in ('D',control)} for c in chroms}
    for row in rows:
        for mode in ('D',control):
            grouped[row['chrom']][mode].update({k:row['metrics'][mode][k] for k in ('tp','fp','fn')})
    rng=np.random.default_rng(42);values=[]
    def f1(c):
        den=2*c['tp']+c['fp']+c['fn'];return 2*c['tp']/den if den else None
    for _ in range(10000):
        counts={m:Counter() for m in ('D',control)}
        for i in rng.integers(0,len(chroms),len(chroms)):
            for mode in counts: counts[mode].update(grouped[chroms[i]][mode])
        a,b=f1(counts['D']),f1(counts[control])
        if a is not None and b is not None:values.append(a-b)
    return {'unit':'chromosome; paired cores','clusters':len(chroms),'replicates':10000,
            'valid_replicates':len(values),'seed':42,'ci95':np.quantile(values,[.025,.975]).tolist() if values else None}


def main():
    base=module(ROOT/'scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py','D_utility_score')
    prep=OLD/'prepared/platypus';geometry=json.loads((prep/'geometry.json').read_text())
    if len(geometry)!=20:raise ValueError('Fixed 20-core denominator changed')
    # Establish full completion before looking at new accuracy.
    for core in geometry:
        for folder in (BASE/'run/platypus'/core['id'],OLD/'run-r1/platypus'/core['id']):
            status=json.loads((folder/'status.json').read_text())
            if status['status']!='COMPLETED' or status['core']!=core:
                raise ValueError('Incomplete or mismatched paired cell: '+str(folder))
    reference=json.loads((prep/'reference.json').read_text())
    units={u['unit_id']:u for u in reference['units']};mapping={}
    for uid,unit in units.items():
        for iso in unit['isoforms']:
            key=(unit['chrom'],unit['strand'],tuple(map(tuple,iso['intervals'])))
            if key in mapping and mapping[key]!=uid:raise ValueError('Ambiguous reference chain')
            mapping[key]=uid
    totals={m:Counter() for m in MODES};correct={m:set() for m in MODES};rows=[]
    for core in geometry:
        c=base.Core(**{k:core[k] for k in ('chrom','index','start','end','halo_start','halo_end')})
        truth={uid for uid,u in units.items() if u['core_id']==core['id']}
        row={'id':core['id'],'chrom':core['chrom'],'reference_loci':len(truth),'metrics':{}}
        for mode in MODES:
            cell=(BASE/'run/platypus' if mode=='D' else OLD/'run-r1/platypus')/core['id']
            inputs=json.loads((cell/'input.json').read_text())
            obs=json.loads((cell/(mode+'.observation.json')).read_text())
            if not inputs['same_uppercase_letters'] or not obs['passed'] or not obs['model_calls']:
                raise ValueError('Input qualification missing')
            a,ac=base.parse_predictions(cell/(mode+'.gtf'),c,'gtf')
            b,bc=base.parse_predictions(cell/(mode+'.gff3'),c,'gff3')
            if a!=b or ac!=bc:raise ValueError('Native GTF/GFF3 disagree')
            matched={chain for chain in a if (core['chrom'],chain.strand,chain.intervals) in mapping}
            found={mapping[(core['chrom'],chain.strand,chain.intervals)] for chain in matched}
            if not found<=truth:raise ValueError('Reference locus assigned to wrong core')
            metrics=base.metrics(len(found),len(a-matched),len(truth-found))
            row['metrics'][mode]=metrics;correct[mode].update(found)
            totals[mode].update({k:metrics[k] for k in ('tp','fp','fn')})
        rows.append(row)
    expected=json.loads((Path(__file__).with_name('expected_controls.json')).read_text())
    if len(units)!=expected['reference_loci']:
        raise ValueError('Reference denominator differs from frozen historical controls')
    for mode,counts in expected['metrics'].items():
        if any(totals[mode][key]!=value for key,value in counts.items()):
            raise ValueError('Reused control counts differ from the completed frozen result: '+mode)
    metrics={m:base.metrics(**totals[m]) for m in MODES};comparisons={}
    for control in MODES[1:]:
        gain=correct['D']-correct[control];loss=correct[control]-correct['D']
        fraction=len(loss)/len(correct[control]) if correct[control] else None
        comparisons['D_minus_'+control]={'f1_delta':metrics['D']['f1']-metrics[control]['f1'],
            'gained_loci':sorted(gain),'lost_loci':sorted(loss),'lost_correct_fraction':fraction,
            'loss_above_one_percent':fraction>.01 if fraction is not None else None,'bootstrap':bootstrap(rows,control)}
    result={'protocol':'D-TIBERIUS-PLATYPUS-20260917','status':'COMPLETED','species':'platypus',
            'scope':'Retrospective fixed 20-core extension; reference-relative locus utility, not independent biological truth',
            'new_D_cells':20,'reused_control_cells':100,'reference_loci':len(units),
            'reference_exclusions':reference['excluded'],'primary_comparison':'D_minus_R_TE',
            'flow_comparison':'D_minus_U_nosm','metrics':metrics,'comparisons':comparisons,'per_core':rows,
            'correct_loci':{m:sorted(v) for m,v in correct.items()}}
    out=BASE/'run/result.json'
    with out.open('x') as handle:json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')
    print(json.dumps({'status':'COMPLETED','metrics':metrics,'delta':{k:v['f1_delta'] for k,v in comparisons.items()}}))


if __name__=='__main__':main()
