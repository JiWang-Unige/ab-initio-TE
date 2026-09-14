#!/usr/bin/env python3
"""Run actual traditional callers on the unchanged four-region D inputs.

This is a finite real-sequence feasibility/T2 panel, not whole-genome accuracy.
Native failure status is retained even when the native caller exits nonzero.
"""
from __future__ import annotations
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

SPECIES = ['platypus', 'sea_urchin', 'c_briggsae']
TAXA = [9258, 7668, 6238]


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def read_fasta(path):
    name, seq = None, []
    with path.open() as handle:
        for line in handle:
            if line.startswith('>'):
                if name is not None:
                    yield name, ''.join(seq)
                name, seq = line[1:].split()[0], []
            else:
                seq.append(line.strip())
    if name is not None:
        yield name, ''.join(seq)


def prepare_panel(source, work):
    records = list(read_fasta(source / 'panel_regions.fa'))
    regions = json.loads((source / 'panel_regions.json').read_text())
    if [r[0] for r in records] != [r['id'] for r in regions]:
        raise ValueError('FASTA order/IDs differ from original D regions')
    mapping = []
    with (work / 'panel.fa').open('w') as handle:
        for i, ((original, seq), region) in enumerate(zip(records, regions), 1):
            if len(seq) != region['length_bp'] or len(seq) != 1048576:
                raise ValueError('fixed panel length mismatch')
            short = f'r{i:02d}'
            handle.write(f'>{short}\n{seq}\n')
            mapping.append({'short_id': short, 'frozen_region_id': original,
                            'length_bp': len(seq), 'callable_bp': sum(b in 'ACGT' for b in seq.upper())})
    write_json(work / 'id_map.json', mapping)
    return mapping


def canonicalize(adapter, source, fmt, output, mapping):
    raw = output.with_name('canonical.raw.tsv')
    adapter.convert(source, raw, fmt)
    lengths = {r['short_id']: r['length_bp'] for r in mapping}
    counts = 0
    with raw.open() as handle, output.open('w') as target:
        reader = csv.DictReader(handle, delimiter='\t')
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        for row in reader:
            if row['seqid'] not in lengths or not 0 <= int(row['start']) < int(row['end']) <= lengths[row['seqid']]:
                raise ValueError('native output outside unchanged panel coordinates')
            writer.writerow(row)
            counts += 1
    return counts


