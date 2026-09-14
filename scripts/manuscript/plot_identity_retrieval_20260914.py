#!/usr/bin/env python3
"""Plot the fixed hg38 exploratory retrieval comparison from its metric JSONs."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


ARMS = [
    ('single_train_medoid', 'glm_single_train_medoid', 'Single TRAIN medoid'),
    ('k4_natural_prototypes', 'glm_k4_natural_prototypes', 'Four TRAIN medoids'),
    ('random4_natural_prototypes', 'glm_random4_natural_prototypes', 'Four random TRAIN copies'),
    ('basic_train_centroid', 'glm_train_centroid', 'TRAIN centroid'),
    ('single_consensus', 'glm_single_consensus', 'External Dfam consensus'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kmer', type=Path, required=True)
    parser.add_argument('--glm', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    data = [json.loads(p.read_text()) for p in (args.kmer, args.glm)]
    selected = [[data[i]['methods'][arm[i]] for arm in ARMS] for i in range(2)]
    for group in selected:
        for row in group:
            if row['queries'] != 235 or row['families'] != 29:
                raise ValueError('Figure requires the same 29-label, 235-query panel for every arm')

    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.8), sharey=True)
    colors = ['#2878a5', '#d87532']
    labels = ['6-mer frequencies', 'Native NTv2-500M embedding']
    positions = np.arange(len(ARMS))
    for ax, metric, title in zip(axes, ['top1_accuracy', 'family_macro_f1'],
                                 ['Top-1 accuracy', 'Macro family F1']):
        for i, rows in enumerate(selected):
            values = np.array([row[metric] for row in rows]) * 100
            y = positions + (i - 0.5) * 0.30
            ax.barh(y, values, height=0.27, color=colors[i], label=labels[i])
            for yy, value in zip(y, values):
                ax.text(value + 1.0, yy, f'{value:.1f}', va='center', fontsize=8)
        ax.set_xlim(0, 108)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xlabel('Percent')
        ax.set_title(title, loc='left', weight='bold')
        ax.axhline(3.5, color='#9a9a9a', linestyle='--', linewidth=0.8)
        ax.grid(axis='x', alpha=0.18)
        ax.set_axisbelow(True)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis='y', length=0)
    axes[0].set_yticks(positions, [a[2] for a in ARMS])
    axes[0].invert_yaxis()
    fig.suptitle('Exploratory family retrieval on annotated hg38 intervals',
                 x=0.02, ha='left', fontsize=13, weight='bold')
    axes[1].legend(loc='lower right', bbox_to_anchor=(1, 1.08), frameon=False, fontsize=9)
    fig.text(0.02, 0.025,
             '29 exact repeat labels; 235 EVAL queries; identical splits and reference-copy IDs.\n'
             'External Dfam consensus has a different construction history. These scores do not establish tool readiness.',
             fontsize=8, color='#444444')
    fig.subplots_adjust(left=0.24, right=0.98, top=0.80, bottom=0.20, wspace=0.15)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ('svg', 'pdf', 'png'):
        fig.savefig(str(args.output_prefix) + '.' + suffix, dpi=170)
    plt.close(fig)
    print(args.output_prefix)


if __name__ == '__main__':
    main()
