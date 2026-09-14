# Follow-up control figures

**Family-supervised contrastive projection.** Top-1 accuracy and macro-F1 for
centroid retrieval on the same 235 natural-copy evaluation intervals and 29
matched repeat labels. Inputs are L2-normalized 6-mer frequencies or frozen
native NTv2 embeddings; each uses a 128-dimensional linear projection trained
for 50 epochs on TRAIN family labels. CAL selects the epoch at the fixed 1%
negative-pair false-acceptance budget. Input dimensionality yields different
parameter counts, which are shown. This panel was previously examined, so
the comparison is exploratory; accepted-query error is not bounded by that
pair-level budget. Bars show point estimates without inferential error bars.
[PNG](retrieval-training-controls.png), [PDF](retrieval-training-controls.pdf),
[SVG](retrieval-training-controls.svg).

**Sequence-corresponding matched annotation support.** Fraction of old FP
and matched old TN intervals with at least 80% coverage by the fixed 2022
CHM13 TE annotation. Matching used only source chromosome, exact length, GC,
non-ACGT count and old TE boundary relationship/distance. The displayed
subset requires strict chain correspondence and identical ACGT sequence
between hg19 and CHM13 for both pair members; controls are not reselected.
The 18,079 pairs use 2,729 distinct TN controls, with maximum reuse775, and
are not independent experimental replicates. Boundary-adjacent and isolated
subsets are reported separately. This is descriptive annotation support,
not biological insertion confirmation, statistical enrichment or corrected
F1. [PNG](annotation-matched-sequence-support.png),
[PDF](annotation-matched-sequence-support.pdf),
[SVG](annotation-matched-sequence-support.svg).

Both figures are generated directly from compact results by
`scripts/manuscript/plot_followup_controls_20260914.py`.
