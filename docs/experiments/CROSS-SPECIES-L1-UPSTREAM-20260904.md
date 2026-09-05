# L1 upstream coverage pilot, 2026-09-04

## Decision and evidence boundary

**Current status: bounded D0-D2 coverage pilot closed.** CPU uncertainty
job12376069 completed0:0. CONF D-L point AP/F1 directions and original guards
pass for both seeds, but D CONF F1=0.794878/0.803820 for seeds42/17; stable
absolute usability is not achieved. Seed42 effect intervals include zero.
Full closure and frozen spatial CIs are in
`CROSS-SPECIES-L1-UPSTREAM-20260904-CONF.md`; exact evidence is in `conf/`.
The original preregistration and chronological ledger below are retained.
No additional training/sweep or external-panel opening is released by this
pilot. Next independent hypothesis requires evidence-backed Pro discussion
and a new bounded protocol, not changing these gates.

Proceed with a bounded upstream diagnostic and a matched shared-model coverage
experiment, conditional on diagnostic and coordinate feasibility. The previous
B0 recovery failure, B2 rejection and conditional-model closure remain valid.
Current three-seed worm B0 mean F1 is 0.792314 versus B1 0.757651; mean raw AP
gain is 0.020882. This motivates a new test but does not identify the cause.

Source commit: `aab2a25a4f1777f09bda178fc6b290c067174015`.
Advisory review: [ChatGPT Pro discussion](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6a9b26e0-59c0-83eb-bc94-a5c5d683de9a).
Pro reported reading that fixed commit and did not run models. Codex checked
the local training, materialization and evaluation implementations separately.
User explicitly authorized consultation followed by execution, including the
new matched 4,000-step pilot budget; no additional approval is needed.

B1 shows each worm tile about 1.33 times, B0 eight times. Neither tests more
than 1,500 independent worm coordinates. A 4,000-step matched shared-model
comparison exposes every tile in both the original and doubled worm pool.

The 6-bp output grid cannot plausibly impose a 0.79 ceiling by itself: using
389,795 positive bp and 1,539 truth runs, a majority-token predictor has a
conservative attainable F1 lower bound of 0.988013. This is a mathematical
bound, not an observed result. Exact label-oracle computation checks the
implementation and quantifies the ceiling. Input representation, context and
learnability remain separate questions.

## Experiment matrix frozen before new result inspection

| ID | Hypothesis / changed variable | Data and split | Method / metrics | Release or stop condition | Budget / dependency | Allowed interpretation |
|---|---|---|---|---|---|---|
| D0-C | Output quantization limits attainable agreement | worm TRAIN/CAL/DEV and five other species DEV | exact token-constant label oracle, mixed-token counts, existing topology at bp-optimal oracle | worm ceiling below mathematical bound triggers implementation investigation; no automatic head experiment | CPU, <=30 min | output-space diagnostic, never model performance |
| D0-M | New independent coordinates can be constructed | same four worm TRAIN chromosomes; same CAL/DEV chromosome | label-blind SCREEN512, nested TRAIN3000, coordinate-only CONF256; 8192-bp separation where specified | insufficient coordinates blocks that panel; no shrinking buffer or label-based resampling | CPU, <=30 min | coordinate feasibility only |
| D0-G | Fit/generalization and calibration can be distinguished | seed42 B0/B1 full TRAIN/CAL/DEV/new SCREEN; B1 seeds17/20260903 CAL/DEV | frozen inference, raw AP, AP at CAL prevalence, pooled F1/P/R/NLL, TRAIN threshold oracle, matched worm-CAL diagnostic | B0 TRAIN APpi<.90 and oracle F1<.90 -> engineering review then initialization branch; APpi>=.95 and gaps to CAL and SCREEN>=.05 -> coverage priority; otherwise one bounded coverage test | <=1 GPU hour, after D0-M; no weight updates | exploratory diagnostics; no deployment species-specific threshold |
| D0-S | Errors concentrate in specific material/context strata | cached seed42 margins, binary labels, raw worm RepeatMasker | spatial512kb, positive-run length, positive class recall/FN, mixed tokens, boundaries, seams, nonACGT/P overlap | informs interpretation; does not permit changing sampling or old masks | CPU, cache consumer after D0-G | no class precision; no biological-copy claim |
| D1-L | More shared-model optimization improves internal performance | original six-species TRAIN1500; old CAL; new SCREEN; old DEV once | complete H0, unchanged NTv2/head/loss, balanced ERM, 4000 steps/400 warmup, seed42, final step | matched control, not old B1-2000 replacement evidence by itself | ~75-85 GPU min, after D0 | new development pilot |
| D1-D | Independent worm coordinate coverage improves the unified model | same as L except worm nested TRAIN3000 | exactly L recipe and compute; five nonworm sampler streams identical | SCREEN AP and F1 gains each>=.01 plus guardrails -> D2 paired replication | ~75-85 GPU min, parallel with L | coverage effect at this fixed compute budget |
| D2 | Signal replicates at another seed and unused coordinates | seed17 matched L/D if D released; CONF only after models/calibration freeze | same frozen recipe; paired spatial-block confidence intervals | consistent AP/F1 direction and guardrails; separately require worm CONF F1>=.8/P,R>=.75 and six-species targets | conditional ~2.5 GPU hours plus inference | prospective internal-coordinate confirmation, not unseen species |

