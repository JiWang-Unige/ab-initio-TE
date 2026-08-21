# Review-Board and Council Summary

- Exp ID: `PIPE-TEFM-CAP-POSTPROC-20260701`
- Date: 2026-07-01
- Scope: bounded diagnostic only; no capability promotion and no SOTA claim.

## Question

The user asked whether the fragmentation threshold was too strict, whether multi-threshold views could show the best tradeoff, whether short fragments should be handled with a shorter threshold while long fragments use HMM/CRF-style smoothing, and whether traditional fragmentation postprocessing ideas should be tested in the same way.

## Review-Board Consensus

- Quorum: 3/3 effective independent review.
- The diagnostic is useful if it is framed as sensitivity analysis, not as a new method.
- The main publication-safe output is a tradeoff curve/table: segment-F1 and boundary-F1 versus missed true TE, deleted true-backed fragments, pred_true_backed_rate, overmerge, and split metrics.
- A single "best threshold" must not be selected from this test panel and presented as a deployable recipe.
- The result must remain subordinate to `DEC-001` and `DEC-002`: post-hoc threshold/gap/HMM/CRF-style refinement is not reopened as the main capability route.

## Council Consensus

- Quorum: 3/3 across two rounds.
- Conditional approval: keep this as a high-risk diagnostic/comparator only.
- The strongest observed interval rows are mostly deletion-driven, especially on human, where HMM/length-adaptive variants improve strict segment metrics while deleting many true-backed raw fragments.
- Species-specific behavior is important: mouse has a guarded gap/min-length row that looks practically useful in this bounded panel, but human prefers a lower raw threshold under strict retention guardrails.
- No universal fixed postprocess rule is promoted.

## Decision

Use `PIPE-TEFM-CAP-POSTPROC-20260701` as a supplement to explain why fragmentation is not merely a threshold-setting issue:

1. Lower thresholds can recover some boundary/segment signal.
2. Strong HMM/gap/length-adaptive cleanup can improve strict segment metrics.
3. However, the best apparent cleanup often deletes true-backed fragments or overmerges.
4. Therefore the main claim remains conservative: bp-level TE detection is strong, but complete interval reconstruction remains an open problem requiring richer interval-level modeling and annotation audit.

## Raw Review Artifacts

- Review-board prompt and outputs: `outputs/PIPE-TEFM-CAP-POSTPROC-20260701/review_board/`
- Council raw outputs: `outputs/PIPE-TEFM-CAP-POSTPROC-20260701/council/`
- Main diagnostic report: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/POSTPROCESS_THRESHOLD_REPORT.md`
