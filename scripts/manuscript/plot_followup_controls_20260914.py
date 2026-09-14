#!/usr/bin/env python3
"""Standalone manuscript plots from completed, compact experimental outputs."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/manuscript/20260914/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})

def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ['png','pdf','svg']:
        fig.savefig(OUT/f'{name}.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)

def main():
    results=json.loads((ROOT/'reports/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/training-controls-12708540/metrics.json').read_text())
    arms=['kmer6_l2_supcon','ntv2_l2_supcon']
    colors=['#327A78','#9464A6']
    fig,ax=plt.subplots(figsize=(6.6,4.4))
    x=np.arange(2);width=.32
    for i,(metric,title) in enumerate([('top1_accuracy','Top-1'),('family_macro_f1','Macro-F1')]):
        values=[results[a][metric] for a in arms]
        bars=ax.bar(x+(i-.5)*width,values,width,label=title,color=[colors[j] for j in range(2)],
                    alpha=1 if i==0 else .52,edgecolor='white')
        for b,v in zip(bars,values): ax.text(b.get_x()+b.get_width()/2,v+.012,f'{v:.3f}',ha='center',fontsize=10)
    ax.set_xticks(x,['6-mer frequencies\n524,416 parameters','Frozen NTv2 embedding\n131,200 parameters'])
    ax.set_ylim(0,.78);ax.set_ylabel('Retrieval score')
    ax.set_title('Family-supervised contrastive projection',loc='left',weight='bold',pad=15)
    ax.text(.5,-.23,'Same natural-copy split · 29 families · 235 EVAL queries\nL2 inputs · 128-d projection · seed42 · exploratory, previously viewed EVAL',
            transform=ax.transAxes,ha='center',va='top',fontsize=9,color='#555555')
    # Colour denotes the input; opacity denotes the endpoint.
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor='#555555',label='Top-1'),Patch(facecolor='#aaaaaa',label='Macro-F1')],
              loc='upper right',frameon=False)
    fig.tight_layout();save(fig,'retrieval-training-controls')

    data=json.loads((ROOT/'reports/HG19-CHR1-REVISION-20260914-MATCHED/support-12708553/exact-support-12708578.json').read_text())
    groups=[data['strata']['both_exact_acgt'],data['both_exact_by_relation']['ADJACENT'],data['both_exact_by_relation']['ISOLATED']]
    fig,ax=plt.subplots(figsize=(7.0,4.5));x=np.arange(3)
    for i,(key,label,color) in enumerate([('fp_fraction','Old FP','#416CA0'),('tn_fraction','Matched old TN','#B59B65')]):
        vals=[g['support']['TE']['ge80'][key]*100 for g in groups]
        bars=ax.bar(x+(i-.5)*.32,vals,.32,label=label,color=color)
        for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+.45,f'{v:.2f}%',ha='center',fontsize=9)
    ax.set_xticks(x,['All pairs\nn = 18,079','Boundary-adjacent\nn = 16,070','Isolated\nn = 2,009'])
    ax.set_ylim(0,23);ax.set_ylabel('Intervals with ≥80% newer TE coverage (%)')
    ax.set_title('Strict sequence-corresponding, source-matched pairs',loc='left',weight='bold',pad=15)
    ax.legend(frameon=False,ncol=2,loc='upper left')
    ax.text(.5,-.22,'hg19 ↔ CHM13: exact ACGT sequence on both pair members\nControls reused; descriptive overlap, not biological confirmation or corrected F1',
            transform=ax.transAxes,ha='center',va='top',fontsize=9,color='#555555')
    fig.tight_layout();save(fig,'annotation-matched-sequence-support')

if __name__=='__main__':main()