The pilot uses computational RepeatMasker+Dfam Label-A, with unchanged P>U>N
priority, including P-overlapping nonACGT bases. The legacy boundary5/25 metric
requires an IoU>=0.8 matched interval with both ends within tolerance. Neither
metric is independent endpoint F1. No family or homology-clean split is claimed.

## Sampling and sealing

SCREEN512 is label-blind, on the four existing TRAIN chromosomes, at least
8192 bp from old TRAIN intervals. TRAIN3000 contains the original 1500 tiles
and 1500 new coordinates from those same chromosomes, excluding SCREEN plus
8192-bp flanks. Quotas are proportional to eligible candidate counts with the
original 10%-30% chromosome contribution bounds on each four-chromosome pool.
Sampling uses deterministic seed 20260904. Coordinates are 8192 aligned and
retain the original <=1% nonACGT eligibility filter. No TE mass or model-error
filtering is permitted. Quota infeasibility blocks the affected panel.

CONF256 is selected on the existing validation chromosome, at least 8192 bp
from old CAL/DEV. Only its coordinates are prepared now; sequence is used only
for the same label-blind eligibility QC, with no CONF sequence export, label
painting or model prediction before D2 model freeze.
If CONF is infeasible at the requested buffer, results remain an engineering
pilot; the reserved chromosome is not used to rescue confirmation.

Old DEV is an already-used development panel. SCREEN shares TRAIN chromosomes
but has new separated coordinates, so is also a development panel. CONF is
new coordinates on the old validation chromosome, not an independent chromosome.
The reserved worm chromosome and horse/opossum/dm6/cattle remain sealed for this
round. Prior historical project exposure must be audited before any claim that
an external species has never been seen. Plant work is deferred.

## Diagnostic and training decisions

APpi reweights positive/negative bases to worm CAL prevalence for cross-split
diagnosis. Natural pooled AP and F1 remain the ordinary performance measures.
Complete TRAIN pooling is required; window means and a few logged losses are
insufficient. Raw margins are cached at float32 with coordinates/masks for the
explicit D0-S consumer, avoiding repeated GPU inference.

D0-G must reproduce the already-frozen corresponding DEV metrics within 1e-6.
A mismatch is an engineering failure, not a scientific no-go. Failed jobs retain
their job-specific error/output paths and are excluded from the scientific denominator.

D1-D releases paired seed17 only when SCREEN delta AP>=.01 and delta F1>=.01
and all guardrails pass relative to D1-L: nonworm DEV F1 drop<=.01;
segment F1@.8 and joint boundary5 drop<=.05; fragments/truth and split <=1.25x;
missed increase<=.03, on each species DEV and worm SCREEN; macro DEV hardN FP
increase<=.005. Old B1 is descriptive only.

