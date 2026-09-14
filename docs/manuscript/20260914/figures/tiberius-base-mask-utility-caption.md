**Figure. Tiberius utility of the P3 base mask on the fixed hg38 panel.**
(A) Pooled locus F1 for the no-mask input (U), the P3-R1 mask input (P),
and the UCSC RepeatMasker input (R). (B) Paired changes in pooled locus F1
with the prespecified frozen 20-core bootstrap 95% confidence intervals. The
primary comparison, P−U, improves locus F1 by 0.063056 (95% CI
0.036503–0.106832); R−U is 0.059125 (0.029941–0.100812), while P−R is
0.003932 (−0.002606–0.013370) and its interval crosses zero. The latter is
not evidence of equivalence or superiority. (C) P−U changes 55 locus units
from missed to recovered while losing 16 U-correct units. The loss is
16/510 = 3.14%, above the prespecified 1% maximum, so the joint four-gate
criterion is not met despite the average input utility improvement.

The comparison uses the fixed hg38 chr16/18 panel with 726 reference locus
units, 20 cores per arm, and 60 completed U/P/R cells. Both the canonical
result and the independent recheck passed their implementation checks. This
is a fixed-panel input-utility analysis; it does not establish independent
generalization, equivalence, or superiority of P over R, and it is not
no-risk evidence.

Reproducibility sources: [canonical result](../../../../reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/result.json),
[independent recheck](../../../../reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/independent_recheck.json),
and [figure script](../../../../scripts/manuscript/plot_tiberius_utility_20260915.py).
