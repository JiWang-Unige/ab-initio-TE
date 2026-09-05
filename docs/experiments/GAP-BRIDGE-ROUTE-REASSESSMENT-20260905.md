# Human gap route reassessment — 2026-09-05

Status: **REASSESSMENT; new training/deployment protocols are DRAFT, not frozen.**

The frozen Stage 1 result remains **NO_ACTIONABLE_ARM**. Retain the original
P3 mask, do not release chr19, and do not reinterpret this diagnostic as a
successful model. The user requested reassessment with ChatGPT Pro and parallel
attempts. This turn performed a retrospective CPU diagnostic and independent
asset audits, not new backbone/head training or a new test release.

Advisory discussion:
[ChatGPT Pro — Gap bridge review](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6a97eb65-42e4-83eb-b491-707f24156505).
Pro reviewed the code/report at `d1790bfdb82fa70652d4ae0f1edf2d2f8e5066aa`;
its advice is not independent experimental evidence or user authorization.
The actual Slurm/output observations below were obtained separately on Baobab.

## Decision and bounded parallel directions

| Direction | Scientific question | Current disposition |
|---|---|---|
| B0: saved-score tail diagnostic | Why does H's global ranking improvement not yield safe useful actions? | Executed on chr13 DEV; no new thresholds, models or CAL-GATE selection |
| A: frozen P3 + NT continuous input | Does a different frozen model provide actionable information missing from H? | Prepare a prospective amendment and label-blind alignment smoke; do not directly launch the full paired experiment |
| C: fixed-mask downstream intervention | Is whole/partial material repair worth learning for gene annotation? | Independent prospective preparation; software/weights and CDS-chain evaluation are not yet ready |

After the second Pro review incorporating the observed B0 results, priority is
**finish seam localization -> A preparation**, with C prepared independently.
An ordered-versus-shuffled fixed-H replay is deferred: it is a lower-priority
optimization hypothesis, not an additional parallel model-search program. P3 continual
training, extra architectures/loss sweeps and a new pangenome program are not
the next action on the current evidence.

## B0: observed results, not Pro estimates

Script: `scripts/experiments/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/gap_tail_diagnostic.py`.
Remote project: `/home/users/j/jwang/ab-initio-TE`.
Inputs under `outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/`:

- `candidate-manifest-20260902-r1/candidate_manifest.tsv`;
- `score-20260904-r1/chr13_stage1_raw_logits.tsv`;
- `evaluate-20260905-r1/evaluation_summary.json`.

The reader interprets labels only for chr13 DEV rows. It applies the existing
three-seed mean, saved CAL-FIT calibrators and saved per-arm DEV 1e-5 budget
thresholds; it does not refit or scan. Non-DEV manifest/score rows are skipped.
The saved evaluation JSON also contains the already-completed CAL-GATE results,
but none are used to select a new rule.

Job **12385019**: CPU-only, 1 CPU / 4 GB / 15-minute limit,
`private-teodoro-gpu`, **COMPLETED 0:0, 8 seconds**. Output:
`outputs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/dev-r1/gap_tail_diagnostic.json`.
All three original candidate counts and positive/negative/unknown bp totals
were reproduced exactly. The small synthetic tests passed before execution.

Job **12385123** added the full-DEV seam/length/relation denominators and
six-stratum Brier decomposition: **COMPLETED 0:0, 8 seconds**, same CPU limits,
output `outputs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/dev-r2/gap_tail_diagnostic.json`.
The thresholds are unchanged.

Job **12385244** completed the final localization into gap-interior crossing,
gap-endpoint contact, and flank-only crossing: **COMPLETED 0:0, 9 seconds**.
Final output:
`outputs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/dev-r3/gap_tail_diagnostic.json`.
In this final JSON, `excess_fraction_brier` is the length-weighted fraction MSE;
`candidate_fraction_mse` is an explicitly unweighted candidate-level diagnostic.
All original budget totals again reproduced exactly. Two small targeted tests
covered the additional denominator/decomposition and seam-localization fields.