If D fails release but L reaches F1>=.8 and P/R>=.75 on every species DEV and
worm SCREEN, with macro DEV F1>=.83, only L seed17 is released. Otherwise the
round stops with weak/no evidence. No further duration, pool-size or threshold
sweep is released. Two seeds do not open external evaluation; seed20260903 and
reserved/external evaluation require the eventual frozen full protocol.

If D0 shows poor TRAIN fit after engineering consistency passes, replace the
coverage pair with one initialization pair: H0 encoder plus fresh binary head
versus original NTv2 pretrained encoder plus the identical fresh head; same
TRAIN1500, 4000/400 schedule, optimizer, global CAL and stopping rules. No
coverage x initialization matrix. That branch requires its concrete checkpoint
loading contract to be recorded before submission.

## Execution ledger

### CONF point results: positive effect, absolute target still unstable

The once-only CONF pipeline now has valid materialization `12375907` and
four completed inference tasks `12376016`. See the pre-opening contract and
ledger in `CROSS-SPECIES-L1-UPSTREAM-20260904-CONF.md`; exact metrics are
archived in `conf/`. D CONF F1 is 0.794878 (seed42) and 0.803820 (seed17),
versus L 0.786766 and 0.780510. Both AP/F1 effects retain positive direction,
but seed42 fails the absolute0.8 target. No robust all-species usability or
fragment-solution claim. CPU paired uncertainty job `12376069` is pending
completion; no additional training, resampling or threshold sweep is released.

### Seed17 evaluation complete: internal signal replicated

Evaluation `12366939_0` and `_1` completed 0:0 in 14:29 and 14:30.
All six JSON artifacts are finite and consistent with seed17 L/D,
six-species CAL-only calibration, model paths and DEV/SCREEN scopes.
Exact compact artifacts and `assess_replication.py` output are in `seed17/`.
Decision: `PROCEED_TO_PREREGISTERED_CONF`, not public release.

| Species / panel | L bp F1 | D bp F1 |
|---|---:|---:|
| human DEV | 0.940738 | 0.941099 |
| mouse DEV | 0.940696 | 0.940104 |
| chicken DEV | 0.840266 | 0.836385 |
| zebrafish DEV | 0.929808 | 0.929588 |
| pig DEV | 0.893931 | 0.894193 |
| c_elegans DEV | 0.788782 | 0.807216 |
| c_elegans SCREEN | 0.794581 | 0.807310 |

Seed17 SCREEN AP improves 0.871961 -> 0.884926 (+0.012965), and F1
improves +0.012729. All original guards pass, including macro DEV hardN
FP increase 0.002243 <=0.005. D reaches all six DEV F1 targets for this
seed, but seed42 worm DEV remains 0.797565: no across-seed all-species
success claim. SCREEN fragment/truth rises 0.971196 -> 1.018785 and segment
F1 declines 0.340151 -> 0.328025 despite higher bp recall; this is not a
fragment solution. The matched coverage signal has replicated on internal
coordinates and is eligible for the already-registered one-time CONF step.

The concrete pre-opening contract is recorded in
`CROSS-SPECIES-L1-UPSTREAM-20260904-CONF.md`. All four models and calibrations
are final; no best-seed selection, recalibration or additional training.
Attempted Pro follow-up was blocked by the local Mac lock screen. No new
Pro advice is claimed; the existing authorized CONF protocol continues.

### Seed17 training complete; paired evaluation running

Training `12361196_0` (L) and `_1` (D) completed 0:0 in 1:15:38 and
1:15:54. Both full logs contain steps 1..4000, finite six-species losses and
uniform ERM weights. Metadata confirms seed17, corresponding arm and 4000/400
schedule; final model/config/tokenizer files are present. Exposure is 4000
presentations per species, with 1500 unique tiles for L and all nonworm D
species, and 3000 for worm D. This establishes engineering completion only.

