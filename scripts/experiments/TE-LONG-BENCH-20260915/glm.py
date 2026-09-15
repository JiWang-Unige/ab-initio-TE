#!/usr/bin/env python3
"""Full-input fixed D forward inference, preserving the existing CAL contract."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import time
import numpy as np
from qualify_simulation import fasta


def run(args):
    root = args.root.resolve()
    cfg = json.loads((root / 'configs/TE-LONG-BENCH-20260915.json').read_text())
    oldcfg = json.loads((root / cfg['fixed_D_config']).read_text())
    spec = importlib.util.spec_from_file_location('long_fixed_D', root / 'scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py')
    rc0 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rc0)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    args.remote_root = root
    args.model_dir = args.tokenizer_dir = args.model_code_dir = args.calibration_json = None
    before = time.monotonic()
    model, tokenizer, device, cal, load_seconds, paths = rc0._load_model(oldcfg, args)
    import torch
    cpu_info = Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    cpu_model = next((s.split(':',1)[1].strip() for s in cpu_info.splitlines() if s.startswith('model name')), platform.processor())
    summary = {'protocol': cfg['protocol'], 'dataset': args.dataset, 'status': 'RUNNING',
               'model_paths': paths, 'calibration': cal, 'model_load_seconds': load_seconds,
               'device': str(device), 'cpus_allocated': os.getenv('SLURM_CPUS_PER_TASK'),
               'hostname': platform.node(), 'cpu_model': cpu_model, 'job': os.getenv('SLURM_JOB_ID'),
               'accelerator': torch.cuda.get_device_name() if not args.cpu else None,
               'window_bp': rc0.WINDOW_BP, 'batch_size': cfg['D_batch_size'],
               'model_changed': False, 'threshold_refit': False,
               'input': cfg['datasets'][args.dataset]['input'], 'sequences': []}
    (out / 'status.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (out / 'predictions.tsv').open('w') as handle:
        handle.write('seqid\tstart\tend\tname\tscore\tstrand\tsource\tattributes\n')
        for index, (name, seq) in enumerate(fasta(root / cfg['datasets'][args.dataset]['input'])):
            if set(seq)-set('ACGTN'):
                raise ValueError('input must be uppercase ACGTN')
            rc0._sync(device)
            start = time.monotonic()
            p = rc0._infer_sequence(seq, model, tokenizer, device, cfg['D_batch_size'],
                                   float(cal['platt_slope']), float(cal['platt_intercept']))
            rc0._sync(device)
            forward_seconds = time.monotonic()-start
            start = time.monotonic()
            call = p >= float(cal['threshold'])
            intervals = rc0._material_runs(call)
            for left, right in intervals:
                handle.write(f'{name}\t{left}\t{right}\tTE\t.\t.\tfixed_D\tmode=F;threshold={cal["threshold"]}\n')
            handle.flush()
            np.save(out / f'probabilities-{index:04d}.npy', p.astype(np.float32))
            summary['sequences'].append({'seqid': name, 'input_bp': len(seq), 'forward_seconds': forward_seconds,
                                          'merge_and_write_seconds': time.monotonic()-start,
                                          'predicted_bp': int(call.sum()), 'intervals': len(intervals),
                                          'probabilities': f'probabilities-{index:04d}.npy'})
            (out / 'status.json').write_text(json.dumps(summary, indent=2)+'\n')
    summary.update(status='COMPLETED', wall_seconds=time.monotonic()-before,
                   input_bp=sum(s['input_bp'] for s in summary['sequences']))
    (out / 'status.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--dataset', choices=['sim100', 'c_briggsae'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpu', action='store_true')
    run(parser.parse_args())
