# GENERanno–NTv2 overlap diagnostic (2026-09-03)

## Question

Do independently pretrained backbones place their false-negative TE gaps at sufficiently different coordinates that a simple ensemble can reduce fragmentation without sacrificing base-pair precision or merging distinct comparator runs?

## Frozen screen

- Existing checkpoints only; no training.
- GENERanno eukaryote 0.5B H0, 4096 bp, seed 42.
- Nucleotide Transformer v2 250M multi-species H0, 4096 bp, seed 42.
- Same Human H0 chr17 first 1,200 non-overlapping windows and same labels.
- Raw per-model threshold is fixed at 0.5.
- Strategies: each model alone, OR, AND, mean probability, and a GENERanno-anchor rule that fills only bounded gaps <=512 bp for which NT calls every gap base positive.
- Primary diagnostic: internal false-negative gap coordinate overlap and donor rescue.
- Outcome metrics: bp precision/recall/F1; segment F1 at IoU 0.8; boundary F1 at 5 bp; fragments/truth; split, missed and short-prediction rates; multi-truth-run fusion proxy.

This is a retrospective engineering screen on a previously consumed test region. It may motivate a separately frozen validation, but it cannot support an independent performance claim.

## Decision

- Continue only if at least one non-oracle ensemble reduces fragments/truth by at least 10% relative to the better single model while bp F1 does not fall by more than 0.005, bp precision does not fall by more than 0.005, missed rate does not rise, and the multi-truth fusion proxy does not increase.
- If OR reduces fragmentation only by buying false positives/fusions, or the two internal-gap masks are strongly shared, close naive backbone overlap as a fragment solution.

## Results

Slurm job `12171265` completed successfully. The immutable output is
`outputs/TEFM-BACKBONE-ENSEMBLE-DIAGNOSTIC-20260903/chr17-1200-r1`.

| Strategy | bp precision | bp recall | bp F1 | segment F1 | boundary F1 | fragments/truth | split rate | missed rate | short rate | multi-truth fusions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GENERanno | 0.940860 | 0.942015 | 0.941437 | 0.371277 | 0.232151 | 1.484338 | 0.171795 | 0.058054 | 0.590136 | 826 |
| NTv2 250M | 0.935095 | 0.933165 | 0.934129 | 0.484113 | 0.276285 | 1.093833 | 0.102325 | 0.070723 | 0.302976 | 913 |
| OR | 0.916126 | 0.958157 | 0.936670 | 0.385252 | 0.219305 | 1.212168 | 0.111792 | 0.047195 | 0.511940 | 1,028 |
| AND | 0.961961 | 0.917024 | 0.938955 | 0.451637 | 0.286863 | 1.356954 | 0.155228 | 0.082138 | 0.460374 | 693 |
| Mean probability | 0.944900 | 0.941560 | 0.943227 | 0.423972 | 0.261836 | 1.294584 | 0.132257 | 0.063344 | 0.485947 | 873 |
| GENERanno + NT complete-gap bridge | 0.936646 | 0.947389 | 0.941987 | 0.416437 | 0.258379 | 1.165947 | 0.096199 | 0.058054 | 0.466751 | 1,005 |

The two backbones are genuinely coordinate-complementary: false-negative bp
Jaccard is `0.504277`, while internal-gap bp Jaccard is only `0.161482`.
NT covers 17,121 of 31,039 GENERanno internal-gap bp and fully covers 2,289
of 3,896 GENERanno gap runs. GENERanno covers 14,908 of 29,041 NT gap bp and
fully covers 616 of 1,182 NT gap runs.

## Frozen-gate decision

**FAIL; close naive backbone overlap as the fragment solution.** NTv2 250M is
the better single model for fragmentation at `1.093833` fragments/truth, so
the registered 10% improvement threshold was `<=0.984449`. No ensemble met
it. The closest ensemble, complete-gap bridging, instead reached `1.165947`
(`6.59%` worse than NT) and increased the fusion proxy from 913 to 1,005.
OR also bought recall with lower precision and more fusions. AND reduced the
fusion proxy but raised missed rate and fragmentation. Mean probability had
the best bp F1, but still worsened fragmentation by `18.35%` relative to NT.

This does not show that backbone diversity is absent. It shows that diversity
alone is insufficient: a useful bridge policy must learn which complementary
gap calls are safe. The result therefore supports the separately frozen
Stage 1 gap-risk experiment, but it does not change its data, gates, or claim
boundary. Because chr17 was already consumed, all numbers above remain an
engineering diagnostic and are not an independent scientific endpoint.
