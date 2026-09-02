# Action-aligned neural whole-gap refinement

Date: 2026-09-02

Status: **protocol frozen; Stage 0 oracle audit authorized; chr19 remains sealed**

Protocol ID: `GAP-BRIDGE-NEURAL-STAGE1-R1`

Repository base: `d49ce1ec2503d455d4f9c19d1b9801c9d487c699`

External methods review:
[`ChatGPT Pro discussion`](https://chatgpt.com/g/g-p-6a29d586630481918525796032225f68-ji-wangke-ti/c/6a97eb65-42e4-83eb-b491-707f24156505)

## Decision being reopened

The completed feature-only G2 experiment remains a valid no-go for its actual
question: an L2 logistic model trained on clean bridge/separation labels from
26 scalar features did not yield a usable whole-gap action on the full chr13
primary denominator. It does not directly test either of the following:

1. supervision on the actual negative-bp cost of every comparator-known gap,
   including mixed gaps; or
2. position-resolved raw sequence and the frozen P3 pre-classifier latent map.

The scientific question reopened here is therefore narrow:

> Does a frozen P3 representation contain information beyond local DNA, P3
> logits and geometry that predicts the negative-bp cost of a whole-gap fill,
> and can that information reduce Human comparator-mask fragmentation on an
> unseen chromosome within fixed genome-wide and gene-feature risk budgets?

This is not another threshold sweep on the old clean classifier. The target,
deployment denominator and observable information all change. The original
P3 mask remains immutable.

## Immutable action and claim boundary

For every adjacent pair of maximal P3-positive runs, the candidate is their
intervening gap. The only two actions are:

- fill the complete gap; or
- abstain.

Stage 1 may not partially fill a gap, delete a P3-positive base, recenter an
8192-bp P3 window, update the P3 backbone/U-Net, add an HMM/CRF, or tune on
chr19. Candidates are 1--512 bp and use 256 bp of sequence on each side. The
P3 window, stride and TE threshold remain 8192, 8192 and 0.5.

The estimand is comparator-consistent secondary softmask continuity. Neither
an all-positive gap nor a successful fill proves same-copy identity,
historical insertion identity, ancestral boundaries or nested parentage.
Distinct-comparator-run fusions and selected gaps containing negative bp are
reported explicitly.

## Why the old G2 target was misaligned

For candidate `i`, let:

- `L_i` be the complete gap length;
- `N_i+` be comparator-positive gap bp;
- `N_i-` be comparator-negative gap bp; and
- `N_i?` be comparator-unknown gap bp.

The old model fitted only rows with `clean_target in {0,1}`, while its action
threshold was evaluated on every eligible row with `N_i? = 0`. Mixed gaps
were therefore present at deployment but absent from the fitted estimand.

The new sole target is

`r_i = N_i- / L_i`,

the negative-bp risk of filling the complete gap. A prediction of 0.98 versus
0.97 is not interpreted as a semantic correct/incorrect boundary. A frozen
threshold is chosen only by constrained action utility.

## Stage 0: whole-gap oracle feasibility

Stage 0 asks whether the action ontology is worth learning before any GPU
training. It does not measure prediction performance.

### Label-blind model eligibility

A candidate is model eligible only when all conditions below hold before the
comparator is read:

- it comes from adjacent maximal runs in the frozen P3 mask;
- `1 <= L_i <= 512`;
- `[gap_start - 256, gap_end + 256)` lies inside the real chromosome;
- the complete crop contains only A/C/G/T; and
- it contains no padding, assembly N or P3-unknown base.

Other candidates permanently abstain under
`MODEL_INELIGIBLE_LABEL_BLIND`. The existing whole-chromosome `region.jsonl.gz`
provides the sequence needed for this eligibility check; the existing TSV by
itself proves callability only for the gap, not for both flanks.

The main oracle universe is the model-eligible subset with `N_i? = 0`.
Unknown candidates are counted and scored in later label-blind deployment,
but cannot provide a supervised target. Any selected unknown bp is negative
under the final worst-case safety calculation.

### Frozen strata and oracle policy

Gap-length strata are fixed as 1, 2, 3--5, 6--20, 21--100 and 101--512 bp.
Every main statistic is also reported for `L <= 2` and `L > 5`.

Stage 0 assigns the perfect but unavailable deployment score `r_i` and
enumerates the whole-gap policies

`action_i(rho) = 1[r_i <= rho]`.

For every unique `rho`, it reports candidate and gap-bp coverage, added
positive/negative bp, added-bp precision, positive-gap-bp recovery and the
negative-bp rate per label-blind ACGT genomic bp. Whole-mask confusion metrics
use ACGT bp after effective comparator-unknown intervals are excluded. It must construct each candidate
mask needed for a potentially admissible frontier point and recompute the
existing whole-mask and fragmentation endpoints, rather than assume that
each fill removes one fragment.

Required mask endpoints are bp precision/recall/F1/MCC, predicted run count,
split rate, fragments/truth, missed rate, short rate, terminal omission,
internal-gap count and bp, and recovery for internal gaps longer than 5 bp.
The raw P3-positive mask must be retained exactly.

Two zero-risk subsets are reported separately:

- strict comparator bridge: the gap and adjacent bases lie in one comparator
  run; and
- all-positive gap with a non-bridge/unsupported flank relation.

The second subset is material-safe under the narrow bp target but exposes the
topology/fusion limitation and may not be described as a same-instance repair.

### Gene-feature safety

The frozen `hg38 ncbiRefSeqCurated-20250813` asset is used only after an
oracle policy is selected. Definitions remain all curated transcripts,
union CDS, coding exons, all exons, internal exon boundaries +/-2 bp and
strand-aware TSS +/-200 bp promoters. Canonical-transcript selection is not
allowed.

### Frozen oracle selection and gate

On the aggregate chr3+chr5 oracle frontier, choose the policy that maximizes
absolute split-rate reduction among points satisfying all constraints below.
Ties prefer fewer negative bp, then more recovered positive gap bp, then the
smaller `rho`. Apply that same `rho` to the chr13 DEV blocks without
reselection.

Both chr3+chr5 and chr13 DEV must satisfy:

- selected candidates `>= max(1000, 1% of the oracle-known universe)`;
- added comparator-negative bp `<= 10` per Mb of label-blind callable genome;
- whole-mask precision decreases by no more than 0.001;
- whole-mask F1 and recall do not decrease;
- every raw P3-positive bp is retained;
- split rate and fragments/truth each decrease by at least 10% relative;
- short rate does not increase;
- positive-gap-bp recovery is at least 10% overall and 5% for `L > 5`;
- no worst-case negative/unknown bp is added at splice +/-2 bp;
- worst-case callable-CDS negative rate is at most `1e-5`;
- no transcript CDS receives more than 20 worst-case negative bp;
- all-exon and promoter worst-case rates are at most `2e-5` and `5e-5`.

Failure of any dataset-level requirement is
`WHOLE_GAP_ORACLE_NO_GO`. It closes this P3/Human/whole-gap ontology before
neural training. Partial fill, a new loss, HMM/CRF or window recentering may
not be introduced as an in-protocol rescue.

## Human split and seal

Chromosome roles are frozen:

| Data | Role |
|---|---|
| chr3 + chr5 | head training and Stage 0 policy selection |
| chr13 DEV | threshold-independent mechanism evaluation and Stage 0 transfer |
| chr13 CAL-FIT | calibration fitting only |
| chr13 CAL-GATE | threshold and pretest arm lock only |
| chr19 | one-use sealed test |
| chr20--22 | untouched reserve for a possible later continual-learning protocol |

Chr13 uses label-blind 5,242,880-bp superblocks, exactly 640 original P3
windows. The string
`GAP_BRIDGE_NEURAL_STAGE1_R1|chr13|start|end` is SHA256-ranked before any
comparator field is read. Role counts use largest-remainder allocation of
40% DEV, 30% CAL-FIT and 30% CAL-GATE, with ties resolved in that role order;
for the 22 hg38 chr13 superblocks this gives 9, 7 and 6 blocks. The digest is
the consumed split function, not an unused provenance asset. A candidate is
assigned by midpoint; a 256-gap-256 crop crossing a superblock boundary is
quarantined from all three selection splits.

All comparator-known mixed, all-positive and all-negative gaps enter the
natural supervised denominator. Comparator support of the two P3 flanks is
evaluation-only and may not be an input or sampling variable. Comparator
family/subfamily is also evaluation-only. Raw-sequence homology purge is a
reported challenge, not a feature.

## Stage 1 mechanism arms

All three arms share an identical 1024 x 143 padded tensor and the same
readout. The unpadded order is `[left256][complete gap][right256]`; padding is
only at the right end.

Per-base channels are three P3 logits relative to background, the frozen P3
binary mask, three left/gap/right tags, two clipped relative distances to the
gap boundaries, one validity mask, five raw-DNA slots and 128 latent slots.

Implementation encoding is frozen as follows. Channel order is relative logits
`interior-background`, `left_boundary-background`,
`right_boundary-background`; P3 mask; left/gap/right tags; left and right
distance; validity; raw `A,C,G,T,PAD`; then the 128 decoded channels. For a real
base at genomic coordinate `x`, the two distance channels are
`clip((x-gap_start)/512,-1,1)` and
`clip((x-gap_end)/512,-1,1)`. Right padding has validity zero, `PAD=1`, and all
other channels zero. Every real crop position is A/C/G/T and has validity one;
exactly one of its left/gap/right tags is one.

| Arm | Active information |
|---|---|
| `G_GEOMETRY_LOGITS` | P3 logits/mask, tags, positions and geometry; raw and latent slots zeroed |
| `R_RAW_LOCAL` | G plus raw one-hot DNA; latent slots zeroed |
| `H_P3_LATENT` | R plus the frozen P3 width-128 pre-classifier decoded U-Net map |

The latent is taken immediately before the four-state 1x1 classifier. It
retains task-adapted information discarded by that linear classifier while
avoiding the 1280-channel backbone track. An H-over-R result supports only a
claim about the frozen task-adapted P3 latent, not an isolated causal claim
about foundation-model pretraining.

Each arm also receives seven train-standardized scalars: log gap, left-run,
right-run and span lengths, seam indicator, log absolute seam distance and
signed seam direction. GC, entropy, k-mer and microhomology summaries are not
added because the raw arm must learn sequence information itself.

The four length scalars are `log1p(gap_end-gap_start)`,
`log1p(gap_start-left_run_start)`, `log1p(right_run_end-gap_end)` and
`log1p(right_run_end-left_run_start)`. A seam is an 8192-bp window-grid
boundary. The indicator is one when the unpadded crop crosses a grid boundary.
For gap midpoint `m=(gap_start+gap_end)/2`, the final two scalars are
`log1p(abs(b-m))` and `sign(b-m)`, where `b` is the closest 8192-bp grid
boundary and an exact tie selects the lower boundary. Means and population
standard deviations are computed once from comparator-known chr3+chr5 TRAIN
candidates, stored, and then frozen. A zero standard deviation is an
engineering failure because it leaves this registered encoding undefined.

The fixed readout is a 143-to-32 1x1 convolution, GELU/LayerNorm, four
32-channel residual depthwise-separable convolution blocks with kernel 5 and
dilations 1/2/4/8, masked mean and max pooling for each of left/gap/right,
then `199 -> 64 -> 1` with GELU and dropout 0.1. All arms retain the same
parameter count and paired initialization.

The local latent is captured while each original 8192-bp window is processed.
A one-window carry buffer joins crops crossing a window seam by genomic
coordinate. The gap head consumes the crop immediately; no chromosome-scale
128- or 1280-channel hidden track is written.

## Loss, training and calibration

The sole output is calibrated negative fraction. Training uses soft-target
BCE. The six length strata receive equal total optimization weight; within a
stratum a candidate is weighted proportional to its length, then all weights
are normalized to mean one. Natural-prevalence metrics are never reweighted.
No clean-relation, family, boundary or other auxiliary head is allowed.

Constants are fixed:

- seeds 17, 42 and 20260902;
- two complete chr3+chr5 block-stream passes;
- AdamW, learning rate `3e-4`, weight decay `1e-4`, betas `(0.9, 0.999)`;
- effective candidate batch 512, gradient clipping 1.0;
- dropout 0.1;
- frozen P3 in eval mode;
- no early stopping, model selection or hyperparameter search; and
- the three seed logits are averaged, never best-seed selected.

Each arm fits a monotone Platt calibrator on CAL-FIT using length-weighted BCE.
The calibrator is frozen before CAL-GATE and never refit on chr19.

## Metrics and action selection

The primary threshold-independent endpoint is bp-weighted action AUPRC. Each
candidate score contributes `N_i+` positive weight and `N_i-` negative weight.
Also report normalized AUPRC, AUROC, bp-weighted log loss/Brier, six-stratum
macro Brier, natural Brier, and risk--coverage/continuity Pareto curves.

Calibration gates on CAL-GATE and chr19 are equal-bp-mass 10-bin ECE at most
0.025 and calibration-in-the-large absolute error at most 0.01.

CAL-GATE enumerates calibrated risk thresholds. Admissibility uses the Stage
0 genome/gene/whole-mask safety limits, plus worst-case negative/unknown bp at
most 20 per Mb. Utility uses the Stage 0 candidate coverage, positive-gap-bp,
long-gap, split-rate, fragments/truth and short-rate limits. Among admissible
points, select maximum absolute split-rate reduction, then fewer negative bp,
more positive recovered bp and the smaller risk threshold. Added-bp precision
is reported but is not fixed at 0.98.

All comparisons use 1000 paired 1-Mb block bootstrap replicates with seed
20260902. Seam/non-seam, flank-support, family and homology-purged results are
mandatory secondary strata.

## Mechanism and route gates

R demonstrates information beyond G on chr13 DEV only if all hold:

- action bp-AUPRC improves by at least 0.010 and paired 95% lower bound is
  positive;
- bp-weighted Brier decreases at least 5%;
- at the same `1e-5` negative-bp/genome budget, recovered positive gap bp or
  resolved split edges improves at least 10%, with at least 1000 bp or 100
  edges absolute improvement respectively;
- all three seeds have higher AUPRC; and
- the AUPRC difference remains positive after homology purge.

H must pass the identical conditions relative to R to demonstrate incremental
P3-latent information.

An arm is actionable only when CAL-GATE contains an admissible point. Pretest
selection is H if it is both incremental and actionable, otherwise R if it is
both informative and actionable, otherwise G if it alone is actionable. If no
arm is actionable, chr19 remains sealed and P3 remains the only mask.

Before chr19 labels are released, all three arms are scored label blind and
the selected arm, calibrator and threshold are locked. Chr19 is then evaluated
once. The selected arm must retain all CAL safety and utility point estimates;
the known negative-bp rate must also have a 1-Mb bootstrap 95% upper bound at
most `2e-5`, and both continuity improvements must have positive lower bounds.
No test-side arm switch, calibration, threshold or retraining is allowed.

Backbone continual learning is not part of Stage 1. It becomes eligible only
for a new protocol if H is selected and passes chr19, H-over-R remains at least
0.010 with a positive paired lower bound in natural and homology-purged sets,
the gain is not confined to `L <= 2`, and H reaches less than 70% of the Stage
0 oracle split reduction. Chr20 is then reserved for Stage 2
validation/calibration and chr21+chr22 for sealed confirmation.

## Execution order and resource estimate

1. `S0-ORACLE`: CPU audit on chr3+chr5 and chr13 DEV.
2. `S1-HOOK-IDENTITY`: frozen chr17 engineering identity check.
3. `S1-TRAIN-PASS1` and `S1-TRAIN-PASS2`: one P3 forward per window feeding
   all nine paired heads.
4. `S1-CHR13-SCORE` followed by DEV mechanism, CAL-FIT calibration and
   CAL-GATE pretest lock.
5. Only after a PASS: label-blind chr19 scoring, then one comparator release
   and final evaluation.

Estimated cost is 40--120 CPU core-hours for Stage 0; 62--79 GPU-hours and
300--800 total CPU core-hours for complete Stage 1; and 15--30 GB durable
storage. Full hidden tracks are prohibited.

## Interpretation

A successful G arm supports calibrated geometry/logit-based mask refinement.
A successful R arm additionally supports local raw sequence as action-relevant
information. A successful H arm additionally supports incremental information
in the frozen P3 task-adapted latent representation.

No outcome in this protocol licenses claims about biological insertion
identity, ancestral boundaries, nested parentage, de novo TE discovery,
improved gene prediction, independent foundation-pretraining causality,
cross-species generalization, Mouse/Fly performance or partial filling.

The immediate decision is only whether Stage 0 demonstrates a learnable and
useful whole-gap action ceiling. Until it passes, no Stage 1 GPU job is
authorized.
