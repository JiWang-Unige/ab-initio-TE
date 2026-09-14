#!/usr/bin/env python3
"""Qualify actual annotation changes between two UCSC tables on the same mm10 assembly."""
import argparse
import collections
import csv
import gzip
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://hgdownload.soe.ucsc.edu/goldenPath/mm10/database/'
TABLES = ('rmskOutBaseline', 'rmskOutCurrent')
TE_CLASSES = {'SINE', 'LINE', 'LTR', 'DNA', 'RC', 'RETROPOSON'}
CHROMS = {f'chr{i}' for i in range(1, 20)} | {'chrX', 'chrY', 'chrM'}


def union(intervals):
    out = []
    for s, e in sorted(intervals):
        if not 0 <= s < e:
            raise ValueError(f'invalid half-open interval {(s, e)}')
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(e, out[-1][1]))
        else:
            out.append((s, e))
    return out


def bp(intervals):
    return sum(e-s for s, e in intervals)


def shared(a, b):
    i = j = total = 0
    while i < len(a) and j < len(b):
        total += max(0, min(a[i][1], b[j][1]) - max(a[i][0], b[j][0]))
        if a[i][1] <= b[j][1]: i += 1
        else: j += 1
    return total


def fetch(url, dest):
    if dest.exists():
        raise FileExistsError(f'output acquisition already exists: {dest}')
    partial = dest.with_suffix(dest.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as f:
        headers = dict(response.headers)
        shutil.copyfileobj(response, f)
    partial.rename(dest)
    return dict(url=url, path=str(dest), bytes=dest.stat().st_size,
                acquired_utc=datetime.now(timezone.utc).isoformat(),
                last_modified=headers.get('Last-Modified'), etag=headers.get('ETag'))


def load_table(path):
    records = collections.Counter()
    scopes = {name: collections.defaultdict(list) for name in ('all_repeat', 'known_te', 'potential_te')}
    raw_classes = collections.Counter()
    total = excluded = 0
    with gzip.open(path, 'rt') as f:
        for line in f:
            r = line.rstrip('\n').split('\t')
            if len(r) != 17:
                raise ValueError(f'{path}: expected UCSC 17-column rmsk schema, got {len(r)}')
            total += 1
            chrom = r[5]
            if chrom not in CHROMS:
                excluded += 1; continue
            s, e = int(r[6]), int(r[7])
            if not 0 <= s < e:
                raise ValueError(f'invalid interval {chrom}:{s}-{e}')
            key = (chrom, s, e, r[9], r[10], r[11], r[12])
            records[key] += 1
            raw_classes[r[11]] += 1
            scopes['all_repeat'][chrom].append((s, e))
            c = r[11].upper()
            is_te = c.split('/')[0] in TE_CLASSES and '?' not in c
            potential = is_te or c.rstrip('?').split('/')[0] in TE_CLASSES or c in {'UNKNOWN', 'UNKNOWN?'}
            if is_te: scopes['known_te'][chrom].append((s, e))
            if potential: scopes['potential_te'][chrom].append((s, e))
    merged = {name: {chrom: union(v) for chrom, v in d.items()} for name, d in scopes.items()}
    return records, merged, dict(total_source_records=total,
                                 excluded_noncanonical_records=excluded,
                                 included_records=sum(records.values()),
                                 normalized_distinct_records=len(records),
                                 raw_class_counts=dict(raw_classes))


def compare(old, new):
    rows = []
    for scope in ('all_repeat', 'known_te', 'potential_te'):
        for chrom in sorted(CHROMS):
            a, b = old[scope].get(chrom, []), new[scope].get(chrom, [])
            ab = shared(a, b); aa, bb = bp(a), bp(b)
            rows.append(dict(scope=scope, chrom=chrom, baseline_bp=aa, current_bp=bb,
                             shared_bp=ab, baseline_only_bp=aa-ab, current_only_bp=bb-ab))
    return rows


def run(output, acquire):
    if (output / 'result.json').exists():
        raise FileExistsError('do not overwrite a completed annotation audit')
    output.mkdir(parents=True, exist_ok=True)
    raw = output / 'raw'; raw.mkdir(exist_ok=True)
    sources = []
    if acquire:
        for table in TABLES:
            for suffix in ('.sql', '.txt.gz'):
                sources.append(fetch(BASE+table+suffix, raw/(table+suffix)))
        (output/'acquisition.json').write_text(json.dumps(sources, indent=2)+'\n')
    else:
        sources = json.loads((output/'acquisition.json').read_text())
    old_records, old_masks, old_meta = load_table(raw/(TABLES[0]+'.txt.gz'))
    new_records, new_masks, new_meta = load_table(raw/(TABLES[1]+'.txt.gz'))
    # IDs, alignment scores and consensus offsets are not label identity;
    # retain multiplicity for the normalized coordinate/strand/taxon records.
    common_count = sum(min(n, new_records.get(k, 0)) for k, n in old_records.items())
    rows = compare(old_masks, new_masks)
    scope_totals = {scope: {key: sum(r[key] for r in rows if r['scope']==scope)
                           for key in ('baseline_bp','current_bp','shared_bp','baseline_only_bp','current_only_bp')}
                    for scope in old_masks}
    changes = scope_totals['potential_te']['baseline_only_bp'] + scope_totals['potential_te']['current_only_bp']
    result = dict(status='MATERIAL_CHANGES_PRESENT_PROVENANCE_OPEN' if changes else 'NO_TE_MATERIAL_CHANGE_ON_CANONICAL_MM10',
                  scope='annotation qualification only; no model, FP rescue, or accuracy claim',
                  assembly='mm10 GCA_000001635.2', chromosomes=sorted(CHROMS), sources=sources,
                  baseline=old_meta, current=new_meta,
                  normalized_record_common=common_count,
                  normalized_record_baseline_only=sum(old_records.values())-common_count,
                  normalized_record_current_only=sum(new_records.values())-common_count,
                  normalized_record_fields=['chrom','start0','end','strand','name','class','family'],
                  material=scope_totals, annotation_generation_provenance_closed=False,
                  same_engine_same_library_control=False,
                  note='File timestamps are database dump metadata, not generation dates. Known TE excludes ambiguous/Unknown; potential TE retains them separately. No claim of complete negative truth.')
    with (output/'per_chrom.tsv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],delimiter='\t');w.writeheader();w.writerows(rows)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'STATUS').write_text(result['status']+'\n')
    print(json.dumps({k:result[k] for k in ('status','normalized_record_common','normalized_record_baseline_only','normalized_record_current_only','material')},indent=2))


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--acquire',action='store_true');a=ap.parse_args();run(a.output,a.acquire)