Paired evaluation array `12366939` is running on gpu034, task0=L/task1=D.
Outputs are `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed17/12366939_{0,1}`;
logs are `logs/te_l1_coverage_eval_12366939_{0,1}.{out,err}`. The existing
script uses the unchanged CAL/DEV/SCREEN contract; CONF remains unopened.

Smart-sbatch Phase 1: one unrelated existing job plus two tasks =3/8 jobs,
2/3 directions, array2<=16, RTX3090 24GB>=20GB, 1h/task within limits,
unique seed/job/task outputs, no new checkpoints, 215TB available and no
reservations. Configured exclusions are unchanged; claim_allowed=false.
Private3090 and sharedA5000 test-only estimates were respectively Sep 5
12:56:06 and 13:11:06 cluster time; available private GPUs select private3090.
The completed training array was already absent from Slurm's active table
(`Invalid job id specified`). Following successful sacct and artifact checks,
evaluation was submitted without an unresolvable afterok dependency. No
training or evaluation was duplicated. No seed17 performance is inferred
before both evaluations and their output checks complete.

The seed17-only `assess_replication.py` implements the registered D2 SCREEN
direction check and unchanged nonworm/topology/hardN guardrails, without
relabeling seed17 as seed42 or imposing the seed42 +0.01 release threshold.
Its positive decision only supports the conditional CONF step; the frozen
model/calibration list and concrete paired-block CI protocol must still be
registered before opening CONF. It never establishes a public-release claim.

### Seed42 evaluation: paired seed17 released

Both `12353905` evaluation tasks completed 0:0 in 14:46. Six JSON artifacts
passed finite-number, arm/seed/protocol, CAL-only shared-calibration and
DEV/SCREEN species/split checks; CONF was not evaluated. Exact compact
artifacts and the unchanged gate output are archived under
`docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/`.
Running `decide_upstream.py` returned `RELEASE_PAIRED_LD_SEED17`.

| Species / panel | L bp F1 | D bp F1 |
|---|---:|---:|
| human DEV | 0.940291 | 0.940310 |
| mouse DEV | 0.940945 | 0.941998 |
| chicken DEV | 0.836716 | 0.831720 |
| zebrafish DEV | 0.929668 | 0.927836 |
| pig DEV | 0.891351 | 0.893138 |
| c_elegans DEV | 0.783315 | 0.797565 |
| c_elegans SCREEN | 0.789994 | 0.802736 |

SCREEN AP rises 0.865557 -> 0.884389 (+0.018832); bp F1 rises by
0.012742. All registered nonworm, topology and macro hardN guards pass.
Macro DEV F1 is 0.887048 -> 0.888761, but worm DEV remains below 0.8.
This is a single-seed internal coverage signal, not a deployment result.
It does not establish fragment/boundary recovery: worm DEV segment F1
changes by -0.016620 and boundary5 by -0.004596; fragments/truth increases
0.933073 -> 1.001949 and split rate 0.108512 -> 0.126056, all within the
predeclared *noninferiority guards*, not improvements. SCREEN boundary5
also declines slightly. No gates were changed after inspection.

Seed17 L/D replication is released with the identical recipe and fixed pools.
Smart-sbatch Phase 1 passes: 3/8 jobs including existing work, 2/3 directions,
array2<=16, 24GB GPU>=20GB, 2h/task below cohort/partition limits, <=4 GPUh
for this registered replication, unique seed/job/task output/checkpoint/log
paths, <10GB expected new weights with 215TB available, no reservations,
and unchanged exclusions. Not a Track-A architecture screen, claim_allowed=false.
Live private3090/sharedA5000/sharedA5500 estimates all gave Sep 5 10:17:30;
private has available allocation and is retained to avoid unnecessary billing.

