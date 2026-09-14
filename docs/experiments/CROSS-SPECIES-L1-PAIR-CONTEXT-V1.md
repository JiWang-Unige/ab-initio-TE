# L1-PAIR-CONTEXT-V1 — proposed matched information-path experiment

Date: 2026-09-08. **CLOSED: seed42 scientific NO-GO; no seed17.**
User explicitly replied “批准” to this protocol's seed42 <=8GPUh plus conditional
seed17 <=8GPUh request, including the stated scientific gates and failure stops.
This authorizes implementation, bounded smoke, matched training and result
processing, not sealed-data access or release. Bounded GPU engineering smoke
passed; seed42 matched training array12497274 completed and passed artifact
checks. Registered CAL/SCREEN/DEV evaluation array12499111 completed normally;
the frozen scientific gate failed. No seed17 or rescue sweep is authorized.
The platform's short approval text is not a replacement scientific objective:
the cross-species academically usable model remains the terminal goal.

The current AGENTS.md retires Auto Research/CLI review workflows. Do not restore
them or their old goal files; perform proportionate code/numerical review under
the current collaboration rules. The scientific, data, budget and stop contract
below remains binding; historical framework gate names do not add CLI quorums.

## Question and evidence

Does allowing the existing two halves of each 8192-bp tile to exchange sequence
information improve the shared TE-material model under the same supervision,
coordinates and update budget? The experiment changes attention connectivity,
not initialization, output resolution, loss weighting or coordinate coverage.

Existing J0 shows little scalar-threshold headroom and predominantly completely
missed/terminal FN material. These are motivations to change the discriminator,
not proof that context caused the errors. C's valid negative closes its Human
gene-utility extension and does not answer this L1 question.

