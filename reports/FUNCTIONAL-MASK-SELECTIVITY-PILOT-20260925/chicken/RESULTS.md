# Functional mask selectivity pilot: chicken

This is a fixed-panel development pilot. Chromosome bootstrap intervals are regional sensitivity intervals, not biological-replicate uncertainty.

## Arm-level scores

| arm | TP | FP | FN | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U | 280 | 916 | 784 | 0.234114 | 0.263158 | 0.247788 |
| D_FIXED | 285 | 835 | 779 | 0.254464 | 0.267857 | 0.260989 |
| RM2_FULL | 271 | 777 | 793 | 0.258588 | 0.254699 | 0.256629 |
| D_COMMON_RANDOM | 285 | 835 | 779 | 0.254464 | 0.267857 | 0.260989 |
| RM2_COMMON_RANDOM | 277 | 888 | 787 | 0.237768 | 0.260338 | 0.248542 |
| RM2_COMMON_CONF | 281 | 870 | 783 | 0.244136 | 0.264098 | 0.253725 |

## Paired chromosome-bootstrap comparisons

| comparison | F1 delta | 95% interval |
| --- | ---: | --- |
| D_FIXED_minus_RM2_FULL | 0.004360 | [-0.005875, 0.013242] |
| D_COMMON_RANDOM_minus_RM2_COMMON_RANDOM | 0.012447 | [0.005091, 0.020597] |
| RM2_COMMON_CONF_minus_RM2_COMMON_RANDOM | 0.005183 | [-0.001498, 0.011966] |
| D_COMMON_RANDOM_minus_RM2_COMMON_CONF | 0.007264 | [0.000319, 0.017348] |
| D_FIXED_minus_D_COMMON_RANDOM | 0.000000 | [-0.000360, 0.000355] |

The pilot must not be upgraded to an independent confirmation result without a separately frozen evidence panel.

## Interpretation and terminal evidence

All ten prediction-array elements 13192930 completed, as did the c01
confidence-only repair 13193088 and score 13192933 (9 s). Forty canonical
native arm command records have exit 0, nonempty GFF outputs and parsed gene
chains. The repaired c01 historical output is retained, not scored. The
reference contains the same 1,064 loci; reused U/D metric objects are exactly
unchanged. Per-core TP/FP/FN sums, F1, paired deltas and gained/lost locus
counts pass [validation](validation.json). See [native evidence](native-terminal.json).

On this exposed chicken panel, random thinning and the predefined native
alignment-confidence rule do not reproduce D's complete-CDS-chain F1 at the
common whole-input mask budget. D-common minus RM2-random is +1.245 percentage
points and D-common minus RM2-confidence is +0.726 points. Their ten-chromosome
bootstrap intervals are positive; the latter has a lower bound of only
0.032 percentage points. These are development-panel regional sensitivity
intervals, not independent biological confirmation, equivalence tests or
multiplicity-adjusted population claims.

This is an initial mask-position signal worthy of the already planned second
species, not evidence of superior full workflows: native D minus full RM2 is
only +0.436 percentage points, with its interval crossing zero. The historical
same-assembly R_TE arm remains higher at 0.266114, compared with D 0.260989.
The historical RED arm was produced on this 52-Mb panel and must not be
described as a full-genome RED comparison. Those controls remain in the
[original utility report](../../NONMAMMAL-GENE-UTILITY-20260918/chicken/RESULTS.md).

Whole-input common budget is exactly 693,106 masked A/C/G/T bp per arm,
including halos, versus 706,036 native D bp and 2,623,154 native RM2 bp. The
5-Mb scored cores do not have exactly identical mask totals, and centered
partial-run truncation does not yield identical realized fragment lengths;
those residuals are explicitly retained in `../prepare-summary.json`. Thus
the result does not completely isolate every positional/fragmentation factor.
D-common and native D have identical aggregate TP/FP/FN and recovered true
loci, but their per-core FP distribution differs slightly, explaining the
small nonzero bootstrap interval despite zero aggregate F1 difference.

Neither the independent host complete-CDS evidence set nor the autonomous-TE
exclusion endpoint is ready. This result therefore does not prove that the
model distinguishes functional host genes from autonomous TE coding loci.
Zebrafish has now completed; its native D advantage over full RM2 does not
persist at the common budget. See the [fish result](../zebrafish/RESULTS.md)
and [joint interpretation](../CLOSURE-20260925.md). This limits the generality
of the chicken position-selection signal.

The compact preparation summary's `source_length_strata` fields originally
duplicated the actual post-truncation strata. They have been corrected from
the retained selection records, with all source quotas verified. The original
summary is preserved; no mask, prediction, threshold or scientific score was
changed by this descriptive repair.