Seed17 paired training array `12361196` has been submitted: task0=L, task1=D,
with `PILOT_SEED=17` and the unchanged materialization root `12306000`.
Outputs: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed17/12361196_{0,1}`.
Evaluation follows successful 4000-step training and exposure checks. This
is the predeclared replication, not a new model-selection sweep. Do not run
the seed42-only release script on seed17 by relabeling its metadata; assess
the registered D2 consistency/guardrails explicitly. CONF generation and
inference remain blocked until the applicable models and calibrations are
frozen; resampling implementation details must be registered before opening
that panel, without changing the existing success criteria.

D1 training `12307410_0` (L) and `_1` (D) completed 0:0 in 1:15:43 and
1:15:25 respectively, starting Sep 5 at 02:01:29 and 02:02:15 cluster time.
Both logs contain exactly steps 1..4000 with finite six-species losses and
uniform ERM weights. Metadata confirms seed42, 4000/400 schedule, complete H0
initialization and the registered run role. Final weights/config/tokenizer
files exist. Actual exposure is 4000 presentations per species in both arms;
L has 1500 unique tiles/species, while D has 3000 worm tiles and 1500 for each
other species. This releases evaluation, not a scientific performance claim.

Evaluation Phase 1 passes: one existing user job plus two evaluation tasks
=3/8, two directions<=3, array2<=16, RTX3090 24GB>=20GB, one hour/task below
cohort/partition limits, unique job/task outputs/logs, no checkpoint writes,
215TB free, no reservation and configured GPU exclusions retained. This is
Mode B review of the existing script, not a new architecture batch. Live
estimates gave private3090 and sharedA5000 the same Sep 5 05:02:44 start,
so private3090 is retained. SharedA5500 was later (14:12:16).

The requested `--dependency=afterok:12307410` submission was rejected with
`Batch job submission failed: Job dependency problem`; no evaluation job
was created. The completed training array is absent from the active job
table (`Invalid job id specified`) but remains verified in sacct. Therefore
the same evaluation is submitted after the explicit completed-training and
artifact gate, without the unavailable scheduler dependency. This scheduling
repair changes no scientific inputs and is not a failed model experiment.

Evaluation array `12353905` was successfully submitted: task0=L, task1=D;
roots `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_{0,1}`.
Only old six-species CAL/DEV and worm SCREEN are evaluated; CONF and external
panels remain sealed. No evaluation score is yet available at submission.

D0 job `12306016` ended FAILED 1:0 after 23:15 because the downstream CPU
strata accumulator omitted `positive_bp` and raised `KeyError: positive_bp`.
This failed attempt is not a completed scientific run. GPU inference and the
final diagnostic JSON had already finished, including both additional B1 seeds;
all numeric values are finite, and seed42 frozen DEV maximum reproduction
deltas are 2.68e-9 (B0) and 2.01e-9 (B1), below 1e-6.
The repair reuses these explicit inference caches, without another GPU run,
and writes strata into a new job-specific directory. It also fixes raw-class
overlap lookup to retain long enclosing TE records that start before a tile;
nested RepeatMasker intervals are a supported input, not an exceptional case.
Two focused regression tests cover both defects; local strata tests pass 5/5.
Training remains held until the CPU continuation succeeds.

CPU continuation job `12307362` uses
`outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/strata_repair/12307362` and keeps
the original failed job/cache paths unchanged. It requests zero GPU, 2 CPU,
16 GB and 15 minutes on private-teodoro-gpu; 5/5 regression tests pass remotely.
Phase 1: three jobs including existing work <=8, three directions <=3, no
array/checkpoint/Track-A claim, unique job-id output/logs, 215 TB free and no
reservation. No GPU retraining or inference is authorized by this repair.

CPU continuation `12307362` also failed 1:0 after 1:03, at final JSON output:
`TypeError: Object of type int64 is not JSON serializable`. Truth-run lengths
from NumPy had propagated into the length-bin integer counters. The fix casts
run length to a Python integer at its source, without a generic serialization
wrapper. A complete synthetic panel-to-JSON regression test covers this path;
both failed attempts remain recorded and excluded as completed scientific runs.

The second CPU continuation is `12307404` under the same bounded resource
request and fresh job-id output directory; it includes six focused tests.
It completed 0:0 in 1:02, with 6/6 tests passed. All eight B0/B1 x
TRAIN/CAL/DEV/SCREEN strata panels are finite; their TP/FP/FN/positive counts
and F1 agree with the frozen diagnostic, and length/class positive mass
reproduces each panel's denominator. The successful GPU diagnostic stage
plus this successful CPU continuation now form the validated D0 chain;
the two failed Slurm attempts are not relabeled as successes. D1 L/D is released.

D1 Phase 1 passed: existing two jobs plus two training tasks =4/8, three
directions, array2<=16, RTX3090 24GB>=20, 2h/task below 12h cohort and 168h
partition limits, <=4 additional GPU hours, job/task-specific model/output/log
paths, expected checkpoint storage <10GB versus 215TB free, no reservation,
configured exclusions retained. Not a Track-A architecture batch; no claim
is allowed from this development pilot. Evaluation follows only successful
training and its frozen metadata/exposure checks.

D1 seed42 L/D training array `12307410` was submitted after that validation,
task0=L and task1=D, using the registered private3090 script. Evaluation has
not yet been submitted: successful training and exposure checks must precede
it. The heartbeat now monitors this array rather than rerunning the failed
upstream attempts. Model roots are
`outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_{0,1}`.

Exploratory B0 SCREEN positive-run length strata give bp recall 0.4830
(<80 bp), 0.7634 (80-499), 0.8692 (500-999), and 0.7593 (>=1000).
These are material-run bp recall, not biological-copy/segment F1. They do
not support a blanket monotonic "longer is easier" claim and do not change
the frozen sampling design.

For the conditional D1 pair, live Slurm tests at approximately 23:35 cluster
time estimated starts on Sep 5: private3090 10:35, shared3090 14:13,
sharedA5000 14:41, sharedA5500 14:08, sharedA6000 22:56, sharedA100-40GB 18:01.
Private has no unallocated GPU now. Choose private3090 for both matched arms:
among these eligible candidates it has the earliest estimated finish and no
shared billing. The generic long-private-wait heuristic would suggest shared,
but the tested shared routes are later, not an acceleration. Estimates may
change; actual start/finish must be recorded separately.

The completed diagnostic stage selects `COVERAGE_PAIR_HIGH_TRAIN_GAP`:
B0 TRAIN F1 0.987190 and CAL-prevalence AP 0.999172 contrast with SCREEN
F1 0.793738 and standardized AP 0.872318 (CAL AP 0.883178).
This is a substantial observed training/generalization gap, not proof that
more independent data will fix it. The registered L/D comparison tests that
hypothesis at matched compute; no initialization-pair branch is released.

D0-M CPU job `12306000` completed 0:0 in 24 seconds; its three focused tests
passed. SCREEN512, nested TRAIN3000 and coordinate-only CONF256 are feasible
without relaxing the frozen buffers or sequence eligibility. TRAIN uses
chrI/chrII/chrV/chrX; CONF uses chrIV, with 321 eligible coordinates before
selecting 256. All prescribed gap/non-overlap checks passed. TRAIN positive
mass increases from 1,291,106 to 2,532,606 bp; SCREEN has 407,508 positive bp.
CONF labels, sequence exports and predictions remain unopened.
Materialization root: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000`.

