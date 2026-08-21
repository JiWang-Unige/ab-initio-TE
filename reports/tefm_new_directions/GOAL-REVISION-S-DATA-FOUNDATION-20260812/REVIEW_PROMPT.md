# Independent goal-revision review

Review the proposal in `PROPOSAL.md` and `PROPOSED_ACTIVE_GOAL.json` as supplied below. The active goal currently targets a completed/closed selector+decoder milestone and makes valid S data-foundation jobs fail for a missing selector metric. The proposed milestone counts six ordered CPU-only data-foundation gates, forbids GPU/training/S1/claims, and requires a later human gate before the direct-S0 numerical goal. The previously stale post-result document hashes now have an independent PASS reattestation and a newly materialized authoritative 2/6 genesis.

Verify `CARRY_FORWARD_REVIEW_REQUEST.json` and the completed `CARRY_FORWARD_REATTESTATION.json` against the current files, original review gates, result audits, audited manifests, new genesis and CURRENT. Check the approved request/reattestation byte hashes are hard-pinned before any write and rechecked immediately before CURRENT replacement; reviewer backend/independence/timestamp/authorization must be exact. Confirm old snapshots and crash-orphan children are audit-only, cannot validate, and cannot brick the CURRENT ancestry. Judge whether this is a fair scope correction rather than moving the goalposts, whether the integer primary avoids missing-metric/degenerate-fraction failures, and whether the goal is too permissive or incomplete.

Required output in Simplified Chinese:

- verdict: PASS / PASS_WITH_WARNINGS / BLOCKED
- fair_scope_correction: true/false
- current_2_of_6_carry_forward_valid: true/false
- user_approval_recommended: true/false
- blockers: list
- warnings: list
- required_changes_before_install: list
- reasoning: 3-6 bullets
- confidence: High/Medium/Low

Hard rules: no change may be written to ACTIVE_GOAL without explicit user approval; do not waive or fabricate the stale experiment-doc hashes; no SOTA/screen anchor change; data-foundation success cannot authorize S0 GPU or S1. Review the opt-in validator, immutable carry-forward approval pins, content-addressed `CURRENT` ancestry, writer mutex/CAS and orphan-crash behavior, same-count typed stop events, independent reviewed evidence per extension, real reviewed-files/AUDITED_MANIFEST closure, fixed PASS polarity and authorization allowlist, gate→execution bindings, hash-pinned scientific contract, read-only `--check`, and legacy golden tests. Exact 6/6 retains the four-state `success` status but must stop at a human goal-revision gate with claim/automatic continuation false. Installing the goal does not authorize a job submission.

Proposal files:

- `reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/PROPOSAL.md`
- `reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/PROPOSED_ACTIVE_GOAL.json`
- `reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CARRY_FORWARD_REVIEW_REQUEST.json`
- `reports/tefm_new_directions/GOAL-REVISION-S-DATA-FOUNDATION-20260812/CARRY_FORWARD_REATTESTATION.json`
