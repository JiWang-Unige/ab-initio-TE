# Functional mask selectivity pilot: zebrafish

This is a fixed-panel development pilot. Chromosome bootstrap intervals are regional sensitivity intervals, not biological-replicate uncertainty.

## Arm-level scores

| arm | TP | FP | FN | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U | 211 | 1412 | 773 | 0.130006 | 0.214431 | 0.161872 |
| D_FIXED | 250 | 688 | 734 | 0.266525 | 0.254065 | 0.260146 |
| RM2_FULL | 234 | 696 | 750 | 0.251613 | 0.237805 | 0.244514 |
| D_COMMON_RANDOM | 244 | 834 | 740 | 0.226345 | 0.247967 | 0.236663 |
| RM2_COMMON_RANDOM | 230 | 723 | 754 | 0.241343 | 0.233740 | 0.237481 |
| RM2_COMMON_CONF | 233 | 744 | 751 | 0.238485 | 0.236789 | 0.237634 |

## Paired chromosome-bootstrap comparisons

| comparison | F1 delta | 95% interval |
| --- | ---: | --- |
| D_FIXED_minus_RM2_FULL | 0.015632 | [0.003639, 0.027183] |
| D_COMMON_RANDOM_minus_RM2_COMMON_RANDOM | -0.000817 | [-0.014012, 0.012108] |
| RM2_COMMON_CONF_minus_RM2_COMMON_RANDOM | 0.000153 | [-0.006640, 0.007729] |
| D_COMMON_RANDOM_minus_RM2_COMMON_CONF | -0.000970 | [-0.013882, 0.009392] |
| D_FIXED_minus_D_COMMON_RANDOM | 0.023482 | [0.013078, 0.034905] |

The pilot must not be upgraded to an independent confirmation result without a separately frozen evidence panel.

## Terminal validation and interpretation

All ten prediction tasks `13192931_0` through `_9` and score `13192934`
(13 s) completed. Forty native command records return 0, their GFFs are
nonempty and were parsed by the prediction and scoring code. All 984 reference
loci remain in the denominator; the reused U and D metric objects exactly
match the historical result. Per-core count sums, F1 and paired gain/loss
counts pass [validation](validation.json); see [native records](native-terminal.json).

Native D exceeds full RM2 by 1.563 percentage points in complete-CDS-chain F1,
with a ten-chromosome bootstrap interval [0.364, 2.718] points. Relative to
full RM2 it recovers 22 reference loci and loses 6; TP/FP are 250/688 versus
234/696. This supports reference-relative utility in the exposed fish panel,
not unseen-species transfer or independent biological correctness.

At the common budget, D is not better in aggregate F1 than the random or
confidence-selected RM2 controls: differences are -0.082 and -0.097 points,
with both intervals crossing zero. D-common retains more reference loci than
RM2-random (244 versus 230 TP), but also more unmatched predictions (834
versus 723 FP). This tradeoff must not be reduced to a recall-only success.
Removing part of native D's mask lowers F1 by 2.348 points, with interval
[1.308, 3.491], losing 6 recovered reference loci and adding 146 FP.

The common full-input budget is 22,012,067 masked bp, compared with native D
24,249,297 and native RM2 27,366,986. Scored-core totals are 21,148,536 for
D-common, 21,133,963 for RM2-random and 21,114,615 for RM2-confidence; source
length quotas are matched but actual fragment lengths and core-only coverage
are not exactly matched. See `../prepare-summary.json`. Thinning changes
positions and fragmentation as well as amount, so this does not prove that
total coverage alone caused the native D advantage. It does show that the
chicken equal-budget advantage does not reproduce in fish under the frozen
intervention. No new seed, mask threshold or alternative matching rule was
searched to recover it.

Historical R_TE F1 0.250513 and panel-only RED F1 0.223658 remain in the
[original report](../../NONMAMMAL-GENE-UTILITY-20260918/zebrafish/RESULTS.md).
The latter is not a whole-genome RED workflow. The source-stratum descriptive
field correction affects neither these values nor any pilot mask or score.