D0-G plus its CPU cache-strata consumer was submitted as job `12306016`
on shared A5000 and actually started on gpu044 at cluster time
2026-09-04 22:56:55, earlier than the scheduler estimate. Results are pending;
no D1 model has been trained under this new protocol yet.

Focused upstream tests ran on CPU job `12306034`: COMPLETED 0:0, 7 seconds,
17/17 passed with no skips in `te_benchmark`. This includes unchanged nonworm
sampler streams when the worm pool doubles, correct CAL/DEV/SCREEN input
selection excluding CONF, and independent fragment/split gate failures.
Local bundled Python passed 14 tests but skipped three because torch is
absent; the remote run resolves that engineering test gap.
Reproduction command (inside the established conda environment):
`python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904 -p 'test_*.py'`.
The test job used private-teodoro-gpu with zero GPU, 2 CPU, 16 GB, 5-minute
walltime and `logs/te_l1_upstream_tests_12306034.{out,err}`. Together with D0-G
and the two existing user jobs this was 4/8 jobs within three directions.

The existing `te-cross-species-seed42-pilot` heartbeat has been updated (not
duplicated) to this upstream protocol and resumed at 15-minute intervals.
It monitors D0 before conditionally releasing D1 and D2, preserves sealed
panels and the old B0 no-go, and stays quiet on unchanged state. No training
result or unseen-species claim is implied by submitting the diagnostics.

