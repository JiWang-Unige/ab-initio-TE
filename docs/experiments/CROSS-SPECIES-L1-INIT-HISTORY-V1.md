# L1 initialization-history comparison V1

## Decision and status

Registered 2026-09-05 after the completed Pro follow-up on source commit
`48867e0a73f8f8b5991ee6270273a3795beddcc6`. Status: **protocol registered;
J0 loading passed; score caches valid, diagnostic JSON recovery pending;
no scientific J1 released**.
Advisory source: [completed Pro discussion](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6a9b26e0-59c0-83eb-bc94-a5c5d683de9a).

Accept one new question: under the same finite supervised budget, does encoder
initialization improve the shared system? This is not the old underfitting
branch: B0 fits TRAIN well, but its result does not establish D's TRAIN fit.
H0 may help or hurt generalization; neither has been established. Keep the
closed coverage result and all old no-go decisions unchanged.

This is the last automatically released training hypothesis on the current
backbone/data/development panels. At most four new 4000-step training runs,
with an 8 GPU-hour cap including diagnostics, engineering GPU smoke and
evaluation. No pool/step/loss/context/head-reset sweep follows a failure.
Scientific failures are retained; engineering-invalid jobs are separately
logged and their resource use still counts toward the cap.

## Immutable data and matrix

Use the existing D materialization: worm TRAIN3000, other five species
TRAIN1500, unchanged Human chromosome exclusions, six-species balanced ERM.
Existing D anchors: seed42 `12307410_1`, seed17 `12361196_1`, with their
frozen calibration/evaluation `12353905_1` and `12366939_1`. Do not retrain them.

| Arm | Encoder | Classification head | Role |
|---|---|---|---|
| D-anchor | existing complete H0 continuation | existing H0 head | frozen utility reference, no training |
| H0R | H0 checkpoint encoder | fresh head h(seed) | matched control |
| P0R | local native NTv2-500M encoder | identical h(seed) | candidate |

Primary paired contrast: P0R minus H0R. Practical contrast: P0R minus
D-anchor. Beating only a degraded head-reset control is insufficient.
The practical contrast changes encoder and head together and is not a pure
encoder mechanism estimate.

Train seed42 first; release seed17 only by the rule below. Each new arm uses
4000 steps, 400 warmup, final-step checkpoint, full encoder fine-tuning,
AdamW LR2e-5/weight decay0.01, TE bp weight3, grad norm1, original per-half
loss normalization, six tiles/twelve4096 halves per step. Preserve tokenizer,
6-mer/tail projection, P>U>N and all non-intervened model configuration.
Both arms have identical per-species sampling streams. No LP-FT, augmentation,
early stopping, layer-specific rates, extra warmup or encoder interpolation.

Old six-species CAL is fitted once per new model with the existing global
Platt/global threshold rule. SCREEN and DEV are already-used development
panels; each new arm gets one predeclared evaluation. New seeds do not make
these independent data. CONF is historical closure only: **no new model
inference, diagnostics or model selection on CONF**. Reserved worm chromosome
and horse/opossum/dm6/cattle remain sealed. No new confirmation set is created.

## J0: bounded prerequisites, no new training

### A. D-score diagnosis

Use only existing D seed42/17 worm SCREEN and DEV with each model's frozen
global calibrator. Inspect actual cache availability first. If absent, perform
one apply-only inference per required model/panel and preserve float32 margins.
Reproduce archived pooled point F1/P/R/AP within1e-6 before interpreting the
new diagnostic. A mismatch means repair inference/alignment, not science no-go.
Do not refit CAL or substitute B0 caches.

Report two summaries:

1. Exact raw-margin tie-group PR curve: maximum F1 constrained to P,R>=0.75,
   and maximum recall among thresholds with precision>=0.80. No eligible
   threshold gives null plus a reason, not a fabricated zero. If constrained
   best F1<0.8, a scalar threshold cannot meet that panel's goal; if oracle
   minus deployed F1>=0.02, score alignment has substantial headroom.
   Otherwise report mixed limitations. These are label-oracle diagnostics;
   never export their threshold as a deployment candidate.
2. FN bp partition using existing callable Label-A runs: completely missed
   runs; internal gaps between the first/last hit in partially hit runs;
   terminal missing bp of partially hit runs. Categories must exhaust FN bp.
   U-induced breaks are evaluation boundaries, not biological insertion ends.

