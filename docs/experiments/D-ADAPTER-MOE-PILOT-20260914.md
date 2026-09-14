# D adapter/MoE pilot (2026-09-14)

This document records the protocol before the first feature extraction. The run is a bounded, exploratory, seed-42 pilot requested after the six-species D model review. Version 2 supersedes the initial rank-1 sketch before any formal extraction: it uses a 64-unit dense residual and two 32-unit experts with a hidden-state gate. It keeps the native D backbone and token-to-base evaluation contract fixed, and trains only residual prediction heads on the frozen final hidden features.

## Locked design

The input is the first 32 complete 8192-bp tiles in source order for each of human, mouse, chicken, zebrafish, pig, and *C. elegans* in each of TRAIN, CAL, and DEV. A tile is complete only when both 4096-bp halves are present with 4096 labels. The *C. elegans* TRAIN file uses the upstream materialization override specified in the JSON config. Selection is deterministic and is recorded in the remote manifest.

The native encoder is loaded from the D final model together with the frozen NTv2 code. For each non-special attended token, the run stores the final sequence hidden state and the frozen D two-logit output. Six-base tokens and the trailing single bases follow `cross_species_token_task.encode_record`, `sequence_tokens`, and `label_chunk_masses`. Margins are projected back to bases only with `calibrate_evaluate_x0.project_token_margins`; token counts are never reported as base-pair counts.

The four reported arms are:

* `D_recalibrated`: frozen D logits with the shared six-species CAL Platt fit and legacy global threshold selection.
* `dense_residual_adapter`: D logits plus a `1024 -> 64 -> 2` tanh residual adapter. Its trainable count is 65,730.
* `two_expert_soft_gate_residual_adapter`: two `1024 -> 32 -> 2` residual experts and a two-way softmax gate driven by the detached 1,024-dimensional hidden state. Its count is 67,782, 3.1% above the dense adapter and is therefore a capacity-matched prediction-head MoE; it does not route the 500M backbone.
* `constant_average_experts`: the same two 32-unit residual experts with fixed weights `(0.5, 0.5)`, 65,732 trainable parameters, and no learned gate.

The saved historical full-CAL D artifact is loaded for provenance. The primary pilot recalibrates the D logits on the bounded 32-tile CAL subset; the historical slope/intercept/threshold are reported verbatim. The complete output includes their descriptive application to the same bounded DEV tiles, giving macro bp-F1 0.876984, minimum-species bp-F1 0.750981, segment-F1 at IoU 0.8 of 0.454633 and boundary-F1 at 25 bp of 0.391215. This is a fixed historical-calibration baseline; no parameters are selected on DEV.

The adapter weights see TRAIN only. Each training step contains one tile from every species and both halves, giving equal species weight and 32 steps per epoch. The token loss is callable-base normalized with the historical TE base weight 3.0. For each candidate epoch, one shared Platt fit and one global threshold are fit on CAL; epoch selection first maximizes the minimum species CAL F1 and then macro CAL F1. DEV is touched only once after the selected epoch and CAL parameters are frozen. No multi-seed result is produced.

## Sea-urchin branch

The four fixed sea-urchin regions are a separate exploratory single-domain adaptation. A materializer converts the fixed panel FASTA and lifted RepeatMasker table into non-overlapping 8192-bp tiles using regions 1+2 as TRAIN, region 3 as CAL, and region 4 as EVAL. Unknown/ambiguous labels, including PLE, and every non-ACGT base remain masked; other ACGT bases are reference-negative. The same frozen-feature heads and CAL-only selection are then reused. Any adapted sea result is supervised adaptation and is not called zero-shot.

After sea adaptation, each selected head is also evaluated on the original six-species first-32 DEV tiles. That retention check reports both direct application of the sea-selected CAL parameters and a separate shared six-species CAL calibration fitted after adaptation and applied unchanged to those DEV tiles. It does not use six-species DEV for epoch or threshold selection. This is a stability/forgetting diagnostic, not a seven-domain joint-training result. The new sea mask has its own callable/positive/unknown denominator and must not be compared directly with the earlier four-region T1 positive-only recall denominator.

## Evidence boundary

