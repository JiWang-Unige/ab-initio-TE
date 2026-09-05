# GAP-BRIDGE-NEURAL-STAGE1-R1 closure

Date: 2026-09-05

Decision: **NO_ACTIONABLE_ARM — close the frozen Stage 1 whole-gap route,
retain the original P3 mask, and keep chr19 sealed.**

This is a valid scientific no-go after successful engineering execution.
The result does not establish that all gap correction or post-training is
impossible. It rejects deployment of the registered G/R/H readouts under the
registered whole-gap action, comparator, population and safety/utility gates.

## Evidence and execution

Protocol: [frozen Stage 1 spec](GAP-BRIDGE-NEURAL-STAGE1-R1-SPEC.md).
History: [execution ledger](GAP-BRIDGE-NEURAL-STAGE1-R1-EXECUTION-20260902.md).
Repository HEAD observed during closure: `934ef4254fef175ba0e80b13ca73bfa9e8f641a9`.

All source artifacts below are relative to the Baobab project
`/home/users/j/jwang/ab-initio-TE/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/`.

| Phase | Slurm job | Artifact directory | Outcome |
|---|---|---|---|
| Training | 12156002 | `train-20260902-r1` | PASS; nine heads; two complete passes of 741,503 known TRAIN candidates |
| Blind chr13 scoring | 12293475 | `score-20260904-r1` | COMPLETED, exit 0:0, 07:06:44; STATUS PASS |
| chr13 evaluation | 12331422 | `evaluate-20260905-r1` | COMPLETED, exit 0:0, 01:52:33; STATUS PASS |

Primary evidence is `score_summary.json`, `evaluation_summary.json`,
`cal_gate_frontier.tsv`, `cal_gate_selected.tsv`, and corresponding job-ID
logs. The raw-score TSV has one header plus 184,584 rows and all nine head
columns. Its summary records `labels_read=false`, `chr19_read=false`,
13,961 forwarded windows, and native 8192-bp window/stride geometry. No
chromosome-scale latent track was written.

Frozen split: chr3+chr5 training; chr13 DEV 60,574 candidates, CAL-FIT 66,742,
CAL-GATE 57,268. All arms use the same candidate universe. Comparator-unknown
candidates are excluded from supervised targets and known-bp metrics; any
selected unknown bp consumes the worst-case deployment budget. Three seed
logits are averaged before CAL-FIT-only monotone Platt calibration.

## What was tested

Each gap uses `[left256][complete gap][right256]`, with right padding to
1024 positions. G reads frozen P3 logits/mask and geometry; R adds raw DNA;
H adds the 128-channel decoded P3 U-Net map captured before its classifier.
The P3 model processes original 8192-bp windows in frozen eval mode.
The same small convolutional readout is trained for all arms and three seeds.
Its target is the negative-bp fraction of the whole gap; its action is to
fill the whole gap or abstain. This stage did not continue training P3.

Thus the proposed global-context-plus-local-gap-head design has now been
tested in this particular implementation. The result is not an experiment
on a new Transformer, a CRF, partial filling, or biological insertion identity.

## Mechanism results on chr13 DEV

| Endpoint | G | R | H |
|---|---:|---:|---:|
| bp-weighted action AUPRC | 0.319666 | 0.317994 | 0.328826 |
| Calibrated pseudo-base Brier | 0.104305 | 0.104402 | 0.103698 |
| Candidates at common 1e-5 error/genome budget | 154 | 249 | 169 |
| Recovered positive gap bp at that budget | 1,018 | 1,407 | 1,018 |
| Added known-negative bp at that budget | 233 | 273 | 314 |
| Resolved strict bridge edges at that budget | 125 | 198 | 140 |

R-over-G fails: action AUPRC delta -0.001671 (paired 95% interval
[-0.002747, -0.000560]), and all three seed deltas are negative. Its budgeted
utility gain is 389 positive bp or 73 edges, below the registered absolute
requirements of 1,000 bp or 100 edges.

