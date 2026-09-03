# GAP-BRIDGE-P3-NT-DONOR-RISK-R1

Date: 2026-09-03

Status: **conditional-only; protocol frozen; not authorized to execute**

This document freezes the only cross-backbone experiment that may be
considered **after a valid Stage 1 scientific failure**. It is not part of the
currently running `GAP-BRIDGE-NEURAL-STAGE1-R1`, is not an additional G/R/H
arm, and does not authorize reading chr19. It does not modify
`ACTIVE_GOAL.json`, code, data, checkpoints, or the current Stage 1 execution.

## Authority and motivation

This protocol is subordinate to the frozen
[`GAP-BRIDGE-NEURAL-STAGE1-R1-SPEC.md`](GAP-BRIDGE-NEURAL-STAGE1-R1-SPEC.md)
and its
[`GAP-BRIDGE-NEURAL-STAGE1-R1-EXECUTION-20260902.md`](GAP-BRIDGE-NEURAL-STAGE1-R1-EXECUTION-20260902.md).
The external review that motivated this conditional branch is the
[ChatGPT Pro discussion](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6a97eb65-42e4-83eb-b491-707f24156505).

The retrospective backbone diagnostic is motivation only. It compared
GENERanno H0 and NTv2-250M H0 on the already consumed Human chr17 4096-bp
screen. It showed model-derived error-coordinate complementarity, but it did
not use the P3-R1 candidate universe. Therefore it has **not** established
NT complementarity on the actual P3-R1 whole-gap candidates, has not selected
an action threshold, and cannot be counted as evidence for this protocol.

## Decision boundary

| Item | Frozen decision |
|---|---|
| Trigger | A valid `GAP-BRIDGE-NEURAL-STAGE1-R1` run has a scientific gate failure. An engineering/IO/Slurm failure is not a scientific failure and does not trigger this branch. |
| Current state | **Do not execute.** The current Stage 1 G/R/H training and all its gates remain unchanged. |
| Current G/R/H status | No NT fourth arm is added; no NT input is read by the current scorer. |
| Scientific question | Does a frozen NT continuous per-base signal add conditional whole-gap action-risk information beyond the complete Stage 1 H information? |
| Candidate source | The original P3-R1 candidates only; NT may not create candidates. |
| Action ontology | Fill the complete candidate gap or abstain; never partial fill. |
| Sealed test | At trigger resolution, use chr19 if it is still unconsumed; otherwise use chr20. Do not read either chromosome before authorization. |
| Reserve | chr21 and chr22 remain untouched. |

The branch is therefore a single, pre-registered test of

\[
I\left(z^{NT}; r_i \mid X^{H}_{P3}\right) > 0,
\]

where (X^{H}_{P3}) is the complete frozen Stage 1 H input and
`r_i = N_i^- / L_i` is the comparator-negative fraction of the complete gap.
It is not a test of whether NT is better than P3 in isolation, whether a
fixed NT threshold is optimal, or whether two models should be combined by
OR, AND, or mean probability.

## Frozen candidate universe and data split

The conditional experiment inherits the Stage 1 data contract without
reselection:

| Component | Frozen value |
|---|---|
| Anchor | Actual P3-R1 adjacent maximal positive runs with a 1--512-bp intervening gap |
| Candidate crop | `[left256][complete gap][right256]`, padded only at the right to 1024 positions |
| Target | `r_i = N_i^- / L_i`, using comparator-known candidates for supervised fitting |
| Training | chr3 + chr5, the existing Stage 1 TRAIN role |
| Evaluation split | Existing chr13 DEV / CAL-FIT / CAL-GATE block split, unchanged |
| Sealed test | First unconsumed chromosome in the ordered choice chr19, then chr20 |
| P3 geometry | Native non-recentered 8192-bp windows and original P3-R1 mask/logits |
| NT geometry | Native 4096-bp windows, mapped back by genomic coordinate; no centered re-forward |
| Comparator | Target and evaluation only; no comparator support, family, or label field is an input |

