# Conservative Anchor Trust Router

## Scope

This is a bounded, non-claim selector diagnostic. It uses only deployable genome-derived inputs for prediction and uses target TE-F1 only for held-out evaluation.

## Headline

- Best in-panel rule: `baseline_plus_kmer` / `leave_species_out`.
- top2 contains-best: 0.8636; top2 mean regret: 0.0071; ECE: 0.0372.
- Selected conservative router gate passed: True.
- Leave-clade-out is handled by explicit abstention/local-probe, not by trusting the point formula.

## Decision Wording

If used in the manuscript, this should be described as a conservative triage router: in-panel species get a top-2 anchor shortlist plus local chromosome probe; unseen clades abstain until a local probe or new anchor is trained.
