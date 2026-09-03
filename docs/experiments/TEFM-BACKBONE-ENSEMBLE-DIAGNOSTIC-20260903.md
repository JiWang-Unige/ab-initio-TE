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

Pending Slurm inference.
