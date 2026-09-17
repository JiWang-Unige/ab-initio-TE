#!/usr/bin/env python3
"""Audit fixed representation-panel coordinates against actual D exposures.

This does not select or remove evaluation records. Matching overlapping DNA
substantiates an exposure; absent coordinate overlap is not a homology audit.
"""
import argparse
import bisect
import collections
import gzip
import json
from pathlib import Path


def records(path):
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def audit(root):
    panel = root / 'outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512'
    source = root / 'outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202'
    override = root / 'outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/TRAIN/c_elegans.jsonl.gz'
    species = ('human', 'mouse', 'chicken', 'zebrafish', 'pig', 'c_elegans')
    indexes, provenance = {}, {}
    for split in ('TRAIN', 'CAL', 'DEV'):
        for sp in species:
            path = override if (sp, split) == ('c_elegans', 'TRAIN') else source / split / (sp + '.jsonl.gz')
            chroms = collections.defaultdict(list)
            assemblies = set()
            for row in records(path):
                s, e = int(row['start']), int(row['end'])
                seq = row['sequence'].upper()
                if len(seq) != e - s:
                    raise ValueError('D sequence/coordinate length mismatch')
                chroms[row['chrom']].append((s, e, seq))
                assemblies.add(row.get('assembly'))
            for chrom, values in chroms.items():
                values.sort()
                if any(a[1] > b[0] for a, b in zip(values, values[1:])):
                    raise ValueError('Unexpected overlapping D source intervals')
                indexes[sp, split, chrom] = ([v[0] for v in values], values)
            provenance[sp + ':' + split] = {'path': str(path), 'assemblies': sorted(assemblies),
                                          'records': sum(map(len, chroms.values()))}
    counts = collections.defaultdict(collections.Counter)
    overlapping_records = []
    for sib_split in ('train', 'val', 'test'):
        for row_id, row in enumerate(records(panel / sib_split / 'data.jsonl.gz')):
            sp, chrom = row['species_code'], row['chr']
            s, e, sequence = int(row['start']), int(row['end']), row['sequence'].upper()
            if len(sequence) != e - s:
                raise ValueError('SIB sequence/coordinate length mismatch')
            for d_split in ('TRAIN', 'CAL', 'DEV'):
                c = counts[sib_split, sp, d_split]
                c['panel_records'] += 1
                c['panel_bp'] += e - s
                if sp not in species:
                    c['species_absent_from_D_supervision'] += 1
                    continue
                starts, values = indexes.get((sp, d_split, chrom), ([], []))
                pos = max(0, bisect.bisect_right(starts, s) - 1)
                overlap_bp = matching_bp = 0
                while pos < len(values) and values[pos][0] < e:
                    ds, de, dseq = values[pos]
                    a, b = max(s, ds), min(e, de)
                    if a < b:
                        overlap_bp += b - a
                        matching_bp += sum(x == y for x, y in zip(sequence[a-s:b-s], dseq[a-ds:b-ds]))
                    pos += 1
                c['overlap_bp'] += overlap_bp
                c['sequence_matching_overlap_bp'] += matching_bp
                if overlap_bp:
                    c['overlapping_records'] += 1
                    c['fully_covered_records'] += int(overlap_bp == e - s)
                    c['overlap_sequence_mismatch_records'] += int(matching_bp != overlap_bp)
                    overlapping_records.append({'panel_split': sib_split, 'row_index': row_id, 'species': sp,
                                                'chrom': chrom, 'start': s, 'end': e, 'D_split': d_split,
                                                'overlap_bp': overlap_bp, 'sequence_matching_bp': matching_bp})
    return {'status': 'COMPLETE', 'panel': str(panel), 'D_sources': provenance,
            'rows': [dict(panel_split=k[0], species=k[1], D_split=k[2], **v) for k, v in sorted(counts.items())],
            'overlapping_records': overlapping_records,
            'interpretation': 'Retrospective representation diagnostic. No panel changes. Coordinate-matched DNA exposure is measured; non-overlap does not establish sequence-homology or pretraining independence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'summary_rows': len(result['rows']),
                      'overlapping_record_exposure_pairs': len(result['overlapping_records'])}))
