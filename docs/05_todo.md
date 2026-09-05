# TODO / Run Tracker

## 2026-09-05 Human gap A/C bounded preparation

- [x] A independent code review and real8-candidate input smoke: `12398722` COMPLETED0:0,
  engineeringPASS; no head training, full-population coverage or scientific comparison.
- [ ] C container `12398482` prepared in isolated environment; runtime completion pending.
- [x] C mask `12398578` failed on6 candidate-bearing versus9 frozen DEV cores; preserve
  empty cores via originalsplit. Reviewed retry `12398970` COMPLETED0:0 in26s,
  4/4 testsPASS, all9cores60574candidates; output`masks-20260905-r2`.
- [ ] C fixed400050bp M0/MW/MP runtime `12398977`, afterok container+mask dependencies;
  complete-CDS-chain evaluator readiness remains separate.
- [x] C reference-only `12399185` COMPLETED0:0，7/7testsPASS；243 distinct完整CDS链。
  GTF stop-codon convention尚未验证，不执行科学配对评分。
- [ ] No automatic fulltrain/claim/chr19 release. Protocol `experiments/GAP-BRIDGE-A-C-PARALLEL-20260905.md`.

## 2026-08-11 TEFM new-directions bounded cohort

- [ ] Continuation Wave-1 remains stopped before scientific execution: F registry completed; B Job `11522405` failed semantic audit and is being narrowed to an independently reviewed RM+HiTE validity smoke; S0 repair Job `11523252` passed the CSV fix but exposed `DFAM_FAMILY_IDENTITY_UNRESOLVED`. No GPU S0/S1 or further S data submission before result-chain review and an approved leakage-safe identity repair.
- [ ] S order is binding: direct-superfamily S0 must pass leakage-safe acceptance gates before hierarchical/open-set S1 can start.
- [ ] Repair-only S accession roundtrip: Job `11528744` failed safely in 2 seconds before FamDB/RepeatMasker because the runtime guard assumed a `SLURM_TIMELIMIT` text value not exported in the Baobab allocation. `2/3 DEGRADED_REVIEW` and pivot=`sanity_check_first` authorize strict `scontrol` reconciliation, override/anomaly/pre-pointer tests and fresh independent review; only a new PASS gate may allow at most one new job-id retry.
- [ ] Wave-2 after Wave-1 collection: G exact five-anchor provenance rebuild; E 2,200 binding/split/backend/weight freeze; S1 may take the third slot only if S0 passes.
- [x] `FRAG-EVIDENCE-REGISTRY-20260811-R2`: first attempt `11521393` failed before payload in 1 second (`FAILED_ENV`, 0 GPU); bounded environment repair passed incremental review and retry `11521479` completed in 14 seconds as the expected `FOUNDATIONAL_TYPED_BLOCK` asset audit (`1 CPU / 4 GB / 0 GPU`).
- [x] `BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2`: preparation Jobs `11522328`/`11522329`/`11522330` completed; main Job `11522405` produced structurally complete artifacts, but independent result review reclassified RM/EarlGrey/HiTE/EDTA as `INVALID_RUN` and only TEtrimmer as valid foundational block. Audited status=`FAILED_RUN`; no biological benchmark was run.
- [x] `SF-DIRECT-BASELINE-SCREEN-20260811-R2`: CPU DATA Job `11522718` failed before data materialization because Python `csv` retained the 131072-byte default field limit while reading a frozen manifest with a larger field. `STATUS=DATA_FAILED`, semantic false; GPU and S1 remain blocked.
- [x] S0 repair-only CSV iteration: local 2,000,000-character reader, real 495×17 manifest probe, 15/15 tests, independent PASS review, pre-submit/preflight and Job `11523252` completed the intended parser repair.
- [x] Execute the pivot-selected bounded S0 identity-provenance audit without dropping P-state records or weakening the split. Repair-only Job `11524255` completed as a valid-negative `IDENTITY_PROVENANCE_TYPED_BLOCK`: 6,447/6,727 P identifiers uniquely resolve, 279 are missing and 1 is ambiguous; P/excluded occurrence conservation is exact.
- [x] `SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1` Job `11523938` failed-run repair closed: actual 12-partition layout was frozen, absent-vs-corrupt behavior passed independent review, and the one authorized retry `11524255` completed. No third automatic attempt.
- [x] Run 3-way tri-review and pivot for S provenance Job `11524255`. Quorum 3/3 accepts the audit as a valid negative and unanimously blocks S0 DATA/GPU/S1 under the current exact-identity contract.
- [x] S0 identity contract human gate closed: RepeatMasker direct labels remain prediction truth; sequence homology is split-only; 10 label-contract-excluded identifiers remain U/ignore; `X13_LINE` remains audit-only. No prefix/case/copy-derived identity fallback is allowed.
- [x] `SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1` Job `11525316` stopped as `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`: a healthy exact scan reached 30,000/321,856 datasets in ~1,480 s, projecting ~4.41h beyond the reviewed 2h walltime. Partial zero hits are not evidence.
- [x] Job `11525316` result chain closed: `2/3 DEGRADED_REVIEW` and pivot=`sanity check first`. Both successful reviewers require a deterministic 4-way read-only shard preflight; Antigravity failed three CLI compatibility retries.
- [x] `SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1` was stopped before submission. Fresh code review proved its feasible branch mathematically unreachable: audited serial projection `15,878 s / 4 workers = 3,969.5 s`, versus a 900 s ceiling required for 25% headroom in a 20-minute allocation. No Slurm job or throughput measurement was run; two implementation blockers also remain. Static decision: `STATIC_BOUND_INFEASIBLE_DO_NOT_SUBMIT`.
- [x] `SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2` Job `11526687` failed-run in 4 seconds before any H5 dataset enumeration. The login/compute mount namespaces reported different `st_dev` values (42 vs 65) while symlink hash, inode, size, mtime and mode matched. Canonical immutable failure state and validate-goal stop signal are closed; no automatic retry.
- [x] Narrow guard repair passed 34/34 tests and fresh `PASS_WITH_WARNINGS`; final authorized Job `11526905` completed the exhaustive 35-unit scan as a valid-negative `IDENTITY_RECOVERY_TYPED_BLOCK`: 0/279 exact-name recoveries, 6,432,583/6,432,583 occurrence mass remains missing, all denominator/manifests/conservation gates pass. Partition-3 exact-name recovery is closed; no retry or downstream promotion.
- [x] S0 Job `11523252` identity-layer tri-review completed 3/3. Consensus: valid comparability block, no model result; pivot is provenance audit first, not another DATA/GPU submission.
- [x] `BENCH-RM-HITE-VALIDITY-20260811-R1` Job `11523819` tri-review/pivot closed 3/3: retain immutable RM pass; do not rerun the pair.
- [x] Implement, fresh-review and run the one authorized isolated HiTE-only continuation. Job `11524485` completed in 23m04s: exact HiTE 3.3.3, rc0, no timeout, non-empty final GFF and 14,315 canonical adapter rows.
- [x] Complete result tri-review/pivot for Job `11524485`: 3/3 accept the HiTE pass and parent-RM reuse as two-job/two-cell evidence; parent aggregate remains FAILED, no five-cell metric is synthesized, and HiTE retry authorization is exhausted.
- [ ] Human gate for remaining B scope: decide whether to stop at verified RM+HiTE evidence or commission a new isolated contract for exactly one unresolved workflow. No old five-cell rerun, and no automatic Earl Grey/EDTA/TEtrimmer/Pfam submission.
- [x] Wave-1 failed-run tri-review completed 3/3: unanimous `run-sanity-check-first`. Pivot records a repair-only validity iteration as the sole future path, but no rerun is currently authorized.
- [x] Close Job `11528885` result chain: `2/3 DEGRADED_REVIEW`, pivot=`replace-component`; third accession-roundtrip retry forbidden.
- [x] Implement, independently review and run `SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1`. Job `11533175` passed scheduler/gate/23 tests but failed after the in-memory 72-call probe when read-mode cleanup invoked `FamDB.finalize()` and accessed absent `FamDBLeaf.added`; observations were not published, so exact access remains unknown rather than PASS/typed block.
- [x] Implement, independently review and run the one-shot close-only repair `SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1`. Job `11534847` completed with 72/72 exact-once leaf calls, 6/6 frozen accessions resolved, 0 fallback and 12/12 unique HDF5 handles closed; terminal and observation manifests verify.
- [x] Close Job `11534847` post-result tri-review/pivot: `2/3 DEGRADED_REVIEW`, both valid reviewers=`continue-current-route`; only a new exp-scoped, fresh-reviewed CPU leaf-adapter preflight proposal is eligible.
- [x] Implement, independently review and run `SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1`. Job `11535362` completed the same-six-record paired-header syntax contract; 72 exact calls, 6/6 materialized, identical sequence/class semantics and 12/12 handles closed.
- [x] Close Job `11535362` tri-review/pivot: `2/3 DEGRADED_REVIEW`, both valid reviewers=`continue-current-route`; result is a trustworthy six-record syntax component only.
- [ ] Human gate: approve a minimal `$revise-goal` replacement of the stale selector/decoder milestone with the direct-superfamily data-foundation/S0 sequence. Do not implement a representative CPU gate before approval.
- [x] Close Job `11533175` through tri-review and pivot: `2/3 DEGRADED_REVIEW`; both valid reviewers permit exactly one separately reviewed close-only lifecycle repair, pivot=`replace-component`.
- [ ] Implement a new exp-scoped final close-only lifecycle repair: unchanged single 72-call probe, no read-mode `FamDB.finalize()`, explicit HDF5 close, observations staged before cleanup, cleanup-failure/no-upgrade tests, fresh independent gate. Only one exact 1CPU/4GiB/10m/0GPU attempt may follow.
- [x] Close Job `11529694` F failed-run tri-review/pivot: `2/3 DEGRADED_REVIEW`, decision=`run-sanity-check-first`.
- [x] Add shared pre-submit SHA to the F machine reviewed-files closure, obtain fresh independent delta review, and run the one exact-resource retry. Job `11531090` completed as `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`; no further F compute is authorized.
- [x] Close Job `11531090` with independent tri-review and pivot: `2/3 DEGRADED_REVIEW`, both valid reviewers=`abandon-route`; DEC-004 closes standalone consensus-collinearity assembly and all same-evidence cousins. No further F compute.

- [x] `BENCH-5TOOL-SMOKE-20260811-R1` — Job `11519312` completed in `00:15:13`, exit `0:0`, CPU-only/0 GPU. Semantic matrix PASS: 5 terminal cells, 0 invalid; scientific result is negative (`0/5` engineering PASS, four foundational blocks, one version mismatch). Metrics and validation are under `outputs/BENCH-5TOOL-SMOKE-20260811-R1/`; do not claim.
- [x] Collect F/S/G/E asset-gate packages. Jobs `11519717` (F/G, 1 s) and `11519729` (S/E, 2 s) reproduced four `FOUNDATIONAL_TYPED_BLOCK` states with 0 GPU; no scientific screen was submitted.
- [x] Cohort-level `$tri-review` completed with `3/3` quorum; `$pivot` chose comparability audit first and the durable evidence index is published.
- [x] Separate continuation authorization received. Close B exact runtime/database denominator using exp-scoped immutable configuration; do not mutate a shared production database.

> Recreated minimally on 2026-06-29 after this file was found empty. Historical TODOs should be recovered from backups/logs if needed.

## Run tracker

