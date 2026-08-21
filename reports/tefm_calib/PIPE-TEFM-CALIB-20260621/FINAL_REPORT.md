# FINAL REPORT: PIPE-TEFM-CALIB-20260621

Date: 2026-06-21

## Status

Semantic success, screen complete. This run is not claim-grade and cannot support SOTA claims because it is single seed, screen-profile, and the ACTIVE_GOAL/evaluator/baseline contracts remain draft.

## Scope

Single-seed GENERanno 4096 bp calibration supplement:

- standard supervised plant and cross-kingdom binary fine-tuning with reliable negatives;
- direct western honeybee and red flour beetle chromosome-heldout diagnostic fine-tuning;
- insect-no-beetle anchor training;
- Dfam RepeatMasker consensus family-level embedding clustering;
- extended generalization-decay formula with label/source and panel variables.

## Artifacts

- Config: `configs/pipelines/PIPE-TEFM-CALIB-20260621.yaml`
- Summary status: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/current_status.json`
- Binary eval: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/binary_eval.tsv`
- Dfam consensus embedding: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`
- Decay formula: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/decay_formula_extended/formula_fits_extended.json`
- Runs: `software_outputs/tefm_calib/PIPE-TEFM-CALIB-20260621/runs`
- Logs: `logs/tefm_calib/PIPE-TEFM-CALIB-20260621`

## Semantic Success Checks

- Slurm: prep `9245610`, embedding extract `9245611`, train `9245618`, eval `9245619`, embedding cluster `9245620`, formula `9245621`, and summary `9245622` all completed with exit code `0:0`.
- Eval completeness: 98/98 expected eval JSON outputs exist; `binary_eval=96`, `direct_species=2`.
- Summary completeness: `binary_eval_rows=98`, `embedding_rows=4`.
- Numeric validity: eval-like JSON rows have no non-finite numeric values; summary TSV numeric fields have no NaN cells.
- Log scan: no `Traceback`, CUDA OOM, killed process, missing-file, failed-job, or NaN-loss signature was found in final logs.

## Key Metrics

### Binary TE Detection

| Model | n | Mean TE-F1 | Min | Max |
|---|---:|---:|---:|---:|
| `cross_supervised_4096` | 22 | 0.5786 | 0.0031 | 0.9630 |
| `TFREPAIR_invert_boost_animal_4096_seed42` | 22 | 0.5413 | 0.0044 | 0.9217 |
| `insect_no_beetle_4096` | 22 | 0.4055 | 0.0059 | 0.8259 |
| `plant_supervised_4096` | 22 | 0.3858 | 0.0004 | 0.9620 |
| `direct_western_honey_bee_4096` | 5 | 0.0000 | 0.0000 | 0.0000 |
| `direct_red_flour_beetle_4096` | 5 | 0.0000 | 0.0000 | 0.0000 |

Panel means:

| Stage | n | Mean TE-F1 |
|---|---:|---:|
| `cross_supervised_to_plant_fine` | 5 | 0.8568 |
| `plant_supervised_to_plant_fine` | 5 | 0.8431 |
| `animal_invert_boost_to_plant_eval` | 2 | 0.7269 |
| `cross_supervised_to_plant_eval` | 2 | 0.6718 |
| `plant_supervised_to_plant_eval` | 2 | 0.6712 |
| `animal_invert_boost_to_cross_eval` | 11 | 0.6026 |
| `cross_supervised_to_cross_eval` | 11 | 0.5872 |
| `insect_no_beetle_to_stress_eval` | 4 | 0.3073 |
| `animal_invert_boost_to_stress_eval` | 4 | 0.1749 |
| `cross_supervised_to_stress_eval` | 4 | 0.1607 |

Important species-level observations:

- Standard supervised plant/cross training is validated as meaningful: cross-supervised and plant-supervised beat the old animal branch on the plant fine-tune held-out panel.
- Cross-supervised is strongest on plant fine-tune species: rice 0.8758, maize 0.9630, sorghum 0.9155, brachypodium 0.8175, thale cress 0.7122.
- On plant eval-only species, plant/cross and animal branches split: teosinte is high for plant/cross (`plant=0.9308`, `cross=0.9300`, animal=0.8887), but soybean remains better for animal invert-boost (0.5651) than plant/cross (~0.41).
- Animal invert-boost and cross-supervised remain close on mammal/vertebrate cross-eval: human ~0.90, cattle ~0.92, horse ~0.89, pig ~0.876.
- Insect-no-beetle anchor strongly rescues honeybee in the cross/stress eval protocol (`western_honey_bee=0.7983`) but does not rescue red flour beetle (`0.0059`).
- Direct honeybee and direct beetle base-pretrained fine-tunes give fixed-threshold TE-F1 0.0 on own holdout and cross/stress evaluation. Honeybee still has ranking signal (`own_holdout AUPRC=0.3844`, cross/stress honeybee AUPRC=0.5038), while beetle remains near-no-signal (`own_holdout AUPRC=0.0026`).

