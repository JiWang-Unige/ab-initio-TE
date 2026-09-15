#!/usr/bin/env python3
"""Run complete native annotation workflows on a common long input."""
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


def portable_earlgrey(source):
    """Keep newest-directory semantics without GNU find's unsupported -printf."""
    old = 'latestStrainDir="$(find . -maxdepth 1 -type d -name "TS_${species}-families.fa_*" -printf \'%T@\\t%p\\n\' 2>/dev/null | sort -nr | head -n 1 | cut -f2-)"'
    new = 'latestStrainDir="$(python3 -c \'import glob,os,sys; print(max((p for p in glob.glob("TS_"+sys.argv[1]+"-families.fa_*") if os.path.isdir(p)), key=os.path.getmtime, default=""))\' "$species")"'
    if source.count(new) == 1 and old not in source:
        return source  # A preserved continuation already carries this exact patch.
    if source.count(old) != 1:
        raise ValueError('EarlGrey compatibility patch does not match installed source')
    return source.replace(old, new)


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def run(args):
    root = args.root.resolve()
    cfg = json.loads((root / 'configs/TE-LONG-BENCH-20260915.json').read_text())
    dataset = cfg['datasets'][args.dataset]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work'
    runtime = {k: root / v for k, v in cfg['runtimes'].items()}
    started = time.monotonic()
    prior_seconds = 0.0
    prior = None
    if args.resume_from:
        prior = json.loads((args.resume_from / 'status.json').read_text())
        if (args.method != 'earlgrey' or prior['method'] != args.method or
                prior['dataset'] != args.dataset or prior['status'] != 'FAILED' or
                prior['input'] != dataset['input']):
            raise ValueError('resume must match the failed EarlGrey cell and common input')
        prior_seconds = float(prior['wall_seconds'])
    status = {'protocol': cfg['protocol'], 'dataset': args.dataset, 'method': args.method,
              'status': 'RUNNING', 'cpus': cfg['cpus'], 'memory_gb': cfg['memory_gb'],
              'job': os.getenv('SLURM_JOB_ID'), 'hostname': os.uname().nodename,
              'input': dataset['input'], 'scope': dataset['scope'], 'steps': [],
              'knowledge_condition': cfg['method_information']}
    if prior:
        status.update(resumed_from=str(args.resume_from.resolve()), prior_wall_seconds=prior_seconds,
                      prior_steps=prior.get('prior_steps', []) + prior['steps'],
                      timing_scope='all failed attempts plus copies and continuation; same total native budget')
    write(out / 'status.json', status)

    def command(name, argv, allow_nonzero=False):
        remaining = int(cfg['native_timeout_seconds'] - prior_seconds - (time.monotonic()-started))
        if remaining <= 0:
            raise TimeoutError('cell budget exhausted')
        before = time.monotonic()
        with (out / (name+'.stdout')).open('w') as stdout, (out / (name+'.stderr')).open('w') as stderr:
            result = subprocess.run(['timeout', '--kill-after=30s', str(remaining), '/usr/bin/time', '-v',
                                     '-o', str(out / (name+'.time')), *map(str, argv)],
                                    cwd=work, stdout=stdout, stderr=stderr)
        timing = out / (name+'.time')
        rss = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', timing.read_text() if timing.exists() else '')
        status['steps'].append({'name': name, 'argv': list(map(str, argv)), 'exit_code': result.returncode,
                                'seconds': time.monotonic()-before, 'peak_rss_kb': int(rss.group(1)) if rss else None})
        write(out / 'status.json', status)
        if result.returncode in (124, 137):
            raise TimeoutError(name)
        if result.returncode and not allow_nonzero:
            raise RuntimeError(f'{name}: exit {result.returncode}')

    def container(which, argv):
        cmd = ['apptainer', 'exec', '--cleanenv', '--bind', f'{work}:/work']
        if which in ('rm', 'rm2', 'earlgrey'):
            cmd += ['--bind', f'{runtime["famdb4"]}:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro']
        if which == 'earlgrey':
            cmd += ['--bind', f'{runtime["famdb4"]}:/usr/local/share/RepeatMasker/Libraries/famdb:ro']
            if (work / 'earlGrey.compat.sh').exists():
                cmd += ['--bind', f'{work / "earlGrey.compat.sh"}:/usr/local/bin/earlGrey:ro']
            if (work / 'LTR_FINDER_parallel.compat').exists():
                cmd += ['--bind', f'{work / "LTR_FINDER_parallel.compat"}:/usr/local/share/earlgrey-7.3.0-1/scripts/LTR_FINDER_parallel:ro']
        if which == 'edta':
            cmd += ['--bind', f'{runtime["edta_source"]}:/opt/edta230:ro']
        perl_env = ['PERL5LIB=/usr/local/share/RepeatMasker'] if which == 'earlgrey' else []
        return cmd + [str(runtime[which]), 'env', 'HOME=/work/home', 'TMPDIR=/work/tmp', *perl_env,
                      'FAMDB_DIR=/usr/local/share/famdb-3.0.0/Libraries/famdb',
                      f'OMP_NUM_THREADS={cfg["cpus"]}', *map(str, argv)]

    try:
        if prior:
            # Copy preserves every original failed artifact. This runs inside Slurm.
            shutil.copytree(args.resume_from / 'work', work, symlinks=True)
            strained = work / 'eg/longbench_EarlGrey/longbench_strainer'
            completed = list(strained.glob('TS_longbench-families.fa_*/longbench-families.fa.strained'))
            if len(completed) != 1 or not completed[0].stat().st_size:
                raise ValueError('the interrupted directory-selection step requires one completed strained library')
            shutil.copy2(completed[0], strained / 'longbench-families.fa.strained')
            status['reused_strained_library'] = str(completed[0].relative_to(work))
        else:
            work.mkdir()
            for name in ('home', 'tmp', 'mask', 'hite', 'eg'):
                (work / name).mkdir()
        source = root / dataset['input']
        if not prior:
            shutil.copy2(source, work / 'panel.fa')
        lengths, name = {}, None
        with (work / 'panel.fa').open() as handle:
            for line in handle:
                if line.startswith('>'):
                    name = line[1:].split()[0]
                    if name in lengths:
                        raise ValueError('duplicate common input seqid')
                    lengths[name] = 0
                else:
                    seq = line.strip()
                    if name is None or set(seq) - set('ACGTN'):
                        raise ValueError('common input must be uppercase ACGTN')
                    lengths[name] += len(seq)
        if sum(lengths.values()) < 100000000:
            raise ValueError('long input requires at least 100 Mb')
        status['input_bp'] = sum(lengths.values())
        status['sequence_count'] = len(lengths)
        write(out / 'sequence_lengths.json', lengths)
        if args.method == 'fixed_rm':
            command('rm_version', container('rm', ['RepeatMasker', '-help']), True)
            command('library_export', ['python3', runtime['famdb_cli'], '-i', runtime['famdb3'],
                    'families', '-f', 'fasta_acc', '--include-class-in-name', '-ad', str(dataset['taxid'])])
            if 'ERROR' in (out / 'library_export.stderr').read_text():
                raise RuntimeError('FamDB reported an incomplete library despite a zero exit code')
            library = (out / 'library_export.stdout').read_text()
            if '>' not in library:
                raise RuntimeError('no lineage reference library')
            library = library[library.index('>'):]
            (work / 'lineage.fa').write_text(library)
            status['library_records'] = sum(line.startswith('>') for line in library.splitlines())
            status['library_scope'] = cfg['fixed_library']
            command('repeatmasker', container('rm', ['RepeatMasker', '-pa', '4', '-nolow', '-gff',
                    '-lib', '/work/lineage.fa', '-dir', '/work/mask', '/work/panel.fa']))
            raw, fmt = work / 'mask/panel.fa.out', 'repeatmasker_out'
        elif args.method == 'rm2_rm':
            command('rm2_version', container('rm2', ['RepeatModeler', '-version']))
            command('rm_version', container('rm', ['RepeatMasker', '-help']), True)
            command('build_database', container('rm2', ['BuildDatabase', '-name', '/work/paneldb', '/work/panel.fa']))
            command('repeatmodeler', container('rm2', ['RepeatModeler', '-database', '/work/paneldb',
                    '-threads', '16', '-LTRStruct', '-srand', '42']))
            lib = work / 'paneldb-families.fa'
            if not lib.is_file() or not lib.stat().st_size:
                raise RuntimeError('no discovered library')
            command('mask_discovered', container('rm', ['RepeatMasker', '-pa', '4', '-nolow', '-gff',
                    '-lib', '/work/paneldb-families.fa', '-dir', '/work/mask', '/work/panel.fa']))
            raw, fmt = work / 'mask/panel.fa.out', 'repeatmasker_out'
        elif args.method == 'hite':
            command('hite_help', container('hite', ['python', '/HiTE/main.py', '-h']))
            command('hite', container('hite', ['python', '/HiTE/main.py', '--genome', '/work/panel.fa',
                    '--thread', '16', '--plant', '0', '--annotate', '1', '--out_dir', '/work/hite']))
            outputs = list((work / 'hite').rglob('HiTE.out'))
            if len(outputs) == 1:
                raw, fmt = outputs[0], 'repeatmasker_out'
            else:
                outputs = list((work / 'hite').rglob('HiTE.gff'))
                if len(outputs) != 1:
                    raise RuntimeError('HiTE final output not unique')
                raw, fmt = outputs[0], 'gff3'
        elif args.method == 'edta':
            command('edta_help', container('edta', ['perl', '/opt/edta230/EDTA.pl', '-h']), True)
            command('edta', container('edta', ['perl', '/opt/edta230/EDTA.pl', '--genome', '/work/panel.fa',
                    '--overwrite', '1', '--sensitive', '1', '--anno', '1', '--threads', '16']))
            raw, fmt = work / 'panel.fa.mod.EDTA.TEanno.gff3', 'gff3'
        elif args.method == 'earlgrey':
            command('earlgrey_source', container('earlgrey', ['cat', '/usr/local/bin/earlGrey']))
            patched = portable_earlgrey((out / 'earlgrey_source.stdout').read_text())
            (work / 'earlGrey.compat.sh').write_text(patched)
            (work / 'earlGrey.compat.sh').chmod(0o755)
            command('ltr_finder_source', container('earlgrey', ['cat', '/usr/local/share/earlgrey-7.3.0-1/scripts/LTR_FINDER_parallel']))
            ltr = (out / 'ltr_finder_source.stdout').read_text()
            if not ltr.startswith(('#!/usr/bin/perl -w\n', '#!/usr/local/bin/perl -w\n')):
                raise ValueError('unexpected LTR_FINDER_parallel interpreter declaration')
            ltr = ltr.replace('#!/usr/bin/perl -w\n', '#!/usr/local/bin/perl -w\n', 1)
            (work / 'LTR_FINDER_parallel.compat').write_text(ltr)
            (work / 'LTR_FINDER_parallel.compat').chmod(0o755)
            status['runtime_compatibility_fix'] = 'portable directory selection; actual Perl interpreter; RepeatMasker PERL5LIB; biological stages and parameters unchanged'
            command('earlgrey_help', container('earlgrey', ['earlGrey', '-h']))
            # Use EarlGrey's supported starting-library interface so its initial
            # reference information equals the fixed-RM arm, including uncurated entries.
            command('library_export', ['python3', runtime['famdb_cli'], '-i', runtime['famdb3'],
                    'families', '-f', 'fasta_acc', '--include-class-in-name', '-ad', str(dataset['taxid'])])
            if 'ERROR' in (out / 'library_export.stderr').read_text():
                raise RuntimeError('FamDB reported an incomplete library despite a zero exit code')
            library = (out / 'library_export.stdout').read_text()
            if '>' not in library:
                raise RuntimeError('no lineage reference library')
            library = library[library.index('>'):]
            (work / 'lineage.fa').write_text(library)
            status['library_scope'] = cfg['fixed_library']
            command('earlgrey', container('earlgrey', ['earlGrey', '-g', '/work/panel.fa', '-s', 'longbench',
                    '-o', '/work/eg', '-t', '16', '-q', 'yes', '-l', '/work/lineage.fa']))
            raw, fmt = work / 'eg/longbench_EarlGrey/longbench_summaryFiles/longbench.filteredRepeats.gff', 'gff3'
        if not raw.is_file():
            raise RuntimeError(f'final output absent: {raw}')
        spec = importlib.util.spec_from_file_location('adapter', root / 'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        status['prediction_rows'] = adapter.convert(raw, out / 'predictions.tsv', fmt)
        for seqid, start, end in adapter.read_canonical(out / 'predictions.tsv'):
            if seqid not in lengths or end > lengths[seqid]:
                raise ValueError('native coordinates differ from common long input')
        status.update(status='COMPLETED', native_output=str(raw), native_format=fmt)
    except TimeoutError as exc:
        status.update(status='TIMEOUT', failure_reason=str(exc))
    except Exception as exc:
        status.update(status='FAILED', failure_reason=str(exc))
    finally:
        status['attempt_wall_seconds'] = time.monotonic()-started
        status['wall_seconds'] = prior_seconds + status['attempt_wall_seconds']
        write(out / 'status.json', status)
    if status['status'] != 'COMPLETED':
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--dataset', choices=['sim100', 'c_briggsae'], required=True)
    parser.add_argument('--method', choices=['fixed_rm', 'rm2_rm', 'hite', 'edta', 'earlgrey'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume-from', type=Path, help='preserved failed EarlGrey attempt after library compilation')
    run(parser.parse_args())
