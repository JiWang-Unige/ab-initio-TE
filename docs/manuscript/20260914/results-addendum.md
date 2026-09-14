# Results added after the Pro manuscript review

These paragraphs incorporate experiments completed on 14 September 2026 after the archived Pro review. They are an update for the manuscript, not a second Pro assessment. The original draft remains available as the historical synthesis. Source data are linked below; unfinished experiments are not described as results.

## A chromosome-held-out model agrees with the original hg19 annotation

We trained a fresh TE classification head and the native NTv2-500M encoder on 3,000 fixed chr1 tiles for 4,000 steps with seed 42. No previously TE-fine-tuned checkpoint was used. Calibration used chr11, development used chr13, and evaluation used 2,500 predetermined tiles from chr2, chr3 and chr4. The final checkpoint was evaluated without development-based checkpoint selection. Relative to the old hg19 comparator, pooled base-pair precision, recall and F1 were 0.9515, 0.9372 and 0.9443 across 20,464,212 callable bases. Chromosome-specific F1 values were 0.9396, 0.9448 and 0.9481. The corresponding pooled segment F1 at IoU 0.8 was 0.5669, preserving the distinction between material detection and fragment topology. The experiment establishes task-supervision separation by chromosome; it does not establish homology or pretraining independence. [Evaluation evidence](../../../reports/HG19-CHR1-REVISION-20260914/eval-full-12696405/eval_metrics.json)

An independent source audit found that the effective TE and ignored-label intervals on the six allowed chromosomes matched the original UCSC hg19 RepeatMasker material labels identified with RepBase20090120. Some family-field encodings differed, so the original records were not identical in every field. The model was trained in 2026; this is a retrospective experiment, not a prediction made before the newer annotations existed. [Label provenance](../../experiments/HG19-CHR1-REVISION-20260914-2009-PROVENANCE.md)

The old comparator assigned 472,770 predicted bases to FP and 621,748 unpredicted positive bases to FN. We retained all TP, FP, FN and TN intervals before examining newer labels. Of 97,242 connected source intervals, 93,116 mapped uniquely to CHM13v2 and reciprocally to the original coordinates with unchanged span, including 21,235 of 21,402 old FP intervals. Mapping failures remained in the record. These conditions do not guarantee internal base-by-base correspondence, and mapping qualification alone is not evidence that an FP is a TE. [Mapping evidence](../../../reports/HG19-CHR1-REVISION-20260914/mapping-qualification-12705502/summary.json)

We subsequently measured overlap with the fixed 14 April 2022 CHM13 TE annotation at three prespecified descriptive support levels. Among qualified old FP intervals, 4,059 (19.11%) overlapped at least one annotated TE base, 3,570 (16.81%) had at least 50% TE coverage, and 3,171 (14.93%) had at least 80% TE coverage. The corresponding proportions among qualified, unmatched old TN intervals were 18.81%, 5.69% and 4.25%. Interval length and proximity to old TE boundaries were not matched; these raw contrasts are not an enrichment test. Annotation support across assemblies and biological samples does not by itself validate an insertion, establish that the old label was erroneous, or quantify a correction to F1. [Complete support counts](../../../reports/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-summary-12706180/summary.json)

The subsequent source-only matched analysis retained 18,649 FP–TN pairs
matched for chromosome, exact length, GC fraction, non-ACGT count and old-TE
boundary relationship/distance. In the 18,079 pairs for which both intervals
had strict internal chain correspondence and identical ACGT sequence between
hg19 and CHM13, 13.88% of old FP intervals and 10.84% of matched TN controls
had at least 80% new TE annotation coverage. The contrast was concentrated
in boundary-adjacent intervals (13.42% versus 10.10%); isolated intervals
showed 17.52% versus 16.77%, and their any-overlap contrast reversed direction.
Controls were reused, up to 775 times, so these are descriptive matched
statistics rather than independent replicates. This analysis supports an
annotation-version and boundary-sensitivity interpretation, without a
corrected F1 or a broad missed-insertion discovery claim.
[Matched sequence-qualified analysis](../../experiments/HG19-CHR1-REVISION-20260914-MATCHED-RESULT.md)

## External evaluation exposes a reference-coverage limitation

The frozen shared D model was evaluated on four predetermined 1-MiB regions from each of platypus, sea urchin and C. briggsae CB4. Strict TE-class filtering was required: treating every RepeatMasker row as TE would incorrectly include simple repeats and other non-TE categories. On the platypus panel, forward inference recalled 95.93% of comparator TE-positive bases, and averaging forward and reverse-complement predictions recalled 96.19%. Forward T0 comparator F1 was 0.7841; positive-only T1 scoring did not report independent precision or F1. These selected regions are not a representative genome-wide species sample. [External results and label contract](../../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/RESULTS-20260914.md)

The sea urchin and CB4 panels contained no qualifying TE-positive comparator bases. Both were therefore not evaluable for positive recall, rather than evidence of zero model recall. The required FamDB partitions were installed, but curated target-lineage families were absent under the original library-selection command. This finding motivates a separate library-sensitivity analysis at the same coordinates and frozen model settings. It does not establish that a subsequently expanded library is complete or independent truth.

A separate library-sensitivity run subsequently used all 3,324 uncurated sea-urchin lineage consensus sequences at the same fixed coordinates. After explicit query-ID and coordinate restoration, 3,371 strict TE-class annotation rows covered 844,932 union bases. The frozen D model recalled 42.89% of these bases; reverse-complement averaging recalled 42.42%. T0 comparator F1 was 0.4920 for forward inference, while T1 precision and F1 remained undefined. The uncurated annotation is not independent biological truth, but the observed low recovery demonstrates that external stability has not been established. Neither region nor threshold selection changed. [Library-sensitivity evidence](../../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/LIBRARY-SENSITIVITY-20260914.md)

