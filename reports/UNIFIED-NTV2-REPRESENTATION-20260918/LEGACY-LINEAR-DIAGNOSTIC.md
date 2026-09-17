# Legacy binary linear and composition diagnostic

This bounded CPU analysis explains the earlier GENERanno binary macro-F1
value near 0.522 and tests whether a simple sequence-composition readout can
account for the binary structure.  It reuses completed feature caches and
does not rerun extraction, tune a threshold, or alter the new unified
three-arm protocol.

The denominator is the known-five support of the fixed SIB TEST split:
1,281 records, with 360 BG and 921 TE records.  TRAIN fitting is restricted
to the known-five labels; TE is the union of SINE, LINE, LTR, and DNA.  The
linear probe is a standardized logistic regression fit on TRAIN only.  The
composition baseline uses GC fraction, N fraction, and sequence length, also
standardized from TRAIN only.  TEST is read exactly once.  Rows in the
confusion matrices are true labels and columns are predicted labels, ordered
as BG, TE.

| arm | linear confusion | BG precision / recall / F1 | TE precision / recall / F1 | macro-F1 |
|---|---|---|---|---:|
| GENERanno pretrained | `[[63,297],[69,852]]` | 0.477 / 0.175 / 0.256 | 0.742 / 0.925 / 0.823 | 0.5396 |
| GENERanno binary FT | `[[81,279],[60,861]]` | 0.574 / 0.225 / 0.323 | 0.755 / 0.935 / 0.836 | 0.5794 |
| GENERanno class FT | `[[221,139],[132,789]]` | 0.626 / 0.614 / 0.620 | 0.850 / 0.857 / 0.853 | 0.7367 |
| NTv2 pretrained | `[[136,224],[192,729]]` | 0.415 / 0.378 / 0.395 | 0.765 / 0.792 / 0.778 | 0.5867 |
| NTv2 binary D | `[[181,179],[109,812]]` | 0.624 / 0.503 / 0.557 | 0.819 / 0.882 / 0.849 | 0.7031 |

The composition baseline has the identical confusion matrix for every arm,
`[[2,358],[0,921]]`, and macro-F1 0.4242.  It calls nearly every record TE,
so it has very poor BG recall.  The embedding probes recover BG as well as TE,
especially after binary or class fine-tuning, which is evidence that the
readout is not explained by these three covariates alone.  This does not
establish that the representation is free of all GC, N, length, species, or
label-source effects; those are addressed as fixed-panel confounders in the
new three-arm evaluator.

The previous GENERanno `.5221` number was cosine-weighted 5-NN macro-F1 on
the same known-five denominator.  The new linear result is a complementary
train-only readout: it shows that the low score was not evidence of an
absence of TE information, but reflected a strong BG false-positive pattern.
The class-FT number here is historical and uses a different backbone from the
new NTv2 class arm; it must not be substituted into the new representation
comparison.

Source JSON: `results/legacy-linear-12889615.json` (Slurm `12889615`,
`COMPLETED 0:0`, 4 CPU/16G, 8 seconds).
