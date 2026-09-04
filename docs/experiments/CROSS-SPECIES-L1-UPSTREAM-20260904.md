# L1 upstream coverage pilot, 2026-09-04

## Decision and evidence boundary

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
