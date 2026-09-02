# GAP bridge neural Stage 0 oracle result

Date: 2026-09-02  
Protocol: `GAP_BRIDGE_NEURAL_STAGE1_R1`  
Status: **PASS_TO_STAGE1**  
Code commit: `0946cd5002a26fa73aaf0c224424d672ecc443b7`  
Slurm job: `12153655` (`COMPLETED`, exit `0:0`, elapsed `00:02:38`)  
Remote output: `outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0-oracle-20260902-r1`

## Decision

The frozen Stage 0 oracle passed on aggregate Human chr3+chr5 and, without
reselecting the policy, on the frozen chr13 DEV superblocks. This authorizes
only the frozen Stage 1 hook-identity check and the nested G/R/H gap-head
experiment. It does not promote an oracle-refined mask and does not establish
that any deployable model can recognize the selected gaps.

The selected oracle policy is exactly `rho = 0`: fill every model-eligible,
comparator-known 1--512-bp gap only when its entire span contains zero
comparator-negative bases. The result therefore establishes a large and
transferable whole-gap action ceiling. It also makes the Stage 1 problem
sharper: the learned head must distinguish completely comparator-positive gaps
from every gap containing even one comparator-negative base.

## Frozen data contract

| Role | Data | Use |
|---|---|---|
| policy selection | chr3 + chr5 | enumerate exact negative-fraction frontier and choose `rho` |
| transfer DEV | chr13 DEV, 9 of 22 deterministic 5,242,880-bp superblocks | apply the same `rho=0` without reselection |
| calibration reserves | chr13 CAL-FIT/CAL-GATE, 7/6 blocks | not used in Stage 0 decision |
| sealed test | chr19 | comparator labels not retained or used |
| later reserves | chr20--chr22 | not retained or used |

Eligibility was resolved before comparator projection: a complete
`[left 256][gap 1--512][right 256]` crop had to lie in real chromosome sequence
and contain only A/C/G/T. The action remained `fill_complete_gap_or_abstain`;
partial filling was not evaluated.

| Denominator | chr3+chr5 | chr13 DEV |
|---|---:|---:|
| model-eligible candidates | 741,669 | 60,574 |
| comparator-known candidates | 741,503 | 60,569 |
| candidates containing comparator-unknown bp | 166 | 5 |
| model-eligible gap bp | 44,724,027 | 3,451,022 |
| comparator-known gap bp | 44,697,058 | 3,449,084 |
| full gap bp in unknown-containing candidates | 26,969 | 1,938 |
| effective comparator-unknown bp | 8,232 | 475 |
| label-blind ineligible candidates | 114,353 | 154,474 |

The whole-mask denominator excludes effective comparator-unknown intervals.
The `<=10` negative-bp/Mb safety denominator is the separate label-blind ACGT
genome denominator.

## Exact result

| Metric | chr3+chr5 raw P3 | chr3+chr5 oracle | chr13 DEV raw P3 | chr13 DEV oracle |
|---|---:|---:|---:|---:|
| selected candidates | -- | 190,222 | -- | 17,660 |
| selected gap bp | -- | 1,507,660 | -- | 143,476 |
| selected comparator-negative bp | -- | 0 | -- | 0 |
| added-bp precision | -- | 1.000000 | -- | 1.000000 |
| bp precision | 0.920029 | 0.920675 | 0.918267 | 0.919056 |
| bp recall | 0.934726 | 0.943001 | 0.924765 | 0.934572 |
| bp F1 | 0.927319 | 0.931704 | 0.921505 | 0.926749 |
| bp MCC | 0.859181 | 0.867315 | 0.852782 | 0.862123 |
| split rate | 0.158220 | 0.000333 | 0.171522 | 0.000497 |
| fragments / truth | 1.347852 | 0.919393 | 1.416930 | 0.909208 |
| missed rate | 0.080944 | 0.080942 | 0.091319 | 0.091319 |
| short-prediction rate | 0.589973 | 0.498792 | 0.608059 | 0.505849 |

The relative split-rate reductions were 99.790% and 99.710% on chr3+chr5 and
chr13 DEV. Fragments/truth decreased by 31.788% and 35.833%, and short-rate by
15.455% and 16.809%. Absolute bp-F1 changes were +0.004385 and +0.005244.
Every original P3-positive base was retained.

Internal-gap bp recovery was 0.927723 on chr3+chr5 and 0.916238 on chr13 DEV;
for gaps longer than 5 bp it was 0.913312 and 0.899968. Overall positive-gap-bp
recovery was 0.291712 and 0.310734. The selected-candidate fractions of the
comparator-known universes were 0.256536 and 0.291568.

| Gap length | chr3+chr5 positive-bp recovery | chr13 DEV positive-bp recovery |
|---|---:|---:|
| 1 | 1.000000 | 1.000000 |
| 2 | 0.990832 | 0.992739 |
| 3--5 | 0.973553 | 0.974557 |
| 6--20 | 0.894956 | 0.917742 |
| 21--100 | 0.509272 | 0.538811 |
| 101--512 | 0.146884 | 0.167806 |
| `L > 5` | 0.252992 | 0.270784 |

All 15 preregistered dataset-level gates passed in both datasets. Because
`rho=0`, selected negative bp at curated splice +/-2, CDS, coding exon, all
exon and promoter features was zero; the maximum selected negative bp in any
transcript CDS was also zero. These are comparator-overlap safety results, not
evidence that gene annotation improved.

## Topology audit

Of the selected gaps, 186,763/190,222 on chr3+chr5 and 17,358/17,660 on chr13
DEV were strict comparator bridges. The remaining 3,459 and 302 were
all-positive non-bridges. Non-bridges recovered no internal-gap bp and changed
the chr3+chr5 fragment count by +1; they must not be described as same-instance
repair. No selected gap contained comparator-negative bp and no selected gap
joined two distinct merged comparator-positive runs under the frozen audit.

## What can be claimed

This is a valid scientific result for one narrow question:

> Under the frozen P3 Human mask, RepeatMasker-style comparator, 1--512-bp
> whole-gap action and the registered chr3+chr5-to-chr13-DEV split, a perfect
> zero-negative-bp oracle has enough coverage to improve bp and continuity
> endpoints while satisfying all registered point-estimate safety gates.

This is not a deployable method result. Comparator labels are used to define
the oracle action, RepeatMasker-style material is not independent biological
instance truth, and no post-training, raw sequence or P3 latent representation
has yet been shown to recover the oracle set.

## Engineering, closed routes and next-only

Engineering completed:

- the exact mask was rebuilt rather than inferred from cumulative counts;
- the frozen split and denominators were executed successfully;
- chr19 remained sealed; and
- no GPU or model training was used for this result.

Still closed:

- the previous feature-only G2 remains a validation no-go;
- threshold relaxation, minimum length, gap merging, HMM/CRF smoothing,
  partial fill and post-hoc chr13 reselection are not in-protocol rescues; and
- no refined mask is promoted from an oracle.

The only authorized next route is:

1. verify exact logits identity while exporting the frozen P3 width-128 map
   immediately before its four-state classifier;
2. train nested G (geometry/logits), R (G + local raw sequence) and H
   (R + frozen P3 latent) heads on identical candidates and seeds;
3. use chr13 DEV only for mechanism comparison, then CAL-FIT/CAL-GATE for one
   locked actionable operating point; and
4. release chr19 comparator labels once only if an arm passes every frozen
   pretest gate.

Continual backbone learning, Mouse/Fly tests and chr20--chr22 remain
unauthorized until the frozen Stage 1 evidence conditions are met.
