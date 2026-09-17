# Legacy binary readout diagnostic

This file records the CPU explanation for the previously reported `.522`
value.  It is contextual evidence, not a replacement for the new unified
three-arm extraction.

## Definition

The value is cosine-distance-weighted 5-NN macro-F1 on the known-five support
of the fixed SIB test split.  BG is label 0 and TE is the union of SINE, LINE,
LTR, and DNA.  KNOWN_OTHER_TE, AMBIGUOUS_TE, and UNCLASSIFIED are excluded
from this binary denominator and are retained in the full-eight analyses.

## Confusion matrices and class metrics

Rows are true labels and columns are predicted labels (`BG`, `TE`).

| arm | confusion matrix | BG support | TE support | BG precision / recall / F1 | TE precision / recall / F1 | macro-F1 |
|---|---|---:|---:|---:|---:|---:|
| GENERanno pretrained | `[[67,293],[116,805]]` | 360 | 921 | 0.366 / 0.186 / 0.247 | 0.733 / 0.874 / 0.797 | 0.5221 |
| GENERanno binary FT | `[[135,225],[138,783]]` | 360 | 921 | 0.495 / 0.375 / 0.427 | 0.777 / 0.850 / 0.812 | 0.6192 |
| GENERanno class FT | `[[205,155],[133,788]]` | 360 | 921 | 0.607 / 0.569 / 0.587 | 0.836 / 0.856 / 0.846 | 0.7164 |
| NTv2 pretrained | `[[55,305],[74,847]]` | 360 | 921 | 0.426 / 0.153 / 0.225 | 0.735 / 0.920 / 0.817 | 0.5211 |
| NTv2 binary D | `[[180,180],[83,838]]` | 360 | 921 | 0.684 / 0.500 / 0.578 | 0.823 / 0.910 / 0.864 | 0.7211 |

The `.522` is therefore not a claim that NTv2 has no TE information.  In
both pretrained arms the TE recall is high while BG recall is low; the
macro-F1 is dominated by this background false-positive pattern.  D
fine-tuning improves both the BG and TE readouts on this panel.

The older GENERanno values use its completed historical extraction/evaluator
and are retained only to explain the prior number.  The unified run uses an
explicit structural-special-token policy that retains input UNK/N tokens and
will report its own metrics after extraction.

## SIB composition context

The fixed SIB panel contains 1,843/809/1,580 records in train/val/test.  The
test panel has BG/SINE/LINE/LTR/DNA/KNOWN_OTHER_TE/AMBIGUOUS_TE/UNCLASSIFIED
counts `360/75/306/280/260/125/120/54`.  Its species are *C. elegans*,
chicken, fruit fly, mouse, western clawed frog, and zebrafish; this is a
different evaluation panel from D's human, mouse, chicken, zebrafish, pig,
and *C. elegans* training species.  Therefore the SIB readout is a fixed
cross-panel diagnostic, not an in-distribution six-species estimate.

The test mean GC fractions by class are BG .411, SINE .474, LINE .435, LTR
.442, DNA .390, KNOWN_OTHER_TE .342, AMBIGUOUS_TE .365, and UNCLASSIFIED
.372.  Mean N fractions are near zero (BG .0058 is the largest).  These
composition differences are recorded as possible readout confounders; they
do not establish that GC or N causes the binary false-positive pattern.