def run(args):
    root = args.root.resolve()
    config = json.loads((root / 'configs/TE-REAL-PANEL-BENCH-20260914.json').read_text())
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work'
    work.mkdir()
    for name in ('home', 'tmp', 'hite', 'mask'):
        (work / name).mkdir()
    candidate_index = SPECIES.index(args.candidate)
    source = root / f'outputs/D-EXTERNAL-RC0-20260914/{args.candidate}/slurm-12696615_{candidate_index}'
    mapping = prepare_panel(source, work)
    shutil.copy2(work / 'id_map.json', out / 'id_map.json')
    status = {'protocol': config['protocol'], 'candidate': args.candidate, 'method': args.method,
              'cell_id': f'{args.candidate}|{args.method}', 'status': 'RUNNING',
              'scope': config['scope'], 'source_D_panel': str(source), 'input_bp': 4194304,
              'callable_bp': sum(x['callable_bp'] for x in mapping),
              'random_seed': config['seed'] if args.method == 'rm2_rm' else None,
              'seed_scope': 'RepeatModeler srand only; HiTE uses native defaults',
              'cpus': config['cpus'], 'slurm_job_id': os.getenv('SLURM_JOB_ID'),
              'hostname': os.uname().nodename, 'steps': []}
    write_json(out / 'status.json', status)
    started = time.monotonic()
    runtime = {k: root / v for k, v in config['runtimes'].items()}

    def command(name, argv, cwd=work):
        remaining = int(config['native_timeout_seconds'] - (time.monotonic() - started))
        if remaining <= 0:
            raise TimeoutError('native cell budget exhausted')
        t0 = time.monotonic()
        with (out / f'{name}.stdout').open('w') as stdout, (out / f'{name}.stderr').open('w') as stderr:
            # GNU timeout terminates the process group, including caller children.
            proc = subprocess.run(['timeout', '--kill-after=15s', str(remaining), '/usr/bin/time', '-v',
                                   '-o', str(out / f'{name}.time'), *map(str, argv)],
                                  stdout=stdout, stderr=stderr, cwd=cwd)
        rss = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',
                        (out / f'{name}.time').read_text() if (out / f'{name}.time').exists() else '')
        status['steps'].append({'name': name, 'argv': list(map(str, argv)), 'seconds': time.monotonic()-t0,
                                'exit_code': proc.returncode, 'peak_rss_kb': int(rss.group(1)) if rss else None})
        write_json(out / 'status.json', status)
        if proc.returncode in (124, 137):
            raise TimeoutError(name)
        if proc.returncode:
            raise RuntimeError(f'{name} exited {proc.returncode}; inspect native stderr/stdout')

    def container(which, argv):
        prefix = ['apptainer', 'exec', '--cleanenv', '--bind', f'{work}:/work']
        if which in ('rm', 'rm2'):
            prefix += ['--bind', f'{runtime["famdb4"]}:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro']
        return prefix + [str(runtime[which]), 'env', 'HOME=/work/home', 'TMPDIR=/work/tmp',
                         'OMP_NUM_THREADS=4', *argv]

    try:
        if args.method == 'hite':
            command('hite', container('hite', ['python', '/HiTE/main.py', '--genome', '/work/panel.fa',
                    '--thread', '4', '--plant', '0', '--annotate', '1', '--out_dir', '/work/hite']))
            outputs = list((work / 'hite').rglob('HiTE.out'))
            if len(outputs) == 1:
                raw, fmt = outputs[0], 'repeatmasker_out'
            else:
                outputs = list((work / 'hite').rglob('HiTE.gff'))
                if len(outputs) != 1:
                    raise RuntimeError('HiTE did not produce one final annotation output')
                raw, fmt = outputs[0], 'gff3'
        elif args.method == 'rm2_rm':
            command('build_database', container('rm2', ['BuildDatabase', '-name', '/work/paneldb', '/work/panel.fa']))
            command('repeatmodeler', container('rm2', ['RepeatModeler', '-database', '/work/paneldb',
                    '-threads', '4', '-LTRStruct', '-srand', '42']))
            lib = work / 'paneldb-families.fa'
            if not lib.is_file() or not lib.stat().st_size:
                raise RuntimeError('RepeatModeler did not produce a nonempty family library')
            command('mask_discovered', container('rm', ['RepeatMasker', '-pa', '1', '-nolow', '-gff',
                    '-lib', '/work/paneldb-families.fa', '-dir', '/work/mask', '/work/panel.fa']))
            raw, fmt = work / 'mask/panel.fa.out', 'repeatmasker_out'
        else:
            command('export_library', ['python3', runtime['famdb_cli'], '-i', runtime['famdb3'],
                    'families', '-f', 'fasta_acc', '--include-class-in-name', '-ad', str(TAXA[candidate_index])])
            text = (out / 'export_library.stdout').read_text()
            library = text[text.find('>'):] if '>' in text else ''
            (work / 'lineage.fa').write_text(library)
            status['library_records'] = sum(x.startswith('>') for x in library.splitlines())
            status['library_scope'] = config['fixed_rm_library']
            if not library:
                status['status'] = 'BLOCKED_NO_LIBRARY'
                return
            command('repeatmasker', ['RepeatMasker', '-pa', '1', '-nolow', '-gff', '-lib',
                    work / 'lineage.fa', '-dir', work / 'mask', work / 'panel.fa'])
            raw, fmt = work / 'mask/panel.fa.out', 'repeatmasker_out'
        if not raw.is_file():
            raise RuntimeError(f'final output absent: {raw}')
        spec = importlib.util.spec_from_file_location('adapter', root / 'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        status['prediction_rows'] = canonicalize(adapter, raw, fmt, out / 'predictions.tsv', mapping)
        status['native_output'] = str(raw)
        status['native_format'] = fmt
        status['status'] = 'COMPLETED'
    except TimeoutError as exc:
        status['status'], status['failure_reason'] = 'TIMEOUT', str(exc)
    except Exception as exc:
        status['status'], status['failure_reason'] = 'FAILED', str(exc)
    finally:
        status['wall_seconds'] = time.monotonic()-started
        status['absolute_precision'] = status['absolute_f1'] = None
        write_json(out / 'status.json', status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--candidate', choices=SPECIES, required=True)
    parser.add_argument('--method', choices=['fixed_rm', 'hite', 'rm2_rm'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
