# Fragment linking Phase 1（2026-09-14）

## 目的与边界

Phase 1 adds a bounded learning baseline to the Phase 0 pair contract.  It
uses a small, deterministic semi-simulated fixture whose records represent
independent insertions.  Every sequence is generated from its own fragment
label; no consensus is cropped and then counted as several independent
copies.  The fixture is `ENGINEERING_ONLY`, so its scores are implementation
diagnostics and cannot support a biological claim.

The implementation is
`scripts/experiments/FRAGMENT-LINKING-PHASE1-20260914/fragment_linking_phase1.py`.
It does not call a GLM, create random embeddings, read sealed data, fill a
gap, merge coordinates, or modify a material mask.  M2 sequence evidence and
M3 gap/context evidence remain `INPUT_CONTRACT_ONLY` until real encoder input
and independently verified linkage truth exist.

## Identity and split contract

Each fragment stores `truth.parent_insertion_id` separately from predicted
family/orientation/length.  A known positive requires two known parent IDs
that are equal; a known negative requires two known parent IDs that differ.
`unresolved` truth has no parent ID and is excluded from the negative
denominator.  Empty `source_copy_id` and `homology_component_id` values are
unknown; they never make a pair positive.

The fixture records `host_id` separately from `contig`.  Pair candidates
require the same host and contig, so nearby fragments in different hosts can
never be linked.  Materialized roles (`train`, `cal`, `eval`) are checked for
cross-role overlap in `host_id`, `source_copy_id`, and
`homology_component_id`; the deliberate leakage mutation in the tests must
fail.  The roles are assigned at independent-insertion level, so fragments
from one source copy cannot be split across roles.

## Baselines

The candidate window is 25 bp, with overlapping intervals retained.

- **B0** links a same-role candidate by distance only.
- **B1** adds agreement of predicted exact family, predicted orientation, and
  a predicted-length ratio of at least 0.5.  Missing orientation abstains.
- **M1** fits a small logistic pair model on TRAIN features (distance,
  overlap, family match, orientation match, length ratio), chooses one
  threshold on CAL, and applies it to EVAL.  The CAL false-accept budget is
  fixed at `alpha=0.01`; the production contract requires at least 100 known
  negative pairs.  The tiny fixture is explicitly below that scale and is
  diagnostic only.

The output remains an edge list and optional connected components.  A
component can expose transitive over-merging, but the code never writes a new
interval or fills the sequence between two fragments.

## Fixture coverage and observed engineering output

The fixture contains ordinary same-insertion fragments, adjacent independent
same-family insertions, a nested insertion, a same-family transitive chain,
nearby fragments in different hosts, a known pair with missing predicted
orientation, and a near unresolved pair with empty identity fields.  Running:

```bash
python3 scripts/experiments/FRAGMENT-LINKING-PHASE1-20260914/fragment_linking_phase1.py \
  --out-dir reports/FRAGMENT-LINKING-PHASE1-20260914/toy_run
```

writes `contract.json`, `fragments.jsonl`, `pairs.tsv`, one edge list per
method, `calibration.json`, `fit.json`, `metrics.json`, and `status.json`.
The current deterministic run contains 36 fragments and 19 same-host/contig
candidate pairs.  The known same-insertion all-pair denominator is 12; one
unresolved candidate is excluded from negatives.  B0/B1/M1 respectively
expose 4/3/1 over-merged components in this deliberately adversarial fixture;
M1 is a code-path diagnostic, not a biological improvement estimate.  The
interval and mask invariants remain unchanged.

The machine-readable result is
`reports/FRAGMENT-LINKING-PHASE1-20260914/toy_run/metrics.json`; its
`scientific_claim_status` is `NOTRUN`.  A real experiment needs natural
fragment predictions, a fixed source-copy/host/homology split, and
insertion-level truth before pair precision or cluster over-merge can be
reported for a species.

M2/M3 do not need to remain idle until a natural-insertion gold standard exists.
The next controlled mechanism experiment can use the recovered natural-copy
panel to construct explicitly sourced semi-simulated insertions and fragments,
including nested and adjacent independent insertions. Source copy, host locus
and sequence-similarity components must remain separated across TRAIN/CAL/EVAL.
That experiment can test sequence/context association with known construction
truth; later validation on independently reviewed natural predictions is still
required for an insertion-recovery claim. The current 36-fragment fixture is
only an engineering test and does not constitute that natural-copy experiment.

## Verification

```bash
python3 scripts/experiments/FRAGMENT-LINKING-PHASE1-20260914/test_fragment_linking_phase1.py -v
```

The tests cover independent sequence provenance, materialized split leakage,
host gating, empty-ID semantics, orientation abstention, the fixed CAL gate,
and the no-gap/no-mask invariants.  No training or Slurm job is required for
this fixture.
