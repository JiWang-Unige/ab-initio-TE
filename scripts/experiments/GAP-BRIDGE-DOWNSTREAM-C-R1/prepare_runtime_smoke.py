#!/usr/bin/env python3
"""Extract a fixed technical smoke near the first DEV candidate, not gene-selected."""
import argparse
import csv
import json
from pathlib import Path


def read_fasta(path):
    name, pieces = None, []
    with path.open() as handle:
        for line in handle:
            if line.startswith('>'):
                if name is not None:
                    yield name, ''.join(pieces)
                name, pieces = line[1:].strip(), []
            else:
                pieces.append(line.strip())
    if name is not None:
        yield name, ''.join(pieces)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--masks', type=Path, required=True)
    parser.add_argument('--candidate-manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    with args.candidate_manifest.open() as handle:
        row = min((r for r in csv.DictReader(handle, delimiter='\t')
                   if r['seqid'] == 'chr13' and r['role'] == 'DEV'),
                  key=lambda r: (int(r['gap_start']), r['candidate_id']))
    block = int(row['chr13_block_index'])
    with (args.masks / 'geometry.tsv').open() as handle:
        geometry = next(r for r in csv.DictReader(handle, delimiter='\t')
                        if int(r['block_index']) == block)
    halo_start, halo_end = int(geometry['halo_start']), int(geometry['halo_end'])
    midpoint = (int(row['gap_start']) + int(row['gap_end'])) // 2
    length = min(400050, halo_end - halo_start)
    start = max(halo_start, min(midpoint - length // 2, halo_end - length))
    end = start + length
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sequences = {}
    for mode in ('M0', 'MW', 'MP'):
        sequence = next(seq for name, seq in read_fasta(args.masks / f'{mode}.fasta')
                        if f'|dev_block={block}|' in name)
        sequences[mode] = sequence[start - halo_start:end - halo_start]
        if len(sequences[mode]) != length:
            raise ValueError('smoke genomic extraction length mismatch')
    if len({s.upper() for s in sequences.values()}) != 1:
        raise ValueError('mask modes changed nucleotide letters')
    for mode, sequence in sequences.items():
        with (args.output_dir / f'{mode}.fasta').open('x') as handle:
            handle.write(f'>smoke_chr13_{start}_{end}\n')
            handle.write('\n'.join(sequence[i:i+80] for i in range(0, length, 80)) + '\n')
    summary = {'scope': 'technical runtime only; not full DEV or gene utility evaluation',
               'claim_eligible': False, 'selection': 'first DEV candidate by gap_start and ID',
               'candidate_id': row['candidate_id'], 'seqid': 'chr13', 'start': start, 'end': end,
               'source_block': block, 'all_modes_same_letters': True,
               'lowercase_bp': {m: sum(c.islower() for c in s) for m, s in sequences.items()}}
    (args.output_dir / 'selection.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
