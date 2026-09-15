#!/usr/bin/env python3
"""Execute five paired native Tiberius cells for one fixed external core."""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'outputs/P3-TIBERIUS-EXTERNAL-20260915'
MODES = ('U_soft','U_nosm','P','R_TE','R_all')


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
    return m


def run(index):
    species=('cow','platypus')[index//20]
    prepared=BASE/'prepared'/species
    manifest=json.loads((prepared/'preparation.json').read_text())
    if manifest.get('status')!='PREPARED_WITH_NATIVE_RM' or not manifest.get('complete_library_export'):
        raise ValueError('native reference preparation incomplete')
    geometry=json.loads((prepared/'geometry.json').read_text())
    core=geometry[index%20]
    out=BASE/'run-r1'/species/core['id']
    if (out/'status.json').exists():
        status=json.loads((out/'status.json').read_text())
        if status.get('status')=='COMPLETED' and status['core']==core:
            print('Reuse completed engineering smoke cell',str(out));return
        raise ValueError('existing partial cell requires explicit engineering repair, not overwrite')
    out.mkdir(parents=True,exist_ok=False)
    b=module(ROOT/'scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py','external_base')
    phase0=module(ROOT/'scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py','external_phase0')
    c=b.Core(**{k:core[k] for k in ('chrom','index','start','end','halo_start','halo_end')})
    sequence=(prepared/core['id']/'sequence.txt').read_text().strip()
    started=time.monotonic()
    model=ROOT/'outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet'
    phase0.export_frozen_p3(model,prepared/core['id']/'region.jsonl.gz',out/'p3_pte.npy',out/'p3_states.npy',
                           out/'P.canonical.tsv',out/'p3_export.json',None)
    export=json.loads((out/'p3_export.json').read_text())
    if export['model_schema']!='comparator_run_four_state_unet_v1' or export['threshold']!=0.5:
        raise ValueError('P3 checkpoint/threshold changed')
    masks={m:np.zeros(len(sequence),dtype=bool) for m in MODES}
    masks['P']=b.interval_mask(b.canonical_intervals(out/'P.canonical.tsv',core['chrom']),core['halo_start'],core['halo_end'])
    r_classes={}
    with (prepared/manifest['repeatmasker_canonical']).open() as handle:
        for row in csv.DictReader(handle,delimiter='\t'):
            if row['seqid']!=core['id']:
                continue
            left,right=int(row['start']),int(row['end'])
            if not 0<=left<right<=len(sequence):
                raise ValueError('native RepeatMasker coordinate mismatch')
            masks['R_all'][left:right]=True
            kind=row['attributes'].split('class_family=',1)[1].split(';')[0]
            r_classes[kind]=r_classes.get(kind,0)+1
            if '?' not in kind and kind.split('/')[0] in {'LINE','SINE','LTR','DNA','RC','Retroposon'}:
                masks['R_TE'][left:right]=True
    callable_mask=np.fromiter((base in 'ACGT' for base in sequence),dtype=bool)
    for mode,mask in masks.items():
        mask &= callable_mask
        masked=''.join(base.lower() if flag else base for base,flag in zip(sequence,mask))
        if masked.upper()!=sequence:
            raise ValueError('mask changed sequence letters')
        b.write_fasta(out/(mode+'.fasta'),c.record_id,masked)
    inputs={'core':core,'P3':export,'mask_bp':{m:int(v.sum()) for m,v in masks.items()},
            'same_uppercase_letters':True,'native_R_classes':r_classes,'P3_export_seconds':time.monotonic()-started}
    (out/'input.json').write_text(json.dumps(inputs,indent=2)+'\n')
    source=ROOT/'refs/repos/Tiberius-gap-c-r1'
    nosm=ROOT/'software_outputs/P3-TIBERIUS-EXTERNAL-20260915/source/tiberius/tiberius_nosm_weights_v2'
    image=ROOT/'software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif'
    if not (nosm/'weights.h5').exists():
        raise ValueError('official nosm checkpoint has not been staged')
    status={'status':'RUNNING','species':species,'core':core,'slurm_job_id':os.getenv('SLURM_JOB_ID'),
            'model':'frozen_P3_human','steps':[]}
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    for mode in MODES:
        cell_guest='/work/te/'+str(out.relative_to(ROOT))
        config='mammalia_nosofttmasking_v2' if mode=='U_nosm' else 'mammalia_softmasking_v2'
        channels=5 if mode=='U_nosm' else 6
        cmd=['singularity','exec','--nv','--cleanenv','--env',f'CUDA_VISIBLE_DEVICES={os.environ["CUDA_VISIBLE_DEVICES"]}',
             '--env',f'TIB_OBSERVATION={cell_guest}/{mode}.observation.json','--env',f'TIB_EXPECTED_CHANNELS={channels}',
             '--bind',f'{ROOT}:/work/te','--bind',f'{source}:/opt/Tiberius',
             '--bind',f'{nosm}:/opt/Tiberius/model_weights/tiberius_nosm_weights_v2:ro','--pwd','/work/te',str(image),
             '/usr/bin/python3','/work/te/scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/observed_tiberius.py',
             '--genome',f'{cell_guest}/{mode}.fasta','--model_cfg',f'/opt/Tiberius/model_cfg/{config}.yaml',
             '--seq_len','400050','--batch_size','1','--out',f'{cell_guest}/{mode}.gtf',f'{cell_guest}/{mode}.gff3']
        start=time.monotonic()
        with (out/(mode+'.stdout')).open('w') as stdout,(out/(mode+'.stderr')).open('w') as stderr:
            result=subprocess.run(cmd,stdout=stdout,stderr=stderr)
        status['steps'].append({'mode':mode,'config':config,'argv':cmd,'exit_code':result.returncode,'seconds':time.monotonic()-start})
        (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
        if result.returncode:
            raise RuntimeError(f'Tiberius failed: {mode}')
        obs=json.loads((out/(mode+'.observation.json')).read_text())
        if not obs['passed'] or obs['expected_channels']!=channels or obs['model_calls']<1:
            raise ValueError('native input observation failed')
        if mode.startswith('U_') and obs['masked_positions']!=0:
            raise ValueError('unmasked input had softmask positions')
        gtf,a=b.parse_predictions(out/(mode+'.gtf'),c,'gtf')
        gff,b_counts=b.parse_predictions(out/(mode+'.gff3'),c,'gff3')
        if gtf!=gff or a!=b_counts:
            raise ValueError('native GTF/GFF3 annotation mismatch')
    status.update(status='COMPLETED',wall_seconds=time.monotonic()-started)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'status':'COMPLETED','species':species,'core':core['id']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('index',type=int,choices=range(40));run(p.parse_args().index)
