# PIPE-TEFM-FINAL-INTERPRET-20260630

## Summary

- Total fragment rows: 1409.
- High-score strict background rows: 9; mean binary probability 0.8893; mean SF5 background fraction 0.9974.
- Unknown annotation rows: 260; mean best-main4 SF5 fraction 0.4706.

## Interpretation

- The existing high-score strict-background candidates do not currently support a hidden-TE claim: they are high under the binary model but almost entirely BG under SF5.
- Unknown-annotation fragments are more promising for annotation audit because many have strong main4-like SF5 signal.
- The next interpretability step should target two contrasts: high-score strict-BG versus matched BG, and Unknown-main4-like versus known main4, using saliency/occlusion/k-mer motif enrichment on the same 512 bp fragments.
- Full model-level paper-method alignment remains pending; PDF keyword-level method scoping is available in `pdf_method_alignment.md` when `pypdf` is installed.

## Outputs

- `fragment_feature_table.tsv`
- `source_feature_summary.tsv`
- `high_score_strict_bg_cases.tsv`
- `unknown_main4_like_top30.tsv`
