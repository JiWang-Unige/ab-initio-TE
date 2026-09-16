#!/usr/bin/env python3
"""Verify compact native evidence and summarize the fixed library comparison."""
import csv
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reports/SPECIES-LIBRARY-CONTROL-20260916'
BUNDLE = OUT / 'score-12743581'
KEYS = ('tp', 'fp', 'fn', 'tn', 'callable_bp')


def read(path):
    return json.loads(path.read_text())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    result = read(BUNDLE / 'score/result.json')
    replay = read(BUNDLE / 'replay/complete.json')
    prep = read(OUT / 'preparation/complete-12743578.json')
    old = read(ROOT / 'docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D/dev_metrics.json')['per_species']
    check(result['status'] == 'COMPLETED' and not result['original_scores_overwritten'], 'Incomplete score')
    check(replay['status'] == 'COUNT_REPRODUCED', 'Unqualified replay')
    check(replay['calibration']['threshold'] == 0.42330056285498807, 'Threshold changed')
    check([r['species'] for r in result['species']] == ['zebrafish', 'pig', 'chicken'], 'Species scope changed')
    checked, summary, metrics, classes = [], [], [], []
    for r, rp, pr in zip(result['species'], replay['species'], prep['species']):
        s = r['species']
        check(s == rp['species'] == pr['species'], 'Species alignment')
        panel = read(BUNDLE / 'prepared' / s / 'panel.json')
        blocks = read(BUNDLE / 'score' / (s + '-blocks.json'))
        check(len(panel) == len(blocks) == len({b['tile_id'] for b in blocks}) == 500, s + ': tile denominator')
        check([b['tile_id'] for b in blocks] == [p['tile_id'] for p in panel], s + ': tile order')
        for b, p in zip(blocks, panel):
            check(b['chrom'] == p['chrom'] and b['block512kb'] == p['start'] // 524288, s + ': block identity')
            check(p['end'] - p['start'] == 8192, s + ': centre length')
        check(rp['exact_counts_match'], s + ': replay mismatch')
        check(rp['counts'] == {k: r['old'][k] for k in KEYS}, s + ': replay/score mismatch')
        for k in ('tp', 'fp', 'fn'):
            check(r['old'][k] == old[s]['bp_' + k], s + ': historical ' + k)
        check(r['old']['callable_bp'] == old[s]['callable_bp'], s + ': historical callable')
        for arm in ('old', 'curated', 'combined'):
            ref = r['old'] if arm == 'old' else r['arms'][arm]
            counts = {k: sum(b[arm][k] for b in blocks) for k in KEYS}
            check(counts == {k: ref[k] for k in KEYS}, s + ': block aggregation ' + arm)
            for b in blocks:
                v = b[arm]
                check(all(isinstance(v[k], int) and v[k] >= 0 for k in KEYS), s + ': invalid count')
                check(sum(v[k] for k in KEYS[:4]) == v['callable_bp'] <= 8192, s + ': partition')
                check(v['tp'] + v['fp'] == b['old']['tp'] + b['old']['fp'], s + ': predictions changed')
                check(v['callable_bp'] == b['old']['callable_bp'], s + ': denominator changed')
            t, f, n = (counts[k] for k in ('tp', 'fp', 'fn'))
            values = dict(precision=t/(t+f), recall=t/(t+n), f1=2*t/(2*t+f+n))
            check(all(math.isclose(ref[k], v, abs_tol=1e-12) for k, v in values.items()), s + ': metric arithmetic')
            metrics.append(dict(species=s, arm=arm, **counts, **values))
        native = []
        for arm in ('curated', 'combined'):
            dest = BUNDLE / 'annotation' / s / arm
            status = read(dest / 'complete.json')
            check(status['status'] == 'COMPLETED' and status['exit_code'] == 0, s + ': native incomplete')
            command = status['command']
            check(command[:6] == ['RepeatMasker', '-pa', '4', '-xsmall', '-gff', '-lib'], s + ': settings')
            check(command[7] == '-dir' and command[6].endswith('/' + s + '/' + arm + '.fa'), s + ': library arm')
            check(command[-1].endswith('/prepared/' + s + '/panel.fa'), s + ': native input')
            table = (dest / 'panel.fa.tbl').read_text()
            length = sum(p['query_end'] - p['query_start'] for p in panel)
            check(int(re.search(r'sequences:\s*(\d+)', table)[1]) == 500, s + ': native sequences')
            check(int(re.search(r'total length:\s*(\d+)', table)[1]) == length, s + ': native length')
            log = (dest / 'native-version.txt').read_text()
            check('RepeatMasker version 4.2.2' in log and 'RMBLAST [ 2.14.1+ ]' in log, s + ': engine version')
            native.append(dict(arm=arm, input_bp=length, sequences=500, seconds=status['seconds'], job_id=status['job_id']))
        lo, hi = r['arms']['curated'], r['arms']['combined']
        a, b, u, v = (r[k] for k in ('added_predicted_positive', 'added_predicted_negative', 'lost_predicted_positive', 'lost_predicted_negative'))
        check(hi['tp'] == lo['tp'] + a - u and hi['fp'] == lo['fp'] - a + u, s + ': positive transition')
        check(hi['fn'] == lo['fn'] + b - v and hi['tn'] == lo['tn'] - b + v, s + ': negative transition')
        check(a == sum(t['added_predicted_positive'] for t in blocks) and b == sum(t['added_predicted_negative'] for t in blocks), s + ': tile additions')
        transitions = r['class_membership_transitions']
        check(sum(t['bp'] for t in transitions) == lo['callable_bp'], s + ': class denominator')
        check(sum(t['bp'] for t in transitions if not t['curated_classes'] and t['combined_classes']) == a+b, s + ': class additions')
        check(sum(t['bp'] for t in transitions if t['curated_classes'] and not t['combined_classes']) == u+v, s + ': class losses')
        check(sum(t['bp'] for t in transitions if t['curated_classes']) == lo['tp']+lo['fn'], s + ': curated class union')
        check(sum(t['bp'] for t in transitions if t['combined_classes']) == hi['tp']+hi['fn'], s + ': combined class union')
        check(sum(x['positive_bp'] for x in r['original_exclusive_class_recall'].values()) + r['mixed_class_positive_bp'] == r['old']['tp']+r['old']['fn'], s + ': exclusive classes')
        if pr['identical_libraries']:
            check(lo == hi and a+b+u+v == 0, s + ': empty-increment control')
        summary.append(dict(species=s, curated_records=pr['curated_records'], combined_records=pr['combined_records'],
                            f1_delta=hi['f1']-lo['f1'], precision_delta=hi['precision']-lo['precision'], recall_delta=hi['recall']-lo['recall'],
                            added_positive_bp=a+b, added_predicted_positive=a, added_predicted_negative=b,
                            added_positive_detection_fraction=a/(a+b) if a+b else None,
                            curated_fp_new_support_fraction=a/lo['fp'], lost_predicted_positive=u, lost_predicted_negative=v,
                            unknown_bp=r['unknown_bp']))
        for cl, values in r['original_exclusive_class_recall'].items():
            classes.append(dict(species=s, exclusive_class=cl, **values))
        checked.append(dict(species=s, historical_counts_exact=True, unique_tiles=500,
                            spatial_blocks=len({(t['chrom'],t['block512kb']) for t in blocks}),
                            block_aggregates_and_transitions_exact=True, native_cells=native))
    write('compact-qualification.json', dict(status='PASS', checks=checked,
          scope='Independent compact-count, historical-metric and native-denominator checks. Original raw-mask reproduction and identical-library position equality were enforced by the HPC scorer; arrays were not copied or rescored locally.',
          historical_pointwise_prediction_identity_proven=False))
    write('summary.json', dict(scope='Descriptive retrospective comparator sensitivity; no biological relabelling or new inference', species=summary))
    for name, rows in [('metrics.tsv', metrics), ('exclusive_class_recall.tsv', classes)]:
        with (OUT / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows({k: 'NA' if v is None else v for k, v in row.items()} for row in rows)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
