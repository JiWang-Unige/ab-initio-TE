# D mask to Tiberius: completed result

Protocol: `D-TIBERIUS-PLATYPUS-20260917`. The fixed six-species D checkpoint was applied to all 20 preselected platypus cores (100 Mb total core denominator with the existing 100 kb halos). The five historical comparator arms were reused on the identical cores: unmasked softmask-compatible input (`U_soft`), unmasked no-softmask input (`U_nosm`), RepeatMasker TE mask (`R_TE`), RepeatMasker all-repeat mask (`R_all`), and P3 (`P`). No core was selected using a gene or TE score.

All 20 new D cells completed successfully. Every cell passed the input qualification (`same_uppercase_letters=true`, six-channel observer, native model calls) and the native GTF/GFF3 equality check. The paired score used the fixed 639-locus reference mapping, exact CDS-chain/locus matching, all gain/loss sets, and 10,000 chromosome-cluster bootstrap replicates (seed 42). The reference annotation is a comparator and is not treated as independent biological truth.

## Aggregate reference-relative metrics

| arm | TP | FP | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| D | 412 | 326 | 227 | 0.558266 | 0.644757 | 0.598402 |
| U_soft | 381 | 347 | 258 | 0.523352 | 0.596244 | 0.557425 |
| U_nosm | 358 | 348 | 281 | 0.507082 | 0.560250 | 0.532342 |
| R_TE | 408 | 332 | 231 | 0.551351 | 0.638498 | 0.591733 |
| R_all | 405 | 329 | 234 | 0.551771 | 0.633803 | 0.589949 |
| P | 408 | 338 | 231 | 0.546917 | 0.638498 | 0.589170 |

## Prespecified comparisons

| comparison | F1 delta | gained loci | lost loci | chromosome-bootstrap 95% CI |
|---|---:|---:|---:|---:|
| D − U_nosm | +0.066060 | 91 | 37 | [0.040500, 0.088310] |
| D − U_soft | +0.040977 | 49 | 18 | [0.017171, 0.068708] |
| D − R_TE | +0.006669 | 13 | 9 | [−0.003782, 0.019625] |
| D − R_all | +0.008453 | 16 | 9 | [−0.007089, 0.026845] |
| D − P | +0.009233 | 11 | 7 | [−0.001820, 0.023258] |

The fixed D mask improves the two unmasked receiver controls in this reference-relative analysis. Against the existing RepeatMasker and P3 receiver masks, the point estimates are positive but the paired chromosome intervals cross zero; this supports utility relative to unmasked input and a numerically competitive result relative to the historical mask arms, rather than a claim of superiority. The result is a retrospective platypus extension of the existing P3 experiment and is not an independent biological truth assay.

The scheduler used one D cell at a time while the separate GEN inference was unresolved; after its successful retry, the final cells used at most two D cells concurrently within the global two-GPU cap. Each cell retained the same RTX3090, 8 CPU and 96 GB request. The last two pending cells used a 10-minute scheduler wall limit for backfill; this did not alter the model, input, threshold, or endpoint. The compact cell status, input and observer records are under `run-12853263/`; the complete machine-readable result is `result.json`.

[Figure PDF](d-tiberius-utility.pdf) / [PNG](d-tiberius-utility.png). The figure uses the saved aggregate counts and precomputed chromosome-bootstrap intervals; it adds no selection or re-fitting.
