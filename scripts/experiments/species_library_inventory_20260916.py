#!/usr/bin/env python3
"""Read installed Dfam metadata only; no genome, labels or predictions read."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
runtime=json.loads((ROOT/'configs/TE-LONG-BENCH-20260915.json').read_text())['runtimes']
out=ROOT/'outputs/SPECIES-ANNOTATION-DIAGNOSTIC-20260916'/('library-'+os.environ['SLURM_JOB_ID'])
out.mkdir(parents=True,exist_ok=False)
base=[sys.executable,str(ROOT/runtime['famdb_cli']),'-i',str(ROOT/runtime['famdb3'])]
records=[]
info=subprocess.run(base+['info'],capture_output=True,text=True,check=True,timeout=120)
for species,taxid in [('human',9606),('mouse',10090),('chicken',9031),
                      ('zebrafish',7955),('pig',9823),('c_elegans',6239)]:
    for selection in ('curated','uncurated'):
        cmd=base+['lineage','-ad','--format','totals','--'+selection,str(taxid)]
        started=time.monotonic()
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        match=re.search(r'(\d+) entries in ancestors; (\d+) lineage-specific entries',p.stdout)
        record=dict(species=species,taxid=taxid,selection=selection,command=cmd,
                    exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,
                    seconds=time.monotonic()-started)
        if p.returncode or not match or 'absent related partitions:' in p.stdout:
            (out/'failure.json').write_text(json.dumps(record,indent=2)+'\n')
            raise RuntimeError('family metadata unavailable or incomplete; preserve raw failure')
        record.update(ancestor_entries=int(match[1]),lineage_specific_entries=int(match[2]))
        records.append(record)
result=dict(status='COMPLETED',slurm_job_id=os.environ['SLURM_JOB_ID'],
            scope='Installed Dfam lineage metadata; counts are not annotation completeness or a replay of historical consumed libraries',
            genome_label_model_access=False,famdb_info=info.stdout,
            famdb_info_stderr=info.stderr,records=records)
(out/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
print(str(out/'inventory.json'))