The existing block assignment, boundary-crossing quarantine, known/unknown
handling, homology-purge secondary analysis, bootstrap units, and gene-feature
contract are inherited exactly. Augmentation, family stratification, and any
sampling decision based on comparator fields are prohibited.

Unknown candidates cannot supply a training target. If an unknown bp is
selected at deployment, it counts as negative in the worst-case safety
calculation. The original P3-positive bases are always retained.

## Strictly paired arms

Only two new readout arms are permitted:

| Arm | Input |
|---|---|
| `H0_P3_FULL` | Complete Stage 1 H information; all newly allocated NT and NT-seam slots are zero |
| `HN_P3_PLUS_NT` | `H0_P3_FULL` plus the frozen NT continuous signal and its three seam scalars |

The G and R arms are not retrained or reintroduced. P3 and NT backbones are
both frozen in evaluation mode. H0 and HN use the same readout, parameter
count, initialization, seeds, optimizer, loss, block stream, and calibration
procedure. The zeroed slots in H0 are allocated so that the comparison is
capacity-paired rather than a comparison of different input-layer sizes.

### The only new information

Relative to H0, HN receives exactly:

1. one NT per-base continuous logit channel;
2. one scalar indicating whether the crop crosses an NT 4096-bp window seam;
3. `log1p` distance from the gap midpoint to the nearest NT seam;
4. the signed direction from that seam to the gap midpoint.

For genomic position (x), the only NT channel is

\[
z^{NT}(x) = \operatorname{clip}\left(
\log\frac{p^{NT}_{TE}(x)}{1-p^{NT}_{TE}(x)}, -12, 12\right).
\]

`p^{NT}_{TE}` is the frozen NTv2-250M per-base TE probability aligned to the
P3 candidate crop by genomic coordinate. The continuous logit is retained;
it is not binarized at 0.5. HN may therefore learn a gap-internal profile
from the signal, while H0 sees the same allocated channel as zero.

The Stage 1 per-base tensor has 143 channels. Both conditional arms allocate
`1024 x 144`; H0 zeros the added channel and HN activates it. Both arms carry
the seven frozen Stage 1 candidate scalars plus the three NT-seam scalars
(10 scalars total). No NT latent, family prediction, binary support bit,
new candidate, hand-set threshold, or ensemble arithmetic is allowed.

The following are explicitly excluded because the retrospective diagnostic
already closed them as non-actionable or they would change the question:

- NT latent states or any third backbone;
- NT-generated candidates;
- OR, AND, mean-probability, weighted voting, or complete-gap donor rules as
  a learned input;
- NT probability threshold sweeps;
- maximum-gap or minimum-flank-support sweeps;
- partial filling, gap merging, minimum-length filtering, or HMM/CRF rescue;
- candidate-centered P3 or NT re-encoding;
- any comparator family, boundary, or support field as a model feature.

## Readout and training

The conditional arms reuse the Stage 1 readout contract with equal capacity:

- per-base tensor `1024 x 144`;
- scalar vector of length 10;
- `144 -> 32` 1x1 convolution;
- the same four depthwise-separable residual convolution blocks, kernel 5,
  dilations 1/2/4/8;
- masked mean and max pooling over left/gap/right;
- the same `202 -> 64 -> 1` output path;
- GELU/LayerNorm and dropout 0.1 as in Stage 1.

The output is the calibrated expected negative fraction for a complete-gap
action. Training uses the same soft-target BCE, length-stratum weighting,
AdamW settings, clipping, and two complete chr3+chr5 block-stream passes as
Stage 1. Seeds remain `17`, `42`, and `20260902`; three seed logits are
averaged and no best seed is selected. P3 and NT remain frozen; no backbone
post-training is part of this branch.

