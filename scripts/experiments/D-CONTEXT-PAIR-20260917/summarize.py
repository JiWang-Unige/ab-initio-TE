#!/usr/bin/env python3
"""Summarize the fixed three-arm intervention; no new model or statistical fit."""
import csv
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reports/D-CONTEXT-PAIR-20260917'


def main():
    result = json.loads((OUT / 'run-12848734/result.json').read_text())
    rows = result['per_window']
    table = []
    for species, summary in result['per_species'].items():
        chosen = [row for row in rows if row['species'] == species]
        if len(chosen) != 32 or len({r['tile_id'] for r in chosen}) != 32:
            raise ValueError('The fixed independent-tile sampling contract was not met')
        deltas = [r['arms']['bg_dinuc']['sites']['te']['positive_fraction']
                  - r['arms']['native']['sites']['te']['positive_fraction'] for r in chosen]
        te_bp = sum(r['arms']['native']['sites']['te']['bp'] for r in chosen)
        bg_bp = sum(r['arms']['native']['sites']['bg']['bp'] for r in chosen)
        table.append({
            'species': species, 'windows': len(chosen), 'te_bp': te_bp, 'bg_bp': bg_bp,
            'native_te_recall': summary['native']['te']['positive_fraction'],
            'bg_shuffle_te_recall_delta_pp': 100*summary['bg_dinuc_minus_native']['te']['positive_fraction'],
            'bg_shuffle_interior_recall_delta_pp': 100*summary['bg_dinuc_minus_native']['te_interior']['positive_fraction'],
            'bg_shuffle_te_mean_p_delta': summary['bg_dinuc_minus_native']['te']['mean_p'],
            'bg_shuffle_window_recall_delta_median_pp': 100*median(deltas),
            'bg_shuffle_window_absolute_delta_median_pp': 100*median(abs(d) for d in deltas),
            'bg_shuffle_windows_absolute_delta_at_least_10pp': sum(abs(d)>=.1 for d in deltas),
            'bg_shuffle_window_delta_min_pp': 100*min(deltas),
            'bg_shuffle_window_delta_max_pp': 100*max(deltas),
            'bg_shuffle_windows_recall_down': sum(d < 0 for d in deltas),
            'bg_shuffle_windows_recall_up': sum(d > 0 for d in deltas),
            'bg_shuffle_windows_recall_equal': sum(d == 0 for d in deltas),
            'te_shuffle_original_te_site_positive_fraction': summary['te_dinuc']['te']['positive_fraction'],
            'te_shuffle_original_te_site_mean_p_delta': summary['te_dinuc_minus_native']['te']['mean_p'],
            'bg_changed_fraction': sum(r['arms']['bg_dinuc']['changed_bp'] for r in chosen)/bg_bp,
            'te_changed_fraction': sum(r['arms']['te_dinuc']['changed_bp'] for r in chosen)/te_bp,
        })
    with (OUT/'per-species.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    lines = ['# Fixed-D paired sequence/context intervention', '',
        'Job `12848734` completed: 192 exposed-DEV windows, six species, 32 distinct tiles per species, '
        'three arms. Native inference plus loading took %.2f seconds. No training, calibration refit or sealed data.' % result['wall_seconds'], '',
        '| Species | Native TE recall | BG shuffle Δrecall (pp) | Interior Δrecall (pp) | TE-shuffled original-site positive rate |',
        '|---|---:|---:|---:|---:|']
    for row in table:
        lines.append('| %s | %.4f | %+.3f | %+.3f | %.4f |' % (row['species'],row['native_te_recall'],
                     row['bg_shuffle_te_recall_delta_pp'],row['bg_shuffle_interior_recall_delta_pp'],
                     row['te_shuffle_original_te_site_positive_fraction']))
    lines.extend(['', 'The TE-shuffled column is **not recall**: the biological validity of the original TE labels '
        'does not survive this sequence intervention. It only describes predictions at the original coordinates.', '',
        'Background-only shuffling leaves all TE bases, positions and window boundaries unchanged; '
        'all arms retain exact whole-window mono- and dinucleotide counts. The code checks these properties '
        'during execution. Hard-negative and unknown-labelled bases are protected. Scores use the frozen D '
        'Platt parameters and threshold 0.42330056285498807.', '',
        'In these selected DEV windows, perturbing annotated background has a small pooled effect '
        '(-1.50 to +0.53 percentage points of TE recall), whereas perturbing the TE sequence itself causes '
        'a much larger decrease in original-site positive predictions. This supports sensitivity to TE-local '
        'sequence organization beyond mono-/dinucleotide composition. Higher-order k-mer patterns, internal '
        'context and more complex motifs remain alternative explanations; this does not prove evolutionary '
        'understanding, absence of memorization, or a foundation-model advantage over a k-mer learner.', '',
        'Pooled averages hide local heterogeneity: 21/192 windows change by at least 10 recall percentage '
        'points under background shuffling, with individual changes from -37.85 to +54.88 points. '
        'Species-specific median absolute changes range from 0.44 to 4.65 points. Thus some loci are '
        'strongly context-sensitive; opposite-direction effects can cancel, and the small pooled effect '
        'must not be read as context independence. See the paired plot and every-window records.', '',
        'The native recall values describe the fixed eligibility-selected subset, not the complete DEV panel. '
        'The result does not support treating surrounding-background context as an established explanation '
        'for the prior GARLIC benchmark failure. It does not rule out other context types, sequence-length '
        'effects, tokenization effects, or family-distribution shifts. There is no new independent test, '
        'hypothesis-test p value, or post-hoc alternative perturbation search.', '',
        'See [protocol](../../docs/experiments/D-CONTEXT-PAIR-20260917.md), '
        '[per-species table](per-species.csv), [per-window native result](run-12848734/result.json), '
        'and [pre-inference selection](run-12848734/selection.json). All 192 windows are retained.', '',
        '![Paired intervention](context-pair.png)', '',
        'Figure source: `scripts/experiments/D-CONTEXT-PAIR-20260917/plot.py`; rendered with Matplotlib 3.11.2. '
        'PDF and SVG are provided beside the PNG.', ''])
    (OUT/'RESULTS.md').write_text('\n'.join(lines))
    print(OUT/'RESULTS.md')


if __name__ == '__main__':
    main()
