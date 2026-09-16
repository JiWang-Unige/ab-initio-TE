# Three-species reference-knowledge diagnostic

2026-09-16. Authorized by the user's request to test the zebrafish annotation-completeness hypothesis and continue the finite manuscript closure. This is a retrospective diagnostic on already observed DEV, not a new independent test or a revised acceptance gate.

## Fixed scope

- Zebrafish (danRer11), pig (susScr11), chicken (galGal6): the original 500 DEV tiles per species. Do not select TE-rich regions or change coordinates.
- Original seed42 D checkpoint `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model`, NTv2-500M code, original six-species calibration and threshold 0.42330056285498807. No fitting, threshold selection, training or additional seeds.
- The original evaluation wrote summary JSONs but no position caches. A single fixed-checkpoint inference replay on these three DEV inputs is therefore permitted as technical reconstruction. Compare all original TP/FP/FN/callable counts before using it. Any mismatch blocks combined scoring and is reported; do not silently replace the historical result or tune to reproduce it. No original predictions are claimed to have been recovered bit-for-bit without a saved cache.
- Each RepeatMasker query is the original 8192-bp centre plus up to 4096 bp of flank on each side, clipped only at contig ends. Verify centre sequence equality against the materialized original record. Both library arms use the same prepared file; score original callable centre positions only.
- RepeatMasker 4.2.2 / RMBLAST 2.14.1+, same `-pa 4 -xsmall -gff -lib` settings. Dfam3.9 installed complete target-related partitions, ancestor + descendant taxon rule; L0 is curated consensus export, Lplus adds same-release uncurated records. No new source, taxon widening or outcome-based family selection.
- Historical species probes explicitly say curated-only, with ancestor/lineage counts 249/1717 (zebrafish), 784/0 (pig), 218/0 (chicken). The controlled explicit-library workflow is not the original `-species` multistage run: old label versus reannotated L0 includes context and invocation changes. Only the two new arms isolate the library condition. Save exported record inventories and require the L0 sequences to be an unchanged subset of Lplus. Verify the zebrafish exports are identical; this is an empty-increment control, not a new biological discovery.

## Outputs and interpretation

Preserve original labels and scores. Record full old/L0/Lplus confusion matrices on the same callable bases; additions among predicted positives (a), additions among predicted negatives (b), positive-label losses in both prediction groups, Unknown changes, and overlapping class membership. Library competition can remove old calls even when the reference library is a sequence superset. New uncurated support is comparator evidence, not confirmed biological truth or a corrected F1.

Summarize TRAIN/CAL/DEV material exposure and original DEV class coverage. Strict TE classes remain LINE/SINE/LTR/DNA/RC/Retroposon. For class recall, exclude mixed-class positions from exclusive class strata and disclose them separately. Never assign a TE class or divergence to unannotated background. RepeatMasker divergence denotes reference-sequence divergence, not an absolute age.

The inferential question is whether the predefined added knowledge changes the three-species pattern, while also exposing model misses. Neither family counts nor F1 changes alone establish genome-wide annotation completeness. Independent biological claims still require finite matched FP/TN candidates and orthogonal evidence; such candidates cannot be called rescued TP from RepeatMasker agreement alone.

## Budget and stopping

One CPU preparation (2 CPUs, 24 GB, <=1 h), one GPU inference replay (one 3090, 64 GB, <=1 h), at most six annotation cells (4 CPUs/16 GB, <=2 h each; max three simultaneous), one CPU scoring (2 CPUs/24 GB, <=1 h). Preserve all attempts. No automatic extra runs for an unfavorable result. If an export is empty, related partitions are missing, original coordinates cannot be reconstructed, or counts do not reproduce, report that concrete limitation instead of changing the scientific input.

After valid six-cell scoring, assess whether a bounded candidate check could change the manuscript claim. If only label dependence or unresolved evidence is established, finish with that conclusion. Do not expand until significance or search new libraries for a desired answer. Plant/Fungi training, new MoE, new Gap solutions and sealed panels remain outside this diagnostic.

This protocol follows the focused [Pro discussion](../manuscript/20260916/pro-species-review.md), with the explicitly documented fixed-checkpoint replay needed because original caches were not retained. It does not represent an independent preregistration: the DEV aggregate results were already known.
