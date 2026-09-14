#!/usr/bin/env python3
"""Run the fixed single-species loop using only a native encoder and fresh head."""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXP=HERE.name


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def run(a):
    cfg=json.loads(a.config.read_text())
    prep=json.loads((a.data/'preparation.json').read_text())
    if prep['protocol']!=cfg or prep['status']!='DATA_PREPARED_NO_MODEL_RESULT':
        raise ValueError('fixed prepared data contract mismatch')
    if cfg['seed']!=42 or set(cfg['tiles_by_split']['TRAIN'])!={'chr1'}:
        raise ValueError('only seed42 and hg19 chr1 training are allowed')
    legacy=load('hg19_training',HERE.parent/'CROSS-SPECIES-L1-20260903/cross_species_token_task.py')
    if legacy.LEARNING_RATE!=cfg['learning_rate'] or len(legacy.SPECIES)!=cfg['training_tile_presentations_per_step']:
        raise ValueError('legacy loop no longer matches fixed training budget')
    init=load('hg19_native_init',HERE.parent/'CROSS-SPECIES-L1-INIT-HISTORY-V1/init_model.py')
    def model_loader():
        model,tok,report=init.load_model_and_tokenizer('P0R',42,base_model=a.root/cfg['native_model'])
        report.update(protocol=EXP,helper_protocol=init.PROTOCOL,
                      ancestry_status='native pretrained encoder, fresh classifier; task training only hg19 chr1',
                      interpretation='chromosome-held-out TE task, pretraining sequence exposure unresolved')
        return model,tok,report
    forwarded=argparse.Namespace(arm='B0',species='human',seed=42,output_dir=a.output,
        data_root=a.data,species_data=[],max_steps=2 if a.smoke else cfg['train_steps'],
        warmup_steps=cfg['warmup_steps'],experiment_arm='HG19_NATIVE_CHR1',protocol=EXP,
        run_role='hg19_engineering_smoke' if a.smoke else 'hg19_annotation_revision',collect_exposure=True)
    legacy.train(forwarded,model_loader=model_loader)
    logs=[json.loads(x) for x in (a.output/'train_log.jsonl').read_text().splitlines()]
    if len(logs)!=forwarded.max_steps or any(not math.isfinite(v) for r in logs for v in r['loss'].values()):
        raise ValueError('training did not complete finite prescribed steps')
    (a.output/'completion.json').write_text(json.dumps(dict(status='ENGINEERING_SMOKE_PASS' if a.smoke else 'TRAINING_COMPLETED_NOT_EVALUATED',steps=forwarded.max_steps,seed=42,task_training_chromosomes=['chr1']),indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--smoke',action='store_true');run(ap.parse_args())
