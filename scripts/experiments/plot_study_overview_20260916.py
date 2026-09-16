#!/usr/bin/env python3
"""Conceptual map of distinct experiments; contains no inferred measurements."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/manuscript/20260916/figures'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(13,8))
ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
columns=[(.02,.26),(.315,.28),(.63,.35)]
for (x,w),title in zip(columns,['MODEL / EXPERIMENT','MEASURED TARGET','INTERPRETATION BOUNDARY']):
    ax.text(x,.91,title,fontsize=10,fontweight='bold',color='#4d5962')
rows=[
 ('Shared D · NTv2-500M','TE material (L1), comparator runs (L2)\nInternal, external and simulated panels','Reference coverage and true model omissions\nare distinct limitations.','#506cc4'),
 ('Human hg19 source detector','Apparent FP versus matched background\nSupport under two reference libraries','Additional library agreement is evidence\nof support, not confirmed biological rescue.','#7f939d'),
 ('NTv2 representation adaptation','Family-label-free learning on\nTE-enriched natural copies','Clustering performance is not a measure\nof genome-wide TE detection.','#bf9146'),
 ('SF5 class/status model','Complete six-species evaluation\nBroad TE classes and unresolved statuses','A repaired evaluation denominator does not\nestablish a superfamily annotation tool.','#7e77a5'),
 ('Fixed P3 gaps + NT/seam features','Gap-risk information and admissible\nwhole-gap masking actions','Improved score information need not\nproduce an acceptable masking action.','#9b795f'),
 ('P3 · GENERanno-derived mask','Tiberius exact-CDS-chain agreement\nHuman, cattle and platypus panels','Pooled gains coexist with local losses;\nbenefit is specific to the mask and workflow.','#278579'),
]
for i,(model,target,boundary,color) in enumerate(rows):
    y=.78-i*.115
    for j,((x,w),text) in enumerate(zip(columns,[model,target,boundary])):
        box=FancyBboxPatch((x,y),w,.09,boxstyle='round,pad=0.008,rounding_size=0.009',
                           linewidth=1,edgecolor=color,facecolor=color,alpha=.09 if j else .16)
        ax.add_patch(box)
        ax.text(x+.008,y+.045,text,va='center',ha='left',fontsize=9.5,
                fontweight='bold' if j==0 else 'normal',linespacing=1.5)
    for start,end in ((.287,.303),(.602,.618)):
        ax.annotate('',xy=(end,y+.045),xytext=(start,y+.045),
                    arrowprops={'arrowstyle':'->','lw':1,'color':'#819098'})
fig.suptitle('Distinct models answer different annotation questions',x=.03,y=.965,
             ha='left',fontsize=16,fontweight='bold')
fig.text(.03,.022,'L1: TE-associated bases.  L2: contiguous comparator-run topology.  L3: biological insertion identity.\nRows are separate experiments, not stages of one unified model. L3 recovery is not established by these endpoints.',
         fontsize=10,color='#4d5962',linespacing=1.5)
fig.subplots_adjust(left=.015,right=.99,bottom=.08,top=.94)
for ext in ('png','pdf','svg'):fig.savefig(OUT/('study_overview.'+ext),dpi=180)
svg=OUT/'study_overview.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
