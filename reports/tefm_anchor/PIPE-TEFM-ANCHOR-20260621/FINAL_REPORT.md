# FINAL REPORT: PIPE-TEFM-ANCHOR-20260621

Status: generated summary. This is a single-seed screen and is not claim-grade.

## Output Files
- Binary eval: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/binary_eval.tsv`
- Embedding: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/embedding_bg_unknown.tsv`
- SF5 candidates: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_candidate_summary.json`
- Anchor formula: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/anchor_formula/anchor_formula_results.json`

## Binary Model Summary
- `TFREPAIR_invert_boost_animal_4096_seed42`: n=6 mean_TE_F1=0.4248 min=0.0044 max=0.9437
- `cross_supervised_4096`: n=6 mean_TE_F1=0.4134 min=0.0031 max=0.9424
- `insect_no_beetle_4096`: n=6 mean_TE_F1=0.4520 min=0.0059 max=0.9448
- `insect_primary_4096`: n=6 mean_TE_F1=0.5197 min=0.0054 max=0.9465

## Embedding Summary
- `bg_main4:A0`: ARI=0.09891764270915265 NMI=0.12024394421792615 holdout_macro_F1=0.2805495267097703 status=ok
- `bg_main4:A1`: ARI=0.4066984571075202 NMI=0.4168980465248707 holdout_macro_F1=0.5630350879271084 status=ok
- `bg_main4:C0`: ARI=0.08707354625544114 NMI=0.1300534379989442 holdout_macro_F1=0.31569560797519947 status=ok
- `bg_main4:C1`: ARI=0.8353175150949033 NMI=0.8044606719895218 holdout_macro_F1=0.7359712586378795 status=ok
- `unknown_highscore:A0`: ARI=0.14172303415511292 NMI=0.2102964383888707 holdout_macro_F1=0.2696580000958363 status=ok
- `unknown_highscore:A1`: ARI=0.4048828376104039 NMI=0.4416066187640616 holdout_macro_F1=0.49488406360985765 status=ok
- `unknown_highscore:C0`: ARI=0.15831762630715168 NMI=0.26314599757541507 holdout_macro_F1=0.3493884805823188 status=ok
- `unknown_highscore:C1`: ARI=0.8600064259121131 NMI=0.8352940708844608 holdout_macro_F1=0.7598066930812 status=ok

## SF5 Candidate Summary
```json
{
  "high_score_strict_bg": {
    "n": 9,
    "best_main4_counts": {
      "SINE": 9
    },
    "mean_best_main4_frac": 0.0,
    "mean_unknown_frac": 0.0026041666666666665,
    "mean_bg_frac": 0.9973958333333334
  },
  "unknown_annotation": {
    "n": 260,
    "best_main4_counts": {
      "SINE": 104,
      "DNA": 131,
      "LTR": 25
    },
    "mean_best_main4_frac": 0.47058293269230766,
    "mean_unknown_frac": 0.06196664663461538,
    "mean_bg_frac": 0.38255709134615384
  }
}
```

## Anchor Formula Summary
- deployable_linear: status=ok R2=0.30731636405152185 LOO_RMSE=0.4089340599553428
- annotation_aware_linear: status=ok R2=0.5087278802725599 LOO_RMSE=0.5417820100206738
