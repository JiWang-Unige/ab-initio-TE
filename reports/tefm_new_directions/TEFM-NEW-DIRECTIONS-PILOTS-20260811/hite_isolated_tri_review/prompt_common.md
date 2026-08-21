# Independent result review prompt — BENCH-HITE-ISOLATED-20260811-R1

Act as an independent scientific/runtime reviewer. Do not use tools and do not
assume facts beyond this frozen evidence. Return a concise structured review
with: (1) semantic validity, (2) reproducibility/comparability, (3) whether the
cross-run RM+HiTE reconciliation is defensible, (4) claim boundary, (5) one
judgment from `continue`, `run-sanity-check-first`, `comparability-blocker`,
`replace-component`, `abandon-route`, (6) exactly one next action, and
(7) confidence.

## Frozen question and authorization

The parent `BENCH-RM-HITE-VALIDITY-20260811-R1` Job 11523819 was a failed
two-cell aggregate: its exact RM2+RepeatMasker+Dfam4 cell was an independently
audited ENGINEERING_PASS with 43 adapter rows, while exact HiTE 3.3.3 timed out
at 600 seconds. A prior 3/3 tri-review authorized one new isolated HiTE-only
attempt with byte-identical assets/fixture/direct argv, 1800-second timeout,
4CPU/48GiB/1h/0GPU. It prohibited rerunning RM or other tools. A fresh
independent code review passed with 0 blockers and 18/18 behavior tests.

## Job 11524485 result

- Slurm `COMPLETED 0:0`, 23m04s allocation, 4 CPU/48 GiB/0 GPU.
- `hite_help_identity`: rc0, not timed out, anchored exact official line
  `HiTE, version 3.3.3`.
- `hite_min`: direct argv `python /HiTE/main.py --genome ... --thread 2
  --annotate 1 --out_dir ...`; rc0, not timed out; command wall time 21m58.53s;
  peak RSS 2,111,456 KiB.
- Final exact `HiTE.gff`: 1,203,491 bytes, SHA-256
  `11bbefe6044c5959d2906711ccfaa3e95bf6d94cd54e44305cb4512f464f3114`.
- Canonical adapter: 14,315 rows, SHA-256
  `89ca6f9e2da0f88b273771ea500ab86c1a375c83dda9e30ea803c6056cbec78c`.
- Cell status `ENGINEERING_PASS`; `hite_engineering_pass=1`;
  `semantic_success=true`; no STOP or failure bundle.
- Independent audit: artifact manifest 12/12 paths and hashes pass; published
  canonical payloads 5/5 pass. Staging payloads were atomically moved to their
  canonical paths by design; runtime environment retains matching staged and
  canonical copies.
- Reconciliation byte-verifies the immutable parent RM result and parent HiTE
  600s timeout. It reports parent aggregate `FAILED`, parent RM
  `ENGINEERING_PASS_REUSED_BY_HASH`, isolated HiTE `ENGINEERING_PASS`,
  `two_cell_evidence_ready=true`, `single_successful_run=false`,
  `accuracy_claim=false`, `claim_eligible=false`.
- Route-level validator against the five-cell `GOAL_B_DENOMINATOR_R2` returns
  `failed_run` because the isolated child does not expose the complete
  `terminal_cell_count`. It is forbidden to synthesize that metric.

## Questions that must be answered

1. Is the isolated HiTE engineering pass semantically valid?
2. Is it scientifically/auditably defensible to retain the parent RM pass and
   combine it with isolated HiTE as two-job evidence, while preserving the
   parent aggregate failure?
3. Does this close only two cells, or authorize another denominator run?
4. Should `further_retry_allowed=true` in reconciliation be treated as a
   semantic warning because the human authorization allowed only one isolated
   attempt, even though success means no retry is needed?
5. What exactly is the single next action? No GPU, biological benchmark, S0/S1,
   other tool, or automatic rerun may be authorized by this review.