### Dfam Consensus Family-Level Embedding

| Setting | ARI | NMI | Holdout Macro-F1 |
|---|---:|---:|---:|
| A0 native GENERanno embedding | 0.0796 | 0.1411 | 0.2383 |
| A1 native GENERanno + contrastive | 0.2242 | 0.3119 | 0.4137 |
| C0 basic sequence features | 0.1423 | 0.2386 | 0.3385 |
| C1 basic features + contrastive | 0.7083 | 0.7135 | 0.4219 |

Interpretation: Dfam consensus is now executed, not skipped. A1 improves over A0, but C1 remains the strongest clustering baseline by ARI/NMI. Do not claim FM embedding superiority.

### SF5 Unknown Audit

The prior SF5 branch uses a strict main4+Unknown label map (`BG`, `SINE`, `LINE`, `LTR`, `DNA`, `Unknown`). The preparation code maps ambiguous, non-main, `?`, `Unknown`, `RC`, and `Retroposon` RepeatMasker classes into `Unknown`, while only clear SINE/LINE/LTR/DNA labels enter main4.

Prior base-pretrained SF5 evidence remains: TE-F1 0.9041-0.8982, main4 conditional macro-F1 0.8644-0.8547, and Unknown recall 0.3886-0.3957. The low Unknown recall is therefore best framed as incomplete open-set/reject calibration, not as a failure of closed-set main4 superfamily classification. It is also plausible that part of the annotation-level Unknown bucket contains biologically assignable main4 sequence, as shown by the high `unknown_to_main4_rate` (~0.41-0.42). This should be reported honestly as an open-set limitation requiring label audit or hierarchical calibration.

### Extended Decay Formula

Rows: 244.

| Formula | R2 | RMSE |
|---|---:|---:|
| distance only | 0.0396 | 0.3526 |
| distance + label Jaccard + library completeness | 0.3818 | 0.2829 |
| distance + label Jaccard + TE bp log + entropy + GC | 0.5675 | 0.2366 |
| full variable set including train-clade/stress/kingdom/insect indicators | 0.7407 | 0.1832 |

Interpretation: genetic distance alone is too weak. Source concordance, TE amount/composition, GC, stress/kingdom indicators, and whether the training panel covers the target clade are required for a plausible descriptive decay model.

## Conclusions

1. The user's correction was right: plant/cross standard supervised training with reliable negatives is necessary and should not be compared to PU/positive-only as if they were equivalent. It substantially improves plant fine-tune held-out performance.
2. PU remains abandoned as the primary route. Its role is negative ablation or future gated repair with reliable RN/hardN controls.
3. Cross-supervised is the best broad mean in this screen, but the correct claim framing must be panel-specific. It improves plant fine-tune performance; animal invert-boost remains competitive or slightly better on broad cross-eval and stress means.
4. Insect-no-beetle is a useful honeybee anchor but not a general insect rescue. Beetle remains a hard label/library/domain failure candidate and should stay out of primary success means unless source evidence is repaired.
5. Direct honeybee/beetle base-pretrained species fine-tuning failed at the fixed threshold. Honeybee's AUPRC suggests calibration/threshold/protocol may recover it; beetle still looks source/domain-limited.
6. Dfam consensus embedding confirms the earlier conservative representation conclusion: A1 is useful, C1 is a mandatory strong baseline, and FM embedding superiority is not supported.
7. SF5 should be framed as stable main4 classification plus an incomplete open-set/reject channel. Unknown recall is a diagnostic limitation, not the primary closed-set metric.
8. The extended decay formula is useful only when label/source variables are included; distance-only decay should not be used for paper-level explanation.

## Recommended Pivot

Carry forward:

- GENERanno 4096 as the main backbone/window.
- `invert_boost_animal_4096` and `cross_supervised_4096` as complementary robust branches, reported by primary/stress/kingdom panel rather than one mixed mean.
- insect-no-beetle as a honeybee stress-anchor diagnostic, not a universal insect solution.
- main4+Unknown/reject framing for superfamily, from prior SF5 evidence.
- C1/A1 baselines for embedding.
- extended decay formula with label/source/coverage variables.

Do not carry forward:

- PU/positive-only as a primary route.
- direct honeybee/beetle base-pretrained fixed-threshold fine-tuning as a successful recovery result.
- Dfam consensus embedding as FM superiority evidence.
