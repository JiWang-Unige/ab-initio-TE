# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 selector action policy

## Scope

The point selector is not accurate enough to be a standalone F1 confidence formula. This report tests a safer deployment policy: single-anchor recommendation only when margin and uncertainty are favorable; otherwise return a top-2 shortlist and require a local mini-probe/fine-tune before trust.

## Headline

- Best policy: `baseline_plus_kmer` / `leave_species_out`, margin=0.0, min_pred=0.0, max_sd=0.05.
- Single-anchor coverage: 0.0000; top2/probe coverage: 1.0000.
- Action contains true-top2 rate: 0.8636; mean regret: 0.0071; p90 regret: 0.0008.
- Usable action-policy gate: True.

## Interpretation

If this gate passes, the selector is useful as a conservative routing assistant, not as an exact performance predictor. If it fails under leave-clade-out, new clades require local probing or a new anchor.
