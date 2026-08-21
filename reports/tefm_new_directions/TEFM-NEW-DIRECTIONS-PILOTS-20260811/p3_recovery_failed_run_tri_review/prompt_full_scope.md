# Independent Full-Scope Research Review

You are an independent external reviewer. Do not assume a specialized role and do not rely on other reviewers. Review the full scope below and answer in professional Simplified Chinese. The host will aggregate independently; do not ask questions.

## 1. Research question and north star

The project must first establish a leakage-safe direct-superfamily S0 baseline before any hierarchical/open-set S1 work. Frozen human decision: RepeatMasker direct `BG/SINE/LINE/LTR/DNA/Unknown` annotations are prediction truth; sequence homology defines split components only and never relabels; 10 label-contract-excluded identifiers remain U/ignore; `X13_LINE` is audit-only. Before homology clustering, R0 must determine whether 279 exact-name misses are recoverable from Dfam 3.9 partition 3, whose canonical H5 legitimately lacks `Lookup/ByName`.

This experiment is a claim-ineligible CPU asset audit, not a model benchmark. No R1 full catalog, R2 homology graph/split, GPU S0, S1, or claim is permitted unless this gate completes and later gates independently pass.

## 2. Method under test

`SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1` freezes 279 missing identifiers from Job 11524255 (occurrence mass 6,432,583) and scans all canonical `Families/...` datasets in `dfam39_full.3.h5` by exact, case-sensitive dataset `name` attr. It requires full counts: 321,856 datasets, 321,856 consensus attrs, 321,818 model attrs. Recovery requires a unique versioned accession plus consensus SHA. Prefix/casefold/substring/genome-copy fallback, sampling, clustering, split and model execution are forbidden. Progress is emitted every 10,000 datasets.

Terminal semantics: complete unique recovery permits only a separately reviewed full-catalog stage; complete unresolved results are a valid-negative typed block; input/count/read/conservation failure is failed-run. Partial scan is never a valid negative.

## 3. Result and trend

Job 11525316 ran on `private-teodoro-gpu`, 4 CPU, 48 GiB, 2h limit, 0 GPU. Independent code review was PASS with 0 blockers; 13/13 allocation-side tests passed. The real scan was healthy and I/O-bound: checkpoints at 10k, 20k, 30k; no traceback; RSS about 121 MiB; CPU cumulative about 8 seconds; disk reads continuously increased. The 30k checkpoint occurred after about 1,480 seconds. Linear exhaustive projection: 15,878 seconds (4.41h), beyond the reviewed 2h walltime. The controller cancelled the exact job early at 01:25:01 CEST instead of consuming the entire allocation for a certain TIMEOUT.

Audited terminal: `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`, semantic_success=false, validate_goal=failed_run rc3. Raw runner STATUS remains RUNNING because external SIGTERM interrupted it; a separate audited status/metrics/audit plus 18-entry hash manifest closes this without rewriting raw state. `sacct` is unavailable because slurmdbd refused connection; Slurm stderr records exact cancellation and squeue became empty.

The first 30,000 datasets had 0 exact candidates, but coverage is only 9.321096%. Contract says this is diagnostic telemetry only and cannot support biological or identity claims.

Prior trend: Job 11524255 completed exact-index provenance across 35.6M annotations and resolved 6,447/6,727 identifiers, leaving these 279 missing plus audit-only X13. Earlier Job 11523938 failed because a resolver assumed every H5 partition had `Lookup/ByName`; this R0 intentionally removed that index dependency and did make correct progress.

## 4. Known weaknesses and conflicts

- The H5 is 63,939,647,016 bytes. Contract intentionally does not hash all 64 GB; it pins layout, size, Dfam/FamDB metadata and exact terminal counts.
- Serial h5py small-attribute access is extremely I/O-bound and currently uses little of the 4-CPU allocation.
- A naive walltime extension to 5-6h would likely complete but costs more and preserves inefficient serial access.
- Deterministic disjoint sharding across accession-prefix bins/processes may use available CPU and fit a short allocation, but must avoid concurrent HDF5 corruption, duplicate/omitted datasets, nondeterministic aggregation, and output races. Source is read-only.
- Restart/checkpoint reuse could reduce repeated work, but the current attempt is partial and must not be promoted; any reuse semantics require new implementation/review.
- Active project `ACTIVE_GOAL.json` is an old selector/decoder goal and is not metric-compatible with this route. validate_goal therefore only provides the failed-run stop signal; no SOTA gap/tuning decision is meaningful.

## 5. Comparability contract

This is asset identity, not SOTA comparison. Required fairness dimensions are exact frozen source/layout, exhaustive dataset denominator, exact-case name semantics, input and occurrence conservation, no test-derived genome copy substitutions, no partial-result promotion, and claim-ineligible 0-GPU execution. The latest evaluator contract is SHA `fe0d63e9b525a0bac5ee03b3b88b83385fc4582f8a1b3f9802d171c72594ade2`.

## 6. Abandoned cousins

Do not propose prefix/case/suffix guessing, random/chromosome split, dropping unresolved identifiers, genome-copy-derived representative sequences, or combining resolver repair with homology clustering. Do not restart abandoned local threshold/gap/HMM/CRF fragmentation routes. This review only decides the next R0 validity action.

## 7. This round versus last round

Unlike Job 11523938, this implementation does not call the missing ByName index and successfully traverses `Families` attrs. Unlike Job 11524255, it targets only the 279 unresolved identifiers in partition 3. The new failure is resource sizing/serial traversal shape, not identity semantics, data corruption, or model quality.

## Artifacts

- Result log: `docs/06_results_log.md` section `SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1`
- Audited outputs: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`
- Raw progress: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/preview/attempts/slurm-11525316.tmp/scan_progress.jsonl`
- Config: `configs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.yaml`
- Code: `scripts/experiments/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/recover_p3_identities.py`
- Sbatch: `sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch`

## Required output

### 1. Overall judgment
Choose exactly one: continue-current-route; scale-to-track-b; tune-only-if-near-sota; replace-component; change-backbone; change-objective-or-loss; run-sanity-check-first; comparability-blocker; abandon-route; return-to-literature.

### 2. SOTA gap interpretation
State N/A where appropriate and say whether tuning is meaningful.

### 3. Comparability and benchmark fairness audit
Table: dataset/source version, denominator/exhaustiveness, identity semantics, preprocessing, external assets, resource profile/claim.

### 4. Semantic success and reproducibility audit
Table: metrics/audit parseability, finite values, execution health, partial-result guard, logs/config/manifests, Slurm accounting limitation.

### 5. Architecture/implementation assessment
What does the result imply? Compare at least these repair options: (A) deterministic 4-way read-only disjoint scan with strict union/count/conservation, (B) 5-6h serial rerun, (C) resumable checkpointed serial scan. Name concrete failure guards and whether a small preflight throughput benchmark should precede formal resubmission.

### 6. Track recommendation
State exactly what may run next and what remains forbidden.

### 7. Risks and blockers
List concrete risks, including billing waste.

### 8. Next action
Give one concrete bounded repair experiment, its resource envelope, required code-review tests, and stop rules. Do not authorize R1/R2/GPU/S1.

### 9. Confidence
High/Medium/Low with reason.
