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

## Execution ledger

The pre-opening contract and seed17 evidence were committed as `779daf4`
and synchronized to the cluster before any CONF-label job. Materialization
and apply-only inference code plus synthetic tests were added in `be3bcae`.
CPU job `12375907` is submitted to private-teodoro-gpu with zero GPU, 2 CPU,
16GB and 30min. It runs three materialization and three inference-contract
tests in the established cluster environment before painting CONF labels.
Output: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/conf_materialization/12375907`.
Logs: `logs/te_l1_conf_material_12375907.{out,err}`.

Phase 1 passed: CPU phase 2/8 jobs, later evaluation at most5/8 with array4,
2/3 directions, evaluation24GB>=20GB, all walltimes<=30min (CI separately
bounded2h), unique job-id outputs/logs and no checkpoint writes, 215TB free,
no reservations, GPU exclusions retained. Not a Track-A architecture screen;
claim_allowed=false. CPU takes the private zero-GPU fast path. GPU routing
will be checked again before submission rather than assuming availability.

CONF-M `12375907` completed 0:0 in 9 seconds; six focused tests passed.
The exact256 tiles/512 halves contain 2,087,374 callable bp and 198,325
positive bp with zero out-of-bounds annotation records. The output summary
confirms chrIV/ce11, original manifest path and no resampling/new coordinates.
This is successful materialization, not a model result.

CONF-E array `12376016` is submitted, task0=42L, task1=42D, task2=17L,
task3=17D. Each consumes the successful `conf_materialization/12375907`;
outputs are `conf_evaluate/12376016_{0,1,2,3}` under the experiment output root.
Logs: `logs/te_l1_conf_eval_12376016_{0,1,2,3}.{out,err}`. CPU success was
verified before submission. Private3090 and sharedA5500 test-only start
estimates both gave Sep5 17:08:23 cluster time; private had six available
allocations and was selected, with unchanged Phase1 constraints.

The paired uncertainty consumer has five passing synthetic tests: weighted
tie AP equals explicit pooled replication, zero-weight score groups do not
corrupt AP, identical paired models cancel under shared draws, absolute
targets are separate from directional improvement, and degenerate AP stays
undefined. It accepts only the actual 256x8192 CONF cache and metric schema,
without alternate-format compatibility. Cache point metrics must reproduce
the authoritative GPU-output metrics within 1e-6 before bootstrapping;
a mismatch blocks interpretation and triggers a minimal engineering fix.

All four `12376016` inference tasks completed 0:0 in 1:47 each. Four finite
metric JSONs confirm the correct seed/arm, CONF256, old CAL-only shared
calibration and identical callable/positive denominators; each has its
nonempty job-specific cache. Exact JSONs are archived under the parent
experiment's `conf/seed42_L`, `conf/seed42_D`, `conf/seed17_L`, `conf/seed17_D`.

| Seed | L CONF F1 | D CONF F1 | L AP | D AP | D precision | D recall |
|---|---:|---:|---:|---:|---:|---:|
| 42 | 0.786766 | 0.794878 | 0.865011 | 0.871452 | 0.839529 | 0.754736 |
| 17 | 0.780510 | 0.803820 | 0.856010 | 0.876104 | 0.825505 | 0.783245 |

Both point-effect directions are positive. Seed42 D fails the absolute
F1>=0.8 target while seed17 passes; do not select the successful seed or call
this robust multi-species usability. CONF segment F1 declines for D in both
seeds (42:0.327273->0.302781; 17:0.327568->0.324635), and fragments/truth
increase (42:0.901639->0.929742; 17:0.898126->0.935597). The frozen guardrails
will be reported separately from improvements; lower missed rate alone
does not mean fragment reconstruction is solved.

Paired CPU assessment `12376069` is submitted with 2 CPU,16GB,2h,zero GPU.
Inputs are exactly the four completed `12376016` task outputs. It runs
the five focused tests, verifies cached point metric reproduction, then
executes the preregistered1000 shared block draws. Output:
`outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/conf_assessment/12376069/assessment.json`;
logs:`logs/te_l1_conf_assess_12376069.{out,err}`. Phase1 passes2/8 jobs,
2/3 directions,noarray/GPU,2h below12h cohort/168h private,unique paths,
no new weights,215TB available and no reservation. CI results are pending.
