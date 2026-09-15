#!/usr/bin/env python3
"""Replace incomplete Dfam4 export with complete Dfam3.9 lineage in a new attempt."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from prepare import ROOT, BASE, META, write

species=argparse.ArgumentParser()
species.add_argument('species',choices=sorted(META))
species=species.parse_args().species
out=BASE/'prepared'/species
meta=META[species]
manifest_path=out/'preparation.json'
original=json.loads(manifest_path.read_text())
if original.get('complete_library_export'):raise ValueError('qualified reference already exists')
write(out/'preparation-dfam4-incomplete.json',original)
attempt=out/('reference-dfam39-'+os.environ['SLURM_JOB_ID'])
attempt.mkdir()
cfg=json.loads((ROOT/'configs/TE-LONG-BENCH-20260915.json').read_text())
runtime={k:ROOT/v for k,v in cfg['runtimes'].items()}
with (attempt/'library.fa').open('w') as stdout,(attempt/'export.stderr').open('w') as stderr:
    subprocess.run(['python3',str(runtime['famdb_cli']),'-i',str(runtime['famdb3']),
        'families','-f','fasta_acc','--include-class-in-name','-ad',str(meta['taxid'])],
        stdout=stdout,stderr=stderr,check=True)
library=(attempt/'library.fa').read_text()
if 'ERROR' in (attempt/'export.stderr').read_text() or not library.startswith('>'):
    raise ValueError('complete lineage export failed; cannot compare native RM')
shutil.copy2(out/'panel.fa',attempt/'panel.fa')
(attempt/'mask').mkdir()
cmd=['apptainer','exec','--cleanenv','--bind',f'{attempt}:/work','--bind',
     f'{runtime["famdb4"]}:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro',
     '--pwd','/work',str(runtime['rm']),
     'RepeatMasker','-pa','4','-gff','-xsmall','-lib','/work/library.fa','-dir','/work/mask','/work/panel.fa']
started=time.monotonic()
with (attempt/'repeatmasker.stdout').open('w') as stdout,(attempt/'repeatmasker.stderr').open('w') as stderr:
    subprocess.run(cmd,stdout=stdout,stderr=stderr,check=True)
spec=importlib.util.spec_from_file_location('repair_adapter',ROOT/'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
rows=adapter.convert(attempt/'mask/panel.fa.out',attempt/'R.canonical.tsv','repeatmasker_out')
original.update(status='PREPARED_WITH_NATIVE_RM',library='Dfam3.9 complete lineage curated+uncurated',
                complete_library_export=True,library_records=library.count('>'),repeat_rows=rows,
                repeatmasker_seconds=time.monotonic()-started,repeatmasker_argv=cmd,
                repeatmasker_canonical=str((attempt/'R.canonical.tsv').relative_to(out)),
                superseded_reference='Dfam4 partial export; preserved and excluded from comparisons')
write(manifest_path,original)
print(json.dumps(original))
