# Sea-urchin adapter/MoE pilot: Slurm 12709175

Status: `completed` (`20:47`, exit `0:0`). This is an exploratory, single-seed, supervised single-domain adaptation. It is not a zero-shot or seven-domain result.

The corrected materializer subtracts each region `start_bp` from the absolute scaffold coordinates in the lifted RepeatMasker table. Unknown/ambiguous/PLE labels and non-ACGT bases are masked; remaining A/C/G/T bases outside known TE intervals are reference-negative. EVAL was extracted only after CAL epoch/threshold selection.

## New-mask denominators

| split | total bp | positive bp | reference-negative bp | masked bp | callable bp |
|---|---:|---:|---:|---:|---:|
| TRAIN | 2,097,152 | 445,247 | 1,043,315 | 608,590 | 1,488,562 |
| CAL | 1,048,576 | 149,786 | 579,072 | 319,718 | 728,858 |
| EVAL | 1,048,576 | 152,710 | 582,987 | 312,879 | 735,697 |

All arms below use exactly the EVAL mask (152,710 positive, 582,987 reference-negative, 312,879 masked; 735,697 callable bp). These denominators are specific to this new mask and cannot be compared directly with the old T1 known-TE union denominator or its positive-only recall.

## Sea EVAL comparison

| arm | CAL/parameter source | P | R | bp-F1 | AP | segment-F1 IoU 0.8 | boundary-F1 25 bp |
|---|---|---:|---:|---:|---:|---:|---:|
| D historical full-CAL | fixed six-species full-CAL artifact | 0.759113 | 0.442230 | 0.558879 | 0.657578 | 0.136667 | 0.111667 |
| D + Sea CAL recalibration | Sea region 3 CAL | 0.622707 | 0.789457 | 0.696237 | 0.657578 | 0.176498 | 0.145843 |
| Dense residual adapter | TRAIN regions 1+2; epoch 5 from Sea CAL | 0.692975 | 0.781200 | 0.734447 | 0.801651 | 0.119278 | 0.104449 |
| 2-expert soft-gate head | TRAIN regions 1+2; epoch 6 from Sea CAL | 0.687148 | 0.785993 | 0.733255 | 0.777332 | 0.110905 | 0.096035 |
| Constant-average experts | TRAIN regions 1+2; epoch 23 from Sea CAL | 0.698495 | 0.781252 | 0.737559 | 0.808723 | 0.105889 | 0.089233 |

For the single sea-urchin species, macro values equal the species values. The best bounded EVAL bp-F1 was constant-average (`0.737559`), followed closely by dense (`0.734447`) and soft-gate (`0.733255`); all three heads had much lower segment/boundary scores than their bp aggregate suggests. The fixed historical calibration had bp-F1 `0.558879` because its recall was `0.442230`; Sea recalibration raised it to `0.696237` but still did not match the adapted heads.

## Training and routing audit

| arm | trainable parameters | nominal tile loops/epoch | optimizer steps/epoch | skipped fully masked steps/epoch | selected epoch | selected CAL bp-F1 |
|---|---:|---:|---:|---:|---:|---:|
| Dense residual adapter | 65,730 | 256 | 255 | 1 | 5 | 0.678728 |
| 2-expert soft-gate head | 67,782 | 256 | 255 | 1 | 6 | 0.683099 |
| Constant-average experts | 65,732 | 256 | 255 | 1 | 23 | 0.681176 |

The nominal 256 tile loops per epoch contain one fully masked step, so each head performs 255 optimizer updates per epoch. The skipped step is counted and does not contribute a fabricated negative. The soft gate’s EVAL mean expert weights are `0.961793/0.038207`; the constant-average control is exactly `0.5/0.5`.

## Original six-species retention

The following uses the original first-32 CAL/DEV tiles. “Sea CAL direct” applies the parameters selected on the sea TRAIN/CAL data directly to original six-species DEV. “Six CAL refit” fits a separate shared six-species CAL after adaptation and then applies it to six-species DEV. Six-species DEV never selects a Sea epoch or threshold.

| arm / calibration applied | macro P | macro R | macro bp-F1 | worst-species bp-F1 | segment-F1 IoU 0.8 | boundary-F1 25 bp |
|---|---:|---:|---:|---:|---:|---:|
| D historical full-CAL (fixed) | 0.886984 | 0.868591 | 0.876984 | 0.750981 | 0.454633 | 0.391215 |
| D six-species CAL refit | 0.876857 | 0.880594 | 0.878221 | 0.756681 | 0.446629 | 0.383899 |
| D Sea CAL direct | 0.743691 | 0.955626 | 0.833649 | 0.720217 | 0.300167 | 0.240384 |
| Dense residual adapter — Sea CAL direct | 0.684004 | 0.942441 | 0.784429 | 0.629110 | 0.163944 | 0.125133 |
| Dense residual adapter — six-species CAL refit | 0.832064 | 0.855573 | 0.830082 | 0.695730 | 0.221151 | 0.184852 |
| 2-expert soft-gate head — Sea CAL direct | 0.679473 | 0.939753 | 0.780717 | 0.645920 | 0.162319 | 0.125729 |
| 2-expert soft-gate head — six-species CAL refit | 0.821386 | 0.869725 | 0.830388 | 0.685179 | 0.243269 | 0.204605 |
| Constant-average experts — Sea CAL direct | 0.629452 | 0.935591 | 0.737466 | 0.536287 | 0.114521 | 0.086919 |
| Constant-average experts — six-species CAL refit | 0.768071 | 0.866890 | 0.796599 | 0.657493 | 0.173006 | 0.145251 |

The direct Sea CAL parameters substantially overcall the original six species (macro recall `0.9356` for the constant-average arm, for example), while the separate six-species refit still shows degradation after adaptation. These two readings answer different deployment questions and should not be merged into a single “retention” number.

## Claim boundary

This run establishes a correctly materialized, finite single-domain adaptation pilot and records a real head-level MoE routing signal. It does not establish a sparse backbone MoE, universal species generalization, or a confirmation result. The numerical comparisons are exploratory because they use one seed and a bounded tile panel.

Remote output: `outputs/D-ADAPTER-MOE-PILOT-20260914/sea-seed42/slurm-12709175/`. Local compact result: `sea-summary.json`; full result and trace: `results.json`; label provenance: `materialization_manifest.json`.
