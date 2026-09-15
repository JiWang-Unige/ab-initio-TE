#!/usr/bin/env python3
"""Score only the complete fixed two-species, forty-core, five-arm experiment."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import numpy as np
from run_core import BASE, ROOT, MODES, module


def bootstrap(rows,left,right):
    chromosomes=sorted({r['chrom'] for r in rows})
    grouped={chrom:{m:Counter() for m in (left,right)} for chrom in chromosomes}
    for row in rows:
        for mode in (left,right):
            grouped[row['chrom']][mode].update({k:row['metrics'][mode][k] for k in ('tp','fp','fn')})
    rng=np.random.default_rng(42)
    values=[]
    def f1(c):
        denominator=2*c['tp']+c['fp']+c['fn']
        return 2*c['tp']/denominator if denominator else None
    for _ in range(10000):
        sums={m:Counter() for m in (left,right)}
        for index in rng.integers(0,len(chromosomes),len(chromosomes)):
            for mode in sums:sums[mode].update(grouped[chromosomes[index]][mode])
        a,b=f1(sums[left]),f1(sums[right])
        if a is not None and b is not None:values.append(a-b)
    return {'unit':'chromosome; both fixed cores resampled together','clusters':len(chromosomes),
            'replicates':10000,'valid_replicates':len(values),'seed':42,
            'ci95':np.quantile(values,[.025,.975]).tolist() if values else None}


def score():
    base=module(ROOT/'scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py','external_score_base')
    # Complete denominator is checked before any accuracy calculation.
    for species in ('cow','platypus'):
        for core in json.loads((BASE/'prepared'/species/'geometry.json').read_text()):
            path=BASE/'run-r1'/species/core['id']/'status.json'
            if not path.exists() or json.loads(path.read_text()).get('status')!='COMPLETED':
                raise ValueError(f'full 200-cell experiment not complete: {species}/{core["id"]}')
    result={'protocol':'P3-TIBERIUS-EXTERNAL-20260915','status':'COMPLETED','completed_cells':200,
            'scope':'two external mammals; assembly-matched annotation-relative locus/CDS-chain utility',
            'primary_comparison':'P_minus_R_TE','flow_comparison':'P_minus_U_nosm','species':{}}
    for species in ('cow','platypus'):
        prep=BASE/'prepared'/species
        refs=json.loads((prep/'reference.json').read_text())
        units={u['unit_id']:u for u in refs['units']}
        mapping={}
        for uid,unit in units.items():
            for iso in unit['isoforms']:
                key=(unit['chrom'],unit['strand'],tuple(map(tuple,iso['intervals'])))
                if key in mapping and mapping[key]!=uid:raise ValueError('ambiguous reference chain')
                mapping[key]=uid
        totals={m:Counter() for m in MODES};correct={m:set() for m in MODES};per_core=[]
        for core in json.loads((prep/'geometry.json').read_text()):
            cell=BASE/'run-r1'/species/core['id']
            c=base.Core(**{k:core[k] for k in ('chrom','index','start','end','halo_start','halo_end')})
            truth={u for u,v in units.items() if v['core_id']==core['id']}
            row={'id':core['id'],'chrom':core['chrom'],'reference_loci':len(truth),'metrics':{}}
            inp=json.loads((cell/'input.json').read_text())
            if not inp['same_uppercase_letters']:raise ValueError('invalid paired input')
            for mode in MODES:
                obs=json.loads((cell/(mode+'.observation.json')).read_text())
                if not obs['passed'] or not obs['model_calls']:raise ValueError('native model observation missing')
                a,ac=base.parse_predictions(cell/(mode+'.gtf'),c,'gtf')
                b,bc=base.parse_predictions(cell/(mode+'.gff3'),c,'gff3')
                if a!=b or ac!=bc:raise ValueError('GTF/GFF3 disagree')
                matched={chain for chain in a if (core['chrom'],chain.strand,chain.intervals) in mapping}
                found={mapping[(core['chrom'],chain.strand,chain.intervals)] for chain in matched}
                if not found<=truth:raise ValueError('reference locus scored in wrong core')
                values=base.metrics(len(found),len(a-matched),len(truth-found))
                totals[mode].update({k:values[k] for k in ('tp','fp','fn')})
                correct[mode].update(found);row['metrics'][mode]=values
            per_core.append(row)
        metrics={m:base.metrics(**totals[m]) for m in MODES}
        comparisons={}
        for control in ('U_nosm','U_soft','R_TE','R_all'):
            lost=correct[control]-correct['P'];gained=correct['P']-correct[control]
            fraction=len(lost)/len(correct[control]) if correct[control] else None
            comparisons['P_minus_'+control]={'f1_delta':metrics['P']['f1']-metrics[control]['f1'],
                'precision_delta':(metrics['P']['precision']-metrics[control]['precision']
                    if metrics['P']['precision'] is not None and metrics[control]['precision'] is not None else None),
                'recall_delta':metrics['P']['recall']-metrics[control]['recall'],
                'gained_loci':sorted(gained),'lost_loci':sorted(lost),'lost_correct_fraction':fraction,
                'loss_above_one_percent':fraction>.01 if fraction is not None else None,
                'bootstrap':bootstrap(per_core,'P',control)}
        curated={uid for uid,u in units.items() if u['curated_transcript_present']}
        result['species'][species]={'reference_loci':len(units),'reference_exclusions':refs['excluded'],
            'metrics':metrics,'comparisons':comparisons,'per_core':per_core,
            'curated_locus_recall':{'denominator':len(curated),'modes':{
                m:len(curated&correct[m])/len(curated) if curated else None for m in MODES}},
            'curated_scope':'locus has at least one NM transcript; recall only, no invalid subset precision',
            'correct_loci':{m:sorted(v) for m,v in correct.items()}}
    out=BASE/'run-r1'/'result.json'
    if out.exists():raise FileExistsError(out)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({s:{'metrics':d['metrics'],'deltas':{k:v['f1_delta'] for k,v in d['comparisons'].items()}}
                      for s,d in result['species'].items()},indent=2))


if __name__=='__main__':score()
