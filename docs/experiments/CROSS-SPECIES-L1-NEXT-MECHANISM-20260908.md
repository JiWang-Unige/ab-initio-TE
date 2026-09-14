# L1 next mechanism: evidence and completed advisory review

2026-09-08. Status: **Pro consultation complete; bounded proposal ready for approval**.
The terminal goal remains an academically usable cross-species sequence-only
TE-material masking model. The completed Human C experiment is not that goal.

## Selected proposal, not yet authorized for execution

Pro recommends one matched information-path test: BLOCK4 versus PAIR8. Both
pack the unchanged two half encodings; only cross-half attention differs.
This keeps loss weighting, token phase/tails, coordinates and training budget
unchanged. Actual local-native source confirms why embedding padding and pairwise
attention masks must be separate. No new weights or model behavior tested yet.

Full approval-ready proposal:
[L1-PAIR-CONTEXT-V1](CROSS-SPECIES-L1-PAIR-CONTEXT-V1.md).
Seed42 new cap8GPUh; optional explicitly approved conditional seed17 another8GPUh.
New +.005 paired F1 effect gates are proposed, not previously approved or inferred
from C. All old absolute readiness/topology/hardN and sealed-data rules remain.
The host specifies numerical test tolerances, a20% resource-estimate margin and
minimal exp-local implementation scope; these are proposal details, not measured
feasibility. No new training/real GPU smoke has been submitted.

## Decision-relevant evidence

1. C utility is now a valid negative under its frozen conjunctive gate. Both
   MW/MP gained zero correct CDS chains; this closes C-derived gene-utility
   expansion, not every TE-material hypothesis. Full closure:
   `GAP-BRIDGE-C-UTILITY-20260906-R1-RESULT.md`.
2. D's J0 frozen-cache diagnosis reproduces original metrics within 1e-6.
   Seed42 DEV FN=92008: completely missed=44594, terminal=35256, internal=12158.
   SCREEN FN=91288: completely missed=49668, terminal=29858, internal=11762.
   Across both seeds/four panels scalar-threshold oracle F1 headroom is only
   0.000009–0.002048. These categories locate errors, not their causal mechanism.
3. INIT P0R does not beat both references and fails its frozen release. No seed17,
   fresh-head rescue, threshold sweep or same-recipe step extension follows.
   Existing B0/B2/coverage and structured-decoder closures remain unchanged.
4. Actual shared trainer `cross_species_token_task.py:182` normalizes each
   4096-bp half by its class-weighted callable mass, then averages halves;
   P/N token masses preserve six-bp mixed labels and tails. Per-step sampling
   contributes a tile pair per species. These are concrete possible intervention
   points, not evidence that this loss causes the observed misses.
5. Prior D0 already measured token-space ceilings, B0 TRAIN fit and length/class/
   seam strata. Do not repeat these as a new diagnostic. B0 length-bin recall
   was non-monotonic; short-run difficulty alone does not justify length weighting.

## Read-only implementation feasibility facts

Live Baobab metadata read on 2026-09-08 from the existing H0 checkpoint's
`config.json`: EsmForTokenClassification, rotary positions,
max_position_embeddings=2050, 29 layers, hidden_size=1024, 16 attention heads;
attention/hidden dropout=0. Current shared code batches the two 4096-bp halves
as separate sequences, so an 8192-bp tile does not currently imply cross-half
attention. This makes context connectivity and loss reweighting distinct
interventions. The config alone does not establish longer-context validity,
arbitrary attention-mask support or GPU memory feasibility; no forward pass,
new data read or training was performed for this metadata check.

## Consultation dispatched

User-authorized in-app browser Pro follow-up sent on 2026-09-08 to the existing
[full repository review](https://chatgpt.com/c/6a9ca31f-0610-83eb-b663-a3e26a020c7c).
It uses the already-reviewed complete Git snapshot
`b6b2c08b436c9fe5ce49b2af67f46690fdaa9350` plus the explicit verified C update.
Current local base `852b65e1accb560cce62ffdb3c9b99260511fe63` was identified,
without claiming that new uncommitted result files were in the old archive.

Requested output: compare at most three distinguishable mechanisms, choose one
bounded next step, specify matched controls, data/selection rules, resource
estimate and stop criteria. A cache diagnostic must change the subsequent action.
No new archive, weights, raw data or sealed panel was uploaded. The page visibly
accepted the message, then returned a complete response after17m55s.
This consultation is advisory, not a tri-review quorum or scientific evidence.

## Non-negotiable completion and authorization boundaries

Retain internal per-species F1>=0.8, P/R>=0.75, macro F1>=0.83 and original
topology/hardN guards. Internal success would still leave approved external and
real continuous-FASTA validation, provenance/license and release review to do.
Do not delete the weakest species or rename local Human work as cross-species
completion. Existing D is a frozen baseline, not a successful terminal model.

No new CONF inference/diagnosis/selection; reserved worm chromosome and
horse/opossum/dm6/cattle remain sealed. No unused C/INIT budget is transferable
by default. A new scientific training scope must be concretely reviewed and
authorized; existing-result synthesis and scoped engineering preparation can
continue now. Advisory preparation and targeted source inspection are complete;
the next material step requires explicit approval of the new context experiment,
its new effect gates and its resource budget. This is not ordinary progress
confirmation and cannot be inferred from the closed C or INIT authorization.
