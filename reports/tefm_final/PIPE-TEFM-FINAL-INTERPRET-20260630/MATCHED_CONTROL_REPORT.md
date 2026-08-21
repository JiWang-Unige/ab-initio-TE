# PIPE-TEFM-FINAL-INTERPRET-20260630 matched-control sanity check

## Summary

- High-score strict-BG cases matched: 9 / 9 from a same-species/same-chromosome BG pool of 63.
- Unknown main4-like cases at SF5 best-main4 fraction >= 0.8 matched: 32 / 32 from a human known-main4 pool of 661.
- This is a composition/control sanity analysis, not model-level saliency or occlusion.
- Match-quality flags: high_score_strict_bg_vs_matched_bg=ACCEPTABLE_COMPOSITION_SCREEN, unknown_main4like_vs_matched_known_main4=POOR_GC_MATCH.

## Interpretation

- The high-score strict-BG contrast is now controlled within western_honey_bee GroupUn, but sample size remains only 9. Use it to diagnose binary false-positive triggers, not hidden TE prevalence.
- The Unknown-main4-like contrast has enough cases for audit prioritization, but match quality must be checked before interpreting it as true main4 relabeling.
- If the Unknown contrast is flagged as `POOR_GC_MATCH`, treat the signal as a high-GC/SVA/model-bias audit first, not as annotation correction.
- K-mer enrichment is descriptive and must be followed by model occlusion/saliency before mechanistic claims.
- PDF text extraction was attempted with pypdf; see `pdf_method_alignment.md` for extracted keyword-level alignment.
