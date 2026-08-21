# PIPE-TEFM-FINAL-SELECTOR-20260630

## Summary

- Species-probe audit rows: 22.
- Poor after species-specific NTv2-500M fine-tune: red_flour_beetle, thale_cress.
- Partial recovery / use with caution: soybean, c_elegans.
- Non-species-specific anchor performance rows: 156.
- Observed multi-anchor oracle mean over species: 0.7787.
- Best broad single model with >=5 rows: `cross_supervised_4096` mean TE-F1 0.5432 over 28 rows.
- Deployable selector RF: in-sample R2 0.8203, leave-species-out RMSE 0.3040.

## Interpretation

- Species-specific NTv2-500M recovery should be treated as a soft annotation-quality audit, not an automatic exclusion rule.
- Multi-anchor reporting is supported: animal/human, plant/cross, and insect-specific anchors solve different target panels.
- Deployable selector features deliberately exclude target TE annotations; annotation-aware formulas are explanatory controls only.
- Red flour beetle remains the clearest hard label/library/domain-risk species because it stays poor even after species-specific fine-tuning.

## Outputs

- `species_probe_quality_audit.tsv`
- `anchor_performance_matrix.tsv`
- `multi_anchor_recommendations.tsv`
- `selector_formula_results.json`