### The Brier floor does not explain away the no-go

Known DEV comprises 60,569 candidates and 3,449,084 gap bp (5 additional
unknown candidates are outside this denominator). Of these, 7,450 mixed gaps
contain 1,432,807 bp: 318,257 positive and 1,114,550 negative.

For one predicted risk per gap, with observed negative fraction `r_i`,
the pseudo-base Brier equals the length-weighted fraction MSE plus
`C = sum(L_i r_i (1-r_i)) / sum(L_i)`.

| Metric | G | R | H |
|---|---:|---:|---:|
| Pseudo-base Brier | 0.1043053681 | 0.1044024350 | 0.1036983163 |
| Fixed within-gap term C | 0.0441379552 | 0.0441379552 | 0.0441379552 |
| Fraction MSE | 0.0601674128 | 0.0602644798 | 0.0595603611 |

Removing C changes H-over-R relative improvement from 0.6744% to approximately
**1.1684%**, still well below 5%. C is a scoring floor for one probability per
mixed gap, not proof of irreducible uncertainty in the input representation.
Neither this decomposition nor any future metric amendment reopens Stage 1.

### H's error budget is concentrated, but not in one error only

| Original budget tail | G | R | H |
|---|---:|---:|---:|
| Selected gaps | 154 | 249 | 169 |
| All-positive gaps | 126 | 199 | 141 |
| Mixed gaps | 6 | 7 | 7 |
| All-negative gaps | 22 | 43 | 21 |
| Positive bp | 1,018 | 1,407 | 1,018 |
| Negative bp | 233 | 273 | 314 |
| Negative bp from mixed gaps | 134 | 136 | 223 |
| Top 5 error gaps' share of negative bp | 72.1% | 61.5% | 79.0% |
| Top 10 error gaps' share | 84.5% | 73.3% | 89.5% |

H's two selected 101–512-bp gaps contribute 182 of its 314 negative bp (58.0%).
R/H share 162 candidates with 853 positive / 224 negative bp. R alone adds
87 candidates with 554 positive / 49 negative bp; H alone adds 7 with
165 positive / 90 negative bp. Thus the H tail is not simply a cleaner subset
of R. The entire G selection is contained in R, which adds 95 candidates and
389 positive / 40 negative bp.

All selected crops in all arms cross an original 8192-bp P3 window boundary
(`gap +/- 256`); original region windows are aligned at chromosome coordinate
zero. This is an observed concentration, not evidence by itself that the
window boundary caused either the gaps or their misranking.

The denominator is 4,817 seam-crossing known candidates out of 60,569 (7.95%),
with 63,700 positive / 285,013 negative bp. Non-seam candidates number 55,752,
with 398,033 positive / 2,702,338 negative bp. All three selected tails are
therefore concentrated in this minority seam stratum. This makes boundary
context a concrete next diagnostic question, but not a reason to construct a
seam-only deployment policy from the same DEV observations.

The final localization is more specific than "cross-window gaps":

| Localization | All known DEV | G selected | R selected | H selected |
|---|---:|---:|---:|---:|
| Gap interior crosses a seam | 456 | 1 | 3 | 1 |
| Gap endpoint exactly at a seam | 498 | 100 | 117 | 102 |
| Only the flanks make the crop cross a seam | 3,863 | 53 | 129 | 66 |

H's seam-endpoint group contributes **286/314 negative bp (91.1%)**. Its sole
gap-interior crossing contributes zero negative bp. The immediate question is
therefore boundary-endpoint behavior, not a demonstrated general failure to
classify gaps spanning two windows. Source inspection confirmed zero-aligned
native windows and consistent sequence/logit/latent slicing of the adjacent
carry in `stage1_train.py:assemble_crop`; no evident coordinate-offset defect
was found. This was a source/geometry check, not a new tensor-level forward.
These final localization results arrived after the second Pro response and
are the agent's additional empirical refinement of that response.

