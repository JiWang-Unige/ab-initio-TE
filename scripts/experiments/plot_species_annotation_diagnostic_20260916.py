#!/usr/bin/env python3
"""Plot saved retrospective count diagnostics; no model or label mutation."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'reports/SPECIES-ANNOTATION-DIAGNOSTIC-20260916'
rows = {r['species']:r for r in json.loads((OUT/'summary.json').read_text())['per_species']}
with (OUT/'prevalence_sensitivity.tsv').open() as f:
    curves=list(csv.DictReader(f, delimiter='\t'))
species=['chicken','pig','zebrafish']
colors={'chicken':'#c17e19','pig':'#278579','zebrafish':'#506cc4'}
labels={'chicken':'Chicken','pig':'Pig','zebrafish':'Zebrafish'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axs=plt.subplots(1,3,figsize=(14,4.8))
for i,s in enumerate(species):
    r=rows[s]; color=colors[s]
    axs[0].bar(i-.17,r['f1'],width=.32,color=color)
    axs[0].bar(i+.17,r['all_fp_rescue_f1_upper_bound'],width=.32,
               edgecolor=color,facecolor='none',hatch='///')
    axs[0].text(i-.17,r['f1']+.007,f"{r['f1']:.3f}",ha='center',fontsize=9)
    axs[0].text(i+.17,r['all_fp_rescue_f1_upper_bound']+.007,
                f"{r['all_fp_rescue_f1_upper_bound']:.3f}",ha='center',fontsize=9)
    axs[1].scatter(100*r['reference_negative_fpr'],100*r['recall'],s=90,color=color)
    axs[1].annotate(labels[s],(100*r['reference_negative_fpr'],100*r['recall']),
                    xytext=(6,-13 if s=='zebrafish' else 7),textcoords='offset points',color=color)
    c=[v for v in curves if v['species']==s]
    axs[2].plot([100*float(v['prevalence']) for v in c],
                [float(v['f1']) for v in c],color=color,label=labels[s],lw=2)
    axs[2].scatter(100*r['reference_prevalence'],r['f1'],color=color,edgecolor='white',s=65,zorder=3)
axs[0].axhline(rows['zebrafish']['f1'],color='#506cc4',linestyle=':',lw=1)
axs[0].set(xticks=range(3),xticklabels=[labels[s] for s in species],ylim=(0,1.05),ylabel='Comparator bp F1')
axs[0].set_title('A  Observed score and FP-only ceiling',loc='left',fontweight='bold')
axs[0].text(.01,-.22,'Solid: observed. Hatched: all FP become TP;\noriginal FN fixed, no newly discovered FN.',
             transform=axs[0].transAxes,fontsize=9,va='top')
axs[1].set(xlim=(0,12.5),ylim=(75,100),xlabel='Reference-negative FPR (%)',ylabel='Reference-positive recall (%)')
axs[1].set_title('B  Error rates use different denominators',loc='left',fontweight='bold')
axs[1].text(.01,-.22,'Reference-negative sequence is not verified\nbiological non-TE sequence.',transform=axs[1].transAxes,fontsize=9,va='top')
axs[2].set(xlim=(0,100),ylim=(0,1.02),xlabel='Common hypothetical positive prevalence (%)',ylabel='Reweighted comparator F1')
axs[2].set_title('C  Ranking depends on prevalence',loc='left',fontweight='bold')
axs[2].legend(loc='lower right',frameon=False)
pi=json.loads((OUT/'summary.json').read_text())['descriptive_trio_pooled_prevalence']
axs[2].axvline(100*pi,color='#666666',linestyle=':',lw=1)
axs[2].text(100*pi+1,.18,f'Pooled {100*pi:.2f}%',fontsize=8,color='#555555',rotation=90)
axs[2].text(.01,-.22,'Dots: each species at its observed prevalence.\nReweighting is not annotation correction.',transform=axs[2].transAxes,fontsize=9,va='top')
for ax in axs:ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
fig.suptitle('Frozen six-species D: retrospective internal DEV diagnostic',x=.05,ha='left',fontsize=14,fontweight='bold')
fig.subplots_adjust(left=.05,right=.98,top=.84,bottom=.28,wspace=.34)
for ext in ('png','pdf','svg'):fig.savefig(OUT/f'species_annotation_diagnostic.{ext}',dpi=180)
svg=OUT/'species_annotation_diagnostic.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
