#!/usr/bin/env python3
"""Retrospective arithmetic on the existing six-species D DEV counts only."""
import csv
import json
from math import ceil, isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D/dev_metrics.json')
OUT = ROOT / 'reports/SPECIES-ANNOTATION-DIAGNOSTIC-20260916'


def f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn)


def run():
    original = json.loads((ROOT / SOURCE).read_text())
    target = original['per_species']['zebrafish']['bp_f1']
    trio = [original['per_species'][s] for s in ('zebrafish','pig','chicken')]
    pooled_pi = sum(m['positive_bp'] for m in trio) / sum(m['callable_bp'] for m in trio)
    rows, curves, thinning = [], [], []
    # The whole range is a sensitivity display, not a selected deployment prior.
    prevalence_grid = [i / 100 for i in range(1, 100)]
    for species, m in original['per_species'].items():
        tp, fp, fn, n = (m[k] for k in ('bp_tp', 'bp_fp', 'bp_fn', 'callable_bp'))
        pos, neg = tp + fn, n - tp - fn
        tn = neg - fp
        assert min(tp, fp, fn, tn) >= 0 and pos == m['positive_bp']
        precision, recall, fpr = tp / (tp + fp), tp / pos, fp / neg
        assert isclose(f1(tp, fp, fn), m['bp_f1'], abs_tol=1e-12)
        assert isclose(precision, m['bp_precision'], abs_tol=1e-12)
        assert isclose(recall, m['bp_recall'], abs_tol=1e-12)
        row = dict(species=species, tiles=m['tiles'], callable_bp=n,
                   tp=tp, fp=fp, fn=fn, tn=tn, reference_prevalence=pos/n,
                   precision=precision, recall=recall, f1=m['bp_f1'],
                   reference_negative_fpr=fpr, fp_per_million_callable_bp=fp/n*1e6,
                   balanced_accuracy=(recall + 1-fpr)/2,
                   all_fp_rescue_f1_upper_bound=f1(tp+fp, 0, fn))
        row['f1_at_trio_pooled_prevalence'] = 2*pooled_pi*recall/(pooled_pi*(1+recall)+(1-pooled_pi)*fpr)
        needed = max(0.0, (target*(2*tp+fp+fn)-2*tp)/(2-target))
        row.update(fp_rescue_bp_needed_for_observed_zebrafish_f1=ceil(needed),
                   fp_rescue_fraction_needed=needed/fp,
                   fp_only_rescue_can_reach_observed_zebrafish=needed <= fp)
        for pi in prevalence_grid:
            p = pi*recall / (pi*recall + (1-pi)*fpr)
            value = 2*pi*recall / (pi*(1+recall)+(1-pi)*fpr)
            # Equivalent synthetic contingency-table calculation verifies weighting.
            assert isclose(value, f1(pi*recall, (1-pi)*fpr, pi*(1-recall)), abs_tol=1e-12)
            curves.append(dict(species=species, prevalence=pi, precision=p, f1=value))
            if pi in (0.1, 0.25, 0.5):
                row[f'f1_at_prevalence_{pi}'] = value
        rows.append(row)
        # Proportional removal of existing positive labels, independent of predictions.
        # These fractional cells are an analytical mechanism illustration, NOT a
        # random deletion experiment or an estimate of real annotation missingness.
        for keep in (1.0, 0.9, 0.75, 0.5, 0.25):
            a, b, c, d = keep*tp, fp+(1-keep)*tp, keep*fn, tn+(1-keep)*fn
            assert isclose(a+b+c+d, n, abs_tol=1e-7)
            thinning.append(dict(species=species, retained_positive_fraction=keep,
                                 tp=a, fp=b, fn=c, tn=d, precision=a/(a+b),
                                 recall=a/(a+c), f1=f1(a,b,c)))
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(source=str(SOURCE), scope='Previously observed internal DEV; six trained species',
                  status='RETROSPECTIVE_COUNT_DIAGNOSTIC_COMPLETED',
                  label_scope='RepeatMasker/Dfam comparator, not independent biological truth',
                  actual_labels_or_predictions_changed=False, per_species=rows,
                  descriptive_trio_pooled_prevalence=pooled_pi,
                  prevalence_grid=prevalence_grid,
                  thinning_scope='Analytical proportional-label-removal illustration only')
    (OUT/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for name, items in [('species_counts',rows), ('prevalence_sensitivity',curves),
                        ('analytical_label_thinning',thinning)]:
        with (OUT/(name+'.tsv')).open('w') as f:
            writer=csv.DictWriter(f, fieldnames=list(items[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader();writer.writerows(items)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    run()
