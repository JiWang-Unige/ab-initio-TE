# Sprint and Capability-Pursue Ledger / 分层推进与证据短跑台账

> 本文档由 `/evidence-sprint` 与 `/capability-pursue` 维护，集中记录非 SOTA-Claim 级的研究推进进度、求证指标与原型验证日志。

## Active Sprint / Capability Targets

| Target Component / Question | Mode | Status | Start Date | Target/Success Criteria | Main Output |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TEFM-CAP-FRAGARCH-20260701 interval-level TE annotation module | Capability-Pursue | Closed as future-work limitation | 2026-07-01 | Usable prototype failed current bounded gate: Round 1 and Round 2 did not improve segment-F1@IoU0.8 and boundary-F1@5bp over CE/smoothing while keeping missed_true_rate <= CE+0.03 and deleted_true_backed_fraction <=0.15. | `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/` |
| PIPE-TEFM-CAP-POSTPROC-20260701 threshold/postprocess sensitivity audit | Capability-Pursue diagnostic | Done; diagnostic only | 2026-07-01 | Answer whether threshold harshness or short-vs-long HMM handling explains fragmentation without violating true-backed deletion guardrails. | `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/` |
| [Example Question] | Evidence-Sprint | Done | YYYY-MM-DD | 验证 CRF-head 在 10% screen 上的表现 | metrics 正常，写 findings/10 |

---

## Execution Logs

### [Evidence-Sprint] 2026-08-12 — Dfam 3.9 authoritative alias/accession recovery

- **Question/Diagnostic**: Can a version-frozen official Dfam 3.9 source map the 279 unresolved RepeatMasker identifiers (6,432,583 occurrences) to unique versioned accessions and consensus hashes without changing labels, deleting the denominator, or using genome-copy/name-similarity fallbacks?
- **Hypothesis / expected answer**: The official curated EMBL `AC/ID/PI/SN/DR/SQ` records may recover a subset; any missing or one-to-many alias must remain an explicit valid-negative typed block rather than being guessed away.
- **Budget / non-goals**: source acquisition plus one bounded target-only CPU audit (planned 4 CPU/32 GiB/2h/0 GPU); no full Dfam scan, homology graph, split construction, data materialization, training, GPU, S1, relabeling, current-API drift, or Repbase redistribution.
- **Actions taken**: froze the official Dfam 3.9 curated EMBL export, official MD5 sidecar, and release notes under `refs/supp/dfam39-authoritative-alias/`; verified the 25,501,240-byte payload against official MD5 and SHA-256; opened isolated implementation `SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1` for exact-relation audit only.
- **Preliminary evidence**: target-limited streaming inspection indicates partial coverage and genuine one-to-many cases (`L1HS`, `L1PREC2`). These are design inputs only; formal metrics await independently reviewed Slurm execution.
- **Decision**: `needs_bounded_action`. Preserve the 279/6,432,583 denominator, 10 U-ignore identifiers, and X13 audit-only case; permit only official exact relation evidence and unique `(versioned accession, consensus SHA-256)` resolution. Any unresolved/conflicting row blocks S0 identity promotion.
- **Durable outputs**: `refs/dossiers/dfam39-authoritative-alias.md`; `refs/supp/dfam39-authoritative-alias/`; planned `outputs/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1/`.

### [Evidence-Sprint] 2026-08-12 — HiTE isolated runtime validity

- **Question/Diagnostic**: Was the parent HiTE 600-second timeout a runtime incompatibility, or could the exact frozen HiTE 3.3.3 demo finish within one bounded 1800-second continuation?
- **Hypothesis / expected answer**: rc0 plus exact final GFF and canonical adapter rows would establish cell-level engineering validity; another timeout would permanently stop retries.
- **Budget / non-goals**: one 4 CPU/48 GiB/1h/0 GPU job; no RM rerun, other tools, biological benchmark, accuracy claim or GPU.
- **Actions taken**: independent code review, smart-sbatch Phase 1, Job `11524485`, manifest/semantic validation and route-level validator.
- **Metrics/Findings**: rc0 in 21m58.53s command time; 1,203,491-byte GFF; 14,315 canonical rows; no STOP; 12/12 artifact and 5/5 canonical hashes pass.
- **Decision**: `answered_yes` at cell level. Parent RM+isolated HiTE two-job evidence is ready, but the five-cell goal is not closed and further B compute stops for tri-review/pivot.
- **Tri-review/Pivot**: 3/3 accept the two-cell evidence; archive it, set operational retry permission false, and stop at a human gate. No new compute.
- **Durable outputs**: `outputs/BENCH-HITE-ISOLATED-20260811-R1/`; `docs/06_results_log.md`; `docs/07_tri_review.md`; `docs/08_pivot_decisions.md`; evidence `E110`/`E111`.

