#!/usr/bin/env python3
"""Materialize the complete authorized CB4 assembly, without reading labels."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
cfg = json.loads((ROOT / 'configs/TE-LONG-BENCH-20260915.json').read_text())
record = cfg['datasets']['c_briggsae']
source = ROOT / record['source_fasta']
output = ROOT / record['input']
output.parent.mkdir(parents=True, exist_ok=True)
lengths, name, nonacgt = {}, None, 0
with gzip.open(source, 'rt') as handle, output.open('x') as out:
    for line in handle:
        if line.startswith('>'):
            name = line[1:].split()[0]
            if name in lengths:
                raise ValueError('duplicate genome seqid')
            lengths[name] = 0
            out.write('>' + name + '\n')
        else:
            seq = line.strip().upper()
            if name is None or set(seq) - set('ACGTN'):
                raise ValueError('unsupported assembly alphabet')
            lengths[name] += len(seq)
            nonacgt += seq.count('N')
            out.write(seq + '\n')
report = {'source': str(source), 'input': str(output), 'lengths': lengths,
          'input_bp': sum(lengths.values()), 'N_bp': nonacgt, 'labels_read': False}
(output.parent / 'input.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
