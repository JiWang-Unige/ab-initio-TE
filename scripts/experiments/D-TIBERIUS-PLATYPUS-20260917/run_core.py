#!/usr/bin/env python3
"""One fixed D mask on one already-defined platypus Tiberius core."""
import argparse
import gc
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT/'outputs/P3-TIBERIUS-EXTERNAL-20260915'
BASE = ROOT/'outputs/D-TIBERIUS-PLATYPUS-20260917'


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
    return mod


def run(index):
    import numpy as np
    prepared=OLD/'prepared/platypus'
    manifest=json.loads((prepared/'preparation.json').read_text())
    if manifest['status']!='PREPARED_WITH_NATIVE_RM' or not manifest['complete_library_export']:
        raise ValueError('Old paired comparator qualification is missing')
    geometry=json.loads((prepared/'geometry.json').read_text())
    if len(geometry)!=20: raise ValueError('Fixed 20-core geometry changed')
    core=geometry[index]
    old_cell=OLD/'run-r1/platypus'/core['id']
    prior=json.loads((old_cell/'status.json').read_text())
    if prior['status']!='COMPLETED' or prior['core']!=core:
        raise ValueError('Historical paired controls are not complete for this core')
    if index:
        smoke=json.loads((BASE/'run/platypus/c00/status.json').read_text())
        if smoke['status']!='COMPLETED': raise ValueError('The engineering smoke has not qualified')
    out=BASE/'run/platypus'/core['id'];out.mkdir(parents=True,exist_ok=False)
    status={'status':'RUNNING','protocol':'D-TIBERIUS-PLATYPUS-20260917','core':core,
            'job_id':os.environ.get('SLURM_JOB_ID'),'steps':[]}
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    started=time.monotonic()
    b=module(ROOT/'scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py','D_utility_base')
    rc=module(ROOT/'scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py','D_utility_infer')
    cfg=json.loads((ROOT/'scripts/experiments/D-EXTERNAL-RC0-20260914/config/panel.json').read_text())
    args=argparse.Namespace(remote_root=ROOT,model_dir=None,tokenizer_dir=None,model_code_dir=None,calibration_json=None,cpu=False)
    model,tokenizer,device,cal,load_seconds,paths=rc._load_model(cfg,args)
    sequence=(prepared/core['id']/'sequence.txt').read_text().strip()
    p=rc._infer_sequence(sequence,model,tokenizer,device,12,float(cal['platt_slope']),float(cal['platt_intercept']))
    callable_mask=np.fromiter((v in 'ACGT' for v in sequence),dtype=bool)
    mask=(p>=float(cal['threshold'])) & callable_mask
    np.save(out/'D_probability.npy',p)
    c=b.Core(**{key:core[key] for key in ('chrom','index','start','end','halo_start','halo_end')})
    masked=''.join(v.lower() if flag else v for v,flag in zip(sequence,mask))
    if masked.upper()!=sequence: raise ValueError('Mask changed uppercase sequence')
    b.write_fasta(out/'D.fasta',c.record_id,masked)
    inp={'core':core,'same_uppercase_letters':True,'mask_bp':int(mask.sum()),'model_paths':paths,
         'calibration':cal,'load_seconds':load_seconds,'D_export_seconds':time.monotonic()-started,
         'window_origin':'halo start, no phase search','historical_control_dir':str(old_cell)}
    (out/'input.json').write_text(json.dumps(inp,indent=2)+'\n')
    del model,tokenizer,p
    import torch
    gc.collect();torch.cuda.empty_cache()
    source=ROOT/'refs/repos/Tiberius-gap-c-r1'
    image=ROOT/'software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif'
    cell='/work/te/'+str(out.relative_to(ROOT))
    cmd=['singularity','exec','--nv','--cleanenv','--env',f'CUDA_VISIBLE_DEVICES={os.environ["CUDA_VISIBLE_DEVICES"]}',
         '--env',f'TIB_OBSERVATION={cell}/D.observation.json','--env','TIB_EXPECTED_CHANNELS=6',
         '--bind',f'{ROOT}:/work/te','--bind',f'{source}:/opt/Tiberius','--pwd','/work/te',str(image),
         '/usr/bin/python3','/work/te/scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/observed_tiberius.py',
         '--genome',f'{cell}/D.fasta','--model_cfg','/opt/Tiberius/model_cfg/mammalia_softmasking_v2.yaml',
         '--seq_len','400050','--batch_size','1','--out',f'{cell}/D.gtf',f'{cell}/D.gff3']
    tick=time.monotonic()
    with (out/'D.stdout').open('w') as stdout,(out/'D.stderr').open('w') as stderr:
        done=subprocess.run(cmd,stdout=stdout,stderr=stderr)
    status['steps'].append({'mode':'D','argv':cmd,'exit_code':done.returncode,'seconds':time.monotonic()-tick})
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    if done.returncode: raise RuntimeError('Native Tiberius D arm failed; preserve the cell')
    obs=json.loads((out/'D.observation.json').read_text())
    if not obs['passed'] or obs['expected_channels']!=6 or obs['model_calls']<1:
        raise ValueError('Actual mask-consuming model input did not qualify')
    if b.parse_predictions(out/'D.gtf',c,'gtf')!=b.parse_predictions(out/'D.gff3',c,'gff3'):
        raise ValueError('Native GTF and GFF3 disagree')
    status.update(status='COMPLETED',wall_seconds=time.monotonic()-started)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('index',type=int,choices=range(20));run(parser.parse_args().index)