---

### [Evidence-Sprint] 2026-08-11 — S0 exact identity/provenance coverage

- **Question/Diagnostic**: Can the frozen S0 P-state identifier universe be assigned 100% unique, hash-bound Dfam provenance using exact name/accession semantics, without dropping occurrences?
- **Hypothesis / expected answer**: complete identity would allow later family/homology split construction; incomplete identity must stop at a human contract gate.
- **Budget / non-goals**: one repaired CPU audit, 4 CPU/32 GiB/2h/0 GPU; no split, clustering, training, inference, S0 metric, S1 or claim.
- **Actions taken**: froze the actual 12-partition H5 layout, passed independent code review, ran Job `11524255`, validated manifests/conservation, then completed 3/3 external tri-review and pivot.
- **Metrics/Findings**: 6,447/6,727 P identifiers uniquely resolved (`0.9583766909`); 279 missing; one ambiguous; 43,728 excluded records explicitly retained; occurrence conservation delta zero.
- **Decision**: `answered_no` / `comparability audit first`. The exact-only contract is insufficient; a human must choose curated exact aliases or frozen sequence-homology components and decide the ambiguous/excluded cases.
- **Durable outputs**: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/`; `docs/06_results_log.md`; `docs/07_tri_review.md`; `docs/08_pivot_decisions.md`; evidence `E108`/`E109`.

---

### [Evidence-Sprint] <YYYY-MM-DD> — [求证问题/诊断内容]
- **Question/Diagnostic**: 
- **Hypothesis / expected answer**:
- **Budget / non-goals**:
- **Actions taken**: 
- **Metrics/Findings**: 
- **Decision**: answered_yes / answered_no / answered_mixed / inconclusive / needs_capability_pursue / needs_full_pursue / feed_publication
- **Durable outputs (if any)**: [dossiers/findings/register refs]

---

### [Capability-Pursue] <YYYY-MM-DD> — [原创组件名称]
- **Capability Target**: 
- **Rounds expected**: [2-5]
- **Rounds completed**: 
- **Prototype Status**: [Under-development / Usable-prototype / Blocked]
- **Decision**: usable_prototype / conservative_limitation / future_work / blocked / promote_to_claim_proposed / abandon_component
- **Limitation Identified**: 
- **Future Work**: 
- **Promoted to SOTA Claim**: [No / proposed / Yes -> via revise-goal or route-reset]

---

### [Capability-Pursue] 2026-07-01 — TEFM-CAP-FRAGARCH-20260701 interval-aware fragmentation architecture
- **Capability Target**: Reusable interval-level TE annotation module that upgrades fragmentation handling from post-hoc smoothing/weak structured decoder to direct boundary/proposal/object-style interval prediction.
- **Rounds expected**: 2-5 bounded rounds.
- **Rounds completed**: 1.
- **Prototype Status**: Method-fail; current components stopped.
- **Round-1 candidates**: A) boundary-aware head + interval proposal scorer; B) anchor-free center/length interval detector.
- **Budget / non-goals**: single seed=42, small human/mouse bounded panel, no threshold/gap/post-hoc HMM/CRF tuning, no another survival/retention tweak without new mechanism, no SOTA claim.
- **Required baselines**: CE raw threshold; same-panel HMM/CRF-style smoothing as comparator only; prior interval_survival_decoder and retention_constrained_decoder as historical reference; overlap center-merge deferred to Stage-2 because the quick panel is non-overlap.
- **Strict metrics**: bp precision/recall/F1; segment-F1@IoU0.5/0.7/0.8/0.9; boundary-F1@5/10/25bp; missed_true_rate; pred_true_backed_rate; short_true_backed_rate; deleted true-backed vs false fragments; overmerge rate; split_true_rate; mean fragments per true TE.
- **Round-1 result**: Semantic success, Slurm job `9865070` completed. No gate-pass panels. Human best new head `anchor_free_interval` segment-F1@IoU0.8 `0.3581`, boundary-F1@5bp `0.1878`, but CRF-style smoothing is `0.4126`/`0.2087` and deleted_true_backed_fraction remains `0.7419`. Mouse best new head `boundary_proposal` segment-F1 `0.2340`, boundary-F1 `0.0922`, below CRF-style smoothing `0.4904`/`0.1720`.
- **Decision**: replace_component. Stop the tested frozen-lightweight interval heads; allow at most one second bounded round only with a genuinely new fragment graph/linking or boundary-conditioned span module.
- **Limitation Identified**: Lightweight frozen-embedding interval heads did not beat unchanged smoothing and still delete too many true-backed fragments.
- **Future Work**: fragment graph linker is the primary re-entry candidate; boundary-conditioned span refinement is optional if kept small and isolated.
- **Promoted to SOTA Claim**: No.

---

### [Capability-Pursue] 2026-07-01 — PIPE-TEFM-CAP-FRAGGRAPH-20260701 fragment graph linker
- **Capability Target**: Round-2 replacement component for TE fragmentation: preserve CE high-recall fragments as graph nodes and learn fragment adjacency/linking to reconstruct complete TE intervals.
- **Rounds expected**: bounded continuation within TEFM-CAP-FRAGARCH, max 2-5 total.
- **Rounds completed**: 2 total rounds; Round 2 completed.
- **Prototype Status**: Method-fail; capability branch closed.
- **Round-2 candidate**: `fragment_graph_linker_keepall`, a learned adjacency decoder over raw CE fragments; optional learned keep/drop diagnostic is trained but not promoted unless it preserves true-backed fragments.
- **Budget / non-goals**: single seed=42, small human/mouse panel, no threshold/gap/HMM/CRF/survival-retention tuning, no SOTA claim.
- **Strict metrics**: same as Round 1: bp precision/recall/F1; segment-F1@IoU0.5/0.7/0.8/0.9; boundary-F1@5/10/25bp; missed_true_rate; pred_true_backed_rate; short_true_backed_rate; deleted true-backed vs false fragments; overmerge rate; split_true_rate; mean fragments per true TE.
- **Round-2 result**: Slurm job `9866570` completed. `fragment_graph_keepall` preserved CE raw fragments with deleted_true_backed_fraction `0`, but metrics were identical to CE raw. `fragment_graph_keepdrop` improved human segment-F1/boundary-F1 to `0.4964`/`0.2458` but deleted true-backed fragments at `0.8632` and did not beat CRF-style smoothing on mouse.
- **Tri-review**: completed with `3/3` quorum; all reviewers recommend `abandon-route`.
- **Decision**: abandon_component / future_work. Stop TEFM-CAP-FRAGARCH interval reconstruction capability for this sprint; do not run a final boundary-conditioned span-refiner round.
- **Limitation Identified**: learned graph links did not fire under preservation-first decode; allowing learned deletion recreates the true-backed deletion failure.
- **Future Work**: only a substantially different end-to-end/global interval detector or biologically richer interval model may reopen this line, and only if it pre-registers strict true-backed deletion guardrails across at least two chromosomes/species.
- **Promoted to SOTA Claim**: No.

---

### [Capability-Pursue Diagnostic] 2026-07-01 — PIPE-TEFM-CAP-POSTPROC-20260701 threshold and length-adaptive postprocess audit
- **Capability Target**: Diagnostic supplement to answer whether strict thresholds are too harsh and whether short fragments should be preserved while long fragments use HMM/gap smoothing.
- **Rounds expected**: 1 bounded diagnostic only.
- **Rounds completed**: 1.
- **Prototype Status**: Not a prototype; comparator/sensitivity evidence only.
- **Budget / non-goals**: seed `42`, small human/mouse panel, no claim, no route reopening after `DEC-001`/`DEC-002`.
- **Actions taken**: ran raw thresholds `0.20-0.80`, gap/min-length heuristics, fixed HMM penalties, HMM+short rescue, and length-adaptive short-raw/long-HMM variants.
- **Round result**: Human strict-safe best was `raw_t0.20` (segment-F1 `0.2422`, boundary-F1 `0.1143`, missed `0.2541`, deleted_true_backed `0.0000`). Mouse strict-safe best was `gap25_min40_t0.50` (segment-F1 `0.4589`, boundary-F1 `0.1575`, missed `0.1133`, deleted_true_backed `0.1042`). Best observed interval rows often failed deletion guardrails.
- **Review-board / Council**: both concluded this is valid sensitivity evidence only; do not select a universal optimal threshold or promote HMM/gap/length-adaptive postprocess as the solved module.
- **Decision**: diagnostic_answered / comparator_only.
- **Limitation Identified**: threshold and HMM settings can move strict segment metrics, but the apparent gains often come from deleting true-backed fragments or increasing overmerge; biological TE fragmentation and annotation fragmentation remain unresolved.
- **Future Work**: only global interval/set prediction, richer biological interval evidence, or annotation audit can reopen the fragmentation capability line.
- **Promoted to SOTA Claim**: No.

---

### [Evidence-Sprint] 2026-07-01 — RepeatMasker+Dfam self Label-A vs UCSC ready audit
- **Question/Diagnostic**: 使用本轮 ready-by-design RepeatMasker+Dfam self Label-A 与 UCSC/local strict-TE comparator 再做一次物种级重叠对比，并确认当前目录状态是否可清理。
- **Hypothesis / expected answer**: 最新 self-run Label-A 已按设计视图落到 `02_ready_by_design`，UCSC/local comparator 已在 `comparators/ucsc_reference_repeatmasker`，应能生成可复查的 paired strict-TE bp overlap 表；de novo benchmark 的 UCSC 对比需等其矩阵完成后另行产出。
- **Budget / non-goals**: 状态审计与既有比较产物核查；不重新训练，不 claim FM 优于传统工具，不删除 active benchmark scratch。
- **Actions taken**: 刷新 de novo benchmark monitor；检查 RepeatMasker+Dfam ready report、ready-by-design symlink tree、UCSC comparator tree、root/quarantine `RM_*` 目录。
- **Metrics/Findings**: `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE` 已完成 24 paired entries，concordance class 为 high=7、moderate=2、low=5、severe=10，missing comparator=6。de novo benchmark 仍为 base 29/32 DONE、Dfam overlay 20/32 DONE，base-vs-UCSC 与 Dfam-vs-UCSC comparison outputs 还未产生。
- **Decision**: answered_mixed；RepeatMasker+Dfam self-vs-UCSC 已回答，de novo-vs-UCSC 仍需等待 active Slurm chain 完成。
- **Durable outputs (if any)**: `reports/repeatmasker_dfam/SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260701_SINGLE/`; `software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/MONITOR_REPORT_20260629.md`.
# [Cap-Pursue] FRAG-CONSENSUS-COLLINEARITY-20260812

- **Capability ID**: `FRAG-CONSENSUS-COLLINEARITY-20260812`
- **Type**: preservation-constrained global copy assembly / CPU information-sufficiency audit
- **Scientific distinction**: use leaf-sequence alignment to frozen TE consensus coordinates, strand and identity to test globally collinear copy paths. This is not threshold/gap/HMM/CRF smoothing, a local fragment graph, or a lightweight interval head; RepeatMasker parent IDs and truth boundaries remain evaluator-only.
- **Success policy**: at most 3 rounds. Round 1 is a Rice T1 label-blind information audit; Round 2 may use FlyBase only if Round 1 passes; Round 3 may connect frozen H0 leaves only after same-input probability tracks are pinned.
- **Round-1 minimum gate**: immutable inputs and aligner/library identity pass; eligible multirow groups are reported; consensus-collinearity improves parent/group recovery over frozen MERGE_STRICT/LOOSE while cross-parent false-fusion proxy is `<=0.05`; leaf retention is `1.0`; truth IDs are absent from assembly inputs.
- **Mandatory metrics**: eligible coverage, exact group recovery, pairwise grouping F1, positive parent recovery, boundary curves at 5/10/25/50 bp, cross-RepeatMasker-ID false-fusion proxy, nested/`*` topology preservation, and complete score-stratified sensitivity. T1 is positive-only: no whole-genome precision/F1 and no unlabeled-as-negative claim.
- **If fail**: record `conservative_limitation` or `abandon_component`; do not tune thresholds on test families and do not reopen DEC-001/002 cousins.
- **Promotion boundary**: even a passing Round 1 is `usable_prototype` at most. Scientific H0 screen requires frozen same-input H0 tracks/leaves, independent code review and a new authorization; claim promotion requires a later human-gated goal revision.
- **Current state**: Closed after one scientific round. Final Job `11531090` is a verified `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`; `2/3 DEGRADED_REVIEW` has two valid `abandon-route` judgments and pivot/DEC-004 closes standalone consensus-collinearity assembly. Exact consensus evidence remains a diagnostic signal only. No further round, Fly/H0 extension, tuning, GPU or promotion; only a genuinely new global evidence mechanism meeting DEC-004 re-entry criteria may open a new capability ID.

# [Evidence-Sprint] DECAY-TRANSFER-PROVENANCE-RECOVERY-20260812

- **Question**: can each of the five frozen G-route checkpoint hashes be uniquely bound to one historical Slurm task, executed command, training metadata, train/validation data identity, initialization, code/launcher/environment identity and successful terminal state?
- **Read-only finding**: candidate chains exist for human H0 (`9060945_14`), animal (`9107751_3`), plant/cross/insect (`9245618_1/2/5`) and their frozen checkpoint hashes. The existing P1 seal remains `PROV_RUN_RECORD_MISSING`; candidate evidence is not a run record and does not authorize transfer-surface evaluation.
- **Next bounded action**: queued behind the two active implementation directions. Proposed isolated CPU audit is `1–2 CPU / 8–16 GiB / <=1 h / 0 GPU`; it must close 5/5 anchors or return a typed block. It may not run inference, fit a selector or make a transfer claim.
- **E comparison**: representation route E remains less ready because exact fragment family/copy/species/component bindings, backend identity and weights are not closed.
# Sprint: S FamDB leaf read-lifecycle closure after Job 11533175

- Date: 2026-08-12 CEST
- Layer: bounded repair / evidence-enabling component
- Evidence: Job `11533175` failed after the single in-memory 72-call probe, before observations were published; audited status is `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`.
- Review: `2/3 DEGRADED_REVIEW`; two valid reviewers distinguish cleanup/publication failure from exact-access failure and agree on one final close-only repair.
- Binding next action: new exp namespace; no read-mode `FamDB.finalize()`; explicit HDF5 close; immutable observation staging before cleanup; exact call-count and failure-injection tests; fresh code review; at most one exact 1CPU/4GiB/10m/0GPU attempt.
- Promotion: none. PASS only makes a future leaf-adapter CPU proposal eligible. Any failure or typed block permanently closes the access/export route. Homology, DATA, GPU S0 and S1 remain false.

## Result update: Job 11534847

- **Outcome**: `LEAF_CLOSE_ONLY_PASS`; 6/6 frozen accessions resolved across 12 partitions, 72/72 exact-once calls, 0 fallback, 12/12 unique handles closed after immutable observation staging.
- **Evidence quality**: exact Slurm resource reconciliation, 59/59 allocation-side tests, terminal 11-file closure and observation 4-file closure all pass.
- **Capability status**: `evidence-enabling component validated`; not a model, annotation, split or performance result.
- **Promotion boundary**: post-result tri-review/pivot is mandatory. PASS may only make a separately implemented/reviewed CPU leaf-adapter proposal eligible; representative/full DATA, homology, GPU S0 and S1 remain false.

---
