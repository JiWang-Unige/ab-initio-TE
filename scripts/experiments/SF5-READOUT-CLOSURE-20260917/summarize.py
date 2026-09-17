#!/usr/bin/env python3
"""Re-score a qualified frozen 8-class confusion matrix without new inference."""
import argparse
import json
from pathlib import Path


def ratio(a, b):
    return a / b if b else None


def prf(tp, fp, fn):
    return dict(tp=tp, fp=fp, fn=fn, precision=ratio(tp, tp+fp),
                recall=ratio(tp, tp+fn), f1=ratio(2*tp, 2*tp+fp+fn))


def describe(matrix, rows, labels):
    # Restrict only reference rows. Rejected/uncertain predictions remain errors.
    selected = [[n if i in rows else 0 for n in row] for i, row in enumerate(matrix)]
    total = sum(map(sum, selected))
    per_class = {}
    for i, name in enumerate(labels):
        support = sum(selected[i])
        tp = selected[i][i]
        fp = sum(row[i] for row in selected)-tp
        fn = support-tp
        per_class[name] = dict(support=support, **prf(tp, fp, fn))
    f1s = [per_class[labels[i]]['f1'] for i in (1,2,3,4) if sum(selected[i])]
    material = prf(sum(sum(row[1:]) for row in selected[1:]),
                   sum(selected[0][1:]), sum(row[0] for row in selected[1:]))
    return dict(positions=total, coverage_fraction=total/sum(map(sum, matrix)),
                accuracy=ratio(sum(selected[i][i] for i in range(8)), total),
                main4_macro_f1=sum(f1s)/len(f1s) if f1s else None,
                material=material, classes=per_class,
                predicted_uncertain_positions=sum(row[6]+row[7] for row in selected))


def run(source, original, out):
    replay = json.loads(source.read_text())
    baseline = json.loads(original.read_text())['aggregate']
    matrix, labels = replay['confusion_rows_true_columns_pred'], replay['labels']
    if len(matrix) != 8 or any(len(row) != 8 for row in matrix):
        raise ValueError('Expected complete eight-class matrix')
    if replay['original_integer_metric_differences']:
        raise ValueError('Replay did not reproduce original integer counts')
    full = describe(matrix, set(range(8)), labels)
    if full['positions'] != 2160*4096:
        raise ValueError('Complete frozen TEST denominator changed')
    for name, stats in full['classes'].items():
        for metric in ('tp','fp','fn','support'):
            if stats[metric] != baseline[name.lower()+'_'+metric]:
                raise ValueError('Matrix disagrees with original class counts')
    groups = {'all_eight': full,
              'known_reference_bg_main4_other': describe(matrix,set(range(6)),labels),
              'known_reference_bg_main4': describe(matrix,set(range(5)),labels),
              'conditional_true_main4': describe(matrix,{1,2,3,4},labels)}
    uncertain = {6,7}
    collapsed = prf(sum(matrix[i][j] for i in uncertain for j in uncertain),
                    sum(matrix[i][j] for i in range(8) if i not in uncertain for j in uncertain),
                    sum(matrix[i][j] for i in uncertain for j in range(8) if j not in uncertain))
    result = dict(protocol='SF5-READOUT-CLOSURE-20260917', status='COMPLETED',
                  source=str(source), original=str(original), source_job=replay['job_id'],
                  no_training=True, no_inference=True, exact_original_counts_reproduced=True,
                  selection='posthoc descriptive reference-label subsets; all predictions retained',
                  groups=groups, merged_ambiguous_unclassified=collapsed,
                  per_species_available=False,
                  limitation='Class/status labels are comparator-relative; subset F1 is not improved model performance or evidence of corrected annotation.')
    out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Frozen SF5 readout: full and known-label subsets','',
           'No training or inference was repeated. The completed 12779829 replay matrix exactly reproduces all original TP/FP/FN/support counts on 2,160 windows.', '',
           '| Reference subset | Positions | Coverage | Main4 macro F1 | Material F1 |',
           '|---|---:|---:|---:|---:|']
    for name,g in groups.items():
        lines.append(f"| {name} | {g['positions']} | {g['coverage_fraction']:.6f} | {g['main4_macro_f1']:.6f} | {g['material']['f1']:.6f} |")
    lines += ['', 'Only reference rows were restricted. Predictions of BG or uncertain states remain errors on known TE rows; no uncertain prediction was removed to improve the score.', '',
              'These subsets answer different conditional questions. They do not constitute retraining, representation improvement, unseen-species generalization, or independent correction of Unknown annotations. In particular, conditional_true_main4 excludes background and cannot measure genome-wide detection precision.', '',
              'The recovered compact matrix is pooled; existing per-species full metrics remain available, but per-species conditional metrics cannot be reconstructed from this pooled matrix. No per-species values are imputed.', '',
              'The merged AMBIGUOUS_TE/UNCLASSIFIED state has exact F1 '+f"{collapsed['f1']:.6f}"+'. KNOWN_OTHER_TE is kept separate because it is a known broad-category label, not an uncertainty state.', '',
              'Source: source/frozen-confusion-12779829.json; original: ../SF5-ONTOLOGY-CLOSURE-20260915/run-12731987/test_results.json.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({name: {k:g[k] for k in ('positions','coverage_fraction','main4_macro_f1')} for name,g in groups.items()},indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.original,a.output)