Advisory basis: completed 6 Pro follow-up (17m55s) in the existing
[Git repository review](https://chatgpt.com/c/6a9ca31f-0610-83eb-b663-a3e26a020c7c).
Pro reused the previously inspected b6b2c08 full tracked tree and explicit new
C/A/J0 evidence; it did not read current local HEAD or independently reparse C.
This is one advisory opinion, not a tri-review quorum or experimental evidence.

## Immutable comparison

| Factor | BLOCK4 matched control | PAIR8 sole candidate |
|---|---|---|
| Input | packed original two 4096-bp encodings | identical |
| Attention | within each half only | within and between halves |
| Initial tensors | original complete H0, including classifier | identical |
| Data, token projection, loss, sampling, updates | original D contract below | identical |
| Inference information | DNA only | DNA only |

Frozen D at each seed is the practical reference, not retrained. BLOCK4 is
never promoted as an alternative winner. Both new arms use the same dense
packing/attention implementation, dtype and memory strategy. No context-length,
radius, head, learning-rate, loss or checkpoint search is included.

Keep each half's existing six-mer phase, four single-bp tail tokens, special
tokens and padding. Do not retokenize concatenated 8192-bp DNA: 4096 is not
divisible by six, so doing so changes the second half's representation. Preserve
original output-to-bp mapping and evaluate exactly the same coordinates.

Attention visibility is based only on original padding validity and half ID,
never labels, callable class, predicted TE or a hand-selected FN subset.
All valid queries see valid keys in their own half for BLOCK4, or both halves
for PAIR8. Padding queries contribute neither loss nor reported logits and must
not create all-masked softmax NaNs. Preserve original two-dimensional embedding
padding semantics separately from the pairwise additive attention mask.

### Actual implementation constraints already checked read-only

The original `cross_species_token_task.py:114–198,408–419` independently encodes
and forwards two halves, preserves P/N bp mass and normalizes each half before
averaging. The live local-native `modeling_esm.py:1015–1067` uses attention_mask
both in embeddings and to build the encoder attention mask; blindly replacing
the top-level 2D mask with 3D is therefore incorrect. Self-attention adds the
expanded mask before softmax at lines438–444. An exp-local forward adapter can
separate those two inputs without editing the original native source or weights.

Live H0 config: rotary, max_position_embeddings2050, 29 layers/1024 hidden/16
heads, attention/hidden dropout0. Two original padded halves are approximately
1376 positions; metadata compatibility is not yet a tested operator or memory
guarantee. Use identical packed position conventions in both arms. BLOCK4 must
numerically reproduce separate-half behavior despite the second-half offset;
do not assume rotary relative-position invariance is sufficient without testing.

## Data, objective and execution contract

- Original D TRAIN: worm3000 tiles, other five species1500 each. Same original
  six-species CAL/DEV and worm SCREEN; no new coordinates or FN enrichment.
- Retain P>U>N, H as negative, '?' without supervised mass, original ambiguity
  input semantics. No cleaning, resampling, deletion, label or denominator change.
- Each step: one original tile per species, paired identical sampling streams.
  Each half loss is weighted token-mass CE divided by 3*positive_bp+negative_bp;
  average the two half losses and then six species uniformly. No whole-tile
  renormalization introduced by packing.
- Full-parameter training, AdamW LR2e-5, weight_decay.01, grad norm1;
  4000 updates/400 warmup, final-step checkpoint only. Each arm has 24000 tile
  presentations (=196608000 bp presented), not that many independent new bp.
- Seed42 BLOCK4/PAIR8 first; seed17 only after the complete seed42 gate and only
  if the approval explicitly covers that conditional stage. No replacement seed.
- Per new model: original global six-species CAL Platt/threshold once; one
  registered SCREEN/DEV evaluation. No worm-specific threshold or oracle export.
  Retain raw float32 margins; use frozen D archived scores/metrics, not new D
  inference on nonworm panels. Existing material/topology/hardN evaluator stays.

## Proposed gates (must be approved before scientific outcomes)

The new +0.005 is a proposed minimum useful effect, not an empirical noise
bound and not a change to any old experiment's gate. PAIR8 must pass against
**both** BLOCK4 and same-seed frozen D, without averaging away a failed panel.

Seed42 release requires all:

1. Worm SCREEN and DEV F1 each improve >=0.005 against both references.
2. All six-species DEV and worm SCREEN F1>=0.8, P/R>=0.75; macro DEV F1>=0.83.
3. Worm SCREEN/DEV raw AP loss <=0.002 against both references.
4. Each nonworm DEV F1 loss <=0.01 against both references.
5. On six-species DEV and worm SCREEN: segment F1@0.8 and joint boundary F1@5
   loss <=0.05; fragments/truth and split <=1.25*reference; missed-rate increase
   <=0.03. Macro DEV hardN FP increase <=0.005 against both references.

Seed17 requires positive worm SCREEN/DEV F1 gains against both references,
the same absolute readiness and all guards; it does not require another +0.005.
Zero references retain multiplicative comparisons, without denominator smoothing.
Spatial uncertainty may reuse occupied512kb blocks/1000 paired draws and the
existing fixed RNG protocol; it is descriptive, not a new release criterion.
Two seeds and spatial intervals do not make reused DEV an independent test.

## Preparation, resource caps and failure actions

Before training, test only new operator risks:

- Exact tile pairing/continuity and unchanged tokens, P/N masses, tails and
  back-projection. Failure: fix packer without editing original data.
- FP32 dropout-off BLOCK4 versus separate halves: valid logits, original loss
  and parameter gradients within predeclared atol1e-5/rtol1e-4. Use a bounded
  synthetic example before real-model smoke; failure blocks science rather than
  silently relaxing tolerance. Record device/dtype and discrepancy.
- Right-half perturbation leaves BLOCK4 left valid logits unchanged within
  that tolerance, while PAIR8 has actual cross-half influence. Check attention
  wiring independently of whether one particular output happens to stay constant.
- Same two-arm GPU compute path, finite loss/gradients and measured memory and
  warmed step time; no unapproved change to batch, sequence or update budget.

Proposed new resource approval: stage1 seed42 <=8 GPUh, including GPU smoke,
training, evaluation and failures. Optional preapproved conditional seed17 <=8
additional GPUh; total hard cap16. CPU preparation/results <=4CPU/32GiB/2h per
job, same research direction; no new dataset downloads. RTX3090-class24GB,
one GPU per arm; at most two concurrent training tasks, subject to cluster rules.
No C/INIT unused budget transfer. No allocation is requested by this document.

Old 4000-step runs took75–76min per arm and eval14–15min; the packed attention
matrix work doubles (2*T^2 to4*T^2), but total time does not follow exactly.
Budget feasibility must use measured warmed step times of both arms plus paired
evaluation, already consumed smoke/failure time and a 20% runtime margin. Start
science only when the complete matched stage fits its remaining8GPUh cap.
If matched24GB execution needs activation checkpointing, fix it identically for
both arms before science. If it still cannot fit, record resource STOP; no silent
larger GPU, reduced data/steps/species or different kernel per arm.

Engineering failure: preserve outputs, no scientific verdict. Only a minimal
in-contract correction with a documented cause and remaining budget may retry;
repeated same failure or inability to complete the pair stops the stage.
Scientific seed42 gate failure: close this PAIR8 extension; no seed17 or rescue
sweep. Seed17 failure: record non-replication and close. Both pass: internal
candidate recipe only; stop before independent evaluation/release approval.

## Implementation scope after approval

New exp-local directory under `scripts/experiments/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/`
for pair packing/forward adapter, bounded operator tests, training/evaluation
wrapper and decision consumer. Reuse original loading, sampling, optimizer,
projection, calibration and metric helpers. Do not refactor shared historical
trainers or overwrite native model code. Code-review gate and resource routing
must precede real GPU work. New run-specific outputs only.

## Still excluded and still required for the terminal goal

### Implementation checkpoint, 2026-09-08

Exp-local `pair_model.py`, `train_pair.py`, and `evaluate_pair.py` now implement
separate-half native embeddings, packed encoder attention, restored half-shaped
outputs, complete-H0 loading and explicit same-tile evaluation. Shared historical
trainers and native source are unchanged. These wrappers are not yet cleared for
scientific execution; real-H0 numerical/memory/timing and reload checks remain.

Slurm CPU job **12496937 COMPLETED, exit0**, 4CPU/8GiB, elapsed2m07s:
synthetic two-layer native ESM FP32 BLOCK4 equivalence PASS at frozen
atol1e-5/rtol1e-4. Maximum valid-logit and parameter-gradient errors both
2.9802322387695312e-8; loss error0. Right-half perturbation leaves BLOCK4 left
unchanged; PAIR8 left-logit change0.014878600835800171 and nonzero cross-half
attention. Evidence: `reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/operator-12496937/result.json`.
This is operator engineering evidence only, not real-H0 equivalence or science.
Initial GPU smoke **12497149 FAILED**, exit1 after1m43s (=0.028611 GPUh),
before model forward: the native class disables the public HF
`gradient_checkpointing_enable()` interface although its encoder implements
checkpointing. All10500 TRAIN tile pairs passed continuity/count checks.
Minimal correction explicitly enables that existing encoder path; no native
source or scientific contract changes. Retry **12497160** is the sole active
H0 smoke, capped20min, including additional TRAIN-only FP32 inference timing.
Both arms use the same checkpointing path. The failure remains charged to seed42.
No scientific training or CAL/SCREEN/DEV inference has run.

Retry **12497160 COMPLETED**, exit0 after1m11s. Real complete-H0 FP32 equivalence
PASS under the predeclared combined absolute/relative tolerance: maximum valid
logit error1.6927719116210938e-5, loss error2.384185791015625e-7, gradient
error1.895427703857422e-5. These maxima exceed the absolute term alone but pass
the frozen `atol + rtol*abs(reference)` criterion; no tolerance was relaxed.
Saved state/config plus explicit adapter reinstall PASS. Right-half perturbation
leaves BLOCK4 left unchanged within tolerance and changes PAIR8 left logits
by up to0.6126629114151001. Native checkpointing was active for the full-gradient
test and both matched training probes. No scientific metrics were produced.

Warmed full six-species step maxima: BLOCK4 1.852390s, PAIR8 1.830552s;
both peak allocated9,867,876,864bytes. FP32 paired inference maxima0.141310s/
0.139550s. With6512 evaluation tiles per arm,30min total non-forward overhead
allowance and20% margin, projected stage cost including174s already consumed is
6.16858GPUh. Training caps2h50m per arm and evaluation caps1h per arm bound
the total allocation at7.715GPUh, below8. Resource gate PASS:
`reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-resource-gate.json`.

Seed42 training array **12497274** submitted after operator/resource review:
index0 BLOCK4, index1 PAIR8, one3090 each, max2 simultaneous tasks,4CPU/32GiB,
2h50m cap per task. Both run4000updates/400warmup with the native activation
checkpointing path. Evaluation is not yet submitted; complete training, finite
logs, matched exposure and saved arm/config are to be checked first. No seed17
release or model success is implied by this submission. Both tasks were verified
RUNNING on gpu034; initial steps1–6 completed with finite six-species losses,
uniform1/6 weights and the expected warmup learning rates.

New decision consumer `assess_pair.py` reuses existing metric definitions and
implements the approved two-reference/two-worm-panel effect gates plus absolute
readiness before seed17 release. Seven focused local boundary tests passed,
including exact0.005, strict-positive seed17, each reference/panel, topology/AP/
hardN failures, zero reference without smoothing, and wrong-seed rejection.

### Seed42 training completion and evaluation, 2026-09-08

Training **12497274_0 BLOCK4** and **12497274_1 PAIR8** both COMPLETED exit0,
elapsed7816s and7764s respectively. Complete 4000-step finite six-species logs,
400-step warmup/registered LR schedule, uniform weights, identical exposure
tables, initialization metadata and saved arm/config checks PASS. Each species
has4000 presentations; unique tiles1500 each except worm3000. Evidence:
`reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-training-check.json`.
Checkpoint tensors will be loaded by the actual registered evaluator.

Actual charged GPU time including174s smoke/failure is15754s=4.376111GPUh.
Two evaluation tasks capped1h each bound this stage at6.376111GPUh, below8.
After live queue/resource checks, evaluation array **12499111** was submitted
once: index0 BLOCK4, index1 PAIR8, seed42, training source12497274, original
global CAL and registered SCREEN/DEV only. No metrics or seed17 release are
yet available; training success does not establish scientific success.

### Seed42 final result, 2026-09-08

Evaluation12499111_0/1 both COMPLETED exit0, elapsed1284s/1568s.
Total stage GPU consumption including training and both smoke attempts:
18606s=5.168333GPUh, below the approved8GPUh cap. Compact calibration and
SCREEN/DEV metrics are retained locally under
`outputs/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/evaluate/seed42/12499111_{0,1}/`;
raw margins and final weights remain on Baobab.

| Worm bp F1 | PAIR8 | BLOCK4 | Frozen D | PAIR8 minus BLOCK4 | PAIR8 minus D |
|---|---:|---:|---:|---:|---:|
| SCREEN | 0.812998 | 0.809500 | 0.802736 | +0.003497 | +0.010262 |
| DEV | 0.794154 | 0.795764 | 0.797565 | -0.001610 | -0.003412 |

The registered+0.005 gate fails on SCREEN versus BLOCK4 and DEV versus both
references. PAIR8 worm DEV F1 also fails absolute0.8 readiness (P0.821229,
R0.768807). Macro DEV F1 is0.892187; this does not override the failed worm
panel. All AP, nonworm F1, topology and hardN guards pass against both references.
Thus this is a valid negative scientific result, not an engineering failure:
**STOP_PAIR_CONTEXT_SCIENTIFIC_NO_GO; release_seed17=false**.
Decision evidence: `reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-decision.json`.

Close this PAIR8 extension without seed17, threshold changes or rescue sweeps.
The result does not establish that all longer-context methods fail; it rejects
this registered matched recipe on the reused internal panels. The terminal
academically usable cross-species model goal remains unmet. A different
experiment or independent-data evaluation requires a new explicit agreement.

No old CONF loading, diagnosis, inference or selection. Reserved worm chromosome,
horse/opossum/dm6/cattle stay sealed; P3/chr19 and all old stop decisions remain.
No public visibility, weights/service release, new backbone download or biological
insertion claim. The proposal tests effective sequence context only.

Even a two-seed PASS leaves external generalization, real continuous-FASTA output
and coordinate/topology behavior, exposure/provenance, actual weight/dependency
license review and approved academic release outstanding. No claim that this
proposal, its implementation or its internal gates alone complete the goal.