## Multiple natural-copy references do not consistently outperform a centroid

We compared reference representations using the same 235 evaluation intervals from 29 exact repeat labels, with fixed source/homology-component splits and identical reference-copy IDs. With 6-mer frequencies, top-1 accuracy increased from 0.2766 for one TRAIN medoid to 0.3191 for four TRAIN medoids, but a TRAIN centroid reached 0.4255. Native frozen NTv2-500M mean-pooled embeddings showed the same ordering: 0.2043, 0.2638 and 0.3234, respectively. The NTv2 representation was weaker than 6-mer frequencies in this experiment. This does not test all pooling methods, contrastive objectives, or GLM-space prototype selection; the prototype IDs were inherited from 6-mer-space selection. [Comparison figure and full caption](figures/identity-retrieval-caption.md)

The external Dfam-consensus reference had a different construction history from the TRAIN copies and is reported separately. A fixed 1% CAL negative-pair false-acceptance budget was applied per arm; it does not bound the error rate among accepted queries. Because the NTv2 arm was added after earlier evaluation results had been viewed, this comparison remains exploratory. It supports neither a universal multi-prototype advantage nor readiness for general family annotation. [NTv2 report](../../../reports/TE-IDENTITY-RETRIEVAL-20260914/NTV2_GLM_REPORT.md)

## Representation learning improves retrieval on the exploratory panel

An additional fixed ablation separated nucleotide k-mer length from prototype count. At lengths 4, 6 and 8, TRAIN-centroid top-1 accuracies were 0.3872, 0.4255 and 0.3915, respectively; the best length depended on reference representation. Increasing natural prototypes from one to four did not consistently improve retrieval. We then trained a 1024-to-128 linear projection of frozen native NTv2 embeddings with family-supervised contrastive loss on TRAIN only. Fifty epochs were specified, and CAL true-pair acceptance at the fixed 1% pair false-acceptance budget selected epoch 49. The projected TRAIN centroid reached top-1 accuracy 0.5106 and family macro-F1 0.5048, compared with 0.3234 and 0.3103 for the raw embedding centroid. Among 235 EVAL queries, 130 were accepted and 72.31% of accepted assignments were correct. Pair-level calibration therefore does not establish a 1% query error rate. Because this panel had already been examined, these results motivate further representation learning but remain exploratory. They do not establish unsupervised clustering quality or broad annotation readiness. [Training and ablation results](../../experiments/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914.md)

A matched-objective follow-up qualified the representation interpretation.
With per-record L2 scaling and the same 50-epoch supervised contrastive
objective, 6-mer inputs reached top-1 0.6426 and macro-F1 0.6057, compared
with 0.5064 and 0.4994 for frozen NTv2 inputs. The 6-mer projection had
524,416 parameters versus 131,200 for NTv2 because input dimensions differed.
This comparison does not isolate equal-capacity effects, but it rules out
attributing the observed raw-to-projected improvement uniquely to the GLM.
[Training controls](../../../reports/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/training-controls-12708540/metrics.json)

## Coarse-category and class-specific audits constrain interpretation

The six encoded SF5 IDs were consistent across materialized train, validation and test sets and their metadata. However, the Unknown ID merged known-other TE classes, including RC and Retroposon, with ambiguous and unclassified annotations. Unannotated bases were initialized as background. The resulting metrics are interpretable under that encoding, but Unknown recall cannot quantify manual annotation omissions or establish recovery of a specific family. The output categories LINE, SINE, LTR and DNA are coarse classes rather than a general family or superfamily ontology. No new SF5 confusion matrix was inferred from aggregate scores because the inspected nonsealed assets lacked per-position predictions. [Ontology and denominator audit](../../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/RESULTS-20260914.md)

Class stratification also qualified the high overall platypus recovery. Forward recovery of comparator-labelled bases was 0.9524 for LINE and 0.9848 for SINE, but 0.1845 for DNA and 0 for the small LTR subset of ten records. In sea urchin it was 0.5063 for LINE, 0.4405 for SINE, 0.5133 for LTR, 0.2354 for DNA, 0.3473 for RC and 0.0196 for Retroposon. These record-stratified diagnostics preserve overlapping records, with union-based totals reported separately. They motivate class-aware adaptation, without establishing vertebrate-wide robustness or a common evolutionary cause of invertebrate errors. [Fixed-prediction strata](../../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/run-12708396/external_strata.json)

A subsequent exact replay of the legacy scored denominators identified a
second limitation. Although the SF5 data contained six species, both archived
models were evaluated on the first 1,200 records in file order: 360 each from
mouse, zebrafish and chicken, and 120 from western-clawed frog. Fruit fly and
C. elegans did not contribute to those test scores. The validation prefix
also omitted C. elegans. Every class-support count was reproduced exactly;
the numerical metrics therefore remain valid for that restricted population,
but do not represent a complete six-species typing evaluation.
[Scored-prefix replay](../../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/run-12708396/scored-prefix-12708568.json)

## Engineering completion and remaining scientific endpoints

The fixed-commit GitHub Omni workflow executed all 12 jobs and retained all 10 expected cells, including synthetic unsupported and blocked states. This validates workflow integration, not a completed comparison against traditional TE pipelines. CPU forward timing was also measured for a 1-MiB region per candidate species, but a matched GPU timing experiment remains absent. Tiberius full U/P/R runs and their dependent scoring are in progress. Fragment linking has passed controlled engineering examples; natural biological insertion recovery remains untested. New training uses the single fixed seed requested by the user, without reinterpreting historical multi-seed results or spatial resampling as initialization variance. [Execution record](../../experiments/DIRECTIONS-EXECUTION-20260914.md)
