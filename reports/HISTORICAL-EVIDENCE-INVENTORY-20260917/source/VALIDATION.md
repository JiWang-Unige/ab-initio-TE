# Historical evidence inventory validation

Validated on 2026-09-17 after copying the four remote summaries and generating the derived manuscript tables.

| Check | Result |
|---|---|
| Local GLM window values versus `window_sweep.tsv` | PASS; 20/20 rows, zero mismatches |
| Local NTv2/NTv3 aggregation versus `matrix_eval.tsv` | PASS; 90 groups from 495 rows, maximum absolute mean difference `4.996003610813204e-16` |
| Remote v2 primary backbone summary versus copied `hg38_backbone_finetune_eval_metrics.csv` | PASS; 5/5 rows, zero mismatches |
| Remote v2 window summary versus copied `fig2_backbone_comparison.csv` | PASS; 5/5 rows, zero mismatches |
| Archived human-library RM summary versus copied `repeatmasker_human_library_comparison.tsv` | PASS; 7/7 rows, zero mismatches |
| Copied-source SHA-256 versus baobab source SHA-256 | PASS; 4/4 files match |

No source-summary versus derived-table numerical discrepancy was found. The local NTv2/NTv3 table rounds the aggregated mean to 15 significant digits; the maximum absolute rounding difference is reported above and is below the validation tolerance `5e-15`.