H's all-positive candidate fraction (141/169 = 83.4%) is higher than R's
(199/249 = 79.9%), despite its higher negative-bp cost. A pure binary
all-positive target would not by itself represent this severity difference.

All selected negative bp have `COMPARATOR_RELATION_AMBIGUOUS`; supported bridge
counts are G=125, R=198, H=140, agreeing with the original strict-edge endpoint.
These relations contain comparator information and cannot be used as a
deployment filter. An ambiguous relation is also not a biological insertion
identity adjudication.

### What this diagnostic did not establish

It did not evaluate final-checkpoint TRAIN predictions, alter the loss,
demonstrate optimization convergence, or test a new policy on CAL-GATE/test.
Fraction BCE is aligned with expected additive negative-bp cost when length
is available. Re-expressing its output as expected positive/negative bp adds
no new information. Zero-contamination probability and comparator bridge
probability describe different events, but neither is automatically the
correct replacement objective. A new target requires a separate prospective
decision, not post-hoc filtering of the errors above.

## A: proposed prospective changes; old conditional protocol is not executable as-is

The existing `GAP-BRIDGE-P3-NT-DONOR-RISK-R1-CONDITIONAL.md` still contains
`0.9 * min(P3,NT)` fragmentation/split criteria and an incompletely specified
same-budget fixed donor comparison. These are real unresolved protocol issues.
Do not silently overwrite that frozen/history document or `ACTIVE_GOAL.json`.

The next amendment should preserve one scientific variable: H0 has the full
original H input; HN adds one frozen NT TE-logit channel and its three native
4096-window seam scalars. Both use 144 channels/10 scalars; H0's extra slots
remain zero after normalization. Keep the original candidates, P3 8192 context,
crop, head, loss, weights, two passes, training order and three seeds. Do not
combine a B1 training-order change with A.

If both native grids start at zero, every P3 8192 seam is also an NT 4096
seam. NT adds a different model observation, not automatically seam-spanning
context. G/R/H already have P3 seam geometry, so adding the same seam flag
is not a new-information experiment. A shifted-window forward would change
the input geometry and requires a separate diagnostic draft, not a hidden
change inside A.

Proposed changes requiring explicit protocol lock before results:

- Make P3 the primary anchor for a P3 fill-only intervention; retain NT at its
  fixed 0.5 operating point as a reported comparator, not a best-of topology gate.
- Represent new false component connections using a fixed comparator-pair set,
  rather than only a prediction-count denominator that changes after bridging.
- Define fixed donor as every legal P3 gap whose **every bp** has NT `p >= 0.5`;
  fill all such gaps up to the existing 512-bp cap. It is one operating point.
  If over budget, report infeasibility; do not truncate using labels.
- Report both Brier components. A 5% fraction-MSE improvement gate, instead of
  the old total-Brier gate, is a prospective proposal, not a correction to H's
  old FAIL. The new boundary/segment noninferiority tolerances also remain draft.
- Keep the original known/unknown negative-bp and gene-safety constraints for
  the whole-gap route. Preserve strict negatives and the full comparator metrics.

Asset facts verified this turn:

- NTv2-250M H0 checkpoint exists (883 MB):
  `software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42/best_model/pytorch_model.bin`.
  This is not the cross-species NTv2-500M model.
- P3 is the original four-state 800-step P3-R1 under
  `outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet/model_state.pt`;
  the directory's `r2` does not identify the later independent-boundary-head model.
- Use `strict_segment_eval.py:infer_probs_for_label_mode` for NT token-to-bp
  alignment. The historical `ensemble_overlap.py:infer_track` also reads labels
  and compresses valid coordinates; it cannot be copied into blind feature
  generation unchanged.
- Before the small alignment smoke, specify NT window start/stride/terminal
  handling, seam-distance ties, and TRAIN-only scaling for the three new scalars.