Each arm fits one monotone Platt calibrator on comparator-known CAL-FIT rows
only, with the Stage 1 length-weighted BCE contract. The calibration maps are
frozen before CAL-GATE and before the sealed test.

## Descriptive baselines

These are evaluated only and cannot select the arm or tune a parameter:

1. original P3-R1 mask;
2. NTv2-250M single-model mask at its fixed 0.5 decision;
3. `H0_P3_FULL`;
4. the frozen, deterministic P3-anchor plus NT complete-gap-support rule,
   with its already specified support and length limits.

The fixed donor rule cannot be optimized on chr13 or the sealed test. It is a
reference for whether HN learns conditional risk rather than merely copying
a hand-written donor action.

## Metrics and gates

All candidate action metrics use the same denominator and the same whole-gap
mask reconstruction as Stage 1. The action is always complete-gap fill or
abstain. Unknown selected bp count as negative under worst-case deployment
safety. Use paired 1-Mb bootstrap units, 1,000 replicates, seed `20260902`,
including zero-candidate bins.

### DEV mechanism gate: HN versus H0

HN is informative only if every condition below holds on chr13 DEV:

1. unnormalized bp-weighted action AUPRC improves by at least `0.010`, with
   a paired 95% lower bound strictly above zero;
2. bp-weighted Brier decreases by at least 5%;
3. at the same `1e-5` negative-bp/genome budget, either positive gap bp
   increases by at least 10% and 1,000 bp, or resolved split edges increase
   by at least 10% and 100 edges;
4. all three seeds have higher action AUPRC for HN than H0;
5. the AUPRC difference remains positive after the frozen homology purge;
6. the HN admissible frontier is better than the fixed donor rule at the same
   budget, rather than merely reproducing it.

The threshold-independent report must also include AUROC, bp-weighted log
loss/Brier, natural and six-stratum Brier, calibration curves, risk-coverage
curves, length strata, seam/non-seam strata, flank-support strata, family
evaluation strata, and homology-purged strata. These secondary reports do not
replace the gate.

### CAL-FIT and CAL-GATE action gate

The Stage 1 calibration and action contract is reused without relaxation or
an NT-specific threshold contract. CAL-GATE enumerates calibrated score ties,
never partially selects a tie group, and locks one threshold by the existing
utility ordering. A selected point must satisfy all of the following:

- known negative bp at most 10 per Mb;
- worst-case negative/unknown bp at most 20 per Mb;
- whole-mask precision does not decrease by more than 0.001 and whole-mask
  F1/recall do not decrease;
- original P3-positive bases are all retained;
- overall positive-gap-bp recovery is at least 10% and recovery for `L > 5`
  is at least 5%;
- split rate and fragments/truth each decrease by at least 10%;
- short rate does not increase;
- all frozen CDS, transcript, exon, promoter, splice-boundary and
  worst-case-unknown safety gates pass;
- equal-bp-mass ECE is at most 0.025 and calibration-in-the-large absolute
  error is at most 0.01.

If no HN point is admissible, the conditional route is closed. H0 remains a
diagnostic control; it cannot be replaced by a newly chosen arm after seeing
CAL-GATE.

### Sealed-test gate

After the arm, calibrator, and threshold are locked, the chosen conditional
action is run once on the first unconsumed sealed chromosome. No test-side
arm switch, calibration, threshold change, retraining, or NT threshold is
allowed. In addition to every Stage 1 safety and utility gate, HN must justify
the cost of using the second backbone relative to the same sealed chromosome
P3 and NT single-model baselines:

#### Continuity and fragmentation

\[
F_{all}^{HN} \le 0.90\min(F_{all}^{P3},F_{all}^{NT})
\]

and, conditioning on detected truth runs,

