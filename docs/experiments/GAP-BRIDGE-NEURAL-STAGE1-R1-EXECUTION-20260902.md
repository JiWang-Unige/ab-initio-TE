# GAP-BRIDGE-NEURAL-STAGE1-R1 execution ledger

Date: 2026-09-02

Status: **Stage 0 and all Stage 1 pretraining gates passed; frozen G/R/H training is running; no chr19 release**

Protocol: [`GAP-BRIDGE-NEURAL-STAGE1-R1-SPEC.md`](GAP-BRIDGE-NEURAL-STAGE1-R1-SPEC.md)

This ledger distinguishes engineering identity checks and evaluation assets
from scientific model results. No Stage 1 model score exists yet.

## Completed decisions

### S0 whole-gap action oracle

Slurm job `12153655` completed successfully. The registered Stage 0 gate was
`PASS_TO_STAGE1` at `rho=0`: filling only comparator-known, zero-negative-bp
gaps provides a useful Human whole-gap action ceiling on both chr3+chr5 and
held-out chr13 DEV. Full endpoints are recorded in
[`GAP-BRIDGE-NEURAL-STAGE0-RESULT-20260902.md`](GAP-BRIDGE-NEURAL-STAGE0-RESULT-20260902.md).
This is an unavailable oracle and is not a deployable result.

### Candidate universe

Slurm job `12154205` completed successfully and wrote 926,253 candidates.
The frozen populations are:

| Role | Chromosome | All | Comparator-known | Comparator-unknown |
|---|---|---:|---:|---:|
| TRAIN | chr3+chr5 | 741,669 | 741,503 | 166 |
| DEV | chr13 | 60,574 | 60,569 | 5 |
| CAL-FIT | chr13 | 66,742 | 66,739 | 3 |
| CAL-GATE | chr13 | 57,268 | 57,263 | 5 |

Twenty-two chr13 crops crossing a role-superblock boundary were quarantined
before comparator use. The manifest did not read chr19.

### Exact latent hook identity

Slurm job `12153995` completed successfully in 01:14:11. On 1,200 frozen
chr17 windows:

- hooked and unhooked logits were bitwise equal;
- the captured classifier input had shape `[1, 128, 8192]`;
- classifier output had shape `[1, 4, 8192]` and equalled forward logits;
- the 25,543 ordered canonical P3 prediction intervals exactly matched the
  historical output; and
- no decoded latent track was written to disk.

This is an engineering identity result. It establishes that arm H reads the
registered pre-classifier decoded U-Net map without changing P3 inference; it
does not establish biological utility.

### DEV homology-purge challenge

Slurm job `12154626` completed successfully. Label-blind 256-bp chr13 DEV
flanks were compared with chr3+chr5 TRAIN flanks using the frozen alignment
contract. It purged 246/60,574 candidates (`0.004061148`), leaving 60,328 for
the mandatory secondary mechanism analysis. The small fraction shows that
this particular detectable flank-homology route is uncommon; it does not
prove absence of family or sequence leakage.

### Evaluation-only family projection

Slurm job `12155477` completed successfully. Its 184,584 candidate IDs exactly
match the scored chr13 DEV/CAL-FIT/CAL-GATE denominator. Projection from the
strict RepeatMasker BED onto `gap_start-1` and `gap_end` produced:

| Flank relation | Candidates |
|---|---:|
| unique same class/family | 52,450 |
| different class/family | 8,085 |
| multiple labels | 55 |
| unsupported on at least one side | 123,994 |

These fields are secondary evaluation strata only. They are not read by the
scorer, calibrator, threshold selector or mechanism gate.

## Frozen implementation audit

The label-blind scorer, monotone calibration/statistical primitives and
family projection are on GitHub main through commit `e2f4775`. Before any
model score was produced, two metric implementation errors were caught and
corrected: weighted AUROC direction and the positive/negative terms in
pseudo-base log loss. Expanded integer-mass comparisons against scikit-learn
now pass. Fourteen targeted scorer/metric/family tests pass in the Baobab
`te_benchmark` environment.

## Active experiment

Slurm job `12156002` is the single frozen Stage 1 training attempt
`train-20260902-r1`. It trains all three nested information arms and three
registered seeds together on comparator-known chr3+chr5 candidates for two
complete passes:

- G: P3 logits/mask plus candidate geometry;
- R: G plus local raw DNA; and
- H: R plus the frozen 128-channel P3 decoded map.

The P3 backbone remains frozen in evaluation mode. No chr13 comparator label
is used for optimization and chr19 remains sealed. Completion of this job is
not itself a scientific result: chr13 label-blind scoring, CAL-FIT-only
calibration, DEV mechanism tests and CAL-GATE actionability still have to
pass before any arm can be locked for chr19.

## Current decision boundary

Do not start continual backbone training, partial-gap prediction, HMM/CRF,
cross-species work or chr19 evaluation while `12156002` is unresolved. If R
does not increment G, raw local sequence has not supplied registered action
information. If H does not increment R, the frozen P3 latent has not supplied
registered incremental information. If no arm has an admissible CAL-GATE
point, retain the original P3 mask and close this whole-gap Stage 1 route.