H-over-R shows a real ranking signal within this comparison: action AUPRC
delta +0.010832 (paired 95% interval [0.007249, 0.014483]); all three seed
deltas are positive, and the homology-purged delta remains +0.010864.
However, pseudo-base Brier improves only 0.6744%, below 5%, and at the common
budget H recovers 389 fewer positive bp and resolves 58 fewer edges than R.
The full H-over-R mechanism gate therefore fails. Improved global ranking
does not demonstrate improved useful actions in the required low-error tail.

These intervals use the registered 1,000 paired 1-Mb block bootstrap. The
homology purge addresses the specified detectable flank-homology route; it
does not prove family-disjoint evaluation or eliminate all leakage.

## Calibration and actionability on CAL-GATE

| Arm | Equal-bp-mass ECE (limit 0.025) | Absolute calibration-in-the-large (limit 0.01) | Calibration | Admissible points |
|---|---:|---:|---|---:|
| G | 0.008583 | 0.002108 | PASS | 0 / 57,248 |
| R | 0.009244 | 0.002243 | PASS | 0 / 57,241 |
| H | 0.007011 | 0.001385 | PASS | 0 / 57,255 |

Each count is the complete equal-score threshold frontier. No selected arm,
calibrator or threshold is locked for chr19. All `actionable_arms` are false;
`pretest_lock.status=NO_ACTIONABLE_ARM` and
`chr19_release_authorized=false`.

The failure is not the old added-bp precision >=0.98 rule: this protocol did
not impose it. It retained known-negative <=10 bp/Mb, worst-case
negative/unknown <=20 bp/Mb, gene safety and minimum continuity/coverage
requirements.

As a descriptive diagnostic of the saved frontier, even at the looser
20-bp/Mb worst-case constraint alone, the largest thresholds cover only
359 G, 405 R and 288 H candidates. These are all below the registered
minimum 1,000 candidates. Recovered positives are respectively 1,930,
1,976 and 1,575 bp, with 589, 564 and 570 added negatives and no unknowns.
These are not admissible deployment points: the separate 10 known-negative
bp/Mb rule still applies. This diagnostic did not change any gate or select
a new policy. The largest gene-safe prefixes cover only 400, 429 and 377
candidates respectively, also below the required coverage.

## Scientific meaning and limitations

The valid result is restricted to Human comparator-consistent secondary
softmask continuity. Training and development/calibration chromosomes are
different, but the species is the same. No held-out chr19 result or
cross-species generalization result was produced in this stage.

H supplies a statistically supported incremental ranking signal, but the
registered readout and whole-gap decision do not turn that signal into
enough safe, useful repairs. Calibration passes; it is not the identified
failure. Neither a successful training job nor higher AUPRC proves that the
fragment problem is solved. Biological insertion identity remains unresolved,
and RepeatMasker-derived comparator agreement cannot establish it.

The Stage 0 oracle remains a non-deployable ceiling: comparator labels can
identify useful whole-gap actions. Stage 1 failed to recover a sufficient
subset using its allowed inference inputs. This leaves uncertainty about
information sufficiency versus finite training/readout limitations; the
experiment does not distinguish them completely.

## Closed and next-only

- Close this frozen G/R/H whole-gap Stage 1 route; keep the original P3 mask.
- Do not release chr19, start chr20 replication, retune on CAL-GATE, or start
  continual P3 training as an in-protocol rescue.
- The [conditional P3+NT donor-risk protocol](GAP-BRIDGE-P3-NT-DONOR-RISK-R1-CONDITIONAL.md),
  frozen at commit `db8754a`, now satisfies its prerequisite of a valid
  Stage 1 scientific failure. It remains a candidate requiring explicit
  execution authorization; no NT job was submitted. chr19 remains available
  as its first sealed test if that branch is authorized.
- No claim is made that all post-training, gap correction, or hybrid
  annotation routes have been falsified. Other mechanisms would require a
  new prospective protocol and independent evaluation.

No model, genome, BED/GFF or large frontier file is added to Git. This report
and the execution ledger are the compact tracked record; full artifacts and
real job logs remain on Baobab. `ACTIVE_GOAL.json` was not modified.