\[
F_{det}^{HN} \le 0.90\min(F_{det}^{P3},F_{det}^{NT}),
\quad
F_{det}=\frac{\sum_j k_j}{\#\{j:k_j>0\}}.
\]

Also require

\[
split^{HN} \le 0.90\min(split^{P3},split^{NT}).
\]

#### Boundary and segment preservation

\[
boundaryF1@5^{HN} \ge
\max(boundaryF1@5^{P3}, boundaryF1@5^{NT}) - 0.005
\]

and simultaneously

\[
boundaryF1@5^{HN} \ge boundaryF1@5^{P3}+0.010.
\]

Segment F1 at IoU 0.8 must satisfy

\[
segmentF1^{HN} \ge
\max(segmentF1^{P3}, segmentF1^{NT}) - 0.005.
\]

#### Fusion, missed truth, and bp retention

Report both the absolute count and the rate

\[
fusion\_pred\_rate =
\frac{\#\text{multi-truth predicted runs}}
{\#\text{predicted runs}}.
\]

Require all of the following:

- multi-truth fusion runs for HN are no greater than P3;
- HN fusion-prediction rate is no greater than P3;
- the paired bootstrap 95% upper bound for the HN-minus-P3 fusion-rate
  difference is at most 0.005;
- missed truth does not increase relative to the original P3 action;
- bp precision and bp F1 each decrease by no more than 0.005 relative to the
  best single-model baseline;
- every original P3-positive bp remains present.

## Stop rules and route closure

The following outcomes close this branch immediately:

```text
CROSS_BACKBONE_WHOLE_GAP_ROUTE_CLOSED
NO_THIRD_BACKBONE
NO_OR_AND_MEAN_RESCUE
NO_DONOR_THRESHOLD_SWEEP
NO_PARTIAL_FILL_RESCUE
PRIMARY_MASK=P3_ORIGINAL
```

Closure occurs after any valid DEV mechanism failure, no admissible CAL-GATE
point, or any sealed-test failure. A technical failure is retained with its
real cause and is not put into a scientific denominator; it cannot be
silently converted into a scientific failure or used to relax a gate. A
technical rerun, if ever required, must preserve this protocol, use a unique
output label, and not change a scientific variable.

No follow-up may add a third backbone, reopen OR/AND/mean combinations, sweep
donor thresholds, introduce partial filling, or add a decoder solely to rescue
an observed failure. If the conditional route closes, retain the original P3
mask as the primary result and stop this comparator-supervised whole-gap
learned-refinement line.

## Claim boundary

### Permitted claims if the conditional experiment passes

- NT continuous prediction supplies incremental **model-derived conditional
  action-risk information** beyond the frozen P3 task-adapted H input;
- the selected whole-gap action is more continuous under the fixed
  comparator-consistent mask contract, with the reported safety and fusion
  controls;
- the result is a cross-backbone donor-risk refinement on the registered
  Human chromosome split.

### Claims that remain prohibited

No result in this protocol establishes:

- biological TE insertion identity or historical insertion boundaries;
- same-copy identity for adjacent or same-family fragments;
- correction of nested, deleted, or truncated TE parentage;
- independent biological truth from the NT model;
- de novo TE discovery, universal TE annotation, or cross-species transfer;
- improved gene annotation without a separately frozen gene-prediction
  evaluation.

The H0 diagnostic remains retrospective motivation, not an independent
scientific validation. In particular, the size of its observed coordinate
complementarity cannot be transferred to P3-R1 candidates until this exact
conditional experiment is run and passes its own gates.

## Frozen route summary

```text
Stage 1 unresolved or technically invalid
    -> keep G/R/H frozen; do not execute this protocol; do not read chr19

Stage 1 valid scientific FAIL
    -> one H0_P3_FULL versus HN_P3_PLUS_NT experiment
       actual P3-R1 candidates, same chr3+chr5 train, same chr13 split,
       whole-gap fill/abstain, one sealed chromosome

DEV/CAL/sealed failure
    -> close cross-backbone route; retain original P3 mask; no rescue branch

DEV/CAL/sealed PASS
    -> claim only incremental model-derived action-risk information;
       never biological instance recovery
```
