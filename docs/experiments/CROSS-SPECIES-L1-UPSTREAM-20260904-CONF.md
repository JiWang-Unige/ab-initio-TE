# D2 internal-coordinate confirmation: pre-opening contract

Registered 2026-09-05 after seed17 DEV/SCREEN replication and before CONF
label materialization or model inference. Parent protocol:
`CROSS-SPECIES-L1-UPSTREAM-20260904-V1`. This implements the already-registered
D2 confirmation; it does not relax previous targets or add a new CI-sign gate.

## Frozen inputs

Use exactly the 256 role=CONF coordinates in
`outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/manifest.tsv`.
No resampling, new sequence eligibility filtering, label-dependent selection
or changes to the 8192-bp separation from old CAL/DEV. Species c_elegans,
assembly ce11, chrIV (the existing validation chromosome). Reuse the same
genome, raw RepeatMasker source, P>U>N labeling and paired 4096-bp inputs as
the existing materializer. Preserve all coordinates including low-TE tiles.

Paths below are relative to `/home/users/j/jwang/ab-initio-TE`; their resolved
BeeGFS paths are already in the archived calibration JSONs. All four final
checkpoints are fixed at step4000 and use their respective original global
six-species CAL calibration. No fit or threshold selection on CONF.

| Seed / arm | Final model | Frozen calibration |
|---|---|---|
| 42 L | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_0/final_model | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_0/calibration.json |
| 42 D | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json |
| 17 L | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed17/12361196_0/final_model | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed17/12366939_0/calibration.json |
| 17 D | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed17/12361196_1/final_model | outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed17/12366939_1/calibration.json |

| Seed / arm | Platt slope | Intercept | Global threshold |
|---|---:|---:|---:|
| 42 L | 0.677802238212863 | -0.7728241824175831 | 0.4435084784035275 |
| 42 D | 0.6984053956932976 | -0.8050313412075021 | 0.42330056285498807 |
| 17 L | 0.6681605196861854 | -0.7859557480688136 | 0.43609524919283243 |
| 17 D | 0.6961029993535062 | -0.8453810468304979 | 0.4117663438252757 |

## Minimal execution matrix

| Step | Changed variable / output | Dependencies | Budget | Decision affected |
|---|---|---|---|---|
| CONF-M | Existing frozen coordinates become labeled input, no new selection | this contract committed; seed17 replication pass | CPU <=30min, 0 GPU | invalid coordinate/label contract blocks inference, not scientific failure |
| CONF-E | Apply each of four frozen models/calibrations to same CONF | successful CONF-M and focused tests | 4 tasks, <=30min GPU/task (expected a few minutes each) | exact internal point metrics and reusable margin caches |
| CONF-CI | Paired 512kb spatial-block resampling of those predictions | four valid CONF-E outputs | CPU <=2h, no GPU | quantify uncertainty, consistent direction and existing guards/targets separately |

No new checkpoints are created. Caches have an explicit CPU uncertainty
consumer and stay outside Git. Code/configuration/compact results enter Git.
Engineering failures preserve job IDs and causes and are not science no-go.

## Exact paired uncertainty algorithm

1. One block is `(chrom, floor(tile_start / 524288))`. 8192-aligned tiles
   belong wholly to one block. Sort occupied block IDs; B is their count.
2. Generate 1000 bootstrap replicates using NumPy `default_rng(20260905)`;
   each replicate draws B block indices with replacement. Identical draws
   apply to all four models. Do not resample seeds or individual bases/tiles.
3. Pool all callable bp using the sampled block multiplicities. F1/P/R
   come from pooled weighted TP/FP/FN, not means of per-block or per-tile
   metrics. Retain each model's frozen slope/intercept/threshold.
4. AP uses raw float32 margins, descending order with ties grouped, and
   exact weighted cumulative positive/negative counts. No score bins or
   AP averaging. Sort once, then reuse the ordering for each draw.
5. Report point estimates and percentile 2.5/97.5 intervals (`quantile`,
   linear interpolation) for each model's AP/F1/P/R and paired D-L AP/F1
   per seed. Also report the arithmetic mean of the two paired seed deltas
   using the same block draws; this is not a prediction ensemble and does
   not estimate uncertainty across the population of training seeds.
6. If a resample makes a metric undefined, record it; never silently drop
   or replace the draw. The affected CI is unavailable, with the full
   point estimate and reason retained. No result-dependent resampling.

The block size is fixed from the existing D0 spatial diagnostic, not chosen
using CONF outcomes. Report occupied block count. Blocks on one chromosome
are not guaranteed independent; these intervals describe conditional spatial
uncertainty within this panel, not unseen-species or genome-wide uncertainty.

## Decision and claim boundaries

For both seeds, report whether CONF D-L AP and F1 retain positive direction
and unchanged topology guards: segment F1@IoU0.8 and legacy joint boundary5
drop<=0.05; fragments/truth and split each<=1.25x; missed increase<=0.03.
Previously computed nonworm DEV and macro DEV hardN guards remain part of
the paired record; do not replace them with CONF-only guards.

Separately report D CONF F1>=0.8 and P/R>=0.75 for each seed, alongside the
original six-species DEV targets and macro DEV F1>=0.83. Do not average
away a failed seed/species or choose only seed17. CI bounds are reported
evidence, not a newly added mandatory significance threshold. A positive
coverage effect can coexist with failure of the absolute usability targets.

This is prospective confirmation on new coordinates of a seen species and
an already-used validation chromosome. It is not a new species/chromosome
holdout, independent biological truth, complete-TE reconstruction, or a
publication/public-release authorization. Reserved worm chromosome and
horse/opossum/dm6/cattle stay sealed. No family/homology-clean split is assumed.
After this one evaluation, close the bounded pilot honestly and consult Pro
for the next independent experiment; no CONF-driven threshold/sample sweep.