The actual P3 historical evaluation covered chr17:0–9,830,400. NT training
metadata has max_eval_samples=1200; its test code uses that same cap, and the
matching historical 1,200-window ensemble result contains only chr17. The
metadata list chr17/19/20/21/22 is an allowed chromosome list, not an observed
coverage inventory. This supports no chr19 use by those specific test runs,
not a claim of whole-project non-exposure. Phase 0 already used chr19 in blind
candidate generation/purge, so "chr19 never read" is also inaccurate.

The chr13 DEV/CAL sets are consumed development data. Before confirmatory
release, trace supervised train/calibration/model-selection/reported-test
regions for the relevant checkpoint ancestry. Different assembly names alone
do not establish independence. No alternative test chromosome is selected
or unlocked in this reassessment.

## C: independent downstream intervention, not a partial-fill learning claim

Prepare three fixed inputs on the existing chr13 DEV regions:

1. M0: original P3 mask.
2. MW: M0 plus every comparator-known entirely positive complete candidate gap.
3. MP: M0 plus comparator-positive bp inside candidate gaps, allowing partial
   fills and leaving unknown bp unchanged.

Hold sequence letters, context, inference partition and gene predictor fixed;
only softmask changes. Do not choose positions using gene annotation. MW and MP
are non-deployable label-assisted interventions, not mathematical upper bounds
on gene utility: more repeat masking need not monotonically improve genes.
Use the full frozen DEV candidate universe, not the selected G/R/H tails.
MP-minus-MW changes both added material coverage and action resolution; its
effect cannot be attributed to resolution alone. It remains a development
intervention, not independent confirmation.

Tiberius `mammalia_softmasking_v2` is a suitable **candidate**, because its
[official configuration documentation](https://github.com/Gaius-Augustus/Tiberius/blob/main/model_cfg/README.md)
explicitly enables softmask input. A model that ignores case would not answer
this question. Project/remote audit found no ready Tiberius installation,
matching weights or complete-CDS-chain evaluator. No installation/download or
gene inference was performed.

Existing assets include hg38 sequence, chr13 P3/candidates, and
`data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz` with SQL fields
for CDS completeness and exon frames. Existing gene-safety code measures
feature overlap/masking harm, not gene prediction accuracy; one older script
is chr19-specific and must not be run for this DEV experiment.

Before inference, fix complete CDS-chain matching, isoform counting,
boundary-spanning gene treatment, context and the predictor version/weights.
Report chain precision/recall/F1, gained/lost correct genes, new unmatched
predictions, and **all** added masking over CDS/exons/splice sites, including
comparator-positive sequence. TE comparator-positive does not mean gene-safe.

Pro suggested F1 gain >=0.005 and <=0.1% loss of originally correct genes as
investment thresholds. These are draft resource decisions, not established
biological constants; the actual gene denominator and discrete loss allowance
must be explicit before they are frozen. A positive MP-versus-MW result would
motivate partial-fill learning; a negative result limits that investment for
this predictor/intervention, not all possible uses of TE annotation.

## Deferred work and resource boundaries

There is no executable 20-locus empty-site panel: the cited Phase 0 document
contains a proposed minimum experiment, not coordinates/assemblies. The actual
172 FlyBase packets (12 calibration, 120 main, 40 reserve; dmel_r6.68) and
same-assembly structural evidence are not independent empty-site truth. Do not
revive the retired, expert-dependent Gate L under a new label.

The ordered-versus-shuffled H replay remains a possible finite diagnostic,
not evidence that ordered training caused failure. If later selected, use a
fixed-seed sample of the block list, not unnecessary coordinate hashes, and
compare equal update counts from paired initialization without unfreezing P3.

Pro's 50–90 GPU-hour estimate for full A and 2–8 GPU-hours for C were planning
estimates, not measured reservations or authorizations. Actual runtime must
come from a bounded readiness smoke. This turn used only the CPU diagnostic;
no new neural training, production mask change, external publication, or
sealed-test access was initiated.
