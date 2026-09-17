#!/usr/bin/env python3
"""Descriptive paired plot; pooled species effects plus all individual windows."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[3]
out = root/'reports/D-CONTEXT-PAIR-20260917'
data = json.loads((out/'run-12848734/result.json').read_text())
species = list(data['per_species'])
names = ['Human','Mouse','Chicken','Zebrafish','Pig','C. elegans']
fig, axes = plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
for index,s in enumerate(species):
    rows = [r for r in data['per_window'] if r['species']==s]
    delta = [100*(r['arms']['bg_dinuc']['sites']['te']['positive_fraction']-r['arms']['native']['sites']['te']['positive_fraction']) for r in rows]
    # Deterministic display offsets, not random resampling.
    axes[0].scatter(delta,index+np.linspace(-.18,.18,len(rows)),s=11,color='#9ba8b5',alpha=.65)
    effect=100*data['per_species'][s]['bg_dinuc_minus_native']['te']['positive_fraction']
    axes[0].scatter([effect],[index],s=54,color='#175a79',marker='D',zorder=4)
    a=data['per_species'][s]['native']['te']['positive_fraction']
    b=data['per_species'][s]['te_dinuc']['te']['positive_fraction']
    axes[1].plot([a,b],[index,index],color='#94a3b8',lw=1.6)
    axes[1].scatter(a,index,s=48,color='#175a79',label='Native' if index==0 else None)
    axes[1].scatter(b,index,s=48,color='#bb6039',label='TE sequence shuffled' if index==0 else None)
for ax in axes:
    ax.set_yticks(range(6),names);ax.invert_yaxis()
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='x',alpha=.16)
axes[0].axvline(0,color='#555',linestyle='--',lw=.8)
axes[0].set_title('A  Only background changed; TE retained',loc='left',fontsize=11)
axes[0].set_xlabel('TE recall change (percentage points)\nGray: each window; diamond: pooled species')
axes[1].set_title('B  TE sequence itself changed',loc='left',fontsize=11)
axes[1].set_xlim(-.03,1.03)
axes[1].set_xlabel('Positive prediction fraction at original TE sites\nShuffled sequence: not a recall metric')
axes[1].legend(loc='center right',frameon=False,fontsize=9)
fig.suptitle('Fixed D: matched composition, different sequence organization\n192 exposed DEV windows; 32 distinct tiles per species; one frozen threshold',fontsize=12)
for ext in ('png','pdf','svg'):
    fig.savefig(out/f'context-pair.{ext}',dpi=180)
svg=out/'context-pair.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
plt.close(fig)
