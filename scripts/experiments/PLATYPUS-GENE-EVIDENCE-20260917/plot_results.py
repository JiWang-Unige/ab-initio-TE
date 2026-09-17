#!/usr/bin/env python3
"""Export native RNA endpoints with all prespecified comparator arms."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--run', type=Path, required=True)
args = ap.parse_args()
d = json.loads((args.run / 'result.json').read_text())
arms = ['U_soft', 'D', 'R_TE']
colors = ['#8b939c', '#007c83', '#bd762b']
fig, axes = plt.subplots(1, 2, figsize=(10.7, 4.5), gridspec_kw={'width_ratios': [1.3, 1]})
for ai, arm in enumerate(arms):
    x = d['raw_rna_support']['by_arm'][arm]
    for ei, key in enumerate(['all_introns_strict', 'stringtie_exact_intron_chain']):
        pos = ei + (ai-1)*.23
        rate = x[key + '_rate'] * 100
        axes[0].bar(pos, rate, width=.21, color=colors[ai], label=arm if ei == 0 else None)
        axes[0].text(pos, rate+.7, str(x[key+'_count']), ha='center', fontsize=9)
axes[0].set(xticks=[0, 1], xticklabels=['All introns supported', 'Exact assembled\nintron chain'],
            ylabel='Supported multi-exon predictions (%)', ylim=(0, 51), title='A  Blind RNA support by mask')
axes[0].legend(frameon=False, ncol=3, loc='upper right', fontsize=9)
sets = d['posthoc_reference_join']['comparison_sets']['D_minus_U_soft']
for i, label in enumerate(['gained_loci', 'lost_loci']):
    x = sets[label]
    n, supported = x['historical_unit_count'], x['all_introns_strict_count']
    axes[1].bar(i, n, color='#e1e5e8', width=.6)
    axes[1].bar(i, supported, color='#007c83' if i == 0 else '#a04c54', width=.6)
    axes[1].text(i, supported/2, f'{supported} supported', ha='center', va='center', color='white', fontsize=9)
    axes[1].text(i, n+1, f'{n} loci', ha='center', fontsize=10)
axes[1].set(xticks=[0, 1], xticklabels=['Gains with D', 'Losses with D'], ylabel='Reference-relative loci',
            ylim=(0, 58), title='B  Both gains and losses have support')
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('Independent platypus RNA-seq: SRR23268362', fontsize=14, y=.98)
fig.text(.5, .02, 'One fibroblast run; no support does not imply a false gene.  A: 104 Mb including halos; B: 100-Mb gene panel.',
         ha='center', fontsize=9)
fig.tight_layout(rect=[0, .08, 1, .94])
for suffix in ['png', 'pdf', 'svg']:
    out = args.run / ('rna_support.' + suffix)
    fig.savefig(out, dpi=180)
    if suffix == 'svg':
        out.write_text('\n'.join(line.rstrip() for line in out.read_text().splitlines()) + '\n')
