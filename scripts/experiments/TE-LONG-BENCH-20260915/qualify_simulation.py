#!/usr/bin/env python3
"""Qualify direct GARLIC BED truth and produce an uppercase benchmark input."""
import argparse
from collections import Counter
import json
from pathlib import Path


def fasta(path):
    name, parts = None, []
    with path.open() as handle:
        for line in handle:
            if line.startswith('>'):
                if name is not None:
                    yield name, ''.join(parts)
                name, parts = line[1:].split()[0], []
            else:
                parts.append(line.strip())
    if name is not None:
        yield name, ''.join(parts)


def te_status(kind):
    root = kind.split('/')[0].lower()
    if root in {'line', 'sine', 'ltr', 'dna', 'rc', 'retroposon', 'helitron', 'dirs', 'penelope'}:
        return 'TE'
    if root in {'simple_repeat', 'low_complexity', 'satellite', 'rrna', 'trna', 'snrna', 'scrna', 'srprna'}:
        return 'NON_TE'
    return 'UNRESOLVED'


def qualify(prefix, expected, output_prefix=None):
    output_prefix = output_prefix or prefix
    sequences = dict(fasta(Path(str(prefix) + '.fasta')))
    if len(sequences) != 1 or sum(map(len, sequences.values())) != expected:
        raise ValueError('simulation sequence count/length differs from the frozen input')
    id_map = {name: f's{i+1:02d}' for i, name in enumerate(sequences)}
    masks = {name: bytearray(len(seq)) for name, seq in sequences.items()}
    rows, categories, families = [], Counter(), Counter()
    clipped, zero = 0, 0
    with Path(str(prefix) + '.inserts').open() as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            fields = line.rstrip('\n').split('\t')
            if len(fields) != 5:
                raise ValueError('expected direct --useBED output with five columns')
            name, start, end, metadata, top_level_group = fields
            start, end = int(start), int(end)
            if name not in sequences or not 0 <= start <= end:
                raise ValueError('invalid simulation coordinates')
            # GARLIC records inserts before checkSeqSize trims the final sequence.
            if end > len(sequences[name]):
                clipped += 1
                start, end = min(start, len(sequences[name])), len(sequences[name])
            if start == end:
                zero += 1
                continue
            # Observed upstream format: repeat_name:class/family:strand:...
            family, kind, *_ = metadata.split(':')
            status = te_status(kind)
            categories[(kind, status)] += end - start
            families[family] += 1
            masks[name][start:end] = b'\1' * (end-start)
            rows.append((name, start, end, kind, family, status, top_level_group, metadata))
    mismatch, lower_bp = 0, 0
    for name, seq in sequences.items():
        if set(seq.upper()) - set('ACGTN'):
            raise ValueError('non-ACGTN simulator output')
        for base, covered in zip(seq, masks[name]):
            is_lower = base.islower()
            lower_bp += is_lower
            mismatch += is_lower != bool(covered)
    summary = {'scope': 'TE_Bench_GARLIC_derived_synthetic_material_only',
               'input_bp': expected, 'inserted_material_bp': lower_bp,
               'input_id_map': id_map,
               'truth_mask_mismatch_bp': mismatch, 'fragment_rows': len(rows),
               'overlapping_fragment_bp': sum(categories.values())-lower_bp,
               'end_clipped_rows': clipped, 'zero_length_rows': zero,
               'categories': [{'type': k, 'truth_status': s, 'fragment_bp': v}
                              for (k, s), v in sorted(categories.items())],
               'families': dict(sorted(families.items())),
               'L3_truth': None, 'strand_truth': None,
               'qualification': ('PASS' if mismatch == 0 and sum(categories.values()) == lower_bp
                                 and any(s == 'TE' for _, s in categories) else 'FAIL')}
    Path(str(output_prefix) + '.qualification.json').write_text(json.dumps(summary, indent=2) + '\n')
    if summary['qualification'] != 'PASS':
        raise ValueError('direct generated truth disagrees with inserted sequence; do not benchmark')
    with Path(str(output_prefix) + '.truth.tsv').open('w') as out:
        out.write('seqid\tstart\tend\ttype\tfamily\ttruth_status\ttop_level_group\tmetadata\n')
        for row in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
            out.write('\t'.join(map(str, (id_map[row[0]], *row[1:]))) + '\n')
    with Path(str(output_prefix) + '.input.fa').open('w') as out:
        for name, seq in sequences.items():
            out.write('>' + id_map[name] + '\n')
            for start in range(0, len(seq), 80):
                out.write(seq[start:start+80].upper() + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'families'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--expected-bp', type=int, required=True)
    parser.add_argument('--output-prefix', type=Path)
    args = parser.parse_args()
    qualify(args.prefix, args.expected_bp, args.output_prefix)
