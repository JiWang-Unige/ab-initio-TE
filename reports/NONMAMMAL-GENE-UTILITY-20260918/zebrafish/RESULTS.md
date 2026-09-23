# Zebrafish native gene-utility result

The fixed zebrafish arm completed all ten 5-Mb cores (50,000,000 core bp; 52,000,000 bp including halos) on danRer11. The complete exact-assembly reference contains 984 protein-coding CDS-chain loci. Every core has all four paired arms `U`, `D`, `R_TE`, and `RED`; no cell was selected or discarded by an interim score.

This is an AUGUSTUS 3.5.0 native-parameter experiment. The softmasked FASTA is consumed by AUGUSTUS, not Tiberius, so this result is evidence for a second gene predictor and must not be described as a Tiberius result or as unseen-species generalization: zebrafish is one of the six D-supervision species and uses its existing same-species AUGUSTUS parameters.

| arm | TP | FP | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| U | 211 | 1412 | 773 | 0.130006 | 0.214431 | 0.161872 |
| D | 250 | 688 | 734 | 0.266525 | 0.254065 | 0.260146 |
| R_TE | 244 | 720 | 740 | 0.253112 | 0.247967 | 0.250513 |
| RED | 225 | 803 | 759 | 0.218872 | 0.228659 | 0.223658 |

The primary paired comparisons are chromosome-bootstrap sensitivity intervals (10,000 resamples, seed 42), not biological-replicate uncertainty:

| comparison | F1 difference | 95% chromosome-bootstrap interval | gained loci | lost loci |
|---|---:|---:|---:|---:|
| D−U | +0.098274 | [+0.080732, +0.114279] | 46 | 7 |
| D−R_TE | +0.009632 | [+0.002451, +0.017094] | 10 | 4 |
| D−RED | +0.036488 | [+0.025937, +0.048305] | 34 | 9 |

D improves over U by 0.098274 F1 (95% interval [0.080732, 0.114279]), over R_TE by 0.009632 ([0.002451, 0.017094]), and over RED by 0.036488 ([0.025937, 0.048305]). The D−R_TE margin is positive but small; the interval is a fixed-chromosome sensitivity interval and should not be presented as a biological-replicate confidence interval.

## Per-core completeness and scores

All ten fixed cores and all 984 reference loci are retained. The per-core reference counts sum to 984, and each row below contains the four completed arm-level locus scores.

| core | chromosome | reference loci | U F1 | D F1 | R_TE F1 | RED F1 |
|---|---|---:|---:|---:|---:|---:|
| c00 | chr16 | 134 | 0.192926 | 0.281250 | 0.289062 | 0.264151 |
| c01 | chr20 | 134 | 0.231579 | 0.302326 | 0.294574 | 0.258555 |
| c02 | chr8 | 109 | 0.198582 | 0.325359 | 0.303318 | 0.269767 |
| c03 | chr17 | 106 | 0.192469 | 0.236967 | 0.238095 | 0.223256 |
| c04 | chr14 | 66 | 0.143646 | 0.218750 | 0.210526 | 0.194030 |
| c05 | chr13 | 93 | 0.190083 | 0.304348 | 0.287234 | 0.282723 |
| c06 | chr18 | 50 | 0.093617 | 0.213592 | 0.205607 | 0.137405 |
| c07 | chr12 | 79 | 0.094828 | 0.185185 | 0.184049 | 0.143713 |
| c08 | chr19 | 97 | 0.074074 | 0.180851 | 0.152284 | 0.153846 |
| c09 | chr15 | 116 | 0.195652 | 0.278027 | 0.266667 | 0.233184 |

## Masking and CDS-overlap diagnostic

The post-hoc diagnostic uses the same merged CDS union as the frozen score and does not rerun AUGUSTUS or change any prediction. The ten-core CDS union is 1,845,174 bp.

| arm | masked core bp | masked core | masked CDS bp | masked CDS fraction |
|---|---:|---:|---:|---:|
| U | 0 | 0.0000% | 0 | 0.0000% |
| D | 23,269,086 | 46.5382% | 25,830 | 1.3999% |
| R_TE | 20,196,539 | 40.3931% | 15,464 | 0.8381% |
| RED | 19,547,753 | 39.0955% | 77,267 | 4.1875% |

Across the 52-Mb inputs including halos, U/D/R_TE/RED mask 0 / 24,249,297 / 21,021,267 / 20,349,038 bp (0.0000% / 46.6333% / 40.4255% / 39.1328%). RED overlaps roughly three times as much reference CDS as D (77,267 versus 25,830 bp; 4.19% versus 1.40%), which is compatible with genic masking contributing to RED's lower F1. RED masks less total core sequence than D, however, so its lower score cannot be attributed simply to total masked-bp intensity. R_TE overlaps less CDS than D while D remains modestly better, showing that the learned-mask effect is not determined by CDS overlap alone. These are panel-level diagnostics and do not establish causality.

## Terminal execution evidence

Core `c00` completed as `12889049_0`; cores `c01`–`c09` completed as `12889054_1`–`12889054_9`; and the complete-denominator score completed as `12889063` (all exit 0). The post-hoc CDS diagnostic completed as `12899904` (exit 0, private CPU, 18 s). All 40 native AUGUSTUS arm commands recorded exit code 0 and identical uppercase sequence checks. The first native smoke/assessment established that AUGUSTUS consumes lowercase input as its native `nonexonpart` hint mechanism.

Machine-readable artifacts are `zebrafish/result.json`, `zebrafish/compact-result.json`, `zebrafish/posthoc-mask-cds-diagnostic.json`, and `zebrafish/D_mask.json`; the paired comparison source is the exact assembly `ncbiRefSeq` reference documented in `zebrafish/reference.json`.
