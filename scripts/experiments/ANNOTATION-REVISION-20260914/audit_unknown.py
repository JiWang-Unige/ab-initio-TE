#!/usr/bin/env python3
"""Audit existing chrX Unknown records without relabeling or opening new test data."""
import argparse
import ast
import collections
import csv
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path('.'))
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    source = a.root / 'reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/fragment_feature_table.tsv'
    mapper = a.root / 'pipelines/PIPE-TEFM-LOCK-20260619/prepare_superfamily5_data.py'
    # Execute only the actual pure historical mapping function; no data loaders.
    tree = ast.parse(mapper.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'map_sf5')
    scope = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(mapper), 'exec'), scope)
    rows = []
    for r in csv.DictReader(source.open(), delimiter='\t'):
        # Inspect eligibility before considering labels/predictions. No chr19-22,
        # reserved utility chromosomes, other species, or new label acquisition.
        if r['species'] != 'human' or r['chrom'] != 'chrX':
            continue
        if r['source'] != 'unknown_annotation':
            continue
        c, f = r['rep_class'], r['rep_family']
        actual = scope['map_sf5'](c, f, '')
        if actual != 5 or r['label_name'] != 'Unknown':
            raise ValueError('archived Unknown disagrees with historical mapping')
        if c.upper() in {'RETROPOSON', 'RC'} and f and '?' not in f:
            reason = 'named_non_main4_taxon'
        elif '?' in c or '?' in f:
            reason = 'ambiguous_annotation'
        else:
            reason = 'other_unknown'
        rows.append(dict(idx=r['idx'], chrom=r['chrom'], start=int(r['start']),
                         end=int(r['end']), rep_class=c, rep_family=f,
                         historical_label='Unknown', mapping_reason=reason))
    if not rows:
        raise ValueError('no eligible archived chrX Unknown rows')
    a.output.mkdir(parents=True, exist_ok=True)
    with (a.output / 'unknown_chrx_audit.tsv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=rows[0], delimiter='\t'); w.writeheader(); w.writerows(rows)
    reasons = dict(collections.Counter(r['mapping_reason'] for r in rows))
    taxa = collections.Counter((r['rep_class'], r['rep_family']) for r in rows)
    result = dict(status='HISTORICAL_ONTOLOGY_DIAGNOSTIC', source=str(source),
                  mapper=str(mapper), eligibility='human chrX archived unknown_annotation only',
                  fragment_count=len(rows), mapping_reasons=reasons,
                  taxonomy=[dict(rep_class=k[0], rep_family=k[1], fragments=v) for k, v in sorted(taxa.items())],
                  historical_mapping_mismatches=0, model_predictions_used=False,
                  new_annotation_validation=False, representative_population_estimate=False,
                  scope='Explains label construction; does not prove model family assignments correct or estimate population annotation error.')
    (a.output / 'unknown_result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