| Date | Run | Jobs | Status | Evidence |
|---|---|---|---|---|
| 2026-08-12 | SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1 | `11533175` | FAILED_RUN_CHAIN_PENDING | Exact 1CPU/4GiB/10m/0GPU; gate and 23/23 tests passed; read-mode finalizer raised after in-memory probe and before result publication; audit manifest verified; no scientific inference or downstream authorization |
| 2026-08-12 | SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1 | `11534847` | COMPLETED_COMPONENT_PASS_CHAIN_CLOSED | Exact 1CPU/4GiB/10m/0GPU; 59/59 tests; 72/72 exact calls, 6/6 resolved, 12/12 handles closed; audited manifests pass; 2/3 degraded tri-review and pivot allow only a new CPU leaf-adapter proposal |
| 2026-08-12 | SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1 | `11535362` | COMPLETED_COMPONENT_PASS_CHAIN_CLOSED | 1CPU/4GiB/10m/0GPU; paired 6-record FASTA syntax pass, identical ordered sequence/class semantics; 2/3 degraded tri-review/pivot continue only to goal-revision human gate and a future representative CPU proposal |
| 2026-08-12 | FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1 final retry | `11531090` | DONE_VALID_NEGATIVE_CHAIN_CLOSED_ROUTE_ABANDONED | Slurm COMPLETED `0:0` in 25 s on exact 8CPU/32GiB/2h/0GPU; all manifests verify; candidate above shuffle but below GAP comparators, mapped fraction `0.5551`, false fusion `0.07586`; `2/3 DEGRADED_REVIEW` unanimously abandons standalone consensus-collinearity assembly; DEC-004 recorded, no F follow-up |
| 2026-08-12 | FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1 | `11529694` | FAILED_REVIEWED_RUNTIME_CLOSURE | Slurm FAILED `1:0` at 0 s on exact 8CPU/32GiB/2h/0GPU; prepayload guard rejected missing reviewed runtime path `scripts/pre_submit_gate.py` before tests, Rice reads or payload. Audited manifest/validate_goal=`failed_run`; no scientific result and no retry authorization |
| 2026-08-12 | SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1 repair retry | `11528885` | FAILED_FAMDB_API_COMPATIBILITY | Slurm FAILED `2:0` in 10 s on exact 1CPU/4GiB/20m/0GPU; strict scheduler guard and 37/37 tests passed, then `FamDBLeaf.added` raised before RepeatMasker. Canonical failed bundle and post-run audit are hash-closed; no geometry result or downstream authorization; automatic retry budget exhausted |
| 2026-08-12 | SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1 | `11528744` | FAILED_RESOURCE_GUARD | Slurm FAILED `2:0` in 2 s on exact 1CPU/4GiB/20m/0GPU allocation; pre-submit and 33/33 tests passed, then the runner rejected the absent/nonmatching `SLURM_TIMELIMIT` representation before reading FamDB or running RepeatMasker; canonical CURRENT unchanged; audited result and validate_goal both `failed_run` |
| 2026-08-12 | SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2 repair retry | `11526905` | DONE_VALID_NEGATIVE_TYPED_BLOCK_CHAIN_CLOSED | Slurm COMPLETED 0:0 in 1:40:52, 4CPU/48GiB/0GPU; 35/35 units and 321,856 unique datasets/objects; 0 exact candidates for 279 targets/6,432,583 occurrences; 3/3 tri-review closes partition-3 exact-name recovery and selects human-gated identity-source replacement; no GPU/S1 |
| 2026-08-12 | SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2 | `11526687` | FAILED_PRE_SCAN_CHAIN_CLOSED | Failed in 4 s before dataset enumeration/checkpoints: mount-namespace `st_dev` mismatch (login 42, compute 65) while symlink hash/inode/size/mtime/mode matched; 2/3 degraded tri-review and pivot allow only narrow identity-guard repair, fresh review, then at most one repair retry |
| 2026-08-12 | SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1 | `11525316` | FAILED_RESOURCE_MISMATCH_CHAIN_CLOSED | Healthy exact scan reached 30,000/321,856 datasets in ~1,480 s; projected 4.41h exceeded reviewed 2h walltime, so controller cancelled early. Audited manifest verifies; 2/3 degraded tri-review and pivot authorize only a shard-throughput sanity preflight |
| 2026-08-12 | BENCH-HITE-ISOLATED-20260811-R1 | `11524485` | DONE_ENGINEERING_PASS_CLAIM_INELIGIBLE | Slurm COMPLETED 0:0 in 23m04s, 4CPU/48GiB/0GPU; HiTE 3.3.3 identity and 1800s minimum rc0; final GFF 1,203,491 bytes; 14,315 canonical adapter rows; parent RM pass reverified by hash, parent aggregate remains FAILED |
| 2026-08-11 | SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1 repair-only retry | `11524255` | DONE_VALID_NEGATIVE_TYPED_BLOCK | Slurm COMPLETED 0:0 in 18m32s, 4CPU/32GiB/0GPU; 35,616,746 records audited; 6,447/6,727 P identifiers uniquely resolved, 279 missing, 1 ambiguous; 43,728 excluded records explicitly retained; no split/train/GPU |
| 2026-08-11 | SF-DIRECT-BASELINE-SCREEN-20260811-R2 CPU DATA | `11522718` | DATA_FAILED | zero-GPU data stage stopped before materialization at Python `_csv.Error: field larger than field limit (131072)`; no training, DATA PASS or scientific metrics |
| 2026-08-11 | SF-DIRECT-BASELINE-SCREEN-20260811-R2 CPU DATA repair retry | `11523252` | DATA_TYPED_BLOCK | CSV repair passed; zero-GPU data stage stopped at unresolved one-to-one Dfam identity for canonical custom/ambiguous RepeatMasker families; no DATA PASS, leakage audit, training or metric |
| 2026-08-11 | SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1 | `11523938` | AUDIT_FAILED | 4CPU/32GiB/0GPU audit stopped at a real Dfam partition-layout assumption (`Lookup/ByName` absent in partition 3); no provenance metrics or scientific output |
| 2026-08-11 | BENCH-RM-HITE-VALIDITY-20260811-R1 | `11523819` | FAILED | RM2+RM+Dfam4 ENGINEERING_PASS with 43 adapter rows; HiTE 3.3.3 identity PASS but minimum run timed out at 600s before GFF; overall semantic false |
| 2026-08-11 | BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2 main | `11522405` | FAILED_SEMANTIC_AUDIT | artifact manifest 778/778 hashes verified, but independent audit found 4 executed runtime/integration failures misclassified as foundational blocks; audited counts INVALID=4, foundational=1 |
| 2026-08-11 | BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2 prep FamDB-v2 | `11522328` | PREPARED | bounded CPU preparation completed and published `famdb-v2/manifest.json`; legacy FamDB remains provenance-limited |
| 2026-08-11 | BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2 prep HiTE | `11522329` | PREPARED | exact HiTE 3.3.3 SIF/help/inspect/manifest atomically published; 0 GPU |
| 2026-08-11 | BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2 prep EDTA | `11522330` | PREPARED | exact EDTA v2.3.0 source tree and manifest atomically published; 0 GPU |
| 2026-08-11 | FRAG-EVIDENCE-REGISTRY-20260811-R2 | `11521393` | FAILED_ENV_PRE_PAYLOAD | Slurm `FAILED`, exit `1:0`, elapsed 1 s, 0 GPU; conda MKL activation failed under `set -u`; no builder/research payload executed, one bounded repair allowed |
| 2026-08-11 | FRAG-EVIDENCE-REGISTRY-20260811-R2 retry | `11521479` | DONE_FOUNDATIONAL_TYPED_BLOCK | Slurm `COMPLETED`, exit `0:0`, elapsed 14 s, 1 CPU/4 GB/0 GPU; integrity audit passed 6/6 and retained accepted-postprocessor/scientific-lattice typed blockers |
| 2026-08-11 | BENCH-5TOOL-SMOKE-20260811-R1 | `11519312` | DONE_VALID_NEGATIVE | Slurm `COMPLETED` in 913 s, 0 GPU; `outputs/BENCH-5TOOL-SMOKE-20260811-R1/metrics.json` and `semantic_validation.json`; 0/5 engineering pass, 4 typed blocks, 1 version mismatch, 0 invalid |
| 2026-08-11 | F/G asset-gate reconstruction | `11519717` | DONE_FOUNDATIONAL_TYPED_BLOCK | `COMPLETED` in 1 s, 1 CPU/1 GB, 0 GPU; F lacks A0/A4/A5, G lacks 5/5 anchor run records |
| 2026-08-11 | S/E asset-gate reconstruction | `11519729` | DONE_FOUNDATIONAL_TYPED_BLOCK | `COMPLETED` in 2 s, 1 CPU/1 GB, 0 GPU; S lacks ontology/homology/clade split, E lacks bindings/weights/backend pins |
| 2026-08-11 | FRAG-PARENT-LATTICE-SCREEN-20260811-R1 | `11519717` | DONE_FOUNDATIONAL_TYPED_BLOCK | Shared F/G allocation; deterministic A0/A4/A5 asset gate only, no scientific screen |
| 2026-08-11 | DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1 | `11519717` | DONE_FOUNDATIONAL_TYPED_BLOCK | Shared F/G allocation; five anchor run records absent, no scientific screen |
| 2026-08-11 | SF-HIER-OPENSET-SCREEN-20260811-R1 | `11519729` | DONE_FOUNDATIONAL_TYPED_BLOCK | Shared S/E allocation; ontology/homology/clade split absent, no scientific screen |
| 2026-08-11 | EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1 | `11519729` | DONE_FOUNDATIONAL_TYPED_BLOCK | Shared S/E allocation; exact bindings/split/backend/weights absent, no scientific screen |
| 2026-06-29 | PIPE-TEFM-FINAL-20260623 NTv3 train recovery | `9839610`, `9839611` | DONE | 30/30 `software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv3_*_H0_w*_seed42/test_results.json` |
| 2026-06-29 | PIPE-TEFM-FINAL-20260623 NTv3 eval first attempt | `9844255`, `9844256` | FAILED_SUPERSEDED | rotary cache state-dict load failure; see docs/21 |
| 2026-06-29 | PIPE-TEFM-FINAL-20260623 NTv3 eval retry | `9845158`, `9845159` | DONE | 330/330 JSONs under `reports/tefm_final/PIPE-TEFM-FINAL-20260623/matrix_eval/ntv3_*` |
| 2026-06-29 | PIPE-TEFM-FINAL-20260623 summarize | local summary command | DONE | `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv` |
| 2026-06-29 | PIPE-TEFM-FINAL-EBAR-20260629 chromosome-repeat prep | `9849317` | DONE | 66/66 metadata jobs; outputs under `software_outputs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/data` |
| 2026-06-29 | PIPE-TEFM-FINAL-EBAR-20260629 chromosome-repeat eval | `9849318` | DONE | 66/66 JSONs; summaries under `reports/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/summaries/` |
| 2026-06-29 | PIPE-TEFM-FINAL-STRICTSEG-20260629 promoted strict segment | `9849319`, retry `9850150`, retry2 `9852364` | DONE_AFTER_REPAIR | 66/66 JSONs, 6600 strict rows; summaries under `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/` |
| 2026-06-30 | PIPE-TEFM-FINAL-SELECTOR-20260630 multi-anchor selector synthesis | local | DONE | `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/FINAL_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-INTERPRET-20260630 short-fragment interpretability screen | local | DONE | `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/INTERPRETABILITY_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-INTERPRET-20260630 independent tri-review | local CLI | DONE | 3/3 quorum; `docs/07_tri_review.md#tri-review-pipe-tefm-final-interpret-20260630` |
| 2026-06-30 | PIPE-TEFM-FINAL-INTERPRET-20260630 matched controls/k-mer/PDF extraction | local | DONE | `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/MATCHED_CONTROL_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-INTERPRET-20260630 occlusion smoke | `9853263`/`9853287` cancelled, `9853298` DONE | DONE_AFTER_REPAIR | `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/OCCLUSION_SMOKE_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-GENOMEDECAY-20260630 genome-derived selector + fragment council | local + CLI council | DONE | `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/GENOME_DECAY_REPORT.md`; `FRAGMENT_COUNCIL_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-FRAGSANITY-20260630 bounded mouse chr1 forward/RC/oracle sanity | `9856508` DONE; full `9856510` CANCELLED_NOT_EVIDENCE | DONE_BOUNDED | `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/FRAGMENT_SANITY_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-FINAL-INTERVALREFINER-20260630 frozen bp interval refiner smoke | 120-window attempts `9856920`/`9856939`/`9856942` cancelled before evidence; 40-window `9856944` DONE | DONE_BOUNDED_WEAK | `reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/INTERVAL_REFINER_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-NEXT-DECAY-FRAG-20260630 selector calibration + trainable decoder smoke | selector local; decoder `9858072` DONE | DONE_BOUNDED_WEAK | `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/FINAL_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-STRUCTDEC-20260630 joint backbone structured decoder smoke | first `9860192` FAILED_ENV, retry `9860193` DONE | DONE_BOUNDED_SIGNAL | `reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/JOINT_STRUCTURED_DECODER_REPORT.md` |
| 2026-06-30 | PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630 conservative selector router + boundary/retention decoder | selector local DONE; decoder `9860400` DONE | DONE_BOUNDED_MIXED | Selector router gate passed as top-2/local-probe + leave-clade abstention; decoder promotion gate failed due missed_true_rate rise. Reports under `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/` and `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/` |
| 2026-06-30 | PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630 selector MinHash + interval-survival decoder | selector local DONE; decoder `9861062` DONE | DONE_GUARDRAIL_FAIL | Selector remains conservative router-only; MinHash helps leave-clade risk but not point formula. Decoder primary gates pass (`segment +0.0687`, `boundary +0.0391`, `missed_true +0.0287`), but `deleted_true_backed_fraction=0.4592` fails guardrail. Metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/pursue_combined_metrics.json` |
| 2026-06-30 | PIPE-TEFM-PURSUE-RETCONSTR-20260630 final retention-constrained decoder screen | first 80GB submit rejected pre-job; 3090 job `9862135` DONE | DONE_METHOD_FAIL_STOP | Final decoder-only attempt completed on 24GB 3090. Retention reduced missed_true_rate but failed segment/boundary and still exceeded true-backed deletion guardrail. Metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/pursue_combined_metrics.json` |
| 2026-07-01 | PIPE-TEFM-CAP-FRAGARCH-20260701 interval-aware fragmentation architecture screen | first report job `9864888` DONE; corrected reference rerun `9865070` DONE; tri-review/pivot DONE | DONE_METHOD_FAIL_REPLACE_COMPONENT | Two new interval heads on frozen GENERanno 4096 completed. No candidate passed strict promotion gate. Pivot: stop tested heads; allow at most one second bounded round with a new fragment graph/linking or boundary-conditioned span module. Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_metrics.tsv`; status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_status.json` |
| 2026-07-01 | PIPE-TEFM-CAP-FRAGGRAPH-20260701 fragment graph linker screen | `9866570` DONE | DONE_METHOD_FAIL_STOP | Graph linker Round 2 completed and passed 3/3 tri-review/pivot closeout. `keepall` preserves CE raw but equals CE metrics; `keepdrop` improves human interval metrics but fails true-backed deletion guardrail and mouse smoothing comparator. Pivot: abandon current fragmentation capability branch as future work; DEC-002 recorded. Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_metrics.tsv`; status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_status.json` |
| 2026-07-01 | PIPE-TEFM-CAP-POSTPROC-20260701 multi-threshold/length-adaptive postprocess diagnostic | `9880686` DONE | DONE_DIAGNOSTIC_ONLY | User-requested threshold harshness and short-vs-long fragment audit completed. Human strict-safe best is lower raw threshold `raw_t0.20`; mouse strict-safe best is `gap25_min40_t0.50`; best observed HMM/length-adaptive rows fail true-backed deletion guardrails. Use as tradeoff/sensitivity figure only, not as a promoted recipe. Report: `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/POSTPROCESS_THRESHOLD_REPORT.md` |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 EarlGrey tail + R2 benchmark rechain | EarlGrey tail `9840108_4/5/7/8`, beetle repair `9854664_6` DONE; R2 chain `9854670` -> `9854671`, `9854672` -> `9854673`; P27 array throttle raised to `%20` | RUNNING/PENDING | R2 chain in `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/rechain_jobs_20260630.tsv`; waits on opossum/pig/honeybee/x_laevis EarlGrey and P27 Dfam fix `9843979`; as of 2026-06-30 20:14 CEST base is 28/32 DONE, Dfam-overlay is 14 DONE / 13 running / 5 missing, base UCSC compare `9854671` and Dfam UCSC compare `9854673` are submitted but still pending on normal unmet dependencies; no new failed/dependency-broken jobs observed except the already-superseded `9840108_6`; active logs show pig EarlGrey 44%, honeybee 59%, X. laevis 70%, opossum EarlGrey remains in post-batch `ProcessRepeats`, and Dfam overlay batch counters are still advancing; no standardized de novo UCSC compare outputs exist yet; root-level `RM_*` directories are not present under project root, and historical `RM_*` scratch has been quarantined under `repeatmasker_dfam/99_internal/rm_scratch_quarantine_20260619/` |
| 2026-06-30 | SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V3 | local `srun` job `9854803` | DONE | `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V3/`; 24 paired entries; high=7, moderate=2, low=5, severe=10; `summary.tsv` byte-identical to `V2` |
| 2026-06-30 | SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V4 | `srun -p public-short-cpu` rerun after default partition time-limit retries | DONE | `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V4/`; 24 paired entries; high=7, moderate=2, low=5, severe=10; `summary.tsv` sha256 `c030a6e165bafa963ea22b23b4034cc2e2c6fa14db57ac517cc0412858064b05` and `qc_flags.tsv` sha256 `9073736e137971f5535838470d098b98df9005061d09f81c6afdbab6e0a8fef3`, both byte-identical to `V3` |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + Slurm `squeue`/`sacct` | RUNNING/PENDING | As of 2026-06-30 20:32 CEST, base de novo remains 28/32 DONE with opossum/pig/western_honey_bee/x_laevis EarlGrey still running; Dfam overlay advanced to 15/32 DONE after `dfam_augmented/pig/repeatmodeler` completed, with 12 running and 5 EarlGrey-overlay items intentionally missing until R2 array `9854672` is released. Base and Dfam UCSC compare directories remain empty because compare jobs `9854671` and `9854673` are still waiting on normal dependencies. No new failed/dependency-broken jobs observed; old `9840108_6` remains superseded. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 incremental UCSC compare | `srun -p public-short-cpu -c 4` on completed rows only | DONE_PARTIAL_NOT_FINAL | Temporary outputs: `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/ucsc_compare_incremental_20260630_2038/` for 28 completed base de novo rows and `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/dfam_augmented/ucsc_compare_incremental_20260630_2038/` for 15 completed Dfam-overlay rows. Base mean Jaccard by tool: repeatmodeler 0.4064, earlgrey 0.3865 over 4 available rows, repeatscout 0.3591, edta 0.3303. Dfam-overlay completed subset: cattle/pig repeatmodeler_plus_dfam reached high concordance (Jaccard 0.8041/0.8004); beetle/honeybee remain severe. This is an incremental trend check only; final evidence must come from full `9854671` and `9854673` reports after all dependencies finish. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + Slurm `squeue`/`scontrol`/`sacct` | RUNNING/PENDING | As of 2026-06-30 20:47 CEST, base remains 28/32 DONE and Dfam overlay remains 15/32 DONE. Full compare outputs are still empty because `9854670` waits on EarlGrey tail `9840108_4/5/7/8`, `9854671` waits on `9854670`, `9854672` waits on `9854670` plus `9843979_*`, and `9854673` waits on `9854672_*`. Active EarlGrey logs show pig 45% ETA ~17.5h, western_honey_bee 61% ETA ~15.4h, and X. laevis 71% ETA ~9.5h; opossum remains in `ProcessRepeats` with stale log but Slurm state RUNNING. EarlGrey jobs have TimeLimit 3-12:00:00 and Dfam overlay jobs have TimeLimit 2-12:00:00, so no immediate walltime intervention is needed. No new failed jobs were observed beyond superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | six 5-min local monitor refreshes from 20:49 to 21:14 CEST | RUNNING/PENDING | State remained stable across all six refreshes: base 28/32 DONE, Dfam overlay 15/32 DONE, full base/Dfam compare file counts 0/0. Slurm chain remains pending on normal dependencies (`9854670` after `9840108_4/5/7/8`; `9854671` after `9854670`; `9854672` after `9854670` and `9843979_*`; `9854673` after `9854672_*`). No new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared; `9840108_6` remains the only old superseded failure. Pig EarlGrey progressed to 46% with ETA ~17.5h; western_honey_bee stayed at 61%; X. laevis stayed at 71%; opossum EarlGrey and several Dfam overlays remain in `ProcessRepeats`. No safe duplicate submission or cleanup action is appropriate while these jobs are active. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + Slurm/resource checks through 21:27 CEST | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay 15/32 DONE; full compare directories remain empty. Active EarlGrey progress improved to pig 47%, western_honey_bee 62%, and X. laevis 73%, while opossum remains in `ProcessRepeats` with stale log but RUNNING Slurm state. Dfam overlay batch counters continue to advance for cattle/horse/lizard/opossum/pig/X. laevis, with several final-batch jobs also in `ProcessRepeats`. `scontrol` confirms no walltime pressure yet (EarlGrey TimeLimit 3-12:00:00; Dfam overlay TimeLimit 2-12:00:00), and no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond superseded `9840108_6`. The R2 dependency chain is still valid and should be allowed to continue. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + three 5-min follow-up refreshes through 21:38 CEST | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full base/Dfam compare file counts remain 0/0. Active EarlGrey progress is pig 48%, western_honey_bee 63%, X. laevis 73%, and opossum still in `ProcessRepeats`. Dfam overlay counters continue to advance, but no additional DONE markers appeared. Slurm dependency chain remains valid: `9854670` waits on `9840108_4/5/7/8`, `9854671` waits on `9854670`, `9854672` waits on `9854670` plus `9843979_*`, and `9854673` waits on `9854672_*`. No new FAILED/TIMEOUT/OOM/NODE_FAIL jobs observed; only old superseded `9840108_6` appears in `sacct`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + three 5-min follow-up refreshes through 21:50 CEST | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full compare file counts remain 0/0. Active EarlGrey progress at the latest detailed refresh: pig 48%, western_honey_bee 63%, X. laevis 74%, opossum still in `ProcessRepeats`. Dfam overlay batch counters continue to advance for cattle/horse/lizard/opossum/pig/X. laevis, but no new DONE marker appeared. `9854670/9854671/9854672/9854673` remain pending on normal dependencies; no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs were observed beyond the old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local monitor + two 5-min follow-up refreshes through 21:56 CEST | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full compare file counts remain 0/0. Active EarlGrey logs are still moving for pig/western_honey_bee/X. laevis, with latest detailed progress pig 49%, western_honey_bee 64%, X. laevis 74%; opossum remains in `ProcessRepeats` with stale runner log but active Slurm state. Dfam overlay counters continue to advance. `9854670/9854671/9854672/9854673` remain pending on normal dependencies, and no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs were observed beyond superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh at 21:58 CEST | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full compare file counts remain 0/0. Active EarlGrey progress: pig 49%, western_honey_bee 64%, X. laevis 75%, opossum still in `ProcessRepeats`. Dfam overlay batch counters continue to advance. `9854670/9854671/9854672/9854673` remain pending on normal dependencies, and no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs were observed beyond superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh at 21:58 CEST, rerun after context recovery | RUNNING/PENDING | Base remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full compare file counts remain 0/0. Active EarlGrey progress remains pig 49%, western_honey_bee 64%, X. laevis 75%, opossum in `ProcessRepeats`. Dfam overlay batch counters continue advancing (e.g. cattle/edta 37127/47033, horse/repeatscout 33301/43479, opossum/edta 50561/62171, x_laevis/repeatscout 26623/46764). R2 dependency chain is unchanged and valid; no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond superseded `9840108_6`. |
| 2026-06-30 | SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V5_2 | `srun -p public-short-cpu -c 4 --mem=16G` rerun from current ready-by-design pair manifest | DONE | `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260630_V5_2/`; 24 paired entries; high=7, moderate=2, low=5, severe=10; missing strict comparators remain `setaria_italica`, `tomato`, `wild_rice`, `arabidopsis_lyrata`, `grape`, `green_foxtail`; `summary.tsv` sha256 `c030a6e165bafa963ea22b23b4034cc2e2c6fa14db57ac517cc0412858064b05` and `qc_flags.tsv` sha256 `9073736e137971f5535838470d098b98df9005061d09f81c6afdbab6e0a8fef3`, both byte-identical to `V4`. |
| 2026-07-01 | SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE | local single-process rerun from current ready-by-design manifest after 4-worker process pool was killed | DONE | `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE/`; 24 paired entries; high=7, moderate=2, low=5, severe=10; missing strict comparators remain `setaria_italica`, `tomato`, `wild_rice`, `arabidopsis_lyrata`, `grape`, `green_foxtail`; `summary.tsv` and `qc_flags.tsv` hashes are byte-identical to `20260630_V5_2`. `02_ready_by_design` has 803 symlinks and 0 broken links; root-level `RM_*` directories are absent, while quarantined scratch `RM_*` directories under `99_internal/rm_scratch_quarantine_20260619/` are cleanup-safe after active jobs finish if no forensics are needed. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh after Label-A/UCSC rerun | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full base/Dfam compare file counts remain 0/0. Active EarlGrey progress: pig 50%, western_honey_bee 64%, X. laevis 75%, opossum still in `ProcessRepeats`. Dfam overlay counters continue advancing. `9854670/9854671/9854672/9854673` remain pending on normal dependencies, and no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | two local refreshes from 22:08 to 22:13 CEST | RUNNING/PENDING | State remained stable over the 5-minute check: base de novo 28/32 DONE, Dfam overlay 15/32 DONE, and full base/Dfam compare file counts 0/0. The dependency chain remains valid (`9854670` waits on EarlGrey tail `9840108_4/5/7/8`; `9854671` waits on `9854670`; `9854672` waits on `9854670` plus `9843979_*`; `9854673` waits on `9854672_*`). All active jobs are `RUNNING Reason=None` or normal `PENDING (Dependency)`; no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh plus resource/activity check through 22:20 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; full compare directories still have 0 files. Active base EarlGrey progress: pig 50%, western_honey_bee 65%, X. laevis 76%, opossum still in `ProcessRepeats`. Dfam overlay counters continue advancing (e.g. cattle/edta 37523/47033, horse/repeatscout 33683/43479, opossum/edta 51958/62171, x_laevis/repeatscout 27369/46764). `sstat` shows active CPU/RSS for the running batch steps, so no duplicate submission is warranted. `9854670/9854671/9854672/9854673` remain pending on valid dependencies; no new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:21 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam compare directories still have 0 files. Active base EarlGrey rows remain opossum, pig, western_honey_bee, and x_laevis; progress is pig 50%, western_honey_bee 65%, X. laevis 76%, and opossum in `ProcessRepeats`. Several running status/runner files continue growing, and Slurm shows the active jobs as `RUNNING` with normal dependency waits for `9854670/9854671/9854672/9854673`. No new terminal failure was observed beyond superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:23 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam compare directories still have 0 files. Active base EarlGrey rows are unchanged: opossum in `ProcessRepeats`, pig 50%, western_honey_bee 65%, and X. laevis 76%. Dfam overlay counters continue moving slowly, and runner/status file sizes increased for several running rows, so the jobs still show activity. `9854670/9854671/9854672/9854673` remain in valid dependency wait; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:24 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam compare directories still have 0 files. Active base EarlGrey progress: opossum remains in `ProcessRepeats`, pig advanced to 51%, western_honey_bee remains 65%, and X. laevis remains 76%. Dfam overlay counters and runner/status files continue to advance. Slurm dependency chain remains valid (`9854670` waiting on `9840108_4/5/7/8`, then compare/overlay jobs downstream); no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:25 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam compare directories still have 0 files. Active base EarlGrey rows remain opossum (`ProcessRepeats`), pig 51%, western_honey_bee 65%, and X. laevis 76%. Dfam overlay rows continue slow progress (e.g. cattle/edta 37591/47033, horse/repeatscout 33782/43479, opossum/edta 52289/62171, x_laevis/repeatscout 27533/46764). Slurm shows `9854670/9854671/9854672/9854673` still waiting on valid dependencies; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:26 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey progress is unchanged at opossum `ProcessRepeats`, pig 51%, western_honey_bee 65%, and X. laevis 76%. Dfam overlay counters continue advancing (e.g. cattle/edta 37604/47033, horse/repeatscout 33804/43479, opossum/edta 52371/62171, x_laevis/repeatscout 27583/46764). Slurm dependency chain remains valid; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:28 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey progress is opossum `ProcessRepeats`, pig 51%, western_honey_bee 65%, and X. laevis 76%. Dfam overlay counters continue advancing (e.g. cattle/edta 37636/47033, horse/repeatscout 33831/43479, opossum/edta 52461/62171, x_laevis/repeatscout 27631/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:29 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey progress remains opossum `ProcessRepeats`, pig 51%, western_honey_bee 65%, and X. laevis 76%. Dfam overlay counters continue advancing (e.g. cattle/edta 37666/47033, horse/repeatscout 33851/43479, opossum/edta 52557/62171, x_laevis/repeatscout 27682/46764). Slurm dependency chain is still valid; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:30 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey progress: opossum remains in `ProcessRepeats`, pig remains 51%, western_honey_bee advanced to 66%, and X. laevis advanced to 77%. Dfam overlay counters continue advancing (e.g. cattle/edta 37700/47033, horse/repeatscout 33877/43479, opossum/edta 52648/62171, x_laevis/repeatscout 27733/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 22:32 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey progress remains opossum `ProcessRepeats`, pig 51%, western_honey_bee 66%, and X. laevis 77%. Dfam overlay counters continue advancing (e.g. cattle/edta 37722/47033, horse/repeatscout 33904/43479, opossum/edta 52731/62171, x_laevis/repeatscout 27776/46764). Slurm dependency chain is valid; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | local refresh plus 5-minute follow-up through 22:39 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey rows remain opossum `ProcessRepeats`, pig 51%, western_honey_bee 66%, and X. laevis 77%, with ETA continuing to decrease. Dfam overlay counters continue advancing (e.g. cattle/edta 37881/47033, horse/repeatscout 34010/43479, opossum/edta 53177/62171, x_laevis/repeatscout 28035/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | local refresh through 22:40 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final compare directories remain empty. Active base EarlGrey rows remain opossum `ProcessRepeats`, pig 51%, western_honey_bee 66%, and X. laevis 77%. Dfam overlay counters continue advancing after the previous window (e.g. cattle/edta status file and opossum/edta status file grew; x_laevis/repeatscout output advanced to 28089/46764 in the monitor). Slurm dependency chain remains valid with `9854670` still waiting on `9840108_4/5/7/8`; no new terminal failures appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh at 23:08 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts are still 0/0 because `9854670/9854671/9854672/9854673` remain on valid dependency waits. Active base EarlGrey progress advanced to opossum `ProcessRepeats`, pig 53%, western_honey_bee 67%, and X. laevis 78%. Dfam overlay counters continue advancing (e.g. cattle/edta 38497/47033, horse/repeatscout 34544/43479, opossum/edta 55120/62171, x_laevis/repeatscout 29185/46764). No new FAILED/TIMEOUT/OOM/NODE_FAIL jobs appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | five 1-minute refreshes through 23:14 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active base EarlGrey rows are still opossum `ProcessRepeats`, pig 53%, western_honey_bee 67%, and X. laevis 79%, with runner logs continuing to update for pig, western_honey_bee, and X. laevis. `9854670/9854671/9854672/9854673` remain valid dependency waits behind running EarlGrey/Dfam tail jobs; no new terminal failure was observed beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | local refresh plus three 1-minute follow-ups through 23:18 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Opossum EarlGrey log wrote again at 23:15, so the final `ProcessRepeats` stage is still active rather than stale; active base EarlGrey rows remain opossum `batch 62170/62171`, pig 53%, western_honey_bee 67%, and X. laevis 79%. Dfam overlay counters continue advancing during the follow-up window (e.g. cattle/edta 38679→38724/47033, horse/repeatscout 34689→34742/43479, opossum/edta 55654→55800/62171, x_laevis/repeatscout 29454→29520/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failure appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | local refresh plus three 1-minute follow-ups through 23:21 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active EarlGrey progress moved during this window: pig advanced to 54%, western_honey_bee advanced to 68%, X. laevis remains 79%, and opossum remains in the final `batch 62170/62171`/`ProcessRepeats` stage with recent log activity. Dfam overlay counters continue advancing (e.g. cattle/edta 38770→38814/47033, lizard/repeatscout 28869→28912/31474, opossum/edta 55906→56042/62171, x_laevis/repeatscout 29580→29664/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits, with no new FAILED/TIMEOUT/OOM/NODE_FAIL beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 sustained monitor | local refresh plus follow-up through 23:24 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active base EarlGrey rows are opossum final `batch 62170/62171`, pig 54%, western_honey_bee 68%, and X. laevis 79%, with pig/western_honey_bee/X. laevis logs continuing to update and ETA decreasing. Dfam overlay counters continue advancing (e.g. cattle/edta 38849→38886/47033, lizard/repeatscout 28935→28951/31474, opossum/edta 56119→56206/62171, x_laevis/repeatscout 29725→29772/46764). `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failure appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 23:25 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active base EarlGrey rows remain opossum final `batch 62170/62171`, pig 54%, western_honey_bee 68%, and X. laevis 79%. Dfam overlay counters continue advancing (e.g. cattle/edta 38913/47033, lizard/repeatscout 28979/31474, opossum/edta 56288/62171, x_laevis/repeatscout 29810/46764), and recent logs were written at 23:25 for multiple running rows. `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failure appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 23:26 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active base EarlGrey rows remain opossum final `batch 62170/62171`, pig 54%, western_honey_bee 68%, and X. laevis 79%. Dfam overlay counters continue advancing (e.g. cattle/edta 38934/47033, lizard/repeatscout 29003/31474, opossum/edta 56364/62171, x_laevis/repeatscout 29845/46764), and logs were written at 23:26 for pig/honeybee/X. laevis EarlGrey plus multiple Dfam rows. `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failure appeared beyond old superseded `9840108_6`. |
| 2026-06-30 | DENOVO_B_ANIMAL_EVAL_20260620 monitor refresh | local refresh around 23:27 CEST | RUNNING/PENDING | Base de novo remains 28/32 DONE and Dfam overlay remains 15/32 DONE; final base/Dfam UCSC compare file counts remain 0/0. Active base EarlGrey rows remain opossum final `batch 62170/62171`, pig 54%, western_honey_bee 68%, and X. laevis 79%. Dfam overlay counters continue advancing (e.g. cattle/edta 38968/47033, lizard/repeatscout 29020/31474, opossum/edta 56433/62171, x_laevis/repeatscout 29887/46764), with recent log writes at 23:27 for running EarlGrey and Dfam rows. `9854670/9854671/9854672/9854673` remain valid dependency waits; no new terminal failure appeared beyond old superseded `9840108_6`. |

## Pending integration queue

- [ ] `tefm-copy-aware-mechanism-portfolio-20260812` (2026-08-12): five orthogonal, untried mechanisms beyond abandoned local postprocessing—copy-consensus boundary voting, multi-evidence partial labels, counterfactual direct-SF invariance, evolutionary-state decay, and CopyGraph-SSL. First close the current S0 identity/homology data gate; only then select bounded CPU falsification, and do not open GPU mechanisms before their route-specific gates. [wiki/ideas/tefm-copy-aware-mechanism-portfolio-20260812.md]

- [x] Run `$tri-review` on `PIPE-TEFM-FINAL-20260623` final matrix before promoting any backbone/window to error-bar repeats. Completed 2026-06-29 with 3/3 reviewer quorum.
- [x] Decide error-bar repeat candidates. Pivot decision: minimal primary set is `ntv2_250m@4096` for human/animal and `ntv3_100m_pre@2048` for plant; `ntv2_250m@2048` is optional stability/shared-anchor check if resources allow.
- [x] Implement and run `PIPE-TEFM-FINAL-EBAR-20260629`: chromosome-repeat error bars for `ntv2_250m@4096` and `ntv3_100m_pre@2048`, based on different chromosomes rather than extra seeds. Completed jobs `9849317` -> `9849318`.
- [x] Implement and run `PIPE-TEFM-FINAL-STRICTSEG-20260629`: strict segment/boundary/fragmentation evaluation for promoted candidates, with multi-threshold IoU and tighter boundary thresholds. Completed after NTv3 max-length retry `9850150` and NTv2 token-to-bp retry2 `9852364`.
- [x] Implement and run `PIPE-TEFM-FINAL-PLANTQC-20260629`: plant label/source concordance audit for the plant candidate panel before interpreting low absolute plant TE-F1 as model failure. Output: `reports/tefm_final/PIPE-TEFM-FINAL-PLANTQC-20260629/plant_label_qc.tsv`.
- [x] Feed validated candidate(s) into multi-anchor and deployable decay-selector follow-up as a screen-level synthesis. Output: `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/`.
- [x] Run initial short high-confidence TE fragment / model interpretability screen from existing SF5 and fragment artifacts. Output: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/`.
- [x] Run independent tri-review for `PIPE-TEFM-FINAL-INTERPRET-20260630`. Consensus: `run-sanity-check-first`.
- [x] Complete matched strict-BG controls, matched human known-main4 controls, k-mer enrichment, and PDF keyword-level method extraction for `PIPE-TEFM-FINAL-INTERPRET-20260630`.
- [x] Complete bounded model-level occlusion smoke for `PIPE-TEFM-FINAL-INTERPRET-20260630` after runtime repair. Output: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/OCCLUSION_SMOKE_REPORT.md`.
- [x] Complete genome-derived selector screen and fragment council. Output: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/`.
- [x] Selector bounded MinHash-equivalent upgrade: deterministic bottom-k genome sketches were computed because `mash`/`sourmash` were unavailable. Result: leave-clade risk metrics improve but selector remains conservative-router-only, not claim-grade formula. Output: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/`.
- [x] Fragment sanity: run forward-only, reverse-complement flipped-only, mean-logit, max-logit, and consensus/min-logit inference on bounded animal `ntv2_250m@4096` mouse chr1 screen. Output: `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/`.
- [x] Fragment upper-bound screen: compute oracle same-true interval repair on bounded mouse chr1. Oracle fill reached segment-F1/boundary-F1 `0.9711`.
- [x] Fragment component prototype: fit a deployable frozen bp model + lightweight interval refiner with missed_true_rate, pred_true_backed_rate, short_true_backed_rate, and deleted true-backed vs false-positive guardrails. Completed as bounded 40-window smoke; result is weak and does not support scaling this exact post-hoc refiner.
- [x] Selector usability follow-up: point-estimate formula remains not usable as a new-species confidence score; conservative top-2/local-probe policy is screen-usable within known clades only. Output: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_action_policy/selector_confidence_cards.tsv`.
- [x] Trainable frozen-logit decoder smoke: boundary CNN, linear CRF, and duration-prior variants failed to beat post-hoc CRF on the 40-window strict mouse chr1 screen. Do not scale this exact probability-track decoder.
- [x] Joint structured backend smoke: HMM/CRF/semi-Markov proxy losses attached during GENERanno fine-tuning have now been tested with seed 42. Result shows signal but is not solved: semi-Markov proxy test segment-F1 `0.4258` vs CE baseline `0.3069`, but missed_true_rate rises to `0.3033`.
- [ ] Selector limitation write-up: after two bounded rounds, treat formula direction as triage-only. Manuscript language should say known/in-panel top-2 shortlist plus local chromosome probe; leave-clade/new-clade abstain and require local probe/new anchor.
- [x] Boundary/true-retention joint structured screen executed as `PIPE-TEFM-PURSUE-STRUCTDEC-20260630`. Segment-F1 and boundary-F1 improved, but missed_true_rate rose from `0.2623` to `0.3525`; do not scale this variant.
- [x] Interval-level true-retention / segment-aware decoder bounded screen executed as `PIPE-TEFM-PURSUE-INTERVALSURV-20260630`. Primary segment/boundary/missed_true gates passed, but true-backed deletion guardrail failed (`0.4592` vs allowed `0.15`).
- [x] Run `$tri-review` and `$pivot` for `PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630`. Decision: selector limitation plus exactly one final decoder-only retention-constrained screen.
- [x] Run final decoder-only `PIPE-TEFM-PURSUE-RETCONSTR-20260630`. Result: method failure; stop decoder direction for this milestone.
- [x] Final closeout tri-review/pivot for `PIPE-TEFM-PURSUE-RETCONSTR-20260630`. Decision: stop decoder as future work, record `DEC-001`, carry selector as router-only.
- [x] Capability-pursue Round 1: run `PIPE-TEFM-CAP-FRAGARCH-20260701` boundary/proposal and anchor-free interval heads. Result: method failure.
- [x] Run `$tri-review` for `PIPE-TEFM-CAP-FRAGARCH-20260701`. Quorum 3/3; consensus stop current heads.
- [x] Run `$pivot` for `PIPE-TEFM-CAP-FRAGARCH-20260701`. Decision: replace component; at most one second bounded round with fragment graph/linking or boundary-conditioned span refinement.
- [x] Implement and run bounded Round-2 component `PIPE-TEFM-CAP-FRAGGRAPH-20260701`: fragment graph linker as primary.
- [x] Run `$tri-review` for `PIPE-TEFM-CAP-FRAGGRAPH-20260701`. Quorum 3/3; consensus abandon-route.
- [x] Run `$pivot` for `PIPE-TEFM-CAP-FRAGGRAPH-20260701`. Decision: stop current capability branch as future work; no final boundary-conditioned span-refiner round.
- [x] Record `DEC-002` for frozen/post-hoc interval reconstruction modules so this branch is not restarted without a substantially new end-to-end/global interval mechanism.
- [ ] Optimize full-chromosome fragment sanity metric loop before rerunning 1200-window/full-panel RC/oracle screens; cancelled job `9856510` is not evidence.
- [ ] Run claim-grade selector validation/tri-review only after final panel and external baseline contracts are locked.
- [ ] If interpretability becomes figure-level, repeat occlusion/saliency with full-window context, alternate perturbation baselines, better GC-matched Unknown controls, and coordinate-level audit for high-GC/SVA-like candidates; repeat tri-review only if promoted to a manuscript claim.
- [ ] Recover or audit lost historical `docs/05_todo.md` and `docs/15_evidence_register.md` rows if a complete audit trail is required.
- [ ] Continue monitoring `DENOVO_B_ANIMAL_EVAL_20260620`: base de novo is now 29/32 DONE after `opossum/earlgrey` was manually standardized from complete EarlGrey outputs on 2026-07-01 09:42 CEST; the Slurm wrapper `9840108_4` failed only during scratch tree sync on a transient missing `.prep` file, while the persisted `filteredRepeats.gff`/BED/library were complete and accepted by `finalize_existing_outputs.py`. Base now waits only on EarlGrey for `pig`, `western_honey_bee`, and `x_laevis` (`9840108_5/7/8`). The previous R2 downstream chain `9854670`-`9854673` was cancelled after `9854670` became `DependencyNeverSatisfied`; the corrected R3 chain is `9874722` finalize waiting on `9840108_5/7/8`, `9874723` base-vs-UCSC after `9874722`, `9874724` Dfam overlay after `9874722` plus `9843979`, and `9874725` Dfam-vs-UCSC after `9874724`. Dfam-overlay reached 20 DONE / 7 running / 5 missing on 2026-07-01 12:10:17 CEST after `horse/repeatscout` completed; final de novo comparisons against UCSC must wait for `9874723` and `9874725`, and both comparison output directories are still empty. On 2026-07-01 15:50 CEST, active EarlGrey was still running (`pig` around 78%, `western_honey_bee` around 6% with long ETA, `x_laevis` still active); attempts to extend existing Slurm time limits were denied by Slurm permissions, so a failure-only longrun rescue `9883336_[7]` was submitted for `western_honey_bee/earlgrey` with dependency `afternotok:9840494`, 4 CPU, 10-day time limit, using `manifests/earlgrey_honeybee_rescue_4cpu_matrix.tsv`. This rescue should remain pending and only run if the current honeybee job fails/timeouts. Current ready-by-design self Label-A vs UCSC comparison was rerun as `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE` and is byte-identical to `20260630_V5_2`. Root-level `RM_*` directories are absent; quarantined scratch such as `RM_892559.ThuJun180438082026` remains under `software_outputs/repeatmasker_dfam/99_internal/rm_scratch_quarantine_20260619/` and should only be deleted after all active de novo/Dfam-overlay jobs and comparisons are complete. 2026-07-01 16:28 CEST refresh: `finalize_existing_outputs.py` found no additional completable EarlGrey outputs; base remains 29/32, Dfam overlay 20/32, compare outputs 0 files. Running base EarlGrey is `pig` about 80% in current stage, `western_honey_bee` about 7% with long ETA, and `x_laevis` in a new EarlGrey round about 13%; R3 dependencies remain healthy.
- [ ] 2026-07-01 16:48 CEST focused monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base still 29/32 DONE, Dfam overlay still 20/32 DONE, and both UCSC comparison directories still have 0 files. `pig/earlgrey` reached 99.7% in one stage but then entered another EarlGrey round, so it is still not final; `western_honey_bee/earlgrey` progressed from 7% to 8% and remains alive with failure-only rescue `9883336_[7]` pending; `x_laevis/earlgrey` remains running around 30% in its current round. R3 dependency chain remains pending and healthy.
- [ ] 2026-07-01 17:00 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: still no new completed outputs to standardize. Base remains 29/32 DONE; Dfam overlay remains 20/32 DONE; base-vs-UCSC and Dfam-vs-UCSC comparison directories remain empty. Running EarlGrey tasks are alive and progressing (`pig` about 59% in current round after entering another round, `western_honey_bee` about 9% with rescue `9883336_[7]` still pending, `x_laevis` about 58%). R3 chain `9874722` -> `9874723` -> `9874724` -> `9874725` remains dependency-pending and healthy.
- [ ] 2026-07-01 17:26 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: final all-row comparison is still not ready. Base remains 29/32 DONE and waits on `pig/earlgrey`, `western_honey_bee/earlgrey`, and `x_laevis/earlgrey`; Dfam overlay remains 20/32 DONE. `pig/earlgrey` entered another 102-family internal batch and was about 3.9%; `western_honey_bee/earlgrey` was about 10% with `9883336_[7]` still pending as failure-only rescue; `x_laevis/earlgrey` was about 10.7% in its current batch. R3 jobs `9874722` finalize, `9874723` base-vs-UCSC, `9874724` Dfam overlay, and `9874725` Dfam-vs-UCSC remain dependency-pending and healthy. Existing incremental comparison `ucsc_compare_incremental_20260630_2038` covers 28 rows only, so it is useful for provisional trend checks but not claim-grade evidence; the official full compare directories still have 0 files.
- [ ] 2026-07-01 17:40 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 20/32 DONE, and official full comparison directories still have 0 files. Active base EarlGrey jobs remain healthy: `pig/earlgrey` about 23.5% in the current internal batch, `western_honey_bee/earlgrey` about 11% with `9883336_[7]` still pending as failure-only rescue, and `x_laevis/earlgrey` about 34.2%. R3 dependencies remain healthy and pending (`9874722` -> `9874723` -> `9874724` -> `9874725`). A manual all-tree `finalize_existing_outputs.py` scan was interrupted because it was rewriting large already-DONE outputs and traversing scratch; the resulting partial temp file was quarantined at `raw_outputs/_interrupted_finalize_tmp_20260701/opossum.repeatmodeler.annotation.gff3.tmp.20260701_1732_interrupted`, while the official `raw_outputs/opossum/repeatmodeler/annotation.gff3` and `DONE` remain intact. Next step should use narrow checks for the three unfinished EarlGrey outputs, then let `9874722` do the full finalize after those jobs exit rather than rerunning a foreground all-tree finalize during active runs.
- [ ] 2026-07-01 18:11 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE and official full comparison directories still have 0 files. Dfam overlay advanced from 20/32 to 21/32 DONE; the newly completed row is `dfam_augmented/x_laevis/repeatscout/DONE` at 17:57 CEST. Active base EarlGrey jobs are still running: `pig/earlgrey` was about 65.7% in the current batch, `western_honey_bee/earlgrey` about 12% with `9883336_[7]` still pending as failure-only rescue, and `x_laevis/earlgrey` reached 98% in one internal stage but then entered a new 138-family batch and was about 17.4%, so it is not complete and has no `annotation.gff3`/`DONE` yet. R3 chain remains dependency-pending and healthy.
- [ ] 2026-07-01 18:29 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. Dfam overlay advanced to 22/32 DONE; the new completion since 18:11 is `dfam_augmented/cattle/edta/DONE` at 18:29 CEST. Active base EarlGrey jobs are still running: `pig/earlgrey` reached about 97% in the current stage but has no `annotation.gff3`/`DONE`, `western_honey_bee/earlgrey` is about 13% with `9883336_[7]` still pending as failure-only rescue, and `x_laevis/earlgrey` again entered a new internal batch after a high-percent stage and was about 5.8%, so it also remains incomplete. Do not start final compare until `9874722` releases after the base EarlGrey jobs exit.
- [ ] 2026-07-01 19:04 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. All R3 downstream jobs remain dependency-pending and healthy. Active base EarlGrey jobs remain RUNNING: `pig/earlgrey` entered another internal stage and progressed from about 10% to about 66%, `western_honey_bee/earlgrey` progressed slowly from 13% to about 15% with `9883336_[7]` still pending as failure-only rescue, and `x_laevis/earlgrey` reached about 99.3% in one stage but immediately entered another 138-family internal batch and was about 10.9% at the final check. No base `annotation.gff3`/`DONE` file appeared for these three rows, so final compare remains blocked on real job completion rather than on missing bookkeeping.
- [ ] 2026-07-01 19:23 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. R3 jobs `9874722`/`9874723`/`9874724`/`9874725` remain dependency-pending and healthy. Active base EarlGrey jobs remain RUNNING: `pig/earlgrey` reached 98% in one stage but entered a new 100-family internal batch and had no standard output yet; `western_honey_bee/earlgrey` progressed to about 16% with rescue `9883336_[7]` still pending; `x_laevis/earlgrey` was about 88% in its current stage but still had no `annotation.gff3`/`DONE`. Continue narrow monitoring; do not rerun full finalize or start final compare until the running EarlGrey jobs exit.
- [ ] 2026-07-01 19:40 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. R3 downstream jobs remain dependency-pending and healthy. Active base EarlGrey jobs remain RUNNING: `pig/earlgrey` was again in a new internal batch and progressed from about 3% to 43%, `western_honey_bee/earlgrey` stayed slow but alive around 16%, and `x_laevis/earlgrey` reached about 98% in one stage but again entered a new batch and was about 9.7% at the final check. No standard output appeared for any of the three, so continue narrow monitoring only.
- [ ] 2026-07-01 19:45 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. Full de novo-vs-UCSC comparison is already queued as R3 dependency chain but has not run: `9874722` finalize waits on active base EarlGrey jobs `9840108_5/7/8`, then `9874723` base-vs-UCSC and `9874725` Dfam-vs-UCSC will run after finalize/Dfam overlay dependencies release. Current active base EarlGrey jobs are still writing logs (`pig` about 68% in current internal batch, `western_honey_bee` about 17% with failure-only rescue `9883336_[7]` pending, `x_laevis` about 40% in current internal batch). Incremental comparison files exist but are incomplete (`ucsc_compare_incremental_20260630_2038` has 28 base rows; Dfam incremental has 15 rows), so they remain provisional only. The current run is organized by `raw_outputs/<species>/<tool>` and `dfam_augmented/<species>/<tool>`, with compare outputs in separate `ucsc_compare_*` directories. Root-level `RM_*` directories are RepeatMasker scratch; some are actively being written now (`RM_3195825...`, `RM_3725114...`, `RM_2423522...`), while older 2026-06-29 genome-copy scratch dirs can be removed only after all active jobs/finalize/compare complete and accepted outputs are verified.
- [ ] 2026-07-01 20:00 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. R3 dependency chain remains healthy and pending. `pig/earlgrey` reached 99% in one internal batch at 19:57 but did not emit `annotation.gff3`/`DONE`; by 20:00 it had entered another internal round at 0%, confirming again that EarlGrey percentage is not whole-job completion. `western_honey_bee/earlgrey` progressed to about 18% with long ETA and failure-only rescue `9883336_[7]` still pending; `x_laevis/earlgrey` entered another internal round and was about 42%. Continue narrow monitoring; do not rerun full-tree finalize or final compare manually.
- [ ] 2026-07-01 20:23 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official full comparison directories still have 0 files. R3 chain is still dependency-pending/healthy. `x_laevis/earlgrey` reached the end of an internal family round and entered RepeatMasker known-repeat/protein search (`Looking for simple/tandem...`, `Looking for similarity to known repeat proteins...`) but still has no standard `annotation.gff3`/`DONE`; do not manually standardize before the wrapper exits. `pig/earlgrey` entered another internal round and was about 28%; `western_honey_bee/earlgrey` progressed to about 19% with failure-only rescue `9883336_[7]` still pending. Dfam overlay running rows remain unchanged (`cattle/repeatscout`, `opossum/repeatmodeler`, `opossum/edta`, `opossum/repeatscout`, `pig/repeatscout`) plus Dfam EarlGrey rows waiting on base/finalize. Continue narrow monitoring.
- [ ] 2026-07-01 20:35 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` is still RUNNING and quiet in RepeatMasker known-repeat/protein search; no `annotation.gff3`, `filteredRepeats.gff`, or `DONE` is visible yet, so it cannot be standardized. `pig/earlgrey` progressed in another internal round to about 46%; `western_honey_bee/earlgrey` remains slow around 19% with rescue `9883336_[7]` pending. Continue monitoring only.
- [ ] 2026-07-01 20:47 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` is actively running RepeatMasker known-repeat scanning (`batch 294-297 of 46764`), so it is alive but far from standard `annotation.gff3`/`DONE`. `pig/earlgrey` progressed to about 60% in the current internal round; `western_honey_bee/earlgrey` progressed to about 20% with rescue `9883336_[7]` still pending. Continue monitoring only; no manual finalize/compare.
- [ ] 2026-07-01 20:49 CEST Dfam overlay focused check for `DENOVO_B_ANIMAL_EVAL_20260620`: no additional Dfam rows are accepted as DONE yet. Active rows are alive: `cattle/repeatscout` is around RepeatMasker batch 15597/47033, `opossum/repeatscout` around batch 24938/62171, and `pig/repeatscout` around batch 15554/43324. `opossum/repeatmodeler` log reached ProcessRepeats adjudication and root scratch `RM_3348149...` updated large `opossum.fa.out/.out.gff` at 20:46, but the wrapper/status matrix has not accepted final `annotation.gff3`/`DONE`; leave it to the running job/finalize chain rather than manual standardization.
- [ ] 2026-07-01 20:50 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` is alive in RepeatMasker known-repeat scanning and progressed to about batch 507/46764; `pig/earlgrey` remains around 60% in the current internal round; `western_honey_bee/earlgrey` remains around 20% with rescue `9883336_[7]` pending. Continue monitoring only.
- [ ] 2026-07-01 21:03 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` is alive and progressed in RepeatMasker known-repeat scanning to about batch 1435/46764; `pig/earlgrey` progressed to about 79% in the current internal round; `western_honey_bee/earlgrey` progressed to about 21% with rescue `9883336_[7]` still pending. Continue monitoring only.
- [ ] 2026-07-01 21:26 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` is alive and progressed in RepeatMasker known-repeat scanning to about batch 3197/46764. `pig/earlgrey` is still in the same internal round and tail shows about 98.4%, but no standard `annotation.gff3`/`DONE` exists; scratch `RM_3725114...` is still writing TRF/RepeatMasker temp files, so do not mark complete or delete scratch. `western_honey_bee/earlgrey` progressed to about 22% with rescue `9883336_[7]` still pending. Continue monitoring only.
- [ ] 2026-07-01 21:28 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `x_laevis/earlgrey` progressed to about batch 3338/46764 in RepeatMasker known-repeat scanning. `pig/earlgrey` tail still shows about 98.4% in the current round, but Slurm job `9840108_5` remains RUNNING and scratch `RM_3725114...` is actively writing `pig.fa_batch-*` temp/masked files, so it is not complete. `western_honey_bee/earlgrey` remains about 22% with rescue `9883336_[7]` pending. Continue monitoring only; no scratch cleanup.
- [ ] 2026-07-01 21:30 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` still tails at about 98.4% but job `9840108_5` is RUNNING and scratch `RM_3725114...` is actively writing `pig.fa_batch-*` files, so it is not complete. `x_laevis/earlgrey` progressed to about batch 3464/46764 in RepeatMasker known-repeat scanning. `western_honey_bee/earlgrey` remains about 22%. No new DONE/FAILED markers appeared; continue monitoring only.
- [ ] 2026-07-01 21:32 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official full comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` still tails at about 98.4% in the current round but remains RUNNING with growing log/scratch activity; do not mark complete. `x_laevis/earlgrey` progressed to about batch 3616/46764 in RepeatMasker known-repeat scanning. `western_honey_bee/earlgrey` remains about 22%. Continue monitoring only.
- [ ] 2026-07-01 21:34 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official base-vs-UCSC and Dfam-vs-UCSC comparison directories still have 0 files, and R3 chain remains dependency-pending/healthy (`9874722` finalize waits on active base EarlGrey jobs, then `9874723`/`9874725` compare). Active base EarlGrey jobs are alive: `pig/earlgrey` still tails at about 98.4% but has no standard `annotation.gff3`/`DONE` and scratch `RM_3725114...` is actively writing; `x_laevis/earlgrey` progressed to about batch 3785/46764 in RepeatMasker scanning; `western_honey_bee/earlgrey` remains around 22% with failure-only rescue `9883336_[7]` pending. Active Dfam rows are also alive (`cattle/repeatscout`, `opossum/repeatscout`, `pig/repeatscout`; `opossum/repeatmodeler` has large recent root scratch outputs but no accepted final row). Root-level `RM_*` directories include active scratch (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`) and should not be deleted until all jobs, finalize, and compare complete.
- [ ] 2026-07-01 21:40 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: still not ready to rerun final UCSC comparison because official compare jobs have not started (`ucsc_compare_full_20260630` and Dfam counterpart both still 0 files). Base remains 29/32 DONE and Dfam overlay remains 22/32 DONE. `pig/earlgrey` has entered another internal round after the 98.4% stage and now tails around 1.6% (`rnd-1_family-31.fasta`), confirming again that the prior high percentage was not whole-job completion. `x_laevis/earlgrey` progressed to about batch 4224/46764; `western_honey_bee/earlgrey` remains around 22% with long ETA. Active root-level RepeatMasker scratch remains present and recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so scratch cleanup remains deferred.
- [ ] 2026-07-01 21:41 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and both official UCSC compare directories still have 0 files. R3 jobs remain dependency-pending (`9874722` finalize blocked by active `9840108_5/7/8`; compare jobs wait behind it). Active base EarlGrey jobs are alive: `pig/earlgrey` is about 3.2% in the new internal round, `x_laevis/earlgrey` progressed to about batch 4343/46764, and `western_honey_bee/earlgrey` remains around 22%. Dfam RepeatScout rows are alive (`cattle` around 15843/47033, `opossum` around 25649/62171, `pig` around 15998/43324). Active root-level scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`); no scratch cleanup.
- [ ] 2026-07-01 21:52 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, and official UCSC compare directories still have 0 files. R3 dependency chain remains healthy and pending. Active jobs are progressing rather than stalled: `pig/earlgrey` advanced to about 21% in the current internal round, `x_laevis/earlgrey` progressed to about batch 5174/46764, and `western_honey_bee/earlgrey` advanced to about 23%. Dfam RepeatScout rows are also alive (`cattle` around 15895/47033, `opossum` around 25799/62171, `pig` around 16098/43324). Active root-level scratch directories are still being written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so `RM_*` cleanup remains unsafe.
- [ ] 2026-07-01 22:08 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official base-vs-UCSC and Dfam-vs-UCSC compare directories still have 0 files, and R3 dependency chain remains pending/healthy. Active base EarlGrey rows continue to progress: `pig/earlgrey` is about 69% in its current internal round but still has no `annotation.gff3`/`DONE`, `x_laevis/earlgrey` progressed to about batch 6381/46764, and `western_honey_bee/earlgrey` remains about 23%. Dfam RepeatScout rows also continue (`cattle` around 15968/47033, `opossum` around 26030/62171, `pig` around 16214/43324). Active root-level scratch directories remain recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`); do not delete `RM_*` yet.
- [ ] 2026-07-01 22:24 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 dependency chain remains healthy/pending. `pig/earlgrey` reached about 90% in the current internal round but still has no standard output markers; continue to require `annotation.gff3`/`DONE` rather than percent. `x_laevis/earlgrey` progressed to about batch 7531/46764, and `western_honey_bee/earlgrey` progressed to about 24%. Dfam RepeatScout rows are still advancing (`cattle` around 16055/47033, `opossum` around 26243/62171, `pig` around 16313/43324). Active root-level scratch remains recently written; no `RM_*` cleanup.
- [ ] 2026-07-01 22:45 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 dependency chain remains pending/healthy. `pig/earlgrey` entered another internal round after the prior high-percent stage and is now about 34%, so finalize is still correctly waiting. `x_laevis/earlgrey` progressed to about batch 9115/46764, and `western_honey_bee/earlgrey` progressed to about 25%. Dfam RepeatScout rows remain alive (`cattle` around 16166/47033, `opossum` around 26485/62171, `pig` around 16488/43324); `opossum/repeatmodeler` log updated at 22:33 but still lacks accepted final outputs. Active root-level scratch remains recently written; no `RM_*` cleanup.
- [ ] 2026-07-01 23:16 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains pending/healthy. `pig/earlgrey` again entered a new internal round and is around 6.8%, so no finalize release yet. `x_laevis/earlgrey` progressed to about batch 11421/46764, and `western_honey_bee/earlgrey` progressed to about 26%. Dfam RepeatScout rows continue to advance (`cattle` around 16309/47033, `opossum` around 26853/62171, `pig` around 16700/43324); `opossum/repeatmodeler` remains in ProcessRepeats/adjudication without accepted final outputs. Active root-level scratch remains recently written; no `RM_*` cleanup.
- [ ] 2026-07-01 23:46 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains pending/healthy. Active base EarlGrey rows remain alive: `pig/earlgrey` is about 52% in the current internal round, `x_laevis/earlgrey` progressed to about batch 13747/46764, and `western_honey_bee/earlgrey` progressed to about 27%. Dfam RepeatScout rows continue (`cattle` around 16471/47033, `opossum` around 27249/62171, `pig` around 16937/43324); `opossum/repeatmodeler` still lacks accepted final outputs. Active root-level scratch remains recently written; no `RM_*` cleanup.
- [ ] 2026-07-01 23:48 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` remains in a current internal round around 52% with no standard output markers; `x_laevis/earlgrey` progressed to about batch 13852/46764; `western_honey_bee/earlgrey` remains around 27%. Dfam RepeatScout rows continue (`cattle` around 16478/47033, `opossum` around 27271/62171, `pig` around 16951/43324); `opossum/repeatmodeler` remains without accepted final outputs. Root-level active scratch is still being written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 00:19 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 82% in the current internal round but still has no standard output markers; `x_laevis/earlgrey` progressed to about batch 16182/46764; `western_honey_bee/earlgrey` progressed to about 29%. Dfam RepeatScout rows continue (`cattle` around 16648/47033, `opossum` around 27709/62171, `pig` around 17206/43324); `opossum/repeatmodeler` remains without accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 00:50 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` entered another internal round and is about 11%, so no standard output/finalize release yet. `x_laevis/earlgrey` progressed to about batch 18521/46764, and `western_honey_bee/earlgrey` progressed to about 31%. Dfam RepeatScout rows continue (`cattle` around 16823/47033, `opossum` around 28070/62171, `pig` around 17452/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 01:20 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 75% in the current internal round but still has no standard output markers; `x_laevis/earlgrey` progressed to about batch 20838/46764; `western_honey_bee/earlgrey` progressed to about 32%. Dfam RepeatScout rows continue (`cattle` around 17002/47033, `opossum` around 28442/62171, `pig` around 17685/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 01:51 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 52% in the current internal round with no standard output markers; `x_laevis/earlgrey` progressed to about batch 23164/46764; `western_honey_bee/earlgrey` progressed to about 33%. Dfam RepeatScout rows continue (`cattle` around 17142/47033, `opossum` around 28824/62171, `pig` around 17952/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 02:22 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` entered another internal round and is about 12%, so no finalize release yet. `x_laevis/earlgrey` progressed to about batch 25467/46764; `western_honey_bee/earlgrey` progressed to about 35%. Dfam RepeatScout rows continue (`cattle` around 17295/47033, `opossum` around 29180/62171, `pig` around 18212/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 02:53 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 57% in the current internal round; `x_laevis/earlgrey` progressed to about batch 27808/46764; `western_honey_bee/earlgrey` progressed to about 36%. Dfam RepeatScout rows continue (`cattle` around 17470/47033, `opossum` around 29548/62171, `pig` around 18400/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 02:55 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` remains about 57% in the current internal round with no standard output markers; `x_laevis/earlgrey` progressed to about batch 27902/46764; `western_honey_bee/earlgrey` remains about 36%. Dfam RepeatScout rows continue (`cattle` around 17476/47033, `opossum` around 29560/62171, `pig` around 18404/43324); `opossum/repeatmodeler` still has no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 03:25 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 94% in the current internal round but still has no standard output markers; `x_laevis/earlgrey` progressed to about batch 30253/46764; `western_honey_bee/earlgrey` progressed to about 37%. Dfam RepeatScout rows continue (`cattle` around 17642/47033, `opossum` around 29895/62171, `pig` around 18576/43324). `opossum/repeatmodeler` root scratch `RM_3348149...` wrote large `opossum.fa.out/.out.gff` at 03:20, so it is still active despite no accepted final outputs. Root-level active scratch remains recently written (`RM_2423522...`, `RM_3195825...`, `RM_3348149...`, `RM_3725114...`), so cleanup remains deferred.
- [ ] 2026-07-02 03:56 CEST monitor update for `DENOVO_B_ANIMAL_EVAL_20260620`: base remains 29/32 DONE, Dfam overlay remains 22/32 DONE, official compare directories still have 0 files, and R3 chain remains dependency-pending/healthy. `pig/earlgrey` is about 70% in the current internal round with no standard output markers; `x_laevis/earlgrey` progressed to about batch 32585/46764; `western_honey_bee/earlgrey` progressed to about 39%. Dfam RepeatScout rows continue (`cattle` around 17804/47033, `opossum` around 30186/62171, `pig` around 18754/43324). `opossum/repeatmodeler` remains without accepted final outputs and root scratch `RM_3258618...` wrote large `opossum.fa.out/.out.gff` at 03:53, so cleanup remains deferred for active `RM_*`.

## 2026-07-02 04:38 CEST - de novo/Dfam benchmark monitor update

- User request in force: rerun UCSC comparison using this annotation round and clarify output layout/cleanup after completion.
- Current status: official UCSC compare dirs are still absent because final compare jobs are dependency-gated behind annotation completion.
- Base de novo matrix: 29/32 accepted; remaining base rows are EarlGrey for `pig`, `western_honey_bee`, and `x_laevis`.
- Dfam-augmented matrix: 22/32 accepted before rescue finalize; remaining rows include `opossum` repeatmodeler/edta, repeatscout rows for `cattle`/`opossum`/`pig`, and EarlGrey overlays waiting for base EarlGrey outputs.
- `cattle/repeatscout_plus_dfam` whole-genome job `9843979_3` timed out at 60h around batch 17827/47033. The same whole-genome strategy is unlikely to fit the public-cpu walltime.
- Added chunked rescue implementation:
  - `scripts/experiments/denovo_benchmark/run_chunked_dfam_repeatmasker.py`
  - `sbatch/denovo_b_animal_eval_dfam_repeatscout_chunked_rescue_20260702.sbatch`
  - `sbatch/denovo_b_animal_eval_dfam_repeatscout_chunked_finalize_20260702.sbatch`
- Chunked rescue manifest: `$RUN/dfam_augmented/repeatscout_chunked_rescue_20260702_manifest.tsv`, 63 chunks total: cattle 32, opossum 10, pig 21.
- Queue changes:
  - cancelled whole-genome Dfam repeatscout tasks `9843979_15` and `9843979_18` because progress indicated likely timeout;
  - submitted chunked rescue array `9886845`, finalize `9886846`;
  - replaced pending Dfam R2/compare jobs with `9886847` and `9886848`, dependent on base finalize plus chunked finalize.
- Code review gate records written under `/home/users/j/jwang/ab-initio-TE/outputs/denovo_b_animal_eval_dfam_repeatscout_chunked_*_20260702/code_review_gate.json`; docs/21 updated.
- Cleanup note: do not delete root or quarantined `RM_*` directories until `9886848` and official base compare both finish and matrices show accepted outputs. Older `RM_892559.ThuJun180438082026` remains a cleanup candidate after final verification.

## 2026-07-02 07:54 CEST - de novo/Dfam benchmark monitor handoff

- Official UCSC comparison has not run yet; both compare directories still have 0 files because dependencies are waiting on unfinished annotations.
- Active/pending jobs:
  - base finalize: `9874722`; base UCSC compare: `9874723`.
  - chunked Dfam RepeatScout rescue: `9886845`; chunk finalize: `9886846`; Dfam R2: `9886847`; Dfam UCSC compare: `9886848`.
  - base EarlGrey still running for `pig`, `western_honey_bee`, and `x_laevis`.
  - Dfam old array still has `opossum/repeatmodeler` running; `opossum/edta` completed and dropped from the remaining matrix.
- Chunked rescue status at last monitor: 0/63 DONE, 0 FAILED, active chunks running up to ~3h15m; this is progressing but not yet at first chunk completion.
- Current remaining matrices are available at:
  - `$RUN/current_matrix_status_20260629_refresh.tsv`
  - `$RUN/dfam_augmented/current_matrix_status_20260629.tsv`
- Resume monitor commands:

```bash
RUN=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
squeue -u "$USER" -o '%.18i %.28j %.8T %.12M %.30E %.24R' | rg '988684|987472|9840108|9843979|9883336|DENOVO|DFAM|EG_B'
python3 scripts/experiments/denovo_benchmark/refresh_denovo_monitor.py --run-root "$RUN"
find "$RUN/dfam_augmented" -path '*repeatscout_chunked_rescue_20260702*' -name FAILED -print
for s in cattle opossum pig; do printf "$s="; find "$RUN/dfam_augmented/$s/repeatscout_chunked_rescue_20260702/repeatmasker_chunks" -maxdepth 2 -name DONE 2>/dev/null | wc -l; done
find "$RUN/ucsc_compare_full_20260630" "$RUN/dfam_augmented/ucsc_compare_full_20260630" -maxdepth 2 -type f 2>/dev/null | sed -n '1,80p'
```

- Cleanup remains unsafe until `9874723` and `9886848` finish and both matrices show accepted outputs. Do not delete active/recent `RM_*` scratch. The quarantined old `RM_892559.ThuJun180438082026` can be removed only after final compare verification.

## 2026-07-02 12:00 CEST - de novo/Dfam benchmark monitor update

- Official UCSC comparison still has not run. `ucsc_compare_full_20260630` and `dfam_augmented/ucsc_compare_full_20260630` remain at 0 files because annotations are not complete.
- Active dependency chain remains:
  - `9874722` base finalize -> `9874723` base-vs-UCSC compare.
  - `9886845` chunked Dfam RepeatScout rescue -> `9886846` chunk finalize -> `9886847` Dfam R2 -> `9886848` Dfam-vs-UCSC compare.
- Chunked rescue progress: cattle `20/32` chunks DONE, `0` FAILED; opossum chunks have started but `0/10` DONE; pig chunks not started yet. This validates the chunked rescue path but it is still running.
- Base still waits on EarlGrey for `pig`, `western_honey_bee`, and `x_laevis`.
- Dfam still waits on `opossum/repeatmodeler`, chunked repeatscout rows for cattle/opossum/pig, and EarlGrey overlay rows that depend on base EarlGrey outputs.
- `opossum/repeatmodeler` job `9843979_13` remains RUNNING with time limit ending 2026-07-02 20:36 CEST. Do not cancel unless it fails/timeouts; if it fails, prefer a chunked rescue rather than another whole-genome RepeatMasker rerun.
- Cleanup remains unsafe: do not delete active/recent `RM_*` or quarantined old scratch until `9874723` and `9886848` complete and matrices show accepted outputs.

## 2026-07-02 14:02 CEST - de novo/Dfam benchmark monitor update

- Official compare still not released: base compare `9874723` and Dfam compare `9886848` remain dependency-pending; compare output directories remain 0 files.
- `opossum/repeatmodeler` Dfam overlay completed successfully and dropped from `dfam_augmented/current_matrix_status_20260629.tsv` remaining rows.
- Chunked Dfam RepeatScout rescue `9886845` remains healthy: cattle `22/32` DONE, opossum `0/10` DONE, pig `0/21` DONE, `0` FAILED. Opossum chunks are running; later tasks are pending by resource/priority.
- Base still waits on EarlGrey rows for `pig`, `western_honey_bee`, and `x_laevis`; failure-only honeybee rescue `9883336_[7]` remains pending and should stay pending unless current honeybee job fails.
- Do not manually run finalize or compare; standard outputs are still incomplete. Cleanup remains unsafe.

## 2026-07-02 16:05 CEST - de novo/Dfam benchmark monitor update

- Official compare still has not run; base compare `9874723` and Dfam compare `9886848` remain dependency-pending with 0 output files.
- Chunked Dfam RepeatScout rescue `9886845` continues to work: cattle `24/32` chunks DONE, opossum `1/10` DONE, pig `0/21` DONE, and `0` FAILED.
- `opossum/repeatmodeler` Dfam overlay remains accepted DONE after completion earlier today; it is no longer a blocker.
- Remaining annotation blockers: base EarlGrey for `pig`, `western_honey_bee`, `x_laevis`; Dfam chunked repeatscout for cattle/opossum/pig; Dfam EarlGrey overlay rows waiting on base/finalize.
- Do not clean `RM_*` or run manual compare/finalize yet.

## 2026-07-02 19:33 CEST - de novo/Dfam benchmark monitor update

- User request in force: compare this annotation round against UCSC again, confirm whether outputs are still assigned into the expected folder layout, and decide whether root-level `RM_*` scratch such as `RM_892559.ThuJun180438082026` can be cleaned.
- Official compare still has not run: `$RUN/ucsc_compare_full_20260630` and `$RUN/dfam_augmented/ucsc_compare_full_20260630` both still contain 0 files. `9874723` and `9886848` remain dependency-pending, which is expected until standard annotation outputs are complete.
- Base matrix remains 29/32 accepted. Remaining base rows are EarlGrey for `pig`, `western_honey_bee`, and `x_laevis`.
- Dfam matrix still has 8 remaining rows. The main blockers are chunked RepeatScout+Dfam for `cattle`, `opossum`, and `pig`, plus EarlGrey overlay rows waiting on base EarlGrey/finalize.
- Chunked Dfam RepeatScout rescue `9886845` is healthy but still running: cattle `31/32` chunks DONE, opossum `2/10` DONE, pig `0/21` DONE, and `0` FAILED at the last monitor. Chunk time limit is 4 days, so current chunk jobs are not near walltime risk.
- Root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories were not present in the latest `find -maxdepth 1` check. If an old `RM_892559.ThuJun180438082026` path appears only in old logs, it is likely already gone; do not delete any current `RM_*`, `_quarantine_*`, or `_interrupted_finalize_tmp_*` under the de novo run root until `9874723` and `9886848` finish and matrices show accepted outputs.
- Layout note: formal ready-to-use RepeatMasker+Dfam data remain under `software_outputs/repeatmasker_dfam/02_ready_by_design/<design>/{genomes,annotations}/{fine_tune,eval_only,self_labelA,ucsc_comparator}`. This de novo/Dfam benchmark round remains under `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620` until final compare and validation complete.

## 2026-07-02 19:36 CEST - EarlGrey longrun rescue prepared

- `pig/earlgrey` is unlikely to finish within the remaining public-cpu walltime based on its RepeatMasker batch progress. `western_honey_bee/earlgrey` already had a failure-only longrun rescue, and `x_laevis/earlgrey` may still finish but also has walltime risk.
- Added `scripts/experiments/denovo_benchmark/submit_earlgrey_pig_xlaevis_longrun_rescue.sbatch`.
- `public-longrun-cpu` currently uses `longrun` QOS with `cpu=4` max per job, so generated `$RUN/manifests/earlgrey_task_matrix_longrun4.tsv` from the standard EarlGrey matrix with the CPU column reduced from 16 to 4.
- Submitted failure-only rescue jobs:
  - `9945280_[5]`: `pig`, dependency `afternotok:9840110`.
  - `9945299_[8]`: `x_laevis`, dependency `afternotok:9840108_8`.
  - existing `9883336_[7]`: `western_honey_bee`, dependency `afternotok:9840494`.
- These jobs should remain pending and never run if the active public-cpu EarlGrey tasks complete successfully. If any rescue actually runs, replace downstream finalize/compare dependencies after the rescue succeeds; do not rely on the current `9874722 -> 9874723 -> 9886847 -> 9886848` chain after a base EarlGrey failure.

## 2026-07-02 20:30 CEST - de novo/Dfam benchmark monitor update

- Official UCSC compare still has not run; base and Dfam compare directories remain at 0 files.
- Active base EarlGrey jobs still running: `pig` (`9840108_5`), `western_honey_bee` (`9840108_7`), and `x_laevis` (`9840108_8`). `pig` and `western_honey_bee` logs are actively writing. `x_laevis` runner log has not written since 15:35, but Slurm CPU accounting is still increasing, so it appears to be in a quiet compute stage rather than dead.
- Failure-only EarlGrey rescue jobs are queued: `9945280_[5]` for pig, `9883336_[7]` for honeybee, and `9945299_[8]` for x_laevis.
- Chunked RepeatScout+Dfam rescue `9886845` remains healthy with 0 failed chunks. Latest counts: cattle `31/32`, opossum `3/10`, pig `2/21`. Recent runner logs for all three species have current mtimes, so the chunked path is still progressing.
- Root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories remain absent in the latest check. Run-root quarantine/interrupted directories still exist and should not be deleted until final compare verification.

## 2026-07-02 21:10 CEST - de novo/Dfam benchmark monitor update

- Official UCSC compare still has not run; `$RUN/ucsc_compare_full_20260630` and `$RUN/dfam_augmented/ucsc_compare_full_20260630` remain at 0 files.
- Active annotation blockers remain unchanged: base EarlGrey for `pig`, `western_honey_bee`, `x_laevis`; chunked RepeatScout+Dfam for `cattle`, `opossum`, `pig`.
- Chunked RepeatScout+Dfam rescue is still healthy with `0` FAILED. Latest counts: cattle `31/32`, opossum `4/10`, pig `2/21`. Task `9886845_46` started, so the pig chunk array continues to advance as resources free up.
- Failure-only EarlGrey rescue jobs remain pending as intended: `9945280_[5]` pig, `9883336_[7]` honeybee, `9945299_[8]` x_laevis.
- Current downstream jobs `9874722`, `9874723`, `9886847`, and `9886848` are still dependency-pending. If any base EarlGrey rescue actually runs, replace this downstream chain after rescue completion.

## 2026-07-02 22:14 CEST - de novo/Dfam benchmark monitor update

- Official UCSC compare still has not run; compare directories remain at 0 files.
- Base matrix remains 29/32 accepted; remaining rows are EarlGrey for `pig`, `western_honey_bee`, and `x_laevis`.
- Dfam matrix remains with 8 incomplete rows, pending chunked RepeatScout+Dfam and EarlGrey overlays.
- Chunked RepeatScout+Dfam rescue remains healthy with `0` FAILED. Latest counts: cattle `31/32`, opossum `5/10`, pig `2/21`; pig chunks `47`, `48`, `49`, `50`, and `51` have started as resources opened.
- `pig/earlgrey` is still actively progressing, now around RepeatMasker batch `14308/43324`; `western_honey_bee/earlgrey` is around `86%` with about `5h18m` ETA; `x_laevis/earlgrey` remains quiet in the log but its Slurm job is still RUNNING.
- Failure-only rescues remain pending as intended: `9945280_[5]` pig, `9883336_[7]` honeybee, `9945299_[8]` x_laevis.
- Do not clean run-root quarantine/interrupted directories and do not manually run compare/finalize yet.

## 2026-07-02 23:07 CEST - de novo/Dfam benchmark monitor update

- Official UCSC compare still has not run; compare directories remain at 0 files and downstream compare jobs are dependency-pending.
- Base matrix remains 29/32 accepted. `pig`, `western_honey_bee`, and `x_laevis` EarlGrey are still running. `pig/earlgrey` is actively writing and has progressed to about RepeatMasker batch `17478/43324`; `western_honey_bee/earlgrey` is around `88%` with about `4h29m` ETA; `x_laevis/earlgrey` still has no new runner-log lines but the Slurm task remains RUNNING.
- Dfam matrix still has 8 incomplete rows. Chunked RepeatScout+Dfam remains healthy with `0` FAILED: cattle `31/32`, opossum `5/10`, pig `2/21`. Chunk runner logs for cattle/opossum/pig have current mtimes.
- Failure-only rescue jobs remain pending as intended: `9945280_[5]` pig, `9883336_[7]` honeybee, `9945299_[8]` x_laevis. The active public-cpu EarlGrey jobs should hit walltime around 2026-07-03 01:22-01:36 CEST if they do not finish first.
- Root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories remain absent in the latest check. Do not clean run-root quarantine/interrupted directories until final compare verification.

## 2026-07-02 23:59 CEST - de novo/Dfam benchmark monitor update

- Official UCSC compare still has not run; compare directories remain at 0 files and downstream compare jobs are dependency-pending.
- Base matrix remains 29/32 accepted. `pig`, `western_honey_bee`, and `x_laevis` EarlGrey are still running.
- `pig/earlgrey` remains active and has progressed to about RepeatMasker batch `20351/43324`; `western_honey_bee/earlgrey` is around `90%` with about `3h40m` ETA; `x_laevis/earlgrey` still has no new runner-log lines but the Slurm task remains RUNNING.
- Dfam chunked RepeatScout+Dfam remains healthy with `0` FAILED. Latest counts: cattle `31/32`, opossum `6/10`, pig `2/21`. Chunk runner logs for cattle/opossum/pig have current mtimes.
- Failure-only rescue jobs remain pending as intended: `9945280_[5]` pig, `9883336_[7]` honeybee, `9945299_[8]` x_laevis.
- Next critical check is after the active public-cpu EarlGrey walltime window around 2026-07-03 01:22-01:36 CEST. If any rescue starts, replace the downstream finalize/compare chain after rescue success.

## 2026-07-03 01:43 CEST - EarlGrey walltime transition

- Original public-cpu EarlGrey tasks timed out:
  - `9840108_5` pig: `TIMEOUT` at 2026-07-03 01:22 CEST.
  - `9840108_7` western_honey_bee: `TIMEOUT` at 2026-07-03 01:36 CEST.
  - `9840108_8` x_laevis: `TIMEOUT` at 2026-07-03 01:36 CEST.
- Consequence: old downstream chain is now invalid. `9874722` is `DependencyNeverSatisfied`, so do not rely on `9874722 -> 9874723 -> 9886847 -> 9886848`.
- Rescue state:
  - `9945280_5` pig rescue is RUNNING with the 4 CPU longrun matrix.
  - `9945299_8` x_laevis rescue is RUNNING with the 4 CPU longrun matrix.
  - old honeybee rescue `9883336_7` failed immediately because it used a one-row rescue matrix without task id 7.
  - submitted replacement honeybee rescue `9951192_[7]` with the complete `earlgrey_task_matrix_longrun4.tsv`; it is pending on `QOSMaxJobsPerUserLimit` until one of the two running longrun rescues finishes.
- Chunked RepeatScout+Dfam remains healthy with `0` FAILED. Latest counts: cattle `31/32`, opossum `6/10`, pig `6/21`.
- After pig/x_laevis/honeybee rescue success, submit replacement base finalize, base compare, Dfam R2, and Dfam compare jobs with dependencies on the successful rescue jobs and chunk finalize. Do not manually run compare before then.

## 2026-07-03 02:26 CEST - rescue monitor update

- `9945280_5` pig rescue is RUNNING and writing progress; latest runner log shows around `35%` in the current EarlGrey stage with about `1h` ETA for that stage.
- `9945299_8` x_laevis rescue is RUNNING and writing progress; it has resumed into all-by-other comparisons after syncing existing work output.
- Replacement honeybee rescue `9951192_[7]` remains PENDING on `QOSMaxJobsPerUserLimit`; it should start when either pig or x_laevis rescue frees a longrun slot.
- Chunked RepeatScout+Dfam remains healthy with `0` FAILED. Latest monitor counts remain cattle `31/32`, opossum `6/10`, pig `6/21`, with current runner-log mtimes for all three species.
- Old downstream chain remains invalid: `9874722` is `DependencyNeverSatisfied`; do not use `9874722`, `9874723`, `9886847`, or `9886848` as final evidence.

## 2026-07-03 03:13 CEST - current ready Label-A vs UCSC rerun

- Reran current ready-view self-run RepeatMasker+Dfam Label-A vs UCSC/local strict-TE comparator with `srun -p public-short-cpu -c 4`.
- Output: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703/summary.tsv` and `REPORT.md`.
- Compared 24 species with both self Label-A and comparator available. Mean bp-level Jaccard is `0.394736`.
- The 20260703 `summary.tsv` is byte-identical to `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE/summary.tsv`, so current ready-view self/UCSC inputs have not changed since that run.
- Human rows: `human` Jaccard `0.948128`, `human_hg19` `0.892302`, `human_hg38` `0.912476`.
- Very low-concordance rows such as `western_clawed_frog`, `x_laevis`, several plants, `lizard`, and invertebrates should be treated as comparator/source/class-filter audit signals, not claim-grade biological conclusions.
- Separate status: de novo/Dfam-augmented benchmark final UCSC comparison is still not ready. `$RUN/ucsc_compare_full_20260630` and `$RUN/dfam_augmented/ucsc_compare_full_20260630` still contain 0 files.
- Layout remains: ready RepeatMasker+Dfam files are exposed under `software_outputs/repeatmasker_dfam/02_ready_by_design/<design>/{genomes,annotations}/{fine_tune,eval_only}`; raw provenance remains under `software_outputs/repeatmasker_dfam/raw_runs/self_labelA/*`.
- Cleanup status: root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories are absent in the latest check. Quarantined internal `RM_*` directories remain under `software_outputs/repeatmasker_dfam/99_internal` and should not be deleted until final de novo/Dfam compare outputs are produced and accepted.

## 2026-07-03 03:31 CEST - invalid downstream chain cleanup

- Cancelled invalid pending downstream jobs `9874722`, `9874723`, `9886847`, and `9886848` after the original EarlGrey public-cpu tasks timed out and made `9874722` `DependencyNeverSatisfied`.
- Kept valid chunked RepeatScout+Dfam finalize job `9886846` pending on `9886845_*`.
- Current intended next step remains: after pig, x_laevis, and honeybee EarlGrey rescues succeed, submit a replacement base finalize, replacement base-vs-UCSC compare, replacement Dfam R2 overlay, and replacement Dfam-vs-UCSC compare with fresh dependencies.

## 2026-07-03 03:40 CEST - rescue monitor update

- Active valid jobs after cleanup: chunked RepeatScout+Dfam rescue `9886845_*`, chunk finalize `9886846`, pig/x_laevis EarlGrey rescues `9945280_5` and `9945299_8`, and honeybee replacement rescue `9951192_[7]`.
- `pig/earlgrey` rescue reached the end of one internal progress phase, then entered a new RECON/repeat-search/TRFMask/masking phase; it is still RUNNING and has not written standard `annotation.gff3`/`DONE`.
- `x_laevis/earlgrey` rescue is still RUNNING and progressed to about `77%` in its current all-by-other comparison phase.
- `western_honey_bee/earlgrey` replacement rescue remains PENDING on `QOSMaxJobsPerUserLimit`, expected until pig or x_laevis frees a longrun slot.
- Chunked RepeatScout+Dfam remains healthy with `0` FAILED; latest counts are cattle `32/32`, opossum `7/10`, pig `8/21`.

## 2026-07-03 04:36 CEST - longrun rescue still active

- Continued monitoring valid rescue jobs. No downstream compare can be submitted yet because no new EarlGrey rescue has produced standard `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE`.
- `pig/earlgrey` rescue `9945280_5` is RUNNING on `public-longrun-cpu`; after completing one internal phase it entered another long RepeatModeler/EarlGrey batch and was around `7%` with an internal estimate around `11.5h`.
- `x_laevis/earlgrey` rescue `9945299_8` is RUNNING on `public-longrun-cpu`; after reaching `98%` in one internal all-by-other phase it entered a new RECON/repeat-search batch and was around `1%` with an internal estimate around `13h`.
- `western_honey_bee/earlgrey` replacement rescue `9951192_[7]` remains PENDING on `QOSMaxJobsPerUserLimit`; this is expected because pig and x_laevis occupy the two longrun slots.
- Chunked RepeatScout+Dfam remains healthy with `0` FAILED; latest counts are cattle `32/32`, opossum `7/10`, pig `10/21`. Finalize job `9886846` remains correctly pending on the chunk array.
- Current action: leave Slurm jobs running; next active intervention is only after a rescue exits, honeybee starts, a chunk fails, or `9886846` finalizes.

## 2026-07-03 04:42 CEST - honeybee rescue rerouted off longrun

- `western_honey_bee/earlgrey` was blocked by `public-longrun-cpu` per-user job count because pig and x_laevis occupy the two longrun slots.
- Added `scripts/experiments/denovo_benchmark/submit_earlgrey_honeybee_publiccpu_rescue.sbatch`, using `public-cpu`, 4 CPU, 80G, 4-day walltime, task id `7`, and the existing 4-CPU matrix `earlgrey_task_matrix_longrun4.tsv`.
- Cancelled the blocked longrun honeybee pending job `9951192`.
- Submitted replacement public-cpu honeybee rescue `9951555_[7]`. It is currently PENDING on `Resources`, not on a QoS/user-limit error.
- Pig/x_laevis longrun rescues remain running. Latest observed states: pig about `7%` in the current internal batch, x_laevis about `1%` in its current internal batch; neither has standard `annotation.gff3`/`DONE`.
- Chunked RepeatScout+Dfam remains healthy: cattle `32/32`, opossum `7/10`, pig `10/21`, failed chunks `0`.

## 2026-07-03 04:48 CEST - honeybee rescue started on public-bigmem

- `9951555_[7]` remained PENDING on `public-cpu` due to `Resources` despite no QoS limit. Because `public-bigmem` had suitable 4-day capacity, cancelled `9951555`.
- Resubmitted the same honeybee rescue script with command-line Slurm overrides to `public-bigmem`, 4 CPU, 100G, 4-day walltime.
- New job: `9951567_7`, name `EG_B_HB_BIGMEM`, RUNNING on `cpu245`.
- Honeybee runner log updated at `2026-07-03 04:45:34 CEST` and entered `RepeatModeler Round #1`, sampling up to `40000000 bp`; this confirms the rescue is actually executing rather than merely pending.
- Pig/x_laevis longrun rescues remain RUNNING; neither has standard accepted EarlGrey output yet.
- Chunked RepeatScout+Dfam remains healthy at latest check: cattle `32/32`, opossum `7/10`, pig `10/21`, failed chunks `0`.

## 2026-07-03 05:00 CEST - rescue monitor update

- All three EarlGrey rescue jobs are now actively RUNNING:
  - `9945280_5` pig on `public-longrun-cpu`, latest internal progress around `10%`.
  - `9945299_8` x_laevis on `public-longrun-cpu`, latest internal progress around `4%`.
  - `9951567_7` western_honey_bee on `public-bigmem`, in `RepeatModeler Round #1` sampling up to `40000000 bp`.
- No EarlGrey rescue has produced accepted standard outputs yet (`annotation.gff3`, `annotation.bed`, `library.fasta`, `DONE` all still absent for the three rows).
- Chunked RepeatScout+Dfam remains healthy with `0` failed chunks. Current counts: cattle `32/32`, opossum `7/10`, pig `10/21`.
- Detailed chunk check: opossum chunks `4-10` are DONE and chunks `1-3` are still running; pig has chunks `1-4`, `6-10`, and `21` DONE, with the remaining chunks still actively logging RepeatMasker batch progress.
- `9886846` chunk finalize remains correctly PENDING on `afterok:9886845_*`.
- Next intervention remains unchanged: wait for chunk array/finalize or EarlGrey rescue completion, then validate standard outputs before submitting replacement UCSC compare chains.

## 2026-07-03 05:05 CEST - replacement compare chain submitted

- Submitted a fresh downstream R3 dependency chain so the benchmark can continue automatically after the active rescues succeed:
  - `9951603` `DENOVO_B_FINALIZE_R3`, dependency `afterok:9945280_5:9945299_8:9951567_7`.
  - `9951604` `DENOVO_B_UCSC_CMP_R3`, dependency `afterok:9951603`.
  - `9951605` `DENOVO_DFAM_B_R3`, dependency `afterok:9951603:9886846`.
  - `9951606` `DENOVO_DFAM_B_CMP_R3`, dependency `afterok:9951605`.
- Submission ledger: `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/rechain_20260703_submitted.tsv`.
- The chain is intentionally dependency-gated: final compare jobs will not run unless pig, x_laevis, and western_honey_bee EarlGrey rescues succeed and the chunked RepeatScout+Dfam finalize job succeeds.
- Current state after submission: all four R3 jobs are PENDING on dependencies, while the three EarlGrey rescue jobs and remaining RepeatScout+Dfam chunks continue running.
- Do not treat this as final evidence yet. Accepted evidence still requires standard annotation outputs plus completed reports under `ucsc_compare_full_20260630` and `dfam_augmented/ucsc_compare_full_20260630`.

## 2026-07-03 05:13 CEST - rescue monitor update

- R3 downstream chain remains healthy and dependency-gated:
  - `9951603` waits for `9945280_5`, `9945299_8`, and `9951567_7`.
  - `9951604` waits for `9951603`.
  - `9951605_[1-32%8]` waits for `9951603` and `9886846`.
  - `9951606` waits for `9951605_*`.
- EarlGrey rescues remain RUNNING and are still writing logs:
  - `pig/earlgrey` `9945280_5` on `cpu203`, no standard accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8` on `cpu203`, no standard accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7` on `cpu245`, progressed into RepeatScout `build_lmer_table`, no standard accepted outputs yet.
- Chunked RepeatScout+Dfam remains healthy with `0` FAILED chunks. Latest counts after a 5-minute poll:
  - cattle `32/32` DONE.
  - opossum `7/10` DONE; chunks `1-3` still running, at late RepeatMasker/adjudication stages.
  - pig `11/21` DONE; remaining chunks are actively logging RepeatMasker batch progress.
- `9886846` chunk finalize remains correctly PENDING on `afterok:9886845_*`; no manual compare should be run before this finalize succeeds.

## 2026-07-03 05:15 CEST - rescue health check

- Refreshed de novo monitor again; no final compare reports exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain healthy and RUNNING:
  - `9945280_5` pig: runner log advanced to about `12%` in the current internal batch; no accepted standard outputs yet.
  - `9945299_8` x_laevis: runner log advanced to about `6%` in the current internal batch; no accepted standard outputs yet.
  - `9951567_7` western_honey_bee: RepeatModeler finished round 1 with `10` families and entered round 2; no accepted standard outputs yet.
- Chunked RepeatScout+Dfam still has `0` failed chunks by both filesystem markers and `sacct` state checks.
  - opossum chunks `1-3` remain in `ProcessRepeats: Adjudicating alignments`.
  - pig chunk `5` is in adjudication; chunks `11-18` and `20` continue normal RepeatMasker batch progress.
- R3 downstream chain remains pending on dependencies; this is expected and correct.

## 2026-07-03 05:22 CEST - 5-minute poll

- No final compare reports exist yet; R3 jobs `9951603`, `9951604`, `9951605_[1-32%8]`, and `9951606` remain correctly PENDING on dependencies.
- EarlGrey rescues continue making progress:
  - `pig/earlgrey` `9945280_5`: runner log advanced to about `12%` with an internal estimate near `11h`; no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: runner log advanced to about `7%` with an internal estimate near `12h`; no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: now reporting progress around `4%` with an internal estimate near `1h`; no accepted outputs yet.
- Chunked RepeatScout+Dfam counts are unchanged after this poll but remain healthy: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.
- `9886846` remains pending on `afterok:9886845_*`; wait for remaining chunks before Dfam finalize/compare.

## 2026-07-03 05:28 CEST - continued healthy progress

- Refreshed monitor matrix and Slurm queue; no abnormal `sacct` states were observed for the active rescue, chunk, or R3 dependency jobs.
- No final compare reports exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescues continue to write logs:
  - `pig/earlgrey` `9945280_5`: about `13%`, internal estimate around `11h`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `8%`, internal estimate around `11.8h`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `10%`, internal estimate around `1.5h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam counts are unchanged but still failure-free: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.
- R3 chain remains correctly dependency-gated; no manual intervention needed unless a job exits, a dependency becomes unsatisfied, or accepted outputs appear.

## 2026-07-03 05:35 CEST - continued healthy progress

- R3 chain still has no final compare reports and remains correctly PENDING on dependencies.
- EarlGrey rescue jobs continue making progress and still have no accepted standard outputs:
  - `pig/earlgrey` `9945280_5`: about `14%`, internal estimate around `10.9h`.
  - `x_laevis/earlgrey` `9945299_8`: about `9%`, internal estimate around `11.2h`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%`, internal estimate around `1.4h`.
- Chunked RepeatScout+Dfam counts remain unchanged but healthy: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.
- `9886846` remains PENDING on the still-running `9886845_*` chunk array.

## 2026-07-03 05:36 CEST - rescue monitor update

- Refreshed monitor matrix, Slurm queue, and `sacct`; no abnormal states detected.
- No final compare reports exist yet; R3 chain remains dependency-gated.
- EarlGrey rescues remain RUNNING and log-active:
  - `pig/earlgrey` `9945280_5`: about `14%`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `9%`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `19%`, internal estimate around `1.2h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam remains unchanged but healthy: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.
- Continue waiting; next intervention is only if a rescue exits, a chunk fails/completes enough to trigger `9886846`, or standard accepted outputs appear.

## 2026-07-03 05:43 CEST - rescue monitor update

- Refreshed monitor matrix and Slurm queue; no failed markers or abnormal Slurm states observed.
- R3 downstream jobs remain dependency-gated and no final compare reports exist yet.
- EarlGrey rescues continue to write logs:
  - `pig/earlgrey` `9945280_5`: about `15%`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `10%`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `27%`, internal estimate around `1.1h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam counts remain unchanged but healthy: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.

## 2026-07-03 05:44 CEST - rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, and `sacct`; no failed markers or abnormal states observed.
- No final compare reports exist yet; R3 downstream jobs remain dependency-gated.
- EarlGrey rescues remain RUNNING:
  - `pig/earlgrey` `9945280_5`: about `15%`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `10%`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `28%`, internal estimate around `1.1h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam counts remain unchanged and failure-free: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.

## 2026-07-03 05:51 CEST - rescue monitor update

- R3 downstream chain remains dependency-gated; no final compare reports exist yet.
- No failed markers or abnormal Slurm states observed.
- EarlGrey rescues continue making progress:
  - `pig/earlgrey` `9945280_5`: about `16%`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `11%`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `33%`, internal estimate around `1.1h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam counts remain unchanged and failure-free: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.

## 2026-07-03 05:58 CEST - rescue monitor update

- R3 downstream chain remains dependency-gated; no final compare reports exist yet.
- No failed markers or abnormal Slurm states observed.
- EarlGrey rescues continue making progress:
  - `pig/earlgrey` `9945280_5`: about `17%`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `12%`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `40%`, internal estimate around `1h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam counts remain unchanged and failure-free: cattle `32/32`, opossum `7/10`, pig `11/21`, failed chunks `0`.

## 2026-07-03 06:05 CEST - current ready Label-A vs UCSC confirmation rerun

- Reran the current ready-by-design self-run RepeatMasker+Dfam Label-A vs UCSC/local strict-TE comparator audit with `scripts/experiments/compare_self_labelA_ucsc.py --jobs 1`, using the verified 24-pair manifest from `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703`.
- New confirmation output: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_CONFIRM2/`.
- Result counts: 24 paired entries; high concordance `7`, moderate `2`, low `5`, severe `10`; missing comparators `0`.
- Human assembly rows remain high: hs1/T2T `0.948128`, hg38 `0.912476`, hg19 `0.892302` bp-level Jaccard.
- This confirms the current ready RepeatMasker+Dfam Label-A vs UCSC audit, but it is separate from the still-running de novo/Dfam-augmented benchmark under `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620`; that benchmark still has no final compare output because rescue jobs remain dependency-gated.

## 2026-07-03 06:12 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after another poll; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain correctly dependency-gated: `9951603` finalize waits on active EarlGrey rescues; `9951604` base UCSC compare waits on `9951603`; Dfam jobs `9951605_[1-32%8]`/`9951606` wait on base finalize plus chunked Dfam finalize.
- EarlGrey rescue progress remains healthy but not complete:
  - `pig/earlgrey` `9945280_5`: about `19%`, still no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs.
  - `x_laevis/earlgrey` `9945299_8`: about `14%`, still no accepted outputs.
  - `western_honey_bee/earlgrey` `9951567_7`: about `49%`, still no accepted outputs.
- Chunked RepeatScout+Dfam remains failure-free: cattle `32/32`, opossum `7/10`, pig `13/21`, failed chunks `0`.
- No final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.

## 2026-07-03 06:23 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after a 10-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete:
  - `pig/earlgrey` `9945280_5`: about `20%`, estimated remaining time around `10h20m`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `16%`, estimated remaining time around `9h55m`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `60%`, estimated remaining time around `42m`, no accepted outputs yet.
- Chunked RepeatScout+Dfam remains failure-free: cattle `32/32`, opossum `7/10`, pig `13/21`, failed chunks `0`.
- No intervention was made because all active jobs are progressing and the pending finalize/compare dependencies are still valid.

## 2026-07-03 06:44 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after a 20-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete:
  - `pig/earlgrey` `9945280_5`: about `23%`, estimated remaining time around `10h05m`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `18%`, estimated remaining time around `9h55m`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: about `78%`, estimated remaining time around `24m`, no accepted outputs yet.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `7/10`, pig `13/21`, failed chunks `0`.
- No intervention was made; active jobs continue to progress and dependency-gated finalize/compare jobs remain valid.

## 2026-07-03 07:15 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after a 30-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete:
  - `pig/earlgrey` `9945280_5`: about `26%`, estimated remaining time around `9h36m`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `22%`, estimated remaining time around `10h`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: no accepted outputs yet; runner progressed past the previous percentage phase into `RepeatModeler Round #3` after RECON/family refinement, still running.
- Chunked RepeatScout+Dfam remains failure-free and improved: cattle `32/32`, opossum `7/10`, pig `16/21`, failed chunks `0`.
- No intervention was made; active jobs continue to progress and dependency-gated finalize/compare jobs remain valid.

## 2026-07-03 07:46 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after another 30-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete:
  - `pig/earlgrey` `9945280_5`: about `30%`, estimated remaining time around `9h12m`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `25%`, estimated remaining time around `10h`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: still running; entered an all-by-other comparisons phase with `1,378,630` comparisons and an ETA around `10-11h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam remains failure-free and improved: cattle `32/32`, opossum `8/10`, pig `19/21`, failed chunks `0`.
- No intervention was made; active jobs continue to progress and dependency-gated finalize/compare jobs remain valid.

## 2026-07-03 08:49 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after a 60-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete:
  - `pig/earlgrey` `9945280_5`: about `38%`, estimated remaining time around `8h06m`, no accepted outputs yet.
  - `x_laevis/earlgrey` `9945299_8`: about `32%`, estimated remaining time around `9h11m`, no accepted outputs yet.
  - `western_honey_bee/earlgrey` `9951567_7`: still running in all-by-other comparisons; around `7%` in this phase with ETA fluctuating around `16h`, no accepted outputs yet.
- Chunked RepeatScout+Dfam remains failure-free and improved: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- No intervention was made; active jobs continue to progress and dependency-gated finalize/compare jobs remain valid.

## 2026-07-03 08:51 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor and inspected remaining active chunk directories; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `38%`, estimated remaining time around `8h05m`.
  - `x_laevis/earlgrey` `9945299_8`: about `32%`, estimated remaining time around `9h06m`.
  - `western_honey_bee/earlgrey` `9951567_7`: around `7%` in the current all-by-other comparison phase, ETA fluctuating around `16h`.
- Chunked RepeatScout+Dfam remains failure-free: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories are precisely: opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`; active array tasks remain `9886845_33`, `9886845_34`, and `9886845_57`.
- No intervention was made because the remaining jobs are still running and dependencies remain valid.

## 2026-07-03 09:53 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor after a 60-minute wait; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `46%`, estimated remaining time around `7h06m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h09m`.
  - `western_honey_bee/earlgrey` `9951567_7`: around `15%` in the current all-by-other comparison phase, ETA around `12h30m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining active chunk array tasks remain `9886845_33`, `9886845_34`, and `9886845_57`; no intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 09:54 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `46%`, estimated remaining time around `7h06m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h09m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `15%` in the current all-by-other comparison phase, ETA around `12h27m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories remain opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 09:55 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `46%`, estimated remaining time around `7h04m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h06m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%` in the current all-by-other comparison phase, ETA around `12h28m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories remain opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 09:57 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `46%`, estimated remaining time around `7h03m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h03m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%` in the current all-by-other comparison phase, ETA around `12h20m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories remain opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 09:58 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `47%`, estimated remaining time around `7h02m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h03m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%` in the current all-by-other comparison phase, ETA around `12h18m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories remain opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 09:59 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `47%`, estimated remaining time around `7h00m`.
  - `x_laevis/earlgrey` `9945299_8`: about `40%`, estimated remaining time around `8h02m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%` in the current all-by-other comparison phase, ETA around `12h18m`.
- Chunked RepeatScout+Dfam remains failure-free but unchanged: cattle `32/32`, opossum `8/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories remain opossum `chunk0001`, opossum `chunk0002`, and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 10:00 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor; no abnormal Slurm states and no failed chunk markers were observed.
- R3 downstream jobs remain dependency-gated; no final compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue jobs remain active but incomplete, with no accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs yet:
  - `pig/earlgrey` `9945280_5`: about `47%`, estimated remaining time around `6h59m`.
  - `x_laevis/earlgrey` `9945299_8`: about `41%`, estimated remaining time around `8h01m`.
  - `western_honey_bee/earlgrey` `9951567_7`: about `16%` in the current all-by-other comparison phase, ETA around `12h15m`.
- Chunked RepeatScout+Dfam remains failure-free and improved: cattle `32/32`, opossum `9/10`, pig `20/21`, failed chunks `0`.
- Remaining non-DONE chunk directories are now opossum `chunk0001` and pig `chunk0015`.
- No intervention was made because all active jobs are still running and dependencies remain valid.

## 2026-07-03 10:07 CEST - repeatmasker-dfam ready-view UCSC comparison rerun

- User requested another comparison of the current annotation results against UCSC and asked whether the current folder layout/`RM_*` cleanup status is still appropriate.
- Reran the current ready-by-design self-run RepeatMasker+Dfam Label-A vs UCSC/local strict-TE comparator audit via `srun -p public-short-cpu -c 4`.
- New output: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_CONFIRM3/`.
- Result: 24 paired entries, no missing UCSC/local comparator; concordance classes are high=7, moderate=2, low=5, severe=10; mean bp-level Jaccard is `0.394736`.
- Key high-concordance rows: human hs1 `0.948128`, human_hg38 `0.912476`, human_hg19 `0.892302`, mouse `0.892472`, fruit_fly `0.888725`, zebrafish `0.837603`, c_elegans `0.833784`.
- Key moderate rows: horse `0.791397`, pig `0.582164`; cattle/opossum/chicken are low, and several plant/amphibian/insect rows remain severe under this strict UCSC/local comparator view.
- Important distinction: this confirms the ready RepeatMasker+Dfam Label-A vs UCSC audit, but it is not the final de novo/Dfam-augmented benchmark compare. The de novo benchmark still has 0 final compare files because R3 finalize/compare jobs remain dependency-gated behind active EarlGrey and chunked RepeatScout rescues.
- Layout status: formal ready-to-use RepeatMasker+Dfam outputs remain under `software_outputs/repeatmasker_dfam/02_ready_by_design/...`; raw self-run provenance remains under `software_outputs/repeatmasker_dfam/raw_runs/self_labelA/...`; current de novo benchmark work remains isolated under `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620`.
- Cleanup status: root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories are currently absent. The example `RM_892559.ThuJun180438082026` exists only inside `software_outputs/repeatmasker_dfam/99_internal/rm_scratch_quarantine_20260619/`. It is a cleanup candidate, but deletion should wait until final de novo/Dfam compare reports are produced and accepted; do not delete active de novo run-root `RM_*` directories under RepeatModeler outputs because they are provenance/working outputs for completed de novo tools.

## 2026-07-03 10:09 CEST - de novo rescue monitor update

- Refreshed de novo benchmark monitor, Slurm queue, active logs, chunk manifest, and compare directories.
- No abnormal Slurm states were observed. Active jobs remain `RUNNING`: pig EarlGrey `9945280_5`, X. laevis EarlGrey `9945299_8`, western_honey_bee EarlGrey bigmem `9951567_7`, opossum chunked RepeatScout+Dfam `9886845_33`, and pig chunked RepeatScout+Dfam `9886845_57`.
- R3 downstream jobs remain correctly dependency-gated: `9886846` waits on `9886845_*`; `9951603` waits on active EarlGrey rescues; `9951604`, `9951605_[1-32%8]`, and `9951606` wait on those finalizers.
- No final de novo UCSC compare files exist yet under `ucsc_compare_full_20260630` or `dfam_augmented/ucsc_compare_full_20260630`.
- EarlGrey rescue progress remains active but incomplete: pig about `48%` with ETA about `6h48m`; X. laevis about `42%` with ETA about `7h53m`; western_honey_bee about `17%` with ETA about `12h24m`; none has accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` outputs.
- Chunked RepeatScout+Dfam status remains cattle `32/32`, opossum `9/10`, pig `20/21`, failed chunks `0`. The active remaining chunks are exactly manifest task `33` = opossum `chunk0001` and task `57` = pig `chunk0015`; both are in `ProcessRepeats: Adjudicating alignments`.
- No intervention was made. Manual finalize/compare would be premature until these active dependencies complete.

## 2026-07-03 10:16 CEST - de novo rescue monitor update

- Rechecked after a 5-minute wait. No abnormal Slurm states were observed and no final compare files exist yet.
- Progress: pig chunked RepeatScout+Dfam task `9886845_57` completed successfully in `08:34:29`; pig `chunk0015` now has `DONE`, `.out`, `.out.gff`, `.tbl`, `.cat.gz`, and `.masked`.
- Chunk counts are now cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Remaining chunk dependency is only opossum `chunk0001` / task `9886845_33`, still RUNNING in `ProcessRepeats: Adjudicating alignments`. Therefore `9886846` chunk finalize correctly remains PENDING.
- EarlGrey rescue jobs continue to progress without accepted final outputs yet: pig `9945280_5` about `49%` with ETA about `6h42m`; X. laevis `9945299_8` about `42%` with ETA about `7h46m`; western_honey_bee `9951567_7` about `18%` with ETA about `12h08m`.
- Downstream R3 finalize/compare jobs remain valid dependency waits; no repair or duplicate submission was made.

## 2026-07-03 10:18 CEST - de novo rescue monitor update

- Refreshed context, monitor matrices, Slurm queue, active logs, and compare directories.
- No final de novo UCSC compare files exist yet; `9951604` and `9951606` remain correctly dependency-pending.
- No abnormal Slurm states were observed. Active jobs remain `9945280_5` pig EarlGrey, `9945299_8` X. laevis EarlGrey, `9951567_7` western_honey_bee EarlGrey, and `9886845_33` opossum chunked RepeatScout+Dfam.
- EarlGrey logs continue to update: pig about `49%` with ETA about `6h40m`; X. laevis advanced to about `43%` with ETA about `7h44m`; western_honey_bee remains about `18%` with ETA about `12h10m`. No accepted `annotation.gff3`/`annotation.bed`/`library.fasta`/`DONE` markers yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`. The only remaining chunk is opossum `chunk0001` / `9886845_33`, still in `ProcessRepeats: Adjudicating alignments`; `9886846` finalize remains correctly pending on it.
- No manual finalize/compare was run; the next actionable event is completion of `9886845_33` or any of the three EarlGrey rescue jobs.

## 2026-07-03 10:19 CEST - de novo rescue monitor update

- Refreshed context, monitor matrices, Slurm queue, active logs, chunk state, compare directories, and real-time resource usage for the remaining long chunk.
- No final de novo UCSC compare files exist yet; downstream `9951604` and `9951606` remain dependency-pending and have not run.
- No abnormal Slurm states were observed. Active jobs remain pig EarlGrey `9945280_5`, X. laevis EarlGrey `9945299_8`, western_honey_bee EarlGrey `9951567_7`, and opossum chunked RepeatScout+Dfam `9886845_33`.
- EarlGrey logs continue to update but no accepted final markers exist yet: pig about `49%` with ETA about `6h38m`; X. laevis about `43%` with ETA about `7h44m`; western_honey_bee about `18%` with ETA about `12h10m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` log is still at `ProcessRepeats: Adjudicating alignments`, but `scontrol`/`sstat` confirm it is not a ghost job: actual JobId `9888508` for array task `9886845_33` is RUNNING on `cpu207`, with batch `AveCPU=6-08:00:47`, `MaxRSS=9227436K`, large disk read/write, and TimeLimit `4-00:00:00`.
- No repair, cancellation, duplicate submission, finalize, or compare was performed.

## 2026-07-03 10:21 CEST - de novo rescue monitor update

- Refreshed context, monitor matrix, Slurm queue, compare directories, EarlGrey logs, chunk markers, and real-time resource usage for the remaining opossum chunk.
- No final de novo UCSC compare files exist yet. Downstream `9886846`, `9951603`, `9951604`, `9951605_[1-32%8]`, and `9951606` remain valid dependency waits.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig advanced to about `50%` with ETA about `6h37m`; X. laevis remains about `43%` with ETA about `7h43m`; western_honey_bee remains about `18%` with ETA about `12h06m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / array task `9886845_33` remains RUNNING in `ProcessRepeats: Adjudicating alignments`; actual JobId `9888508` still shows active resource accounting (`AveCPU=6-08:02:05`, `MaxRSS=9227720K`, large disk read/write), so it should be allowed to continue.
- No intervention was made.

## 2026-07-03 10:22 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, EarlGrey logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending and have not run.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `50%` with ETA about `6h36m`; X. laevis remains about `43%` with ETA about `7h43m`; western_honey_bee advanced to about `19%` with ETA about `11h57m`. No accepted final markers yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` shows continued resource accounting (`AveCPU=6-08:03:26`, `MaxRSS=9227900K`), so no cancellation or duplicate submission is warranted.
- No intervention was made.

## 2026-07-03 10:23 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active job logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey status: pig remains about `50%` with ETA about `6h34m`; X. laevis remains about `43%` with ETA about `7h43m`; western_honey_bee remains about `19%` with latest ETA about `11h57m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:04:43`, `MaxRSS=9228032K`). This still looks like a long `ProcessRepeats` adjudication, not a scheduler ghost.
- No intervention was made.

## 2026-07-03 10:25 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active job logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream `9886846`, `9951603`, `9951604`, `9951605_[1-32%8]`, and `9951606` remain dependency-pending and have not run.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `50%` with ETA about `6h33m`; X. laevis remains about `43%` with ETA about `7h41m`; western_honey_bee remains about `19%` with ETA about `12h00m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:06:24`, `MaxRSS=9228496K`). Still no reason to cancel or resubmit.
- No intervention was made.

## 2026-07-03 10:26 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active job logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `50%` with ETA about `6h32m`; X. laevis advanced to about `44%` with ETA about `7h38m`; western_honey_bee remains about `19%` with ETA about `11h59m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:07:40`, `MaxRSS=9229140K`). No intervention was made.

## 2026-07-03 10:28 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `50%` with ETA about `6h30m`; X. laevis remains about `44%` with ETA about `7h35m`; western_honey_bee remains about `19%` with ETA about `11h51m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:08:55`, `MaxRSS≈9013M`). No intervention was made.

## 2026-07-03 10:29 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig advanced to about `51%` with ETA about `6h28m`; X. laevis remains about `44%` with ETA about `7h30m`; western_honey_bee remains about `19%` with latest ETA about `11h51m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:10:11`, `MaxRSS=9229544K`). No intervention was made.

## 2026-07-03 10:31 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `51%` with ETA about `6h26m`; X. laevis advanced to about `45%` with ETA about `7h27m`; western_honey_bee remains about `19%` with latest ETA about `12h00m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:12:27`, `MaxRSS=9230068K`). No intervention was made.

## 2026-07-03 10:32 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `51%` with ETA about `6h24m`; X. laevis remains about `45%` with ETA about `7h26m`; western_honey_bee advanced to about `20%` with ETA about `11h56m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:13:48`, `MaxRSS=9234776K`). No intervention was made.

## 2026-07-03 10:33 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `51%` with ETA about `6h24m`; X. laevis remains about `45%` with ETA about `7h23m`; western_honey_bee remains about `20%` with ETA about `11h56m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` crossed 24h runtime but remains within the 4-day walltime and continues to accrue resource counters (`AveCPU=6-08:15:06`, `MaxRSS=9234904K`). No intervention was made.

## 2026-07-03 10:35 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `51%` with ETA about `6h21m`; X. laevis remains about `45%` with ETA about `7h20m`; western_honey_bee remains about `20%` with ETA about `11h55m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:16:28`, `MaxRSS=9235088K`). No intervention was made.

## 2026-07-03 10:36 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig advanced to about `52%` with ETA about `6h19m`; X. laevis remains about `45%` with ETA about `7h19m`; western_honey_bee remains about `20%` with latest ETA about `11h54m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:18:00`, `MaxRSS=9235496K`). No intervention was made.

## 2026-07-03 10:38 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `52%` with ETA about `6h18m`; X. laevis advanced to about `46%` with ETA about `7h16m`; western_honey_bee remains about `20%` with ETA about `11h55m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:19:36`, `MaxRSS=9236032K`). No intervention was made.

## 2026-07-03 10:39 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `52%` with ETA about `6h17m`; X. laevis remains about `46%` with ETA about `7h15m`; western_honey_bee remains about `20%` with ETA about `11h55m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:20:46`, `MaxRSS=9236312K`). No intervention was made.

## 2026-07-03 10:40 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `52%` with ETA about `6h16m`; X. laevis remains about `46%` with ETA about `7h15m`; western_honey_bee remains about `20%` with ETA about `11h55m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:22:04`, `MaxRSS=9252920K`). No intervention was made.

## 2026-07-03 10:42 CEST - de novo rescue monitor update

- Refreshed monitor matrix, Slurm queue, compare directories, active logs, chunk markers, and resource counters.
- No final de novo UCSC compare files exist yet; downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed.
- EarlGrey logs continue to update: pig remains about `52%` with ETA about `6h14m`; X. laevis remains about `46%` with ETA about `7h15m`; western_honey_bee advanced to about `21%` with ETA about `11h56m`. No accepted final markers exist yet.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-08:23:23`, `MaxRSS=9252920K`). No intervention was made.

## 2026-07-03 10:47 CEST - current annotation vs UCSC and layout audit

- Rechecked the current ready-by-design RepeatMasker+Dfam self Label-A vs UCSC/local strict-TE comparator report at `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_CONFIRM3`.
- The report covers 24 paired species/assemblies and remains consistent with the stable current-ready evidence: `high=7`, `moderate=2`, `low=5`, `severe=10`. Top high-concordance entries include hs1 (`Jaccard=0.948128`), hg38 (`0.912476`), mouse (`0.892472`), hg19 (`0.892302`), fruit_fly (`0.888725`), zebrafish (`0.837603`), and c_elegans (`0.833784`).
- `02_ready_by_design` remains allocated by design and role (`fine_tune`/`eval_only`) with 803 symlinks and 0 broken symlinks. It contains current self Label-A links to `raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617` plus UCSC comparator links under `annotations/ucsc_comparator`.
- Root-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories are absent. The old `RM_892559.ThuJun180438082026` and related scratch directories exist only under `software_outputs/repeatmasker_dfam/99_internal/rm_scratch_quarantine_20260619` and total about 60K; they are cleanup-safe if no manual forensic/debug inspection is needed.
- Important separation: the de novo benchmark annotation chain is not yet comparable against UCSC because final compare directories are still empty and the downstream finalize/compare jobs remain dependency-pending.

## 2026-07-03 11:08 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; `DENOVO_B_FINALIZE_R3`, `DENOVO_B_UCSC_CMP_R3`, `DENOVO_DFAM_B_R3`, and `DENOVO_DFAM_B_CMP_R3` are still dependency-pending.
- Active EarlGrey rescues continue to progress: pig about `56%` with ETA about `5h48m`, X. laevis about `49%` with ETA about `6h47m`, and western_honey_bee about `23%` with ETA about `11h25m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING; actual JobId `9888508` continues to accrue resource counters (`AveCPU=6-08:49:13`, `MaxRSS=9252920K`). No intervention was made.

## 2026-07-03 11:38 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs are still dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `59%` with ETA about `5h18m`, X. laevis about `53%` with ETA about `6h21m`, and western_honey_bee about `26%` with ETA about `11h20m`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-09:20:14`, `MaxRSS=9259692K`). No intervention was made.

## 2026-07-03 12:30 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `66%` with ETA about `4h22m`, X. laevis about `59%` with ETA about `5h28m`, and western_honey_bee about `32%` with ETA about `10h32m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING. No intervention was made.

## 2026-07-03 13:00 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `70%` with ETA about `3h52m`, X. laevis about `63%` with ETA about `4h54m`, and western_honey_bee about `35%` with ETA about `10h05m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING. No intervention was made.

## 2026-07-03 13:05 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `71%` with ETA about `3h48m`, X. laevis about `64%` with ETA about `4h51m`, and western_honey_bee about `35%` with ETA about `10h00m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-10:44:37`, `MaxRSS=9285428K`). No intervention was made.

## 2026-07-03 13:35 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `74%` with ETA about `3h19m`, X. laevis about `68%` with ETA about `4h19m`, and western_honey_bee about `39%` with ETA about `9h23m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING. No intervention was made.

## 2026-07-03 14:05 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `78%` with ETA about `2h50m`, X. laevis about `72%` with ETA about `3h39m`, and western_honey_bee about `43%` with ETA about `8h40m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING. No intervention was made.

## 2026-07-03 14:35 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `82%` with ETA about `2h21m`, X. laevis about `76%` with ETA about `3h05m`, and western_honey_bee about `45%` with ETA about `8h22m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-12:15:34`, `MaxRSS=9314808K`); its Slurm stdout/stderr files are empty, with no error message. No intervention was made.

## 2026-07-03 14:37 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `82%` with ETA about `2h18m`, X. laevis about `76%` with ETA about `3h03m`, and western_honey_bee about `46%` with ETA about `8h16m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Monitor matrix still shows base pending rows only for pig/X. laevis/western_honey_bee EarlGrey. Dfam-augmented RepeatScout rows for cattle/pig/opossum remain `running` until the chunk/finalize chain closes; Dfam-augmented EarlGrey rows remain `missing` and should be interpreted by the R3 compare contract, not manually filled.

## 2026-07-03 15:07 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `86%` with ETA about `1h48m`, X. laevis about `80%` with ETA about `2h38m`, and western_honey_bee about `48%` with ETA about `7h57m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- No intervention was made.

## 2026-07-03 15:37 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `89%` with ETA about `1h20m`, X. laevis about `83%` with ETA about `2h08m`, and western_honey_bee about `51%` with ETA about `7h34m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-13:17:33`, `MaxRSS=9360712K`). No intervention was made.

## 2026-07-03 15:39 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `90%` with ETA about `1h18m`, X. laevis about `84%` with ETA about `2h06m`, and western_honey_bee about `51%` with ETA about `7h32m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-13:18:50`, `MaxRSS=9361356K`). No intervention was made.

## 2026-07-03 16:09 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `94%` with ETA about `47m`, X. laevis about `88%` with ETA about `1h35m`, and western_honey_bee about `55%` with ETA about `6h57m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- No intervention was made.

## 2026-07-03 16:39 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Active EarlGrey rescues continue to progress: pig about `97%` with ETA about `18m`, X. laevis about `91%` with ETA about `1h04m`, and western_honey_bee about `58%` with ETA about `6h31m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-14:19:16`, `MaxRSS=9387316K`). No intervention was made.

## 2026-07-03 17:10 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey has passed the coarse percent-progress stage and is in final repeat-model/redefinition/search steps (`RECON` / `Searching for Repeats`) but has not yet emitted accepted final markers.
- X. laevis EarlGrey is about `95%` with ETA about `33m`; western_honey_bee EarlGrey is about `61%` with ETA about `5h54m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-14:49:49`, `MaxRSS=9402288K`). No intervention was made.

## 2026-07-03 17:11 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in final RepeatModeler Round #5 sampling/searching and has not emitted accepted final markers.
- X. laevis EarlGrey is about `96%` with ETA about `31m`; western_honey_bee EarlGrey is about `62%` with ETA about `5h54m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-14:50:56`, `MaxRSS=9402888K`). No intervention was made.

## 2026-07-03 17:41 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in final RepeatModeler cleanup/masking steps (`TRFMask` / masking repeats from previous rounds) and has not emitted accepted final markers.
- X. laevis EarlGrey is about `99%` with ETA about `2m`; western_honey_bee EarlGrey is about `65%` with ETA about `5h27m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Opossum `chunk0001` / `9886845_33` remains RUNNING and continues to accrue resource counters (`AveCPU=6-15:22:08`, `MaxRSS=9419940K`). No intervention was made.

## 2026-07-03 18:03 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey entered a large comparison/search phase after RepeatModeler Round #5 (`Total Comparisons = 23670640`); the early `0%` ETA is noisy but the job has a 10-day `public-longrun-cpu` walltime and remains RUNNING.
- X. laevis EarlGrey also entered RepeatModeler Round #5 sampling/search after reaching 99%; western_honey_bee EarlGrey is about `67%` with ETA about `5h`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Checked job limits: pig/X. laevis longrun rescues have `TimeLimit=10-00:00:00`; honeybee and opossum chunk have `TimeLimit=4-00:00:00`. No intervention was made.

## 2026-07-03 18:04 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Base monitor matrix still has only three running rows: pig EarlGrey, X. laevis EarlGrey, and western_honey_bee EarlGrey. None has emitted accepted final markers yet.
- Pig EarlGrey remains in the large all-by-other comparison phase after sampling (`Total Comparisons = 23670640`); X. laevis remains in RepeatModeler Round #5 sampling; western_honey_bee EarlGrey is about `68%` with ETA about `4h57m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`; opossum chunk continues to accrue resource counters (`AveCPU=6-15:45:00`, `MaxRSS=9433624K`).
- Dfam-augmented monitor matrix still shows RepeatScout rows for cattle/pig/opossum as `running` until chunk/finalize closure; Dfam-augmented EarlGrey rows remain `missing` and should be interpreted by the R3 compare contract, not manually filled. No intervention was made.

## 2026-07-03 18:36 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in the large all-by-other comparison phase at early `0%` progress; ETA remains noisy around ~98-100h but job walltime remains sufficient.
- X. laevis EarlGrey moved from Round #5 sampling into `TRFMask` / masking repeats from previous rounds; western_honey_bee EarlGrey is about `72%` with ETA about `4h14m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`; opossum chunk continues to accrue resource counters (`AveCPU=6-16:16:09`, `MaxRSS=9455196K`).
- No intervention was made.

## 2026-07-03 18:38 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Base monitor matrix still has only three running rows: pig EarlGrey, X. laevis EarlGrey, and western_honey_bee EarlGrey. None has emitted accepted final markers.
- Pig EarlGrey remains in all-by-other comparison at early `0%`; X. laevis remains in previous-round masking; western_honey_bee EarlGrey is about `72%`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`; opossum chunk continues to accrue resource counters (`AveCPU=6-16:17:18`, `MaxRSS=9456112K`).
- Dfam-augmented matrix remains unchanged: RepeatScout rows for cattle/pig/opossum are still `running` until chunk/finalize closure; Dfam-augmented EarlGrey rows remain `missing` by current R3 design. No intervention was made.

## 2026-07-03 18:40 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in all-by-other comparison at early `0%`; X. laevis remains in previous-round masking; western_honey_bee EarlGrey is about `72%`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters confirm the running jobs are still active rather than stale: pig EarlGrey `AveCPU=2-16:05:33`, X. laevis EarlGrey `AveCPU=2-13:25:09`, honeybee EarlGrey `AveCPU=2-03:15:31`, opossum chunk `AveCPU=6-16:18:41`. No intervention was made.

## 2026-07-03 18:41 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in all-by-other comparison at early `0%`; X. laevis remains in previous-round masking; western_honey_bee EarlGrey is about `72%`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-16:09:41`, X. laevis EarlGrey `AveCPU=2-13:29:34`, honeybee EarlGrey `AveCPU=2-03:19:50`, opossum chunk `AveCPU=6-16:19:59`. No intervention was made.

## 2026-07-03 18:42 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey remains in all-by-other comparison at early `0%`; X. laevis remains in previous-round masking; western_honey_bee EarlGrey is about `72%` with ETA about `4h12m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters confirm active jobs: pig EarlGrey `AveCPU=2-16:14:13`, X. laevis EarlGrey `AveCPU=2-13:34:21`, honeybee EarlGrey `AveCPU=2-03:24:29`, opossum chunk `AveCPU=6-16:21:11`. No intervention was made.

## 2026-07-03 19:12 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; all downstream finalize/compare jobs remain dependency-pending.
- No abnormal Slurm states were observed in `sacct`.
- Pig EarlGrey all-by-other comparison has advanced from `0%` to `1%`, confirming the long comparison stage is progressing; noisy ETA remains about `105h`.
- X. laevis EarlGrey remains in previous-round masking; western_honey_bee EarlGrey advanced to about `75%` with ETA about `3h44m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-18:12:22`, X. laevis EarlGrey `AveCPU=2-15:36:00`, honeybee EarlGrey `AveCPU=2-05:23:08`, opossum chunk `AveCPU=6-16:51:37`. No intervention was made.

## 2026-07-03 19:25 CEST - de novo rescue monitor update

- De novo final compare directories remain empty; base finalize `9951603`, base UCSC compare `9951604`, Dfam rerun `9951605_*`, and Dfam compare `9951606` are still dependency-pending. No manual finalize/compare was launched because the dependency chain is not yet satisfied.
- No abnormal Slurm states were observed in `sacct`.
- Base monitor matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`.
- Pig EarlGrey remains in all-by-other comparison at `1%` with noisy ETA around `107h`. X. laevis has now entered all-by-other comparisons at `0%` after previous-round masking/sampling. Western honeybee EarlGrey advanced to `77%` with ETA around `3h26m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`; opossum chunk `9886845_33` is still running.
- Resource counters continue to grow and support non-stale execution: pig EarlGrey `AveCPU=2-19:05:13`, X. laevis EarlGrey `AveCPU=2-16:26:45`, honeybee EarlGrey `AveCPU=2-06:16:12`, opossum chunk `AveCPU=6-17:05:18`.

## 2026-07-03 19:28 CEST - de novo rescue monitor update

- Slurm dependency chain is unchanged: base finalize `9951603`, base UCSC compare `9951604`, Dfam rerun `9951605_*`, Dfam compare `9951606`, and Dfam chunk finalize `9886846` are still pending on active upstream jobs.
- No abnormal Slurm states were observed in `sacct`; final full compare directories remain empty.
- Base monitor matrix still has only `pig`, `x_laevis`, and `western_honey_bee` EarlGrey as running. No EarlGrey final markers (`DONE`, `annotation.gff3`, `annotation.bed`, `library.fasta`) were present for these three species.
- Latest logs show pig EarlGrey still at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison, and western honeybee at `77%` with ETA about `3h24m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:13:31`, X. laevis EarlGrey `AveCPU=2-16:34:58`, honeybee EarlGrey `AveCPU=2-06:24:33`, opossum chunk `AveCPU=6-17:07:26`. No intervention was made.

## 2026-07-03 19:30 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: `9951603`, `9951604`, `9886846`, `9951605_*`, and `9951606` are still dependency-pending; final full compare directories remain empty.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, `western_honey_bee`; no final EarlGrey markers were present for those species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with ETA dropping to about `90h`, and western honeybee at `77%` with ETA about `3h23m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:21:47`, X. laevis EarlGrey `AveCPU=2-16:42:55`, honeybee EarlGrey `AveCPU=2-06:32:49`, opossum chunk `AveCPU=6-17:09:34`. No intervention was made.

## 2026-07-03 19:32 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `97h`, and western honeybee advanced from `77%` to `78%` with ETA about `3h18m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:29:46`, X. laevis EarlGrey `AveCPU=2-16:50:56`, honeybee EarlGrey `AveCPU=2-06:40:48`, opossum chunk `AveCPU=6-17:11:38`. No intervention was made.

## 2026-07-03 19:35 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `105h`, and western honeybee at `78%` with ETA about `3h16m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:38:35`, X. laevis EarlGrey `AveCPU=2-16:59:45`, honeybee EarlGrey `AveCPU=2-06:49:42`, opossum chunk `AveCPU=6-17:13:55`. No intervention was made.

## 2026-07-03 19:37 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `107h`, and western honeybee at `78%` with ETA about `3h14m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:48:39`, X. laevis EarlGrey `AveCPU=2-17:09:40`, honeybee EarlGrey `AveCPU=2-06:59:40`, opossum chunk `AveCPU=6-17:16:30`. No intervention was made.

## 2026-07-03 19:39 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `95h`, and western honeybee advanced to `79%` with ETA about `3h12m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-19:56:55`, X. laevis EarlGrey `AveCPU=2-17:17:45`, honeybee EarlGrey `AveCPU=2-07:08:00`, opossum chunk `AveCPU=6-17:18:38`. No intervention was made.

## 2026-07-03 19:44 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `95h`, and western honeybee at `79%` with ETA about `3h10m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:13:28`, X. laevis EarlGrey `AveCPU=2-17:34:14`, honeybee EarlGrey `AveCPU=2-07:24:54`, opossum chunk `AveCPU=6-17:22:55`. No intervention was made.

## 2026-07-03 19:46 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `94h`, and western honeybee at `79%` with ETA about `3h09m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:21:29`, X. laevis EarlGrey `AveCPU=2-17:42:15`, honeybee EarlGrey `AveCPU=2-07:33:03`, opossum chunk `AveCPU=6-17:25:01`. No intervention was made.

## 2026-07-03 19:48 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `91h`, and western honeybee at `79%` with ETA about `3h07m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:29:50`, X. laevis EarlGrey `AveCPU=2-17:50:33`, honeybee EarlGrey `AveCPU=2-07:41:24`, opossum chunk `AveCPU=6-17:27:10`. No intervention was made.

## 2026-07-03 19:50 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `94h`, and western honeybee at `79%` with ETA about `3h06m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:38:53`, X. laevis EarlGrey `AveCPU=2-17:59:30`, honeybee EarlGrey `AveCPU=2-07:50:30`, opossum chunk `AveCPU=6-17:29:30`. No intervention was made.

## 2026-07-03 19:53 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `86h`, and western honeybee advanced to `80%` with ETA about `3h05m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:48:34`, X. laevis EarlGrey `AveCPU=2-18:09:10`, honeybee EarlGrey `AveCPU=2-08:00:25`, opossum chunk `AveCPU=6-17:32:03`. No intervention was made.

## 2026-07-03 19:55 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `84h`, and western honeybee at `80%` with ETA about `3h02m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-20:58:10`, X. laevis EarlGrey `AveCPU=2-18:18:36`, honeybee EarlGrey `AveCPU=2-08:09:57`, opossum chunk `AveCPU=6-17:34:30`. No intervention was made.

## 2026-07-03 19:58 CEST - de novo rescue monitor update

- Slurm dependency chain remains unchanged: base/Dfam finalize and compare jobs are still dependency-pending, and final full compare directories contain `0` files.
- No abnormal Slurm states were observed in `sacct`.
- Base matrix still has three running EarlGrey rows: `pig`, `x_laevis`, and `western_honey_bee`; no final EarlGrey markers were present for these three species.
- Latest logs show pig EarlGrey at `1%` all-by-other comparison, X. laevis at `0%` all-by-other comparison with noisy ETA around `85h`, and western honeybee at `80%` with ETA about `2h59m`.
- Chunked RepeatScout+Dfam remains cattle `32/32`, opossum `9/10`, pig `21/21`, failed chunks `0`.
- Resource counters continue to grow: pig EarlGrey `AveCPU=2-21:07:20`, X. laevis EarlGrey `AveCPU=2-18:27:40`, honeybee EarlGrey `AveCPU=2-08:19:00`, opossum chunk `AveCPU=6-17:36:51`. No intervention was made.

- 2026-07-03 20:09 CEST - RepeatMasker+Dfam self Label-A vs UCSC fresh rerun completed: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_200218_FRESH` was generated from current `02_ready_by_design/manifests/MANIFEST_ALL.tsv` with a fresh species-deduplicated pair manifest. Result is byte-identical to `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_SINGLE` for `summary.tsv` and `qc_flags.tsv`: 24 paired entries, high=7, moderate=2, low=5, severe=10, missing strict comparators=6 (`setaria_italica`, `tomato`, `wild_rice`, `arabidopsis_lyrata`, `grape`, `green_foxtail`). Ready-by-design audit: 803 symlinks, 424 self Label-A links, 273 UCSC comparator links, 106 genome links, 0 broken links. Separate de novo benchmark jobs remain running/pending; do not treat this Label-A concordance rerun as de novo completion.

- 2026-07-03 20:10 CEST - de novo benchmark monitor update: full UCSC compare output dirs are still empty because downstream finalize/compare jobs remain dependency-gated. Slurm abnormal check for `9886845/9886846/9945280_5/9945299_8/9951567_7/9951603-9951606` reported no FAILED/CANCELLED/OOM states. Running gates: `9945280_5` pig EarlGrey at 1% with runner log updating and `sstat` CPU/disk counters growing; `9945299_8` X. laevis EarlGrey at 1% with runner log updating and counters growing; `9951567_7` western_honey_bee EarlGrey at 81% with ETA about 2h50m and counters growing; `9886845_33` opossum Dfam RepeatScout chunk rescue still running with chunks 9/10 DONE and 0 FAILED. Dfam chunk counts: cattle 32/32, pig 21/21, opossum 9/10. No intervention taken because active jobs are alive and dependency chain is intact.

- 2026-07-03 20:13 CEST - de novo benchmark monitor detail: dependency chain still intact and no Slurm abnormal states. Base EarlGrey gates remain running: pig advanced to 2% with log updating; X. laevis remains 1%; western_honey_bee remains 81% with ETA about 2h49m. Dfam RepeatScout chunked rescue: cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE and 0 FAILED. The remaining opossum chunk is `chunk0001`; its runner is actively processing RepeatMasker batches around 30529/62171, and job `9888508` has TimeLimit until 2026-07-06 10:33 CEST. No finalize/compare outputs yet because `9951603/9951604/9951605/9951606` are still dependency-gated. No cancellation/requeue submitted.

- 2026-07-03 20:15 CEST - de novo benchmark monitor update: no Slurm abnormal states and full UCSC compare dirs remain empty because finalize/compare jobs are still dependency-gated. Base EarlGrey gates remain running: pig at 2%, X. laevis at 1%, western_honey_bee at 81% with ETA about 2h47m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`: all 12898 RepeatMasker batches have been reached and the chunk is in `ProcessRepeats: Adjudicating alignments`; no DONE/FAILED marker yet. `sstat` for actual job `9888508.batch` shows CPU still increasing (`AveCPU=6-17:55:10`) and job state RUNNING with TimeLimit 4 days, so this is a live silent finalization phase. No cancellation/requeue submitted.

- 2026-07-03 20:17 CEST - de novo benchmark monitor update: dependency chain still intact, no Slurm abnormal states, and full UCSC compare dirs are still empty. Base EarlGrey gates remain live: pig at 2% with log and disk counters updating; X. laevis at 1% with log/disk counters updating; western_honey_bee advanced from 81% to 82% with ETA about 2h44m. Dfam RepeatScout chunked rescue remains live and gated by opossum `chunk0001`; it is still in `ProcessRepeats: Adjudicating alignments`, with actual job `9888508.batch` RUNNING and CPU increasing (`AveCPU=6-17:56:25`). Dfam chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No cancellation/requeue submitted.

- 2026-07-03 20:18 CEST - de novo benchmark monitor update: no Slurm abnormal states and full UCSC compare dirs remain empty. Active gates: pig EarlGrey remains 2%; X. laevis EarlGrey remains 1% with log updated at 20:18; western_honey_bee EarlGrey remains 82% with ETA about 2h44m. Dfam RepeatScout chunked rescue remains live and still gated by opossum `chunk0001`, which is in `ProcessRepeats: Adjudicating alignments` without DONE/FAILED marker. `sstat` confirms active CPU growth for opossum actual job `9888508.batch` (`AveCPU=6-17:57:47`, MaxRSS about 9.64G). No intervention taken.

- 2026-07-03 20:20 CEST - de novo benchmark monitor update: dependency chain still intact, no Slurm abnormal states, and full UCSC compare dirs remain empty. Active gates: pig EarlGrey remains 2% with log update at 20:18 and CPU/disk counters growing; X. laevis EarlGrey remains 1%; western_honey_bee EarlGrey remains 82% with ETA about 2h44m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments`; actual job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-17:59:12`, MaxRSS about 9.64G). Dfam chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No cancellation/requeue submitted.

- 2026-07-03 20:21 CEST - de novo benchmark monitor update: no Slurm abnormal states and final compare dirs remain empty. Active gates: pig EarlGrey remains 2% with log updated at 20:21; X. laevis EarlGrey remains 1% with log updated at 20:20; western_honey_bee EarlGrey remains 82% with ETA about 2h43m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments`; actual job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-18:00:29`, MaxRSS about 9.65G). Dfam chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No cancellation/requeue submitted.

- 2026-07-03 20:22 CEST - de novo benchmark monitor update: no Slurm abnormal states and final compare dirs remain empty. Active gates: pig EarlGrey remains 2%; X. laevis EarlGrey remains 1% with log updated at 20:22; western_honey_bee EarlGrey remains 82% with ETA about 2h42m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments` without DONE/FAILED; actual job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-18:01:56`, MaxRSS about 9.65G). Dfam chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No cancellation/requeue submitted.

- 2026-07-03 20:24 CEST - de novo benchmark monitor update: dependency chain still intact and full compare dirs remain empty; no abnormal Slurm states. Active gates: pig EarlGrey remains 2% with log updated at 20:22; X. laevis EarlGrey remains 1% with log updated at 20:23; western_honey_bee EarlGrey remains 82% with ETA about 2h40m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments` without DONE/FAILED. Actual opossum job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-18:03:15`, MaxRSS about 9.65G). Chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No intervention.

- 2026-07-03 20:25 CEST - de novo benchmark monitor update: no Slurm abnormal states and compare dirs remain empty. Active gates: pig EarlGrey remains 2% with log updated at 20:25; X. laevis EarlGrey remains 1%; western_honey_bee EarlGrey remains 82% with ETA about 2h40m and log updated at 20:25. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments` without DONE/FAILED. Actual opossum job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-18:04:36`, MaxRSS about 9.66G). Chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No intervention.

- 2026-07-03 20:27 CEST - de novo benchmark monitor update: no dependency release yet; compare dirs remain empty and no Slurm abnormal states. Active gates: pig EarlGrey remains 2%; X. laevis EarlGrey remains 1% with log updated at 20:26 and ETA about 84h; western_honey_bee EarlGrey remains 82% with ETA about 2h39m. Dfam RepeatScout chunked rescue remains gated by opossum `chunk0001`, still in `ProcessRepeats: Adjudicating alignments` without DONE/FAILED; actual job `9888508.batch` remains RUNNING with CPU increasing (`AveCPU=6-18:05:57`, MaxRSS about 9.66G). Chunk counts remain cattle 32/32, pig 21/21, opossum 9/10, 0 failed. No intervention.

- 2026-07-03 20:30 CEST - user-requested de novo/UCSC compare status and directory audit: final de novo full compare is still not available because `9951603/9951604/9951605/9951606` remain dependency-gated. Running gates remain pig EarlGrey (`9945280_5`, 2%, log updated 20:27), X. laevis EarlGrey (`9945299_8`, 1%, log updated 20:28), western_honey_bee EarlGrey (`9951567_7`, 83%, ETA about 2h39m), and opossum Dfam RepeatScout chunk `chunk0001` (`9888508.batch`) in `ProcessRepeats: Adjudicating alignments`; no Slurm abnormal states and no failed chunks. Current RepeatMasker+Dfam Label-A vs UCSC report remains `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260703_200218_FRESH` (24 paired entries; high=7, moderate=2, low=5, severe=10; 6 plant entries lack UCSC comparator). Directory audit: direct-use Label-A/UCSC/genome views remain under `software_outputs/repeatmasker_dfam/02_ready_by_design/{A0,A1,A2,B,C,D,H0,heldout_stress_pool}` with `genomes/{fine_tune,eval_only}` and `annotations/{self_labelA,ucsc_comparator}`; no top-level `/home/users/j/jwang/ab-initio-TE/RM_*` directories were present at this check.

- 2026-07-03 20:33 CEST - de novo benchmark monitor update: final de novo/UCSC compare outputs are still absent; `DENOVO_B_FINALIZE_R3`, base compare, Dfam augmentation, and Dfam compare remain dependency-pending. Active gates are still healthy: pig EarlGrey (`9945280_5`) remains at 2% with runner log updated at 20:31; X. laevis EarlGrey (`9945299_8`) remains at 1% with runner log updated at 20:32; western_honey_bee EarlGrey (`9951567_7`) remains at 83% with ETA about 2h35m; opossum Dfam RepeatScout chunk rescue (`9886845_33` actual `9888508`) remains RUNNING. `sacct` reported no abnormal states. Time limits are sufficient for the current ETA: pig/X. laevis EarlGrey 10 days, honeybee EarlGrey 4 days, opossum chunk until 2026-07-06 10:33 CEST. No intervention or resubmission was made.

- 2026-07-03 20:34 CEST - de novo benchmark monitor update: dependency chain remains unchanged and full compare directories are still empty. Running gates remain live: pig EarlGrey log updated at 20:33 and remains 2%; X. laevis EarlGrey log updated at 20:33 and remains 1%; western_honey_bee EarlGrey log updated at 20:33 and remains 83% with ETA about 2h34m; opossum Dfam RepeatScout chunk rescue remains RUNNING with CPU/RSS still increasing. Matrix status still reports base running rows for pig/X. laevis/western_honey_bee EarlGrey; Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No FAILED/CANCELLED/OOM states were observed and no intervention was made.

- 2026-07-03 20:35 CEST - de novo benchmark monitor update: `DENOVO_B_FINALIZE_R3`, base UCSC compare, Dfam augmentation, and Dfam compare remain dependency-pending; final compare directories are still empty. Running gates remain healthy: pig EarlGrey log updated at 20:35 and remains 2%; X. laevis EarlGrey log updated at 20:35 and remains 1%; western_honey_bee EarlGrey log updated at 20:35 and remains 83% with ETA about 2h34m; opossum Dfam RepeatScout chunk `chunk0001` is still in `ProcessRepeats: Adjudicating alignments` with actual job `9888508.batch` RUNNING and CPU/RSS increasing. Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. `sacct` showed no abnormal states. No intervention was made.

- 2026-07-03 20:36 CEST - de novo benchmark monitor update: downstream finalize/compare jobs remain dependency-pending and full compare directories contain no files. Base matrix still has pig, X. laevis, and western_honey_bee EarlGrey as running; Dfam matrix still has cattle/opossum/pig RepeatScout wrappers running pending chunk-finalize closure and Dfam EarlGrey rows missing by design until R3 augmentation releases. Honeybee EarlGrey log updated at 20:36 and remains 83% with ETA about 2h33m. Pig and X. laevis EarlGrey logs last updated at 20:35, but `sstat` CPU counters continued to increase, so they are not stale. Opossum chunk `9888508.batch` also remains RUNNING with CPU/RSS increasing. No abnormal Slurm states, no failed chunks, and no intervention.

- 2026-07-03 20:39 CEST - de novo benchmark monitor 2-minute recheck: dependency chain remains unchanged and compare directories are still empty. The apparent short silence in pig/X. laevis logs resolved: pig EarlGrey log updated at 20:37 and remains 2%; X. laevis EarlGrey log updated at 20:37 and remains 1%; western_honey_bee EarlGrey log updated at 20:38 and remains 83% with ETA about 2h32m. Opossum Dfam chunk rescue remains RUNNING. No intervention was made.

- 2026-07-03 20:40 CEST - de novo benchmark monitor update: no downstream dependency release and final compare dirs remain empty. Active gates continue to show real progress: pig EarlGrey log updated at 20:39 and remains 2%; X. laevis EarlGrey log updated at 20:39 and remains 1%; western_honey_bee EarlGrey log updated at 20:39 and remains 83% with ETA about 2h31m. Resource counters increased for all three EarlGrey jobs and opossum Dfam chunk actual job `9888508.batch` (`AveCPU=6-18:19:08`, MaxRSS about 9.69G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No abnormal Slurm states and no intervention.

- 2026-07-03 20:42 CEST - de novo benchmark 90-second recheck: downstream dependency chain remains unchanged and compare dirs are still empty, but western_honey_bee EarlGrey advanced from 83% to 84% with ETA about 2h27m. No honeybee DONE/FAILED/annotation markers yet. Pig EarlGrey log updated at 20:41 and remains 2%; X. laevis EarlGrey log updated at 20:41 and remains 1%. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 20:43 CEST - de novo benchmark monitor update: downstream dependency chain remains unchanged and compare dirs are empty. Pig EarlGrey log updated at 20:42 and remains 2% with ETA trending down to about 109h53m; X. laevis EarlGrey log updated at 20:42 and remains 1%; western_honey_bee EarlGrey log updated at 20:43 and remains 84% with ETA about 2h26m. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:22:17`, MaxRSS about 9.70G). No abnormal Slurm states and no intervention.

- 2026-07-03 20:45 CEST - de novo benchmark 2-minute recheck: downstream dependency chain is still unchanged and compare dirs are empty. No EarlGrey DONE/FAILED/annotation markers appeared. Pig EarlGrey log updated at 20:45 and remains 2%; X. laevis EarlGrey log updated at 20:44 and remains 1%; western_honey_bee EarlGrey log updated at 20:45 and remains 84% with ETA about 2h24m. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 20:47 CEST - de novo benchmark monitor update: downstream dependency chain remains unchanged and final compare dirs are empty. No EarlGrey DONE/FAILED/annotation markers. Pig EarlGrey log updated at 20:46 and remains 2% with ETA about 109h46m; western_honey_bee EarlGrey log updated at 20:46 and remains 84% with ETA about 2h22m. X. laevis EarlGrey log last updated at 20:44 but `sstat` CPU counters continue increasing, so it is not stale. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:25:53`, MaxRSS about 9.71G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 20:49 CEST - de novo benchmark 2-minute recheck: downstream dependencies remain unchanged and compare dirs are still empty. X. laevis EarlGrey resumed visible log writes at 20:48 and remains 1%, so the prior short silence was not stale. Pig EarlGrey log updated at 20:48 and remains 2%; western_honey_bee EarlGrey log updated at 20:49 and remains 84% with ETA about 2h22m. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 20:50 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are still empty. X. laevis EarlGrey log updated at 20:50 and remains 1%; western_honey_bee EarlGrey log updated at 20:49 and remains 84% with ETA about 2h21m. Pig EarlGrey log last updated at 20:48 but `sstat` CPU counters continue increasing, so it is not stale. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:29:35`, MaxRSS about 9.73G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 20:53 CEST - de novo benchmark 2-minute recheck: downstream dependencies remain unchanged and compare dirs are still empty, but western_honey_bee EarlGrey advanced from 84% to 85% with ETA about 2h20m. No EarlGrey DONE/FAILED/annotation markers yet. Pig EarlGrey log updated at 20:52 and remains 2%; X. laevis EarlGrey log updated at 20:51 and remains 1%. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 20:55 CEST - de novo benchmark 90-second recheck: downstream dependencies remain unchanged and compare dirs are still empty. Western_honey_bee EarlGrey remains 85% with ETA about 2h19m and log updated at 20:54. Pig EarlGrey log updated at 20:54 and remains 2%; X. laevis EarlGrey log updated at 20:53 and remains 1%. Opossum Dfam chunk rescue remains RUNNING. No abnormal state or intervention.

- 2026-07-03 20:56 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are still empty. Western_honey_bee EarlGrey remains 85% with ETA about 2h17m and log updated at 20:55; X. laevis EarlGrey log updated at 20:55 and remains 1%. Pig EarlGrey log last updated at 20:54 but `sstat` CPU counters continue increasing, so it is not stale. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:35:15`, MaxRSS about 9.76G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 20:57 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs still contain no files. Pig EarlGrey log updated at 20:56 and remains 2%; X. laevis EarlGrey log updated at 20:57 and remains 1%; western_honey_bee EarlGrey log updated at 20:56 and remains 85% with ETA about 2h16m. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:36:44`, MaxRSS about 9.78G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 20:59 CEST - de novo benchmark 90-second recheck: downstream dependencies remain unchanged and compare file count is still 0. Pig EarlGrey log updated at 20:58 and remains 2%; X. laevis EarlGrey log updated at 20:59 and remains 1%; western_honey_bee EarlGrey log updated at 20:59 and remains 85% with ETA about 2h13m. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 21:01 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are empty. Pig EarlGrey log updated at 21:00 and remains 2%; western_honey_bee EarlGrey log updated at 21:00 and remains 85% with ETA about 2h13m. X. laevis EarlGrey log last updated at 20:59 but `sstat` CPU counters continue increasing, so it is not stale. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:40:00`, MaxRSS about 10.58G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 21:02 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are still empty, but western_honey_bee EarlGrey advanced from 85% to 86% with ETA about 2h11m. Pig EarlGrey log updated at 21:02 and remains 2%; X. laevis EarlGrey log updated at 21:01 and remains 1%. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING. Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 21:04 CEST - de novo benchmark 90-second recheck: downstream dependencies remain unchanged and compare file count is still 0. Western_honey_bee EarlGrey remains 86% with ETA about 2h07m and no DONE/FAILED/annotation marker. Pig EarlGrey log updated at 21:04 and remains 2%; X. laevis EarlGrey log updated at 21:03 and remains 1%. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 21:05 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are empty. Western_honey_bee EarlGrey remains 86% with ETA about 2h05m; X. laevis EarlGrey log updated at 21:04 and remains 1%. Pig EarlGrey log last updated at 21:04 but `sstat` CPU counters continue increasing, so it is not stale. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:44:41`, MaxRSS about 10.60G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 21:07 CEST - de novo benchmark 90-second recheck: downstream dependencies remain unchanged and compare file count is still 0. Pig EarlGrey log updated at 21:06 and remains 2%; X. laevis EarlGrey log updated at 21:06 and remains 1%; western_honey_bee EarlGrey log updated at 21:07 and remains 86% with ETA about 2h03m. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk rescue remains RUNNING. No intervention.

- 2026-07-03 21:09 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are empty, but X. laevis EarlGrey advanced from 1% to 2% with log updated at 21:08. Western_honey_bee EarlGrey remains 86% with ETA about 2h03m and log updated at 21:08; pig EarlGrey log updated at 21:08 and remains 2%. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:47:56`, MaxRSS about 11.00G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.

- 2026-07-03 21:10 CEST - de novo benchmark monitor update: downstream dependencies remain unchanged and compare dirs are empty, but western_honey_bee EarlGrey advanced from 86% to 87% with ETA about 1h59m. X. laevis EarlGrey remains 2% with log updated at 21:10. Pig EarlGrey log last updated at 21:08 but `sstat` CPU counters continue increasing, so it is not stale. No EarlGrey DONE/FAILED/annotation markers yet. Opossum Dfam chunk actual job `9888508.batch` remains RUNNING with CPU/RSS increasing (`AveCPU=6-18:49:23`, MaxRSS about 11.01G). Dfam chunk counts remain cattle 32/32 DONE, pig 21/21 DONE, opossum 9/10 DONE, failed chunks 0. No intervention.
| 2026-08-12 | SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1 | `11527999` | COMPLETED_VALID_NEGATIVE | 50/279 unique, 2 ambiguous, 227 missing; curated route closed; only independent all-family raw-DR support audit allowed; no downstream authorization |
| 2026-08-12 | SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1 | `11528267` | COMPLETED_VALID_NEGATIVE_STOP | Grammar-complete full Dfam3.9 scan; raw DR support=0; current S0 data route closed; awaiting human decision on accession-preserving benchmark replacement |
