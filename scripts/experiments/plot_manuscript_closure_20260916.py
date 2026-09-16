#!/usr/bin/env python3
"""Plot qualified compact results; never estimate intervals from summary means."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/manuscript/20260916/figures'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'svg.fonttype':'none'})


def save(fig,name):
    for ext in ('png','pdf','svg'): fig.savefig(OUT/(name+'.'+ext),dpi=180)
    svg=OUT/(name+'.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


bench=json.loads((ROOT/'reports/TE-LONG-BENCH-20260915/score-12739923/result.json').read_text())['datasets']['sim100']
methods=['fixed_rm','earlgrey','rm2_rm','edta','hite','D_gpu']
names={'fixed_rm':'Fixed RepeatMasker*','earlgrey':'EarlGrey*','rm2_rm':'RepeatModeler2 → RM',
       'edta':'EDTA','hite':'HiTE','D_gpu':'Frozen D'}
fig,ax=plt.subplots(1,2,figsize=(12,5.1),gridspec_kw={'width_ratios':[1.3,1]})
for i,m in enumerate(methods):
    value=bench['metrics'][m]['f1']
    ax[0].barh(i,value,color='#506cc4' if m=='D_gpu' else '#7f939d',
               hatch='//' if m in ('fixed_rm','earlgrey') else None)
    ax[0].text(value+.008,i,f'{value:.3f}',va='center',fontsize=9)
ax[0].set(yticks=range(6),yticklabels=[names[m] for m in methods],xlim=(0,1.08),xlabel='Generation-truth material F1')
ax[0].invert_yaxis();ax[0].set_title('A  Complete 100-Mb simulation',loc='left',fontweight='bold')
for i,m in enumerate(methods[:-1]):
    r=bench['comparisons']['D_gpu_minus_'+m];x=r['delta'];lo,hi=r['ci95']
    ax[1].errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt='o',color='#506cc4',capsize=3)
ax[1].axvline(0,color='#666666',linestyle=':',lw=1)
ax[1].set(yticks=range(5),yticklabels=[names[m] for m in methods[:-1]],xlim=(-.57,.02),xlabel='D minus comparator F1 (95% interval)')
ax[1].invert_yaxis();ax[1].set_title('B  Paired within-input differences',loc='left',fontweight='bold')
fig.suptitle('Frozen D has low material recall on this known-library simulation',x=.03,ha='left',fontsize=14,fontweight='bold')
fig.text(.03,.04,'* Reference-assisted workflows; all 366 generating records have name/accession coverage in the fixed library.\nIntervals: 100 fixed 1-Mb blocks, 10,000 paired draws. CB4 precision/F1 are undefined; its EDTA failure is not scored zero.',fontsize=9)
fig.subplots_adjust(left=.19,right=.97,top=.83,bottom=.23,wspace=.8)
save(fig,'long_benchmark')

tib=json.loads((ROOT/'reports/P3-TIBERIUS-EXTERNAL-20260915/full-r1-score-12740044/result.json').read_text())
assert tib['completed_cells']==200 and tib['status']=='COMPLETED'
fig,ax=plt.subplots(1,2,figsize=(12,5.4),gridspec_kw={'width_ratios':[1.3,1]})
arms=['R_TE','U_soft','U_nosm'];colors={'cow':'#278579','platypus':'#a564a8'}
labels=[];gainlabels=[]
for j,s in enumerate(('cow','platypus')):
    for i,a in enumerate(arms):
        y=j*4+i;r=tib['species'][s]['comparisons']['P_minus_'+a];x=r['f1_delta'];lo,hi=r['bootstrap']['ci95']
        ax[0].errorbar(x,y,xerr=[[x-lo],[hi-x]],fmt='o',color=colors[s],capsize=3)
        labels.append((y,('Cattle' if s=='cow' else 'Platypus')+' · P − '+a))
    for i,a in enumerate(('R_TE','U_nosm')):
        y=j*3+i;r=tib['species'][s]['comparisons']['P_minus_'+a]
        g=len(r['gained_loci']);l=len(r['lost_loci'])
        ax[1].barh(y,g,color=colors[s]);ax[1].barh(y,-l,color=colors[s],alpha=.35,hatch='//')
        ax[1].text(g+2,y,str(g),va='center',fontsize=9);ax[1].text(-l-2,y,str(l),va='center',ha='right',fontsize=9)
        gainlabels.append((y,('Cattle' if s=='cow' else 'Platypus')+' vs '+a))
ax[0].set(yticks=[x[0] for x in labels],yticklabels=[x[1] for x in labels],xlim=(-.03,.23),xlabel='P minus comparator locus F1 (95% interval)')
ax[0].invert_yaxis();ax[0].axvline(0,color='#666666',linestyle=':',lw=1)
ax[0].set_title('A  Gains depend on the comparison',loc='left',fontweight='bold')
ax[1].set(yticks=[x[0] for x in gainlabels],yticklabels=[x[1] for x in gainlabels],xlim=(-55,110),xlabel='Lost ← correct reference loci → gained')
ax[1].invert_yaxis();ax[1].axvline(0,color='#666666',linestyle=':',lw=1)
ax[1].set_title('B  Pooled benefit coexists with loss',loc='left',fontweight='bold')
fig.suptitle('External P3 masking utility: 40 cores, all 200 planned cells',x=.03,ha='left',fontsize=14,fontweight='bold')
fig.text(.03,.035,'Intervals: ten chromosome clusters per species, 10,000 paired draws. P is GENERanno-derived P3, not shared D.\nU_soft: same checkpoint, unmasked input. U_nosm: official unmasked workflow with a different checkpoint.\nNo superiority or equivalence to R_TE established. Locus losses measure reference agreement, not biological gene deletion.',fontsize=9)
fig.subplots_adjust(left=.19,right=.97,top=.83,bottom=.25,wspace=.75)
save(fig,'external_tiberius')
