# PIPE-TEFM-FINAL-GENOMEDECAY-20260630

## Scope

This is a screen-grade deployable selector extension. It only uses features computable from the target genome and anchor identity; target TE annotations are excluded.

## Feature Sources

- Anchor-performance rows: 156 from `PIPE-TEFM-FINAL-SELECTOR-20260630/anchor_performance_matrix.tsv`.
- Species genome rows with features: 22.
- Sampled k-mer setting: k=4, bounded prefix-stream max sampled bases/species=1000000. This is a fast screen proxy, not a Mash/sourmash replacement.
- `mash`: unavailable; `sourmash`: unavailable. No Mash/sourmash distances were used in this run.

## Selector Result

- Baseline deployable leave-species-out RMSE: 0.3042.
- Best genome-derived feature set: `baseline_plus_kmer` with leave-species-out RMSE 0.2666.
- Delta vs baseline: -0.0376 RMSE.

## Interpretation

- Assembly statistics and sampled k-mer shift are valid deployable variables because they can be computed before TE annotation.
- This run is a speed-first prototype: k-mer vectors use bounded prefix-stream sampling, while claim-grade work should use genome-wide MinHash/Mash/sourmash or indexed stratified sampling.
- If the best delta is small or positive, the current screen does not yet justify a claim-grade selector formula; it instead supports reporting anchor families plus uncertainty.
- Mash/sourmash and public phylogenetic matrices remain useful next additions, but should be installed/versioned before being treated as claim-grade evidence.

## Outputs

- `genome_feature_table.tsv`
- `anchor_pair_genome_features.tsv`
- `selector_genome_feature_results.json`
