# Independent Full-Scope Research Review

You are an independent external reviewer. Do not assume a special role. Review all dimensions and recommend the single next decision most likely to advance a publishable TE foundation-model project. Output professional Simplified Chinese and include the exact heading `### 1. Overall judgment`.

## 1. Research question and binding sequence

The long-term goal is a leakage-safe direct-superfamily baseline. Direct S0 must first pass its data, identity, homology-split and numeric acceptance gates; only then may hierarchical/open-set S1 address misclassification. No GPU, annotation generation, homology construction, DATA materialization or S1 work is currently authorized.

This claim-ineligible CPU experiment asks one narrow engineering/scientific-enabling question: can the installed Dfam 3.9 FamDB leaf API retrieve six frozen versioned accessions exact-once across 12 partitions, with no name/prefix/case/alias/copy fallback?

## 2. Frozen experiment contract

- Six frozen accessions × 12 leaves = exactly 72 calls to `FamDBLeaf.get_family_by_accession` in a single formal probe.
- Required published fields: matched partition, versioned accession, canonical name, raw class, consensus length and consensus SHA256.
- PASS requires all six exact-once with all frozen fields equal.
- Missing, duplicate or frozen identity drift is a semantic typed block (rc0) and closes the route.
- API/schema/asset/runtime/scheduler/gate/manifest failure is failed-run (rc2), not a valid negative.
- Even PASS only makes a separately designed leaf-adapter CPU preflight proposal eligible. It never authorizes RepeatMasker, representative/full DATA, homology, GPU S0 or S1.
- One-shot execution authorization only; no automatic retry.

## 3. Job 11533175 result

- Slurm state `FAILED`, exit `2:0`, elapsed 17 seconds on `private-teodoro-gpu`.
- Exact requested and allocated envelope: 1 CPU, 4 GiB, 10 minutes, 0 GPU. `ReqTRES` and `AllocTRES` were exactly `cpu=1,mem=4G,node=1,billing=2`.
- Fresh independent code review was `PASS_WITH_WARNINGS`, blockers=0. Machine pre-submit gate passed. Allocation-side strict scheduler checks and 23/23 tests passed.
- The single in-memory 72-call probe function returned. During cleanup, the runner unconditionally called `FamDB.finalize()`.
- In the installed API, read-mode `FamDBLeaf.__init__` does not define the write bookkeeping attribute `added`; `FamDBLeaf.finalize()` accesses it. Cleanup raised `AttributeError: 'FamDBLeaf' object has no attribute 'added'`.
- The returned 72 observations were never frozen or published. Therefore exact-access PASS, missing, duplicate and drift counts are all unknown. It is forbidden to infer a scientific result merely because the function returned in memory.
- Route-local semantic audit: `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`, `semantic_success=false`, `valid_negative=false`, all downstream authorizations=false.
- Old `ACTIVE_GOAL.json` validation returns `failed_run`; this is consistent with the run failure but the old selector/decoder metric schema cannot score this route.

## 4. Integrity and reproducibility

- Two immutable failure bundles exist: the formal failure with the exact AttributeError and the wrapper terminal failure. Their payload manifests verify.
- `AUDITED_MANIFEST_11533175.sha256` independently closes CURRENT, both failure payload manifests, stdout/stderr, code-review gate, semantic audit and validation; all entries verify.
- The failure is deterministic and local to read-mode lifecycle cleanup. The scientific observation payload is absent.
- The previous aggregate roundtrip Job 11528885 also failed on `FamDBLeaf.added`, before RepeatMasker. Tri-review then replaced the aggregate component with this isolated leaf probe. Thus the route has already consumed two distinct implementation contracts and this leaf probe's one-shot authorization.

## 5. Decision question

Choose whether to stop this FamDB export/access route, or permit exactly one new separately reviewed close-only lifecycle repair that changes only read-mode handle closure/result publication and leaves the single 72-call scientific probe unchanged. Consider the repeated API-lifecycle failures, the high value of the unpublished observation, the low bounded CPU cost, and the risk of endless repair iterations.

If permitting repair, specify hard re-entry conditions: no call to `FamDB.finalize()` in read mode; explicit close of underlying HDF5 handles; synthetic behavior proof that observations are staged before cleanup and cleanup failure cannot erase/upgrade them; exact one 72-call probe; no reuse of consumed gate; fresh code review; one final bounded CPU attempt; any further lifecycle/API failure permanently closes the route. Do not authorize a direct retry of the old code.

## Required output

### 1. Overall judgment
Choose exactly one:
- continue-current-route
- scale-to-track-b
- tune-only-if-near-sota
- replace-component
- change-backbone
- change-objective-or-loss
- run-sanity-check-first
- comparability-blocker
- abandon-route
- return-to-literature

### 2. SOTA gap interpretation
State N/A where appropriate; do not invent model metrics.

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset/version identity | | |
| Split/leakage | | |
| Metric implementation | | |
| Preprocessing | | |
| External weights | | |
| Test-time protocol | | |
| Resource profile supports claim? | | |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Result payload exists | | |
| Values finite | | |
| Failure classification is correct | | |
| No unsupported inference | | |
| Logs/config/artifacts sufficient | | |

### 5. Architecture/component assessment
Explain whether this is an exact-access failure or a cleanup component failure, and whether a close-only repair is distinguishable from retrying the same failed route.

### 6. Track recommendation
State whether any S downstream stage may open now.

### 7. Risks and blockers

### 8. Next action
Give exactly one concrete next action, with explicit permanent stop/re-entry conditions.

### 9. Confidence
High / Medium / Low, with reason.
