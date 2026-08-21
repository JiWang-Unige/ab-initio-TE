# PIPE-TEFM-FINAL-FRAGSANITY-20260630

## Scope

Forward/reverse-complement inference and oracle interval-repair sanity check on animal `ntv2_250m@4096`, mouse chr1.
This is a screen-grade mechanism test, not a claim-grade full-panel result.

## Headline

- Source TSV: `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity/mouse_chr1.tsv`.
- Forward raw segment-F1@IoU0.8/boundary5: 0.3062.
- Forward CRF segment-F1@IoU0.8/boundary5: 0.3569.
- Best non-oracle: `consensus_min + crf_style_penalty4` segment-F1 0.4149, boundary-F1 0.1267, missed true rate 0.0929.
- Best oracle-connect same true interval segment-F1: 0.4339.
- Best oracle-fill supported true interval segment-F1: 0.9711.

## Interpretation

- Double-strand inference is not uniformly helpful; max-prob merge tends to increase unsupported predictions, while conservative consensus can improve this mouse chr1 screen.
- The oracle-fill upper bound is very high, meaning the bp model often touches true intervals even when the final predicted intervals are fragmented. This supports a frozen interval refiner route.
- The deployable next step should not use truth-aware oracle logic; it should train a lightweight interval refiner to approximate keep/drop/merge/refine decisions from logits and local interval features.

## Outputs

- `fragment_sanity_headline_iou80_boundary5.tsv`
- `fragment_sanity_best_iou80_boundary5.tsv`
- `fragment_sanity_summary.json`