These summaries constrain attribution, not release an extra threshold/loss/
context experiment. J1 uses the fixed rules below regardless of an appealing
oracle. Do not repeat token ceilings or B0 full-TRAIN diagnostics.

### B. Loading contract that gates J1

The existing loader constructs a token classifier from the native config and
strict-loads the complete H0 state. Existing training metadata hardcodes H0;
exposure collection is coverage-protocol-specific. Adapt these concrete
interfaces without changing old run behavior; record the actual sources.

Native local directory:
`/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species`.
H0: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_ntv2_500m_H0_w4096_seed42/checkpoints/checkpoint-800`.
Read-only metadata on 2026-09-05 shows the native download source as
`InstaDeepAI/nucleotide-transformer-v2-500m-multi-species`, dated2026-05-21;
H0 training metadata records this same local model path, seed42/max_steps800.
The download metadata does not record a source revision. This supports path
provenance, not independently verified immutable checkpoint ancestry.
Until stronger existing provenance is found, interpret the intervention as
**checkpoint initialization choice**, not proven isolation of Human history.

Before training, persist an exact key partition and loading report: all encoder
parameters come from the designated source; only explicit classifier and
pretrained task-head keys may be replaced/unused. No unknown missing keys or
random encoder residue. Check config/architecture/tokenizer compatibility.
For each seed use an identical fresh classification head in both arms, compare
tensors directly, and restore/reset run RNG after construction so initialization
work does not change subsequent stochastic execution. No requirement for
different encoders to have equal initial logits. Compare sample streams,
token IDs/masks and loss masses directly on the bounded loading smoke.
No new hashes/digests/checksum files: existing source revisions may be recorded,
but direct equality checks answer head and input matching.

Failure of full encoder loading or structural compatibility blocks J1 until
minimal engineering repair. Unverifiable exact ancestry narrows the claim;
it does not justify treating native random weights as pretrained weights.

## J1 releases and scientific closure

Evaluate P0R against **both** H0R and the same-seed D-anchor. Seed42 must meet
all of the following to release the paired seed17:

- Worm SCREEN F1 gain>=0.010 against both references.
- Worm DEV F1 nondecreasing against both.
- SCREEN and worm DEV raw AP loss<=0.002 against both. This is a preregistered
  practical tolerance, not a measured noise bound.
- Each nonworm DEV F1 loss<=0.01 against both.
- For six-species DEV and worm SCREEN, segmentF1@IoU0.8 and joint boundary5
  loss<=0.05; fragments/truth and split<=1.25 times reference; missed increase
  <=0.03. Compare by multiplication, retaining zero denominators honestly.
- Macro DEV hardN FP increase<=0.005 against both references.

Seed17 replication requires positive SCREEN F1 gain against both references,
nondecreasing worm DEV F1, and the same AP/nonworm/topology/hardN guards.
Do not post-hoc demand a second +0.010 effect or replace a failed seed.

FREEZE_READY additionally requires P0R **both seeds** to reach F1>=0.8 and
P,R>=0.75 on every species DEV and worm SCREEN, with macro DEV F1>=0.83.
This is internal recipe readiness only, not external success. Third-seed
replication and final reserved/external opening belong to a separate frozen
protocol and user review, not automatic release here.

Report all per-seed contrasts including AP, not only F1. F1 improvement with
near-constant AP may be calibrated system/score-alignment benefit; do not claim
ranking improvement. For spatial uncertainty reuse occupied512kb blocks,
1000 paired draws with numpy default_rng20260905 and percentile2.5/97.5
linear intervals. Each panel uses shared draws across three arms; pool callable
bp exactly, use raw float32 tie-group AP, no seed resampling, no undefined-draw
removal. Report per-seed paired differences and optional two-seed arithmetic
mean effects explicitly as spatial uncertainty, not an ensemble or seed-
population CI. CI sign is descriptive, not an added release gate.

Any failed scientific release closes that extension. If P0R only beats H0R,
do not replace D. If both fresh-head arms improve similarly, do not silently
open a head-reset branch. If two seeds improve but miss absolute readiness,
retain the evidence and close training expansion. No new CONF rescue.

## Budget, next-only work and release boundary

J0 CPU loading/statistics target30–60min; missing-cache GPU target20–30min.
Each paired training/evaluation stage is estimated at3 GPU-hours from actual
coverage timings. Hard cap8 GPU-hours, no silent step reduction or unmatched
arm change. Before committing any matched stage, account for spent resource
and matched completion estimate; close unstarted extensions if they cannot fit.
Use smart-sbatch for submission and log actual job IDs/resources separately.

Pending implementation outputs: protocol/loading metadata, J0 summaries,
per-arm training/evaluation metadata, exposure.tsv, machine-readable decision
and concise closure. No weights/cache/data enter Git. No new Slurm job is
implied by this registration.

After failure or four runs, continue sequence-only FASTA inference engineering
and scope/utility protocol preparation, not another model sweep. Inference
must not use RepeatMasker labels/Unknown masks to retain predictions; preserve
input ambiguity as a separate QC track. BED connected runs are not insertion
IDs. Synthetic and existing TRAIN sequence smoke only; final generalization,
family/homology exposure and independent utility evidence remain unproven.
Public weights/service, changed visibility and final sealed-panel opening
require user review. Routine engineering and registered releases do not.

## Execution ledger, 2026-09-05

Implemented J0 score diagnostics, strict initialization loading, fixed-budget
training wrapper, new evaluation and dual-reference decision consumer in
`scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1/`. Three independent
implementation assignments were combined. J0 score tests passed11/11 locally;
evaluation/decision tests passed12/12. Torch-dependent loading tests and old
trainer regression tests run in the CPU allocation before real loading.
An archived-metrics schema mismatch was caught and fixed before submission;
this is not an experimental failure or new model result.

Existing D evaluation directories contain only calibration/DEV/SCREEN JSON,
not raw-margin caches. J0 therefore uses once-only apply inference per seed.
Source cache metadata now identifies native config and PyTorch weights at
revision `06615c1660c892fc199840c18123f8385b3542a8`; this is an existing source
revision, not a newly generated checksum. Exact historical H0 ancestry still
has the stated qualification.

Smart-sbatch Phase1 passed for one CPU loading task and two GPU score tasks:
1 current user job +3=4/8; array2<=16; two total research directions<=3;
GPU RTX3090 24GB>=20GB with default3080 exclusions; CPU30min/GPU20min below
cohort12h and partition168h; no maintenance reservation; 215TB free against
small report/cache needs; job-ID-specific outputs/logs, no training checkpoints.
Not TrackA; no smoke/screen scientific claim. Phase2 selected private with
six Slurm-unallocated eligible GPUs across gpu034/035 and no queued GPU claim
ahead in that partition. CPU follows the private0GPU fast path.
These are routing observations, not guaranteed start times or training release.

Code commit `fa5c50c` was pushed locally and fast-forwarded remotely before
submitting CPU contract `12385291` and score-inference array `12385292`
(task0=seed42 D, task1=seed17 D). Outputs:
`outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_contract/12385291/init_contract.json`
and `j0_scores/12385292_{0,1}/`. Jobs pending validation; no scientific
training has yet been submitted. Logs use `te_l1_j0_contract_12385291` and
`te_l1_j0_scores_12385292_{0,1}` under `logs/`.

CPU `12385291` completed0:0 in89sec: old trainer tests6/6, loading tests5/5,
decision/evaluation tests12/12. Both seeds' loading contracts passed:441
encoder tensors/493084113 encoder parameters per arm, direct source equality,
identical fresh heads/tokenizers/inputs/loss masses/sampling traces and restored
construction RNG. No model forward was performed in that CPU check.

GPU `12385292_0/1` failed1:0 after179/180sec at final diagnostic JSON writing:
`numpy.int64` in completely-missed-run bp totals was not JSON serializable.
Both SCREEN and DEV point metrics had already reproduced within1e-6 for both
seeds; all four float32 caches were written and retained. Keep these job IDs as
engineering failures, not scientific no-go or successful complete reports.
GPU consumed359sec=0.099722h; no repeated GPU inference is needed.
The minimal repair casts run length to Python int at its calculation and
adds a JSON roundtrip regression assertion (11/11 score tests passed).
CPU recovery reuses all four caches with new job-specific outputs.

With J0 loading valid and frozen score reproduction observed, engineering-only
4-step H0R/P0R smoke may run alongside CPU report recovery. This is not release
of scientific J1. Routing remains private: one old job +one recovery CPU +two
smoke tasks=4/8, same direction and VRAM/exclusion/path constraints, each10min,
no maintenance, small outputs versus215TB free. Recovery0GPU follows fast path;
smoke has eligible unallocated private RTX3090 capacity. The eventual scientific
release requires complete recovered J0 reports and successful paired smoke.