This run can establish whether a small frozen-feature prediction head improves the bounded DEV sample under the locked CAL protocol. It cannot establish a sparse backbone MoE, species-independent biological generalization, or confirmation on an untouched independent test set. Because the protocol is exploratory and single-seed, any numerical difference is a direction-finding result pending the project's later benchmark and replication decisions.

The execution report will add source paths, selected tile IDs, model/interface checks, exact counts, train/CAL traces, per-species DEV metrics, route statistics, and the actual Slurm job state. A failed load or incomplete output is recorded as an interface failure rather than converted into a model result.

## Main pilot execution record

The six-species run completed on Baobab as Slurm job `12708683` with status
`completed`. The compact result is in
`reports/D-ADAPTER-MOE-PILOT-20260914/main-summary.json`; the complete result
is `main-results.json`. On the bounded first-32 DEV sample, the frozen D
recalibration reached macro base-pair F1 `0.878221` and worst-species F1
`0.756681`. The dense residual adapter reached `0.878234` and `0.756263`,
the constant-average experts reached `0.878389` and `0.756263`, and the
hidden-gated two-expert head reached `0.879017` and `0.762329`.

The gated head therefore raised the base-pair aggregate by about `0.0008`
relative to the bounded D recalibration, but its boundary F1 at 25 bp was
`0.345218` versus `0.383899` for D, with higher short-prediction and split
rates. Its mean expert weights differed by species (for example, `0.914/0.086`
for *C. elegans* and `0.364/0.636` for zebrafish), which demonstrates that the
gate is active but does not establish a biological domain solution. The
historical full-CAL artifact parameters are slope `0.698405`, intercept `-0.805031`,
threshold `0.423301`; the bounded recalibration used slope `0.723122`,
intercept `-0.801312`, threshold `0.374062`. These are exploratory, single
seed, finite-sample observations and do not replace the independent benchmark.

The first Sea attempt (`12708891`) was cancelled after a coordinate audit
found that the lifted RepeatMasker table uses absolute scaffold coordinates
while the panel FASTA is region-relative; it produced no result. The
materializer now subtracts each region's `start_bp` and fails on out-of-range
rows. The corrected Sea job is `12709012`. Its manifest records positive,
reference-negative, masked, and total base-pair counts separately for TRAIN,
CAL, and EVAL. All Sea arms use this same new mask; those denominators must
not be compared directly with the earlier T1 known-TE union denominator
(`844,932 bp`) or its positive-only recall. The Sea retention report will include both
direct application of Sea-selected CAL parameters to the original six-species
DEV and a separate six-species CAL refit diagnostic; neither uses six-species
DEV for selection.

The corrected-coordinate job `12709012` completed materialization and TRAIN/CAL
feature extraction, then failed on a single fully masked TRAIN tile. The
training-loop message incorrectly described that step as an entirely unlabelled
TRAIN selection. The fixed loop skips and counts zero-callable optimizer steps,
retains their manifest entries and fails only if the entire epoch has no loss.
It also passes the single-species order to both epoch and final calibration.
No labels, split, epoch limit or hyperparameters changed. CPU regression job
`12709166` completed in seven seconds, covering a masked tile beside a valid
tile, the entirely masked failure case, and both single-species CAL calls.

The materialization snapshot is retained in
`reports/D-ADAPTER-MOE-PILOT-20260914/sea-materialization-12709012.json`.
TRAIN has 445,247 positive, 1,043,315 reference-negative and 608,590 masked
bases; CAL has 149,786/579,072/319,718 and EVAL has
152,710/582,987/312,879 in the same order. These totals preserve all four
regions, including masked tiles. The failed job record is retained separately;
it supplies no evaluated adapter result.

The repair was resubmitted with the same shared-GPU, four-CPU, 64-GB,
two-hour allocation as Slurm `12709175`, under
`outputs/D-ADAPTER-MOE-PILOT-20260914/sea-seed42/slurm-12709175/`.
Report actual `optimizer_steps` and `skipped_fully_masked_steps` from each
epoch trace: `train_steps_per_epoch` is the nominal tile-loop count. No new
evaluation result existed at resubmission. The active thread heartbeat will
retrieve and score the fixed outputs after completion.
