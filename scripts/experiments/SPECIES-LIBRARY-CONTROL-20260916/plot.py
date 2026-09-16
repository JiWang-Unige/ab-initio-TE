#!/usr/bin/env python3
"""Draw the qualified three-species fixed-prediction library sensitivity."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reports/SPECIES-LIBRARY-CONTROL-20260916'
result = json.loads((OUT / 'score-12743581/score/result.json').read_text())['species']
colors = {'zebrafish': '#506cc4', 'pig': '#278579', 'chicken': '#c17e19'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'pdf.fonttype': 42, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), gridspec_kw={'width_ratios': [1, 1.3]})
for i, r in enumerate(result):
    s = r['species']
    y = [r['arms'][arm]['f1'] for arm in ('curated', 'combined')]
    axes[0].plot([0, 1], y, '-o', lw=2, ms=7, color=colors[s], label=s.title())
    for x, v in enumerate(y):
        axes[0].annotate(f'{v:.4f}', (x, v), xytext=(-8 if x == 0 else 8, -14 if s == 'chicken' and x == 0 else 7),
                         textcoords='offset points', ha='right' if x == 0 else 'left',
                         color=colors[s], fontsize=9)
    a, b = r['added_predicted_positive'], r['added_predicted_negative']
    axes[1].barh(i, a / 1000, color='#278579', height=.5, label='Model positive' if i == 0 else None)
    axes[1].barh(i, b / 1000, left=a / 1000, color='#be6658', height=.5, label='Model negative' if i == 0 else None)
    label = f'{a:,} / {b:,} bp' if a+b else '0 / 0 bp (identical libraries)'
    axes[1].text((a+b)/1000 + 12, i, label, va='center', fontsize=9)
axes[0].set(xlim=(-.32, 1.36), ylim=(0, 1.02), xticks=[0, 1],
            xticklabels=['Curated', '+ Uncurated'], ylabel='Comparator bp F1')
axes[0].set_title('A  Same input, model and annotation engine', loc='left', fontweight='bold', fontsize=11)
axes[0].legend(loc='lower left', frameon=False)
axes[0].text(0, -.22, 'Original historical scores are retained separately;\nonly the two new arms isolate the library condition.',
             transform=axes[0].transAxes, fontsize=9, va='top')
axes[1].set(yticks=range(3), yticklabels=[r['species'].title() for r in result],
            xlim=(0, 1200), xlabel='New strict TE reference-positive bases (kb)')
axes[1].invert_yaxis()
axes[1].set_title('B  New reference support mostly exposes misses', loc='left', fontweight='bold', fontsize=11)
axes[1].legend(loc='lower right', frameon=False)
axes[1].text(0, -.22, 'Labels give model-positive / model-negative bp.\nNew library support is not independent biological confirmation.',
             transform=axes[1].transAxes, fontsize=9, va='top')
axes[0].grid(axis='y', alpha=.18); axes[1].grid(axis='x', alpha=.18)
for ax in axes: ax.set_axisbelow(True)
fig.suptitle('Fixed D predictions under a same-release reference-library expansion', x=.06, ha='left', fontsize=14, fontweight='bold')
fig.subplots_adjust(left=.06, right=.985, bottom=.28, top=.82, wspace=.28)
for ext in ('png', 'pdf', 'svg'):
    fig.savefig(OUT / ('library_sensitivity.' + ext), dpi=180)
svg = OUT / 'library_sensitivity.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