CPU job `12305384` completed 0:0 in 34 seconds. Remote exact-ceiling tests
passed 2/2 and unchanged evaluator tests passed 11/11. Exact token-constant
worm F1 ceilings are TRAIN `0.9946146323`, CAL `0.9944918641`, DEV
`0.9944981991`, consistent with the mathematical lower bound. DEV has 2,405
mixed tokens containing 14,429 callable bp. The bp-optimal oracle's legacy
joint boundary5 F1 is `0.9681654086`; it is not a separately optimized boundary
ceiling. Other species DEV ceilings: human `0.9965179173`, mouse
`0.9962433514`, chicken `0.9944088523`, zebrafish `0.9967663562`, pig
`0.9950065662`. Output quantization alone does not explain current worm F1.
Raw diagnostic evidence: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/ceiling/12305384/ceiling.json`.

CPU ceiling Phase 1 passed: 2 existing user jobs +1=3/8, no array/GPU,
30-minute walltime below 12-hour cohort and 168-hour private limits, no active
reservation, unique job-id outputs/logs, 215 TB free, no checkpoints. The
CPU-only fast path selects private-teodoro-gpu without Phase 2. One upstream
diagnostic direction fits the three-direction limit; this is not Track A.

D0-M/G Phase 1 passed with at most 4/8 active or queued user jobs and three
directions including existing work, independent job-id output/log paths, no
checkpoint writes, 215 TB free and no maintenance. CPU materialization requests
30 minutes, inference one hour; both fit cohort and partition limits. GPU
inference uses the configured >=20GB filter and default RTX3080 exclusions.
Phase 2 scheduler tests estimated private RTX3090 start at 2026-09-05 07:47:48,
shared RTX3090 at 02:23:56, shared A5000 at 01:53:17 and shared A5500 at
01:53:18 (cluster local time). Choose shared A5000 (configured 25GB); these are
queue estimates, not guaranteed starts. Existing DEV reproduction within 1e-6
remains mandatory when using a different eligible GPU type.

Local exact-ceiling unit tests passed (exhaustive token
assignment comparison and unknown/tail handling). Local evaluator tests ran
10/11; the Platt test could not import SciPy in the local bundled runtime.
The unchanged evaluator tests are scheduled in the established remote
`te_benchmark` environment before the CPU diagnostic; this environment issue
is not a scientific failure and did not launch a model run.

## Publication gaps

### Continuing authorization

The user explicitly requested continued autonomous, parallel progression toward
a usable multi-species model after this pilot. Routine engineering repairs,
registered conditional releases, replication and unsealed asset/interface
preparation do not need per-node approval. Existing scientific stop gates stay
unchanged: stopping a failed branch is not stopping the overall research. A
subsequent hypothesis must be evidence-backed, discussed with Pro, and registered
as a bounded experiment before execution; no post-hoc gate relaxation or repeated
sweeps. The existing heartbeat now continues beyond the pilot on this basis.

User review is reserved for opening the final reserved/external test panels,
changing the core scientific goal or substantially expanding resource scale,
changing data/repository visibility, and public weight/service release. The
already-registered conditional D2 CONF opening does not need a new approval.
Per-species BP-F1>=0.8 remains a research target, not a guarantee. Release also
requires generalization evidence, usable reproducible inference, license/source
review and explicit limitations; internal DEV success alone cannot authorize it.

The next required evidence remains frozen species-held-out/full-assembly
performance, TE-family/homology exposure analysis, and independent utility or
curated validation beyond agreement with Label-A. A higher internal bp F1
does not establish complete insertion reconstruction, fragment resolution or
unseen-species performance. MoE is not required for the paper and is not opened
by this upstream pilot.
