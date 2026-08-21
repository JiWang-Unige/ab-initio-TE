# Pivot Decisions

> 由 /pivot append。每个 pivot 一段。

每个 entry 用 # Pivot Decision: <exp_id> 开头。模板见 /pivot SKILL.md。

---

# Pivot decision: SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1 continue to one isolated CPU leaf-adapter proposal after Job 11534847

Date: 2026-08-12 CEST  
Decision: `continue-current-route`  
Review status: `2/3 DEGRADED_REVIEW`

Job `11534847` is an audited component PASS: all six frozen accessions resolved exact-once across 12 leaf partitions, observations were immutably staged before cleanup, and all 12 unique HDF5 handles closed exactly once. Claude and the separate Codex reviewer independently accept the result and choose the same narrow continuation; Antigravity remained invalid, and the external Codex CLI was unavailable from usage exhaustion.

The next permitted work is not a full annotation run. It is one new exp-scoped CPU **leaf-adapter preflight proposal** that uses only the same six frozen records to prove accession-preserving library/header materialization and its exact manifest semantics. It must receive a new implementation, synthetic tests, independent code-review gate and smart-sbatch authorization; the consumed close-only gate cannot be reused.

Binding exclusions remain: no representative or full-genome annotation; no benchmark RepeatMasker run; no full catalog; no homology clustering/split; no DATA build; no GPU direct-superfamily S0; no hierarchical S1; no claim. A leaf-adapter PASS would only make a later representative CPU gate eligible, never automatically authorized. Any runtime/integrity failure or semantic typed block returns to post-result review before further action.

The historical `ACTIVE_GOAL` mismatch remains an automation hard stop and must not be used to rewrite this route-local component result.

# Pivot decision: SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1 continue, pause at goal-revision human gate

Date: 2026-08-12 CEST  
Decision: `continue-current-route` with mandatory human-gated goal reconciliation  
Review status: `2/3 DEGRADED_REVIEW`

Job `11535362` is a trustworthy six-record syntactic component PASS. It demonstrates that the same frozen leaf records can be materialized into paired canonical-name and accession.version views with identical sequence/order/raw-class semantics and complete record provenance. It does not demonstrate RepeatMasker behavior, representative annotation concordance, geometry, catalog coverage, homology-safe splits or direct-superfamily performance.

The next route step is only an eligible **proposal** for a representative CPU gate. Before that proposal is implemented or submitted, the stale selector/decoder `ACTIVE_GOAL.json` must be reconciled through `$revise-goal` with explicit user approval so route-valid component metrics no longer deterministically become `failed_run`. No automatic edit is authorized.

Even after goal revision, a representative gate requires a new exp namespace, frozen representative sampling/denominator, independent contract and code review. This pivot does not authorize RepeatMasker execution now, representative/full annotation, full catalog, homology, DATA, training, GPU direct S0, hierarchical S1 or claim. The Job `11535362` gate is consumed.

---

---

## Pivot Decision: S0 identity provenance before direct-superfamily DATA retry

- Date: 2026-08-11 CEST.
- Inputs: Job `11523252` result-log/validator plus 3/3 external CLI tri-review.
- Deterministic state: `DATA_TYPED_BLOCK`, semantic false, no scientific screen executed.
- Review consensus: two `comparability-blocker`, one `replace-component`; confidence High.

### Sanity and comparability check

- [x] Canonical failure/typed-block artifacts and output hashes verify.
- [x] The bounded CSV repair itself passed real-shape and over-limit tests.
- [x] Three independent reviewers completed.
- [ ] Every P-state annotation has a unique frozen source-library/consensus identity.
- [ ] Homology/component split and leakage audit exist.
- [ ] Any S0 scientific metric exists.

### DECISION

- [ ] Continue current identity implementation and rerun immediately.
- [ ] Tune or scale the S model.
- [x] Comparability audit first.
- [x] Replace the identity component only if the audit proves the current contract infeasible, then use the required human-gated contract revision.
- [ ] Abandon direct-superfamily validation.

The single primary next action is a bounded CPU-only identity-provenance audit in an isolated experiment namespace. It must enumerate every P-state family identifier, try exact Dfam name and exact Dfam accession resolution, and bind successful rows to a versioned accession, consensus SHA-256 and frozen source asset. Missing, ambiguous, conflicting and duplicate-consensus cases must remain explicit terminal categories. It must not delete positives, guess by prefix, build data splits, train a model or launch GPU work.

If and only if this audit reaches 100% unique provenance under the existing accession contract may S0 DATA be repaired without changing the goal. If a sequence homology cluster is needed, first freeze its universe/algorithm/threshold and request the required human gate for the contract change; do not silently revise `GOAL_S_DIRECT_R2.json`. GPU S0 remains conditional on a later DATA PASS, and S1 remains conditional on the full direct-S0 numeric gate.

The orthogonal B action `BENCH-RM-HITE-VALIDITY-20260811-R1` may continue through independent review as a separate short CPU-only validity smoke. The old five-cell main, Earl Grey/EDTA repair, Pfam/TEtrimmer, GPU S0 and S1 are not authorized by this pivot.

---

## Pivot Decision: narrow FamDB partition-layout repair after Job 11523938

- Date: 2026-08-11 CEST.
- Inputs: canonical `AUDIT_FAILED` result, `validate_goal=failed_run`, and 3/3 external CLI tri-review.
- Review consensus: unanimous `run-sanity-check-first`, confidence High.

### DECISION

- [x] Sanity check first: implement one narrow structural-index compatibility repair.
- [ ] Retry immediately without code change.
- [ ] Use the top-level broad exception-swallowing API.
- [ ] Change the S homology contract now.
- [ ] Build split, train S0, or start S1.
- [ ] Abandon the provenance route.

The single next action is to make the leaf resolver inspect the pinned H5 structure before name lookup. A leaf may be skipped for name lookup only when `Lookup/ByName` is structurally absent; this skip must be counted and must not reduce the P/excluded identifier or occurrence denominator. If the group exists, unreadable/corrupt/wrong-type/query errors remain hard failures.

Before any retry, freeze the actual Dfam 3.9 partition-index layout, add real-layout and synthetic absent-vs-corrupt tests, pass allocation-free static checks and obtain a fresh independent code review. After that, at most one more 4CPU/0GPU audit retry is allowed. A valid provenance typed block returns to the already recorded human-gated contract decision; another failed run stops the route for renewed review. Direct S0 remains unmeasured and S1 remains locked.

---

## Pivot Decision: isolate HiTE continuation and reuse frozen RM pass

- Date: 2026-08-11 CEST.
- Inputs: Job `11523819` canonical artifacts, `validate_goal=failed_run`, 3/3 external CLI tri-review.
- Consensus: Option A, confidence High.

### DECISION

- [x] Preserve the RM cell as an immutable, cell-level engineering pass.
- [x] Run-sanity-check-first with a new HiTE-only continuation.
- [ ] Rerun the paired RM+HiTE job.
- [ ] Stop HiTE after only the 600s attempt.
- [ ] Extend beyond the next preregistered 1800s cap.
- [ ] Expand to Earl Grey/EDTA/TEtrimmer/Pfam or biological benchmarking.

Create a new isolated exp_id that consumes exactly the same HiTE 3.3.3 SIF, official fixture, direct argv, `--annotate 1`, two threads and offline contract. Freeze a 1800-second command timeout inside a 1h, 4CPU/48GiB/0GPU allocation and reserve at least 600 seconds for termination, adapter, hashing and atomic publish. Only rc0 plus a final non-empty parseable `HiTE.gff` and canonical adapter output can pass.

The original `BENCH-RM-HITE-VALIDITY-20260811-R1` must remain `FAILED`; its RM cell may be reused only by exact artifact/hash reference. A later reconciliation must cite both job IDs, verify shared asset/config/adapter pins and explicitly say it combines two cell-level runs. If the HiTE-only job times out at 1800 seconds, stop rather than increasing the budget again.

---

# Pivot Decision: PIPE-TEFM-REPAIR-20260618

Date: 2026-06-19

## Inputs consumed

- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-repair-20260618`
- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-repair-20260618`
- Resource profile: screen

## Current evidence summary

`PIPE-TEFM-REPAIR-20260618` completed semantically. `invert_boost_animal_4096` is the strongest no-human animal branch in the current screen, with B-panel mean TE-F1 0.9351 and A1 mean TE-F1 0.8985. A2 all-species mean remains about 0.575 because beetle/honeybee and distant stress species dominate the failure. Segment annotation requires smoothing: threshold 0.35 + `hmm_penalty2` gives segment-F1@IoU0.5 0.7339, much better than raw-threshold segment-F1 0.4846. Superfamily main4 macro-F1 is 0.8927, but `Other` remains unlearned. Embedding diagnostics show C1/A1 are strong baselines, while binary fine-tuned B1 embeddings are weak for clustering.

## SOTA gap

| Metric | Current | SOTA | Gap (abs) | Gap (rel %) | Severity |
|---|---:|---:|---:|---:|---|
| B-panel mean TE-F1 (`invert_boost`) | 0.9351 | unknown | unknown | unknown | cannot judge |
| Segment-F1@IoU0.5 (`hmm_penalty2`) | 0.7339 | unknown | unknown | unknown | cannot judge |
| Superfamily main4 macro-F1 | 0.8927 | unknown | unknown | unknown | cannot judge |

## Sanity check

- [x] Result-log exists and semantic success passed.
- [x] Metrics files are present, parseable, finite, and complete for screen.
- [ ] At least two independent CLI reviewers succeeded: no, only 1/3 succeeded.
- [ ] SOTA benchmark is configured: no, ACTIVE_GOAL remains draft and docs/20 reproduction ledger is incomplete.
- [ ] Claim-level evaluator/comparability contract is locked: no, docs/19 remains draft.
- [x] No evidence of run failure, OOM, NaN/inf, or suspicious exact 0/1 global metric.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | failed-after-retry; advisory text only | Directionally suggested continuing/scaling GENERanno 4096, but not counted due failed structural validation and reviewer identity mismatch | Output did not satisfy required `Overall judgment` validation; not usable for quorum | n/a |
| B · Codex | `scale-to-track-b` | Launch a Track B comparability-lock validation run using GENERanno 4096 + `invert_boost_animal_4096` + threshold 0.35/HMM smoothing; beetle/honeybee as diagnostic appendix | Need verified SOTA/comparability contract; A2 stress mean is misleading; `Other` class and far invertebrates are unresolved | Medium-High from reviewer; workflow aggregate forced Low due quorum |
| C · Antigravity | failed-after-retry | none | `agy` required Google OAuth and timed out on all attempts | n/a |

Consensus: no formal consensus; only one reviewer succeeded. Failed Claude advisory output was directionally consistent with Codex, but is not counted.

Disagreement: no valid multi-reviewer disagreement can be assessed.

Quorum / degraded review status: `1/3 SINGLE_REVIEW_CONTINUATION`, confidence Low. This pivot cannot support SOTA claim, route abandonment, ACTIVE_GOAL revision, or benchmark revision.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into this round's cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | Advisory only: continue/scale GENERanno 4096 with benchmark lock | validation/protocol | Not counted due failed review validation | n/a | no |
| 2 | B · Codex | Track B comparability-lock validation | validation/protocol | Freeze data/split/Label-A/version/inference; promote `invert_boost`; stress invertebrates as diagnostic appendix | yes | after comparability audit |
| 3 | C · Antigravity | none | n/a | reviewer unavailable due OAuth | n/a | no |

## Is tuning justified?

Premature. Tuning is not justified while SOTA benchmark, claim-level evaluator contract, and reviewer quorum are unresolved. The next work is comparability/sanity locking, not learning-rate/dropout tuning.

## Architecture hypothesis status

Supported for the intended no-human animal / close-vertebrate / main-superfamily screen route. Not supported as a universal all-animal claim because beetle/honeybee and distant stress species remain poor and label-source-confounded.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability audit first
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The valid reviewer recommends scaling to Track B, and the metric trend supports that direction. However, the workflow cannot make scale/claim-level decisions from a `1/3 SINGLE_REVIEW_CONTINUATION`, and ACTIVE_GOAL/docs19/docs20 do not yet define a claim-grade SOTA/comparability target. Therefore the only defensible primary decision is to lock comparability first. This is not a rejection of the model; it is the prerequisite needed before the recommended Track B validation can be trusted.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which EXP / Track |
|---:|---|---|---|
| 1 | Freeze Track B comparability contract | Prevent panel/label/inference drift from invalidating the next validation | docs/19 + next Track B config |
| 2 | Promote `invert_boost_animal_4096` as current no-human animal branch | Keeps high B-panel and A1 performance while avoiding human-dominant archive bias | next non-claim Track B validation |
| 3 | Fix interval inference protocol to threshold 0.35 + `hmm_penalty2` | Preserve bp-F1 while improving segment/boundary quality | next segment validation |
| 4 | Freeze superfamily claim set to main four classes | Avoid false claims from `Other` F1=0 | next superfamily validation |

## Parallel cohort this round

- Primary direction: comparability audit first.
- Parallel cohort: none until docs/19/ACTIVE_GOAL/docs20 minimum claim contract is repaired or explicitly waived for a non-claim validation.

| Slot | EXP ID (new) | Direction | major_axis | mechanism_delta | Track | Resource profile |
|---|---|---|---|---|---|---|
| primary | TBD | Comparability-lock protocol | validation/protocol | Freeze data/split/Label-A/version/inference | pre-Track B | documentation + config |

Shared-code conflict: no.

## TODO update

- [x] Update `docs/05_todo.md`
- [x] Update `docs/08_pivot_decisions.md`
- [x] Update evidence register
- [x] Update `docs/11_master_plan.md`
- [ ] Repair or explicitly waive ACTIVE_GOAL/docs19/docs20 before any claim-bearing run
- [ ] After comparability lock, generate the next `/goal` for non-claim Track B validation

---

# Pivot Decision: PIPE-TEFM-EXTEND-20260620

Date: 2026-06-21

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-extend-20260620`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-extend-20260620`
- Final report: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/FINAL_REPORT.md`
- Resource profile: screen

## Current evidence summary

`PIPE-TEFM-EXTEND-20260620` completed semantically. The main result is that the robust annotation route remains GENERanno 4096 + `invert_boost_animal_4096`. This animal no-human model transfers surprisingly well to several plants and cross-panel targets, while plant/cross positive-only and PU variants mostly overcall TE because they lack reliable negatives. Base-pretrained SF5 again supports main4+Unknown/reject. Family-level embeddings are improved by model contrastive projection but still do not beat C1 basic sequence features + contrastive. The decay formula becomes substantially more useful when label concordance is included. Dfam consensus-vs-genomic comparison remains blocked by missing consensus FASTA.

## SOTA gap

| Metric | Current | SOTA | Gap | Severity |
|---|---:|---:|---:|---|
| Cross-eval mean TE-F1 (`invert_boost`) | 0.5914 | unknown | unknown | cannot judge |
| Plant eval-only mean TE-F1 (`invert_boost`) | 0.7269 | unknown | unknown | cannot judge |
| SF5 TE-detect F1 | 0.8982 | unknown | unknown | cannot judge |
| SF5 main4 conditional macro-F1 | 0.8547 | unknown | unknown | cannot judge |
| Best decay-formula R2 | 0.5249 | n/a | n/a | descriptive only |

## Sanity check

- [x] Result-log exists and semantic success passed.
- [x] Metrics files are present and parseable.
- [x] Log scan found no final-run failure signatures.
- [ ] At least two independent CLI reviewers succeeded: no, this was degraded host self-review.
- [ ] SOTA benchmark is configured: no, ACTIVE_GOAL remains draft.
- [ ] Claim-level evaluator/comparability contract is locked: no.
- [ ] Consensus-vs-genomic source comparison completed: no, Dfam consensus FASTA missing.

## DECISION

- [x] Continue current architecture as robust branch
- [ ] Tune current architecture
- [ ] Scale data / training now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability audit first before any claim
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The screen gives useful evidence but not a claim. It strengthens the case for GENERanno 4096 + `invert_boost` and for base-pretrained main4+Unknown, while downgrading plant/cross PU to negative ablation or gated repair. Because review quorum is degraded, ACTIVE_GOAL/docs19/docs20 remain draft, and Dfam consensus input is missing, the correct pivot is to carry forward the supported components and lock the evaluator/comparability contract before any claim-grade run.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which track |
|---:|---|---|---|
| 1 | Freeze evaluator and panel contract | Prevent primary/stress/label-source mixing from invalidating claims | claim-prep |
| 2 | Promote GENERanno 4096 + `invert_boost` as robust branch | Keeps broad animal and plant-transfer signal without PU overcalling | Track B validation |
| 3 | Keep base-pretrained SF5 | Preserves Unknown/reject behavior | superfamily validation |
| 4 | Keep overlap/HMM smoothing | Controls interval fragmentation | segment validation |
| 5 | Add RN/hardN negatives before retrying PU | Adds penalty for U-overcalling | future ablation |
| 6 | Supply Dfam consensus FASTA | Completes consensus-vs-genomic embedding source comparison | embedding diagnostic |

## TODO update

- [x] Update `docs/05_todo.md`
- [x] Update `docs/06_results_log.md`
- [x] Update `docs/04_experiment_iterations.md`
- [x] Update `docs/07_tri_review.md`
- [x] Update `docs/08_pivot_decisions.md`
- [x] Update `docs/10_findings.md`
- [x] Update `docs/11_master_plan.md`
- [x] Update `docs/15_evidence_register.md`

---

# Pivot Decision: TEFM-NEW-DIRECTIONS-PILOTS-20260811

Date: 2026-08-11 CEST

## Inputs consumed

- `$result-log`: B/F/S/G/E entries in `docs/06_results_log.md`.
- `$tri-review`: `docs/07_tri_review.md#tri-review-tefm-new-directions-pilots-20260811`.
- Evidence index: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/COHORT_EVIDENCE_INDEX.json`.
- Resource profile: smoke / pre-screen asset gate; claim-ineligible.
- Experiments consumed: `BENCH-5TOOL-SMOKE-20260811-R1`, `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`, `SF-HIER-OPENSET-SCREEN-20260811-R1`, `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`, `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`.

## Current evidence summary

B completed a valid negative five-workflow identity matrix: 0/5 engineering pass, four foundational blocks, one exact-runtime version mismatch and zero invalid cells. F/S/G/E each completed a deterministic asset gate and reproduced `FOUNDATIONAL_TYPED_BLOCK`; no scientific method, inference, model training or biological comparison ran. The cohort used 919 formal allocation-wall seconds plus 7 preflight seconds and 0 GPU-hours.

## SOTA gap

| Metric | Current | SOTA | Gap (abs) | Gap (rel %) | Severity |
|---|---:|---:|---:|---:|---|
| Scientific performance | N/A | N/A | N/A | N/A | comparison not yet authorized |

## Sanity check

- [x] Three independent CLI reviewers succeeded.
- [x] Metrics/manifests are parseable, finite and hash-bound.
- [x] All completed Slurm allocations have terminal accounting; no stale RUNNING status.
- [x] Smoke/asset-gate semantics match the evaluator contract.
- [x] No silent dependency substitution or claim inflation was observed.
- [ ] Dataset/split/truth/weights/test-time comparability is claim-ready: no; this is the blocker being resolved.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `run-sanity-check-first` | Dfam 4.0 FamDB closure for B | Shared denominator runtime/database identity | High |
| B · Codex | `comparability-blocker` | Freeze F Evidence Input Registry v1 | Biological truth/same-input comparator contract | Medium |
| C · Antigravity | `comparability-blocker` | Close B Dfam/HiTE/EDTA identities | Denominator and split/provenance contracts | High |

Consensus: no promotion/tuning/scale; resolve a foundational contract first.  
Disagreement: B denominator first versus F registry first.  
Quorum / degraded status: `3/3`.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into next authorized cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | Configure/freeze Dfam 4.0 FamDB for RM2+RM and Earl Grey | runtime/database | two denominator rows get queryable immutable database identity | primary dependency | only after separate authorization |
| 2 | A · Claude | Acquire/build exact HiTE 3.3.3 local SIF | runtime/container | replace absent accepted artifact without legacy fallback | yes | optional |
| 3 | A · Claude | Establish F Real-T0/tiered truth registry | data/truth | turn synthetic-only semantics into bounded biological evidence | yes | optional |
| 4 | B · Codex | Freeze F Evidence Input Registry v1 | data/evaluator | bind H0, tiered truth and all same-input comparators | yes | optional |
| 5 | B · Codex | Close B exact runtime/database | runtime/database | freeze five tool/database/container/min-launch identities | no, overlaps #1/#2 | primary |
| 6 | B · Codex | Materialize S ontology/homology/clade split | data/split | create leakage-safe open-set screen contract | yes | optional |
| 7 | C · Antigravity | Close B Dfam/FamDB, HiTE and EDTA patch identity | runtime/database | make denominator exact and reproducible | no, overlaps #1/#2/#5 | primary |
| 8 | C · Antigravity | Freeze S/E ontology, homology split and biological bindings | data/split | remove family/copy/species leakage risk | yes | optional |
| 9 | C · Antigravity | Reconstruct five G anchor run records | provenance | exact training/eval evidence chain | yes | optional |

## Is tuning justified?

Premature. No trainable scientific screen ran and no numeric SOTA gap exists.

## Architecture hypothesis status

Unknown for F/S/G/E; B denominator hypothesis is not yet satisfied. No architecture was falsified.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability audit first: close B exact runtime/database denominator
- [ ] Sanity check with scientific inference
- [ ] Abandon route
- [ ] Return to literature

## Why this decision

The protocol makes the traditional-workflow denominator the substrate for every future FM-vs-workflow comparison. Closing Dfam/FamDB and exact runtime identities can unlock multiple B cells without spending GPU, while running F/S/G/E now would violate explicit truth/split/provenance gates. This is not a decision that F is scientifically superior or inferior; it is a dependency-order choice. No database migration or new acquisition is authorized by this closeout itself, so the next cohort requires a fresh bounded authorization before mutating configured runtimes or submitting another pilot.

## Parallel cohort

- Primary direction: B exact runtime/database closure.
- No new run is launched in this cohort closeout.
- Reviewer-proposed F registry, exact HiTE, S ontology/split, G provenance and E bindings remain parked; at most two orthogonal items may join a separately authorized next cohort.
- Shared-code conflict: no current write cohort.

## TODO update

- [x] Record all reviewer directions before convergence.
- [x] Update `docs/04/05/07/08/11/15` and experiment logs.
- [x] Publish the durable cohort evidence index.
- [ ] Obtain separate authorization before runtime/database mutation or another scientific submission.

---

# Pivot Decision: PIPE-TEFM-CAP-FRAGARCH-20260701

Date: 2026-07-01

## Inputs Consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-cap-fragarch-20260701`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fragarch-20260701`
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_metrics.tsv`
- Resource profile: bounded capability-pursue screen

## Current Evidence Summary

`PIPE-TEFM-CAP-FRAGARCH-20260701` completed semantically. It tested two new interval-aware heads on frozen GENERanno 4096 embeddings/logits: `boundary_proposal` and `anchor_free_interval`. Neither passed the strict capability gate. On human, `anchor_free_interval` improves over CE raw but does not beat CRF-style smoothing and still deletes many true-backed fragments. On mouse, `anchor_free_interval` collapses, and `boundary_proposal` also remains below smoothing. High `deleted_true_backed_fraction` confirms that apparent fragment cleanup is often true-fragment deletion rather than interval repair.

## Sanity Check

- [x] Result-log exists and semantic success passed.
- [x] Metrics are present, parseable, finite, and include strict segment/boundary/retention guardrails.
- [x] Code-review gate passed before Slurm run.
- [x] At least two independent CLI reviewers succeeded: 3/3 quorum.
- [x] No reviewer raised leakage or evaluator comparability blocker.
- [x] Claim eligibility: no claim; screen-only.

## Tri-review Summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `abandon-route` | Stop frozen-lightweight interval head route; any future attempt must be a fundamentally different mechanism. | Both heads fail via the same deletion/retention tradeoff as DEC-001; `anchor_free_interval` collapses on mouse. | High |
| B · Codex | `replace-component` | Replace with fragment graph linker or boundary-conditioned span refinement. | Current shallow heads lack fragment topology and true-fragment preservation. | Medium |
| C · Antigravity | `abandon-route` | Abandon frozen coordinate/boundary head patch route; consider end-to-end detector or contrastive fragment linkage. | High true-backed deletion shows the heads act as filters, not repair modules. | High |

Consensus: stop current `boundary_proposal` and `anchor_free_interval`; do not tune or scale them.

Disagreement: whether to label the whole branch `abandon-route` or `replace-component`. The actionable convergence is `replace-component`: current component is abandoned, but a second bounded capability round may be justified only with a genuinely new mechanism.

Quorum / degraded review status: `3/3`.

## Reviewer-proposed Directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into next cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | End-to-end set prediction / graph instance-level modeling | architecture | Replace shallow frozen head with global interval/instance optimization. | yes | candidate |
| 2 | B · Codex | Fragment graph linker | architecture | Build candidate fragments as graph nodes and learn keep/link/split adjacency with deletion-aware objective. | yes | primary candidate |
| 3 | B · Codex | Boundary-conditioned span refinement | architecture | Use high-recall CE fragments and learn left/right boundary correction with preservation loss. | partly | candidate |
| 4 | C · Antigravity | End-to-end multi-task interval detector | architecture | Unfreeze late backbone layers and train 1D detection loss with matching/GIoU. | yes | candidate |
| 5 | C · Antigravity | Contrastive fragment linkage | representation/objective | Pull fragments from the same TE instance together and separate different instances. | yes | candidate |

## Is Tuning Justified?

No. The failure is structural and cross-panel; tuning thresholds, gaps, smoothing penalties, or shallow head thresholds would violate the active constraints and DEC-001.

## Architecture Hypothesis Status

Weakened for frozen-lightweight interval heads; still unknown for genuinely global interval/instance architectures.

## Decision

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [x] Replace component: abandon the tested frozen-lightweight interval heads and allow at most one second bounded round with a new fragment graph/linking or boundary-conditioned span module.
- [ ] Change backbone
- [ ] Change objective / loss only
- [ ] Comparability audit first
- [ ] Sanity check first
- [ ] Abandon the entire interval-aware capability direction
- [ ] Return to literature

## Why This Decision

The current components failed cleanly and should not be scaled. However, the reviewers did not falsify interval-aware TE annotation broadly: all three point to mechanisms that are materially different from DEC-001 and from the two tested heads. A single second bounded round is defensible if it changes the object of prediction from independent intervals to fragment linking / instance-level set prediction, while retaining the same strict true-fragment guardrails. If that second round also fails, the capability should be written as future work rather than pursued further.

## Best Next Architecture Moves

| Priority | Move | Expected mechanism | Goes to which EXP / Track |
|---:|---|---|---|
| 1 | Fragment graph linker | Preserve CE high-recall fragments, learn adjacency/link/split decisions, and optimize deletion-aware interval metrics. | `PIPE-TEFM-CAP-FRAGGRAPH-YYYYMMDD` / capability-pursue Round 2 |
| 2 | Boundary-conditioned span refinement | Learn pointer/offset corrections for high-recall fragments instead of suppressing fragments. | optional parallel candidate if scoped small |
| 3 | End-to-end 1D set detector | True object-detection style interval prediction with matching loss; heavier and should only follow if Round 2 graph/refiner shows signal. | future work / larger capability |

## Parallel Cohort This Round

- Primary direction: `replace-component`.
- Parallel cohort: none launched automatically in this pivot; next `$capability-pursue` round should implement at most one primary graph/linking module and optionally one boundary-conditioned refiner if code paths are isolated.

## TODO Update

- [x] Update `docs/05_todo.md`
- [x] Update `docs/07_tri_review.md`
- [x] Update `docs/08_pivot_decisions.md`
- [ ] Update `docs/04_experiment_iterations.md` with tri-review/pivot closeout.
- [ ] Update `docs/15_evidence_register.md` via note-gate.
- [ ] Update `docs/11_master_plan.md` if the active next step changes.

---

# Pivot Decision: PIPE-TEFM-CAP-FRAGGRAPH-20260701

Date: 2026-07-01

## Inputs Consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-cap-fraggraph-20260701`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fraggraph-20260701`
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_metrics.tsv`
- Status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_status.json`
- Resource profile: bounded capability-pursue screen

## Current Evidence Summary

`PIPE-TEFM-CAP-FRAGGRAPH-20260701` completed semantically and tested the Round-2 replacement component requested by the prior `replace-component` pivot. The primary preservation-first decoder, `fragment_graph_keepall`, retains all CE raw fragments and therefore has `deleted_true_backed_fraction=0`, but it is identical to CE raw on both human and mouse. The diagnostic learned keep/drop decoder improves human strict segment-F1@IoU0.8 and boundary-F1@5bp to `0.4964`/`0.2458`, above CRF-style smoothing, but deletes true-backed CE fragments at `0.8632` and does not beat CRF-style smoothing on mouse.

## Sanity Check

- [x] Result-log exists and semantic success passed.
- [x] Metrics are present, parseable, finite, and include strict segment/boundary/retention guardrails.
- [x] Code-review gate passed before Slurm run.
- [x] Slurm job `9866570` completed with state `COMPLETED`.
- [x] At least two independent CLI reviewers succeeded: 3/3 quorum.
- [x] No reviewer raised a data leakage or evaluator blocker.
- [x] Claim eligibility: no claim; screen-only.

## Tri-review Summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `abandon-route` | Stop the capability route and write interval reconstruction as future work. | Keep-all graph does not link; keep/drop gains are deletion-driven. | High |
| B · Codex | `abandon-route` | Stop `PIPE-TEFM-CAP-FRAGARCH`; do not run boundary-conditioned span-refiner. | Human gain has `deleted_true_backed_fraction=0.8632`; mouse remains below smoothing. | High |
| C · Antigravity | `abandon-route` | Terminate this interval-aware decoder capability sprint. | Keep/drop behaves like an unsafe filter rather than true interval repair. | High |

Consensus: 3/3 reviewers recommend abandoning the capability-pursue branch after Round 2.

Disagreement: none material.

Quorum / degraded review status: `3/3`.

## Is Tuning Justified?

No. The failure is not a threshold, gap, HMM/CRF penalty, or survival-retention tuning issue. The safe graph decode fails to change intervals; the unsafe graph decode improves human only by deleting true-backed fragments and fails cross-panel transfer. More tuning would overlap with already-abandoned cousin routes.

## Architecture Hypothesis Status

The specific bounded capability hypothesis is falsified for now: frozen/post-hoc interval reconstruction modules built on CE fragments or frozen embeddings have not produced a reusable interval-level TE annotation component under strict true-backed guardrails. This does not prove that all future end-to-end TE interval detectors are impossible, but they require a substantially different research program, larger validation, and likely richer biological/annotation priors.

## Decision

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component again
- [ ] Change backbone
- [ ] Change objective / loss only
- [ ] Comparability audit first
- [ ] Sanity check first
- [x] Abandon this capability route for the current sprint
- [ ] Return to literature

## Why This Decision

Round 1 already showed that lightweight frozen interval heads cannot beat smoothing while preserving true-backed fragments. Round 2 replaced the component with fragment graph linking, but the preservation-safe decoder made no interval improvement and the only improving decoder violated the true-backed deletion guardrail. Because all three reviewers recommend stopping and there is no specific evaluator/data bug, the correct pivot is to close TEFM-CAP-FRAGARCH as future work rather than launch another bounded refiner.

## Best Next Architecture Moves

| Priority | Move | Expected mechanism | Goes to which track |
|---:|---|---|---|
| 1 | Stop capability-pursue branch | Avoid cycling through post-hoc interval reconstruction modules that either do nothing or delete true fragments. | docs/09 / future-work limitation |
| 2 | Keep CE raw + existing overlap/smoothing as fixed comparators | They remain useful baselines and annotation-support heuristics, but not a solved interval module. | publication support |
| 3 | If revived later, require end-to-end global set prediction or biologically richer interval modeling | Must pre-register deletion guardrails and pass at least two chromosomes/species before any claim. | future work only |

## TODO Update

- [x] Update `docs/07_tri_review.md`
- [x] Update `docs/08_pivot_decisions.md`
- [x] Update `docs/09_decisions_log.md`
- [x] Update `docs/04_experiment_iterations.md`
- [x] Update `docs/05_todo.md`
- [x] Update `docs/10_findings.md`
- [x] Update `docs/11_master_plan.md`
- [x] Update `docs/15_evidence_register.md`
- [x] Update `docs/24_sprint_pursue_ledger.md`

# Pivot Decision: PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630

Date: 2026-06-30

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-pursue-minhash-intervalsurv-20260630`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-pursue-minhash-intervalsurv-20260630`
- Validator: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/pursue_combined_metrics.json`
- Resource profile: bounded screen; non-claim support.

## Current evidence summary

Selector MinHash-equivalent genome distance did not make a point-estimate decay formula deployable. The selected in-panel policy remains `baseline_plus_kmer` with top-2 contains-best `0.8636` and mean regret `0.0071`; leave-clade/new-clade stays explicit abstention plus local probe/new anchor. Decoder `interval_survival_decoder` improves segment-F1 and boundary-F1 over CE and now keeps missed_true_rate delta within `+0.03`, but it still deletes too many true-backed fragments (`0.4592` vs guardrail `0.15`), so the validator status is `not_yet`.

## Support gap

| Metric | Current | Gate | Gap | Status |
|---|---:|---:|---:|---|
| selector_top2_contains_best | 0.8636 | >=0.85 | +0.0136 | pass |
| selector_mean_regret | 0.0071 | <=0.03 | +0.0229 margin | pass |
| selector_leave_clade_abstention_rate | 1.0000 | >=0.95 | +0.0500 | pass |
| decoder_segment_f1_delta_vs_ce | +0.0687 | >0 | +0.0687 | pass |
| decoder_boundary_f1_delta_vs_ce | +0.0391 | >0 | +0.0391 | pass |
| decoder_missed_true_rate_delta_vs_ce | +0.0287 | <=0.03 | +0.0013 margin | pass |
| decoder_deleted_true_backed_fraction | 0.4592 | <=0.15 | -0.3092 | fail |

## Sanity check

- [x] Three independent CLI reviewers succeeded.
- [x] No reviewer raised a leakage or metric-comparability blocker for screen use.
- [x] `validate_goal.py` run status and semantic checks passed.
- [x] Screen profile cannot claim SOTA.
- [x] Tuning is not justified; if continuing decoder, the axis must be objective/loss or decoder design.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | abandon-route | stop selector and decoder; record limitation/future work | two decoder rounds both delete too many true-backed fragments | High |
| B · Codex | change-objective-or-loss | one final decoder-only `retention_constrained_interval_loss` bounded screen | true-backed deletion is the remaining hard guardrail | Medium-High |
| C · Antigravity | change-objective-or-loss | lock selector; one final radically different decoder objective such as center-offset or joint CE-constrained loss | survival/retention objectives prune true short fragments | High |

Consensus: selector stops as triage-only; current decoder cannot be promoted or scaled; no threshold/gap/post-hoc smoothing continuation.

Disagreement: whether decoder should stop now or receive one final bounded objective/loss attempt. Because this round newly passed the missed_true_rate delta gate and the remaining failure is sharply targeted, pivot allows one final decoder-only attempt, then stops if guardrail fails.

Quorum / degraded review status: `3/3`.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into next cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | abandon decoder | route decision | write future work after repeated true-backed deletion | yes | no |
| 2 | B · Codex | retention-constrained interval loss | objective/loss | make deleted true-backed fragments part of training penalty | yes | yes, primary |
| 3 | C · Antigravity | center-offset or joint CE-constrained decoder | objective/head | avoid survival-style deletion by predicting segment center/boundaries or protecting bp CE evidence | yes | optional variant only if cheap |

## Is tuning justified?

No. The failed guardrail is structural and far from threshold (`0.4592` vs `0.15`). Hyperparameter tuning, gap merging, and post-hoc HMM/CRF penalty changes are disallowed by the goal and would not address the deletion mechanism.

## Architecture hypothesis status

- Selector hypothesis: supported only as conservative in-panel router; point-estimate formula remains unsupported and should be stopped as limitation.
- Decoder hypothesis: partially supported for structured objective signal, weakened for deployable fragmentation cleanup because true-backed fragment deletion remains high.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component
- [ ] Change backbone
- [x] Change objective / loss
- [ ] Comparability audit first
- [ ] Sanity check first
- [ ] Abandon this route now
- [ ] Return to literature

## Why this decision

The selector has now met the user’s stop condition for formula work: two bounded rounds support only triage, not a deployable decay formula. For decoder, the primary segment/boundary/missed_true gates improved enough that an immediate abandon would leave a targeted, testable guardrail unrepaired. The only allowed continuation is one final bounded objective/loss screen that directly penalizes true-backed deletion. If that fails, the decoder direction must stop and be written as future work.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which EXP / Track |
|---:|---|---|---|
| 1 | `retention_constrained_interval_loss` | make true-backed deletion costly during training, not only diagnostic | final bounded decoder screen |
| 2 | optional cheap center-offset/joint CE-constrained variant | avoid survival decoder’s bias toward deleting short true fragments | only if implementable within same final screen |
| 3 | selector limitation write-up | prevent overclaiming formula/generalization trust | docs/publication support |

## Parallel cohort this round

- Primary direction: decoder-only objective/loss change with hard true-backed deletion guardrail.
- Selector direction: stopped; no further compute.
- Parallel cohort: none unless the center-offset variant is implemented inside the same decoder script without extra shared-code conflict.

| Slot | EXP ID (new) | Direction | major_axis | mechanism_delta | Track | Resource profile |
|---|---|---|---|---|---|---|
| primary | `PIPE-TEFM-PURSUE-RETCONSTR-20260630` | retention-constrained interval objective | objective/loss | train against true-backed deletion | bounded support screen | screen |

Shared-code conflict: no, single script/sbatch under existing structured-decoder pipeline.

## TODO update

- [x] Update docs/07 with full tri-review.
- [x] Implement and submit `PIPE-TEFM-PURSUE-RETCONSTR-20260630`.
- [x] If final decoder screen fails `deleted_true_backed_fraction <= 0.15`, stop decoder direction and write future-work limitation.
- [x] Update docs/05/06/10/11/15 after final decoder screen.

---

# Pivot Decision: PIPE-TEFM-PURSUE-RETCONSTR-20260630

Date: 2026-06-30

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-pursue-retconstr-20260630`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-pursue-retconstr-20260630`
- Validator: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/pursue_combined_metrics.json`
- Resource profile: bounded screen; non-claim support.

## Current evidence summary

The final retention-constrained decoder screen completed cleanly on a 24GB RTX 3090. It reduced missed_true_rate relative to CE (`0.2541` vs `0.2623`) and lowered true-backed deletion relative to the prior interval-survival variant, but it failed the actual method gates: segment-F1 fell from CE `0.3069` to `0.2534`, boundary-F1 fell from `0.1414` to `0.0856`, and deleted_true_backed_fraction remained above the guardrail (`0.2727` vs `0.15`). There is no gate-eligible decoder variant.

## Support gap

| Metric | Current | Gate | Gap | Status |
|---|---:|---:|---:|---|
| decoder_segment_f1_delta_vs_ce | -0.0535 | >0 | -0.0535 | fail |
| decoder_boundary_f1_delta_vs_ce | -0.0558 | >0 | -0.0558 | fail |
| decoder_missed_true_rate_delta_vs_ce | -0.0082 | <=0.03 | pass margin | pass |
| decoder_deleted_true_backed_fraction | 0.2727 | <=0.15 | -0.1227 | fail |

## Sanity check

- [x] Three independent CLI reviewers succeeded.
- [x] Engineering run completed and metrics are finite.
- [x] No leakage/comparability blocker is needed to explain the failure.
- [x] Pre-registered stop condition applies.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | abandon-route | stop decoder, record future work | segment/boundary regressed and deletion guardrail still failed | High |
| B · Codex | abandon-route | close out as engineering success/method failure | final allowed objective/loss attempt did not meet gates | High |
| C · Antigravity | abandon-route | freeze architecture and proceed to publication wording | method degraded core metrics and failed safety guardrail | High |

Consensus: `3/3` agree decoder direction must stop now; selector remains triage-only.

Disagreement: none material.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [ ] Comparability audit first
- [ ] Sanity check first
- [x] Abandon this route
- [ ] Return to literature

## Why this decision

The route received the exact final bounded objective/loss attempt authorized by the previous pivot. It failed both strict segment/boundary improvements and true-backed deletion guardrail. Continuing would violate the active stop rule and convert a bounded publication-support experiment into marginal method fishing.

## Carry-forward

- Selector carries forward as conservative trust router only: known/in-panel top-2 shortlist plus local chromosome probe; leave-clade/new-clade abstain and require local probe/new anchor.
- CE baseline with existing overlap/smoothing remains the defensible default for fragmentation reporting in this milestone.
- Structured decoder objectives are recorded as future work: interval-survival improved segment/boundary but deleted true-backed fragments; retention-constrained loss improved retention but degraded segment/boundary.

## If abandoning, log to decisions-log

- Path tried: post-hoc smoothing -> frozen interval refiner -> joint HMM/CRF/semi-Markov -> interval-survival -> retention-constrained interval objective.
- Evidence why failed: no bounded variant simultaneously improved segment-F1, boundary-F1, controlled missed_true_rate, and kept deleted_true_backed_fraction <=0.15.
- What we now believe: current Markov/survival/retention structured decoder family exposes a real tradeoff but is not a usable fragmentation solution under strict metrics.
- Cousins to avoid: threshold/gap/post-hoc HMM/CRF retuning; another semi-Markov/retention penalty tweak; survival-style decoder with no stronger external interval evidence.

## TODO update

- [x] Update docs/07 final tri-review.
- [ ] Write docs/09 decision log entry.
- [ ] Update docs/05/10/11/15 final closeout.

---

# Pivot Decision: PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630

Date: 2026-06-30

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-pursue-decay-struct-20260630`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-pursue-decay-struct-20260630`
- Selector status: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/selector_conservative_router_status.json`
- Decoder status: `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/joint_structured_decoder_status.json`
- Resource profile: screen

## Current evidence summary

The selector component met the conservative router gate when framed as top-2 shortlist plus local chromosome probe for in-panel/leave-species cases, and explicit abstention for leave-clade/new-clade cases. It remains unsuitable as an exact point F1 confidence formula or a single-anchor automatic selector. The decoder component completed semantically and improved segment/boundary metrics, but failed the hard true-retention gate because missed_true_rate rose too much and deleted fragments were about half true-backed.

## SOTA gap

| Metric | Current | SOTA | Gap | Severity |
|---|---:|---:|---:|---|
| Selector top2 contains-best, leave-species | 0.8636 | n/a | n/a | screen router gate pass |
| Selector mean regret, leave-species | 0.0071 | n/a | n/a | screen router gate pass |
| Selector leave-clade confident anchor coverage | 0.0000 | n/a | n/a | abstention required |
| Decoder best segment-F1@IoU0.8 | 0.4439 | CE 0.3069 | +0.1370 | improved |
| Decoder best boundary-F1@5bp | 0.2290 | CE 0.1414 | +0.0876 | improved |
| Decoder missed_true_rate | 0.3525 | CE 0.2623 | +0.0902 | gate fail |

## Sanity check

- [x] Metrics files exist and are parseable.
- [x] Slurm job `9860400` completed and `job_watch` wrote `COMPLETED`.
- [x] Code-review gate exists for the decoder screen.
- [x] 3/3 independent reviewer outputs were produced.
- [x] Claim eligibility is explicitly false.
- [ ] ACTIVE_GOAL / SOTA claim contract is active: no, still draft; not relevant for this non-claim support screen.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `replace-component` for decoder; selector triage-only | Replace weak token-level retention with interval-level true-retention / fragment-survival objective | `semimarkov_retention` deleted 83 true-backed fragments and failed missed_true_rate | Medium |
| B · Codex | `change-objective-or-loss` | Add true-retention-constrained structured decoder; disqualify any variant violating missed_true_rate gate | Segment/boundary gains are bought by deleting true-backed evidence | High |
| C · Antigravity | `change-objective-or-loss` | Stop expanding current training; design stronger true-retention penalty or decoding constraint | missed_true_rate fails and 49.4% of deleted fragments are true-backed | High |

Consensus: selector can be carried forward only as conservative router; decoder cannot be promoted or scaled.

Disagreement: Claude labels the decoder next step as component replacement, while Codex/Antigravity label it objective/loss change. The operational decision is the same: replace the weak retention proxy with interval-level true-retention constraints.

Quorum / degraded review status: `3/3`.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into this round's cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | interval-level true-retention / fragment-survival objective | decoder objective | penalize deleted true-backed intervals directly | yes | future-only |
| 2 | B · Codex | true-retention-constrained structured decoder with hard gate in model selection | objective/loss + selection rule | variants violating missed_true_rate gate cannot be best | overlaps A | future-only |
| 3 | C · Antigravity | stronger true-retention penalties or constrained decoding | decoder objective | prevent smoothing from erasing high-confidence true fragments | overlaps A/B | future-only |

## Is tuning justified?

- ❌ No. This is not an optimization issue; the decoder objective is trading recall/retention for interval neatness.

## Architecture hypothesis status

- Selector: supported only as conservative router.
- Decoder: weakened as currently implemented; joint structured backend remains promising, but the current retention proxy is inadequate.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [ ] Scale data / training
- [ ] Replace component only
- [ ] Change backbone
- [x] Change objective / loss: replace weak token-level retention with interval-level true-retention or fragment-survival constraint before any further decoder scaling
- [ ] Comparability audit first
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The selector’s objective is now narrow and defensible: avoid confidently wrong anchor choices by returning a top-2 shortlist or abstaining. It does not need another immediate selector experiment. The decoder, however, violates the user’s explicit promotion gate. Since the failure mode is deleting true-backed TE fragments, increasing data or training time would likely strengthen the same behavior unless the loss/objective changes. Therefore the only allowed continuation is an objective-level redesign, not scale-up or threshold tuning.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which EXP / Track |
|---:|---|---|---|
| 1 | Interval-level true-retention loss | Penalize a true TE interval being split away or erased even if segment-F1 improves | future fragment screen |
| 2 | Fragment-survival constrained decoder selection | Treat missed_true_rate and deleted_true_backed_fraction as hard disqualifiers | future fragment screen |
| 3 | Keep selector policy fixed | Avoid overfitting selector into false confidence; use top-2/local-probe + leave-clade abstention | publication-validation docs |

## Parallel cohort this round

- Primary direction: stop current decoder scaling; future work must change objective/loss.
- Parallel cohort: none launched automatically after this pivot. User stopping rules say do not keep expanding if the true-retention gate fails.

| Slot | EXP ID (new) | Direction | major_axis | mechanism_delta | Track | Resource profile |
|---|---|---|---|---|---|---|
| primary | pending only if user continues | true-retention-constrained interval objective | decoder objective | interval-level retention, not post-hoc smoothing | screen | bounded |

Shared-code conflict: no active cohort.

## TODO update

- [x] update docs/05_todo.md
- [x] update docs/08_pivot_decisions.md
- [x] run note-gate/evidence capture to docs/15
- [x] update master-plan state in docs/11

---

# Pivot Decision: PIPE-TEFM-FINAL-20260623

Date: 2026-06-29

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-final-20260623-ntv3-recovery-and-model-size-matrix-closure`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-final-20260623`
- Matrix summary: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`
- Resource profile: Track A screen

## Current evidence summary

The NTv2/NTv3 model-size x window matrix is semantically complete: 495 matrix eval rows, including all expected NTv2 and repaired NTv3 outputs. Human H0 and animal_fine are led by `ntv2_250m@4096`; plant_fine and diagnostic animal+plant combined mean are led by `ntv3_100m_pre@2048`. The screen rejects simple parameter-size monotonicity and rejects a single universal headline mean.

## SOTA gap

| Metric | Current | SOTA | Gap | Severity |
|---|---:|---:|---:|---|
| Human H0 TE-F1 (`ntv2_250m@4096`) | 0.93494 | unknown / not claimable | unknown | screen only |
| Animal_fine mean TE-F1 (`ntv2_250m@4096`) | 0.64823 | n/a | n/a | panel screen |
| Plant_fine mean TE-F1 (`ntv3_100m_pre@2048`) | 0.39802 | n/a | n/a | panel screen |
| Combined animal+plant mean (`ntv3_100m_pre@2048`) | 0.49850 | n/a | n/a | diagnostic only; not headline |

## Sanity check

- [x] At least two independent CLI reviewers succeeded: 3/3.
- [ ] SOTA benchmark is configured for claim: no.
- [x] Metrics file exists and is parseable.
- [x] Accepted outputs are finite and semantically complete.
- [x] NTv3 failed eval arrays were superseded and excluded.
- [ ] Chromosome variance known: no, this is the next required step.
- [ ] Segment/boundary/fragmentation claim metrics complete for these promoted candidates: pending strict follow-up.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `scale-to-track-b` | Promote `ntv2_250m@4096`, `ntv2_250m@2048`, and `ntv3_100m_pre@2048`; lock evaluator/SOTA before claims | `ACTIVE_GOAL`/SOTA and evaluator contract still draft; plant label quality and chromosome variance unresolved | High for screen promotion |
| B · Codex | `scale-to-track-b` | Promote minimal set `ntv2_250m@4096` + `ntv3_100m_pre@2048`; build panel-specific selector | Panel mixing, one-chromosome variance, and missing strict segment metrics | Medium-high |
| C · Antigravity | `scale-to-track-b` | Promote `ntv2_250m@4096` + `ntv3_100m_pre@2048`; optional `ntv2_250m@8192` fallback only if needed | Variance, stress-species distortion, and bp-only metric insufficiency | High |

Consensus: promote to Track B / chromosome-repeat validation; do not tune and do not continue expanding the model zoo.

Disagreement: whether to include an extra NTv2 window in the repeat set. The compromise is to run the required minimal two-candidate set first and include `ntv2_250m@2048` only as a low-cost shared-anchor/stability check if scheduler capacity allows.

Quorum: `3/3`.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into this round's cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | Chromosome-repeat error bars for `ntv2_250m@4096`, `ntv2_250m@2048`, `ntv3_100m_pre@2048` | validation | Estimate split/chromosome variance and window stability | yes | partial |
| 2 | A · Claude | Plant label-concordance audit | data/label | Distinguish plant model weakness from label/source failure | yes | yes, if plant candidate is evaluated |
| 3 | B · Codex | Two-anchor repeat validation for `ntv2_250m@4096` and `ntv3_100m_pre@2048` | validation + anchor routing | Minimal panel-specific promotion set | yes | yes |
| 4 | B · Codex | Strict segment/boundary/fragmentation metrics for promoted candidates | evaluator | Move beyond bp-level TE-F1 | yes | yes |
| 5 | C · Antigravity | Multi-anchor routing logic after error bars | deployment | Animal/human route to NTv2, plant route to NTv3 | depends on error bars | later |
| 6 | C · Antigravity | Optional `ntv2_250m@8192` fallback | window | Check high-context fallback only if 4096 underperforms | no; same axis as NTv2 window | no for minimal run |

## Is tuning justified?

No. The main uncertainty is not optimizer tuning; it is panel-specific backbone choice, chromosome variance, evaluator strictness, and label/source quality.

## Architecture hypothesis status

Supported with qualification: pretrained nucleotide FM choice and window size matter, but larger parameter count and longer pretraining context do not monotonically improve transfer. The best current strategy is panel-specific anchors, not one universal model.

## DECISION

- [ ] Continue current architecture as-is
- [ ] Tune current architecture
- [x] Scale to Track B / chromosome-repeat validation
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability/evaluator contract before claim
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The screen objective has been achieved. Additional broad screening would add cost without resolving the key uncertainty. The right next experiment is repeat validation of the two panel leaders, with strict evaluator metrics and panel-separated reporting. This also carries forward the user's strategic reframe: multiple anchors are preferable to a single universal model unless repeat validation says otherwise.

## Parallel cohort this round

| Slot | EXP ID (new) | Direction | major_axis | mechanism_delta | Track | Resource profile |
|---|---|---|---|---|---|---|
| primary | `PIPE-TEFM-FINAL-EBAR-20260629` | Chromosome-repeat error bars for `ntv2_250m@4096` and `ntv3_100m_pre@2048` | validation | Estimate chromosome variance and panel-specific stability | Track B | repeat screen |
| parallel-1 | `PIPE-TEFM-FINAL-STRICTSEG-20260629` | Strict segment/boundary/fragmentation evaluation on promoted candidates | evaluator | Check annotation usability, not only bp TE-F1 | Track B support | screen |
| parallel-2 | `PIPE-TEFM-FINAL-PLANTQC-20260629` | Plant label/source concordance audit for promoted plant candidate panel | data/label | Explain low absolute plant transfer and prevent overclaim | support | screen |

Shared-code conflict: no expected shared-code edits if implemented as config/sbatch/report stages; if evaluator code changes are required, run code-review gate before submission.

## TODO update

- [x] update `docs/07_tri_review.md`
- [x] update `docs/08_pivot_decisions.md`
- [ ] submit/execute Track B repeat candidates after implementation/gate
- [x] update `docs/05_todo.md`
- [x] update `docs/11_master_plan.md`
- [x] update `docs/15_evidence_register.md`

---

# Pivot Decision: PIPE-TEFM-ANCHOR-20260621

Date: 2026-06-22

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-anchor-20260621`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-anchor-20260621`
- `$council`: `docs/00_active_goal.md#council_2026-06-21_anchor_selector`
- Final report: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/FINAL_REPORT.md`
- Resource profile: screen

## Current evidence summary

`PIPE-TEFM-ANCHOR-20260621` completed semantically. The run supports moving from a single universal model recommendation to panel-specific anchors plus a deployable selector under evaluation. `insect_primary_4096` strongly recovers honeybee, but red flour beetle remains near-zero across all anchors. Unknown annotations contain main4-like SF5 signal and should enter an annotation-audit queue, while strict high-score unannotated candidates are mostly BG and do not support model-only discovery. Background-inclusive embedding still favors C1 basic sequence/kmer features over GENERanno embeddings. The deployable anchor selector is useful as a rough screen but not yet a stable deployment claim.

## SOTA gap

| Metric | Current | Comparator | Gap | Severity |
|---|---:|---:|---:|---|
| Stress mean TE-F1 (`insect_primary_4096`) | 0.5197 | `animal_invert_boost` 0.4248 | +0.0949 | screen improvement only |
| Honeybee TE-F1 (`insect_primary_4096`) | 0.9465 | `animal_invert_boost` 0.0522 | +0.8943 | strong stress recovery |
| Red flour beetle TE-F1 | ~0.005 | usable threshold not reached | n/a | hard failure |
| BG+main4 A1 ARI | 0.4067 | C1 ARI 0.8353 | -0.4286 | model embedding not superior |
| Deployable RF leave-species-out RMSE | 0.3467 | n/a | n/a | descriptive/screen only |

## Sanity check

- [x] Result-log exists and semantic success passed.
- [x] Metrics files are present, parseable, finite, and complete.
- [x] Binary eval has 24 rows and embedding summary has 8 rows.
- [x] SF5 candidate summary and anchor formula outputs exist.
- [x] Initial SF5 failure is superseded by a successful CPU retry.
- [ ] At least two independent CLI reviewers succeeded: no, this closeout is degraded host/council synthesis.
- [ ] SOTA benchmark is configured: no, ACTIVE_GOAL remains draft.
- [ ] Claim-level evaluator/comparability contract is locked: no.

## DECISION

- [x] Continue current architecture as robust route
- [ ] Tune current architecture
- [ ] Scale data / training now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability audit first before any claim
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The run closes the user's requested evidence loop without changing the main backbone. It shows that an insect-primary anchor is valuable for honeybee-like insects, that beetle should remain a hard stress/audit species, and that Unknown/high-score unannotated sequences need conservative evidence tiers. Because the run is screen-only and selector validation is not locked, the correct next action is Track B planning with panel-specific anchors, not a claim or hyperparameter tuning.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which track |
|---:|---|---|---|
| 1 | Freeze panel-specific recommendation protocol | Prevent universal-mean overclaiming | claim-prep |
| 2 | Carry forward `invert_boost_animal_4096` | Animal/vertebrate primary branch | Track B candidate |
| 3 | Carry forward `cross_supervised_4096` or plant-supervised branch | Plant/cross calibration branch | Track B candidate |
| 4 | Carry forward `insect_primary_4096` | Honeybee-like insect anchor | stress/insect branch |
| 5 | Exclude beetle from primary means | Avoid label/library/domain failure distorting claim | stress appendix |
| 6 | Keep C1 and deployable-only selector baselines | Prevent embedding/selector overclaiming | validation contract |

## TODO update

- [x] Update `docs/05_todo.md`
- [x] Update `docs/06_results_log.md`
- [x] Update `docs/04_experiment_iterations.md`
- [x] Update `docs/07_tri_review.md`
- [x] Update `docs/08_pivot_decisions.md`
- [x] Update `docs/10_findings.md`
- [x] Update `docs/11_master_plan.md`
- [x] Update `docs/15_evidence_register.md`

---

## Mid-iteration note 2026-06-21: tefm-anchor-selector-unknown-relabel-20260621

- Relevance: directly-attacks-current-gap.
- Does it change our hypothesis? Refines it: the model recommendation should become kingdom/panel-specific anchors plus a deployable selector under evaluation, not a single universal branch.
- Conflicts with abandoned routes? No formal `docs/09` abandoned route overlap, but it touches the PU/unannotated-risk boundary. This is not a PU restart and must not treat unannotated regions as reliable negatives.
- Recommendation: fold-into-current-batch. `PIPE-TEFM-ANCHOR-20260621` is already running this screen with BG-inclusive embedding, Unknown/high-score SF5 diagnostics, insect-primary anchor, and deployable vs annotation-aware formula.
- Urgency: high for interpretation, not for changing currently submitted jobs. Keep screen-only language until result-log/tri-review/pivot.

---

# Pivot Decision: PIPE-TEFM-CALIB-20260621

Date: 2026-06-21

## Inputs consumed

- `$result-log`: `docs/06_results_log.md#result-pipe-tefm-calib-20260621`
- `$tri-review`: `docs/07_tri_review.md#tri-review-pipe-tefm-calib-20260621`
- Final report: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`
- Resource profile: screen

## Current evidence summary

`PIPE-TEFM-CALIB-20260621` completed semantically. Standard supervised plant/cross fine-tuning with reliable negatives is useful and should replace PU as the main plant/cross calibration evidence. `cross_supervised_4096` is the best broad screen mean and strongest on plant fine-tune held-out species; `animal_invert_boost` remains competitive and slightly stronger on broad cross-eval and stress means. Insect-no-beetle rescues honeybee but not red flour beetle. Dfam consensus embedding confirms C1 remains the dominant representation baseline. The extended decay formula is meaningful only after adding label/source and panel variables.

## SOTA gap

| Metric | Current | SOTA | Gap | Severity |
|---|---:|---:|---:|---|
| Broad mean TE-F1 (`cross_supervised_4096`) | 0.5786 | unknown | unknown | cannot judge |
| Plant-fine mean TE-F1 (`cross_supervised_4096`) | 0.8568 | unknown | unknown | cannot judge |
| Broad cross-eval mean TE-F1 (`animal_invert_boost`) | 0.6026 | unknown | unknown | cannot judge |
| Dfam consensus A1 ARI | 0.2242 | C1 baseline 0.7083 | -0.4841 | model embedding not superior |
| Extended decay full R2 | 0.7407 | n/a | n/a | descriptive only |

## Sanity check

- [x] Result-log exists and semantic success passed.
- [x] Metrics files are present, parseable, finite, and complete.
- [x] Expected eval outputs are complete: 98/98.
- [x] Log scan found no final-run failure signatures.
- [ ] At least two independent CLI reviewers succeeded: no, this closeout is degraded host/council synthesis.
- [ ] SOTA benchmark is configured: no, ACTIVE_GOAL remains draft.
- [ ] Claim-level evaluator/comparability contract is locked: no.

## DECISION

- [x] Continue current architecture as robust route
- [ ] Tune current architecture
- [ ] Scale data / training now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability audit first before any claim
- [ ] Sanity check first
- [ ] Abandon this route
- [ ] Return to literature

## Why this decision

The run resolves the user's main critique: plant/cross standard supervised calibration is not the same as PU, and it works. It also confirms that one mixed mean is the wrong way to communicate performance. Cross-supervised, animal invert-boost, and insect-no-beetle each answer different panel questions. Because the run is screen-only and review quorum/claim contracts remain incomplete, the next decision is to carry forward supported branches into a locked validation design, not to claim SOTA or tune hyperparameters.

## Best next architecture moves

| Priority | Move | Expected mechanism | Goes to which track |
|---:|---|---|---|
| 1 | Freeze evaluator, panel, and label-source contract | Prevent primary/stress/kingdom mixing from invalidating claims | claim-prep |
| 2 | Carry forward `cross_supervised_4096` | Best plant/cross calibration and broad screen mean | Track B candidate |
| 3 | Carry forward `invert_boost_animal_4096` | Stronger animal/vertebrate and stress reference branch | Track B candidate |
| 4 | Keep insect-no-beetle as honeybee diagnostic only | Shows calibratable insect stress without overclaiming beetle | stress appendix |
| 5 | Keep C1/A1 embedding baselines | Prevent overclaiming model representation superiority | embedding diagnostic |
| 6 | Use source-aware decay variables | Separates model generalization from label/library completeness | generalization formula |

## TODO update

- [x] Update `docs/05_todo.md`
- [x] Update `docs/06_results_log.md`
- [x] Update `docs/04_experiment_iterations.md`
- [x] Update `docs/07_tri_review.md`
- [x] Update `docs/08_pivot_decisions.md`
- [x] Update `docs/10_findings.md`
- [x] Update `docs/11_master_plan.md`
- [x] Update `docs/15_evidence_register.md`
## Failed-run stop: BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2

- Date: 2026-08-11 CEST.
- Deterministic verdict: `failed_run` after independent semantic audit.
- Why: RM/EarlGrey/HiTE/EDTA all launched and then failed identity/runtime/integration gates; the collector incorrectly labeled them foundational. Only TEtrimmer's pre-execution immutable-Pfam absence is a valid foundational block.
- Decision: **STOP_AND_NOTIFY**. No rerun, scale or biological benchmark. Repair cell classification and the four runtime integrations, then obtain fresh code review before any bounded retry.
- Claim boundary: no tool performance conclusion; intact artifacts do not rescue invalid semantics.

---

## Failed-run stop: SF-DIRECT-BASELINE-SCREEN-20260811-R2 CPU DATA

- Date: 2026-08-11 CEST.
- Deterministic verdict: `failed_run` (`STATUS=DATA_FAILED`, semantic false).
- Why: the data builder hit Python CSV's 131072-byte default field limit while reading the frozen chunk manifest, before data materialization or leakage verification.
- Decision: **STOP_AND_NOTIFY**. No GPU S0 and no S1. The only admissible next action is a reviewed CPU-only repair adding an explicit bounded field-size contract and regression test, followed by a fresh CPU DATA gate.
- Scientific interpretation: none; no direct-superfamily metric was produced, so the user-required “direct first, hierarchical second” order remains unresolved and binding.

### 3/3 tri-review synthesis

- Consensus: `run-sanity-check-first`, confidence High.
- Single pivot: after this failed-run stop is surfaced, perform one repair-only validity iteration. Priority 1 is S0's locally bounded CSV reader and real-shape regression tests; parallel B work is limited to collector semantics plus cheap RM/HiTE entry fixes.
- Earl Grey/EDTA integration and immutable Pfam/TEtrimmer must remain separate later batches to preserve attribution and avoid long known-failure allocations.
- Any repaired code must receive a fresh independent review. Only bounded CPU gates may rerun; GPU S0 still requires formal DATA PASS, and S1 requires all S0 scientific floors.

---

# Pivot Decision: S0 identity-contract human gate after Job 11524255

Date: 2026-08-11 CEST

## Inputs consumed

- Result log: `docs/06_results_log.md#result-sf-identity-provenance-audit-20260811-r1-repair-only-retry`
- Tri-review: `docs/07_tri_review.md#tri-review-s0-identityprovenance-valid-negative-job-11524255`
- Canonical audit: `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/`
- Review quorum: Claude, Codex and Antigravity, `3/3` complete.

## Sanity and comparability check

- [x] Slurm completed `0:0`; audit semantic success and valid-negative semantics are internally consistent.
- [x] Canonical manifest 7/7 and payload manifest 5/5 rehash.
- [x] Identifier/occurrence conservation delta is zero; unresolved and excluded records were not silently deleted.
- [x] 3/3 independent reviewers accept the audit result.
- [ ] Identity coverage is 100%: no, `6,447/6,727=0.9583766909` unique, with 279 missing and one ambiguous.
- [ ] Leakage-safe family/homology components exist: no.
- [ ] Direct S0 model metric exists: no; `main4_conditional_macro_f1` was not executed.
- [ ] GPU S0 or S1 is authorized: no.

## Single decision

- [ ] Continue current implementation into DATA/training
- [ ] Tune or scale
- [ ] Replace model architecture
- [x] Comparability audit first
- [ ] Return to literature
- [ ] Abandon S route

The current exact-name/accession resolver has answered its diagnostic question and is not sufficient as the production split identity contract. Stop compute and move to a human-gated contract choice.

## Human-gated options

| Option | Contract | Benefit | Main risk / required evidence |
|---|---|---|---|
| A | Curated static exact aliases for all 279 missing identifiers | Minimal semantic change; transparent and auditable | Manual curation burden; must prove one-to-one source provenance and avoid taxonomy/family leakage |
| B | Frozen sequence-homology components | Directly supports the intended homology-blocked split and can cover noncanonical names | Must freeze sequences, algorithm, thresholds, graph/component construction, ambiguous-edge policy and clade zero-overlap evaluator |

Whichever option is selected must also freeze: (1) the resolution or explicit stratum for `X13_LINE`; and (2) whether the 10 excluded identifiers remain U/ignore, become a separate audit stratum, or receive biologically justified P labels. They cannot be silently treated as negatives or removed.

## Immediate consequences

- No new S0 DATA job, GPU S0, S1, split, clustering or automatic goal revision.
- No parameter tuning is relevant because no model metric exists.
- The next artifact is a decision package, not executable scientific code.
- After human selection, any implementation requires a new config, leakage evaluator, independent code review and CPU DATA gate before GPU consideration.

## Reviewer disagreement retained

Claude recommends Option B; Antigravity recommends Option A first; Codex requires a complete full-universe contract and accepts homology only when fully frozen. The driver does not choose between these without the user.

## Durable record

- Evidence IDs: `E108` (run) and `E109` (tri-review/pivot).
- Raw reviews: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/`.

---

# Pivot Decision: accept two-cell evidence and stop B compute after Job 11524485

Date: 2026-08-12 CEST

## Inputs consumed

- Result: `docs/06_results_log.md#result-bench-hite-isolated-20260811-r1`
- Tri-review: `docs/07_tri_review.md#tri-review-isolated-hite-engineering-pass-job-11524485`
- Canonical outputs: `outputs/BENCH-HITE-ISOLATED-20260811-R1/`
- Review quorum: Claude, Codex and Antigravity, `3/3` complete.

## Sanity check

- [x] Slurm `COMPLETED 0:0`, command rc0, no timeout.
- [x] Exact HiTE 3.3.3 identity, non-empty GFF and 14,315 adapter rows.
- [x] Artifact 12/12 and canonical published payload 5/5 hashes pass.
- [x] Parent RM result and parent HiTE timeout evidence are byte-verified.
- [x] 3/3 reviewers accept semantic validity and cross-run reconciliation.
- [ ] Single successful two- or five-cell aggregate: no; parent remains `FAILED`.
- [ ] Five-cell route goal: no; the child has no `terminal_cell_count` and none may be synthesized.
- [ ] Claim eligibility: no.

## Single decision

- [x] Continue by accepting/archiving the verified component evidence
- [ ] Tune or scale
- [ ] Run another denominator job
- [ ] Replace the HiTE component
- [ ] Abandon the denominator route

Here `continue` is documentation/reconciliation only. It is not permission to compute. The denominator ledger now has two independently verified engineering cells: RM from parent Job `11523819` and HiTE from Job `11524485`.

## Retry authorization correction

Raw `reconciliation.json` reports `further_retry_allowed=true`, reflecting only that the timeout STOP rule did not trigger. The human authorization, however, allowed exactly one isolated attempt, and that attempt is consumed. The raw artifact remains immutable; `reconciliation_review.json` hash-binds it and sets `reviewed_operational_further_retry_allowed=false`. No later HiTE attempt is allowed.

## Immediate consequences

- Preserve the parent aggregate `FAILED`; never rewrite the two jobs as one successful run.
- Do not synthesize five-cell terminal metrics or run RM/HiTE again.
- Do not automatically run Earl Grey, EDTA, TEtrimmer/Pfam, a biological benchmark, GPU S0 or S1.
- Remaining denominator scope returns to a human gate. The old full five-cell main remains prohibited.

## Durable record

- Evidence IDs: `E110` (run) and `E111` (tri-review/pivot).
- Post-run audit manifest: `outputs/BENCH-HITE-ISOLATED-20260811-R1/postrun_review_manifest.json`.

---

# Pivot Decision: shard-throughput sanity preflight after Job 11525316

Date: 2026-08-12 CEST

## Inputs consumed

- Result: `docs/06_results_log.md#result-sf-dfam-p3-identity-recovery-20260812-r1`.
- Tri-review: `docs/07_tri_review.md#tri-review-partition-3-identity-recovery-resource-failed-run-job-11525316`.
- Audited outputs: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`.
- Resource profile: bounded CPU asset smoke; claim-ineligible.
- Quorum: `2/3 DEGRADED_REVIEW`; Claude and Codex succeeded, Antigravity failed all three CLI retries.

## Current evidence summary

- The exact index-independent scanner is semantically correct and passed independent code review plus 13/13 allocation-side tests.
- Job `11525316` reached 30,000/321,856 datasets in about 1,480 seconds with steady I/O and no traceback, but the exhaustive projection was about 4.41 hours under a reviewed 2-hour limit.
- The controller cancelled early. Audited status is `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`; partial zero hits are not identity evidence.
- No recovery table, full-catalog authorization, homology split, model result or claim exists.

## Sanity check

- [x] At least two independent CLI reviewers succeeded (`2/3 DEGRADED_REVIEW`).
- [x] Input/source/layout and exact identity semantics remained hash-bound.
- [x] Partial-result promotion was explicitly forbidden and did not occur.
- [x] Logs/progress/audited manifest identify the failure mode reproducibly.
- [ ] Semantic success: no; validator=`failed_run`.
- [ ] Exhaustive denominator: no; 30,000/321,856 only.
- [ ] Slurm accounting: unavailable because `slurmdbd` refused connection.

Because semantic success is false, the decision is restricted to sanity/resource repair. No tuning, scaling, scientific promotion or claim is allowed.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `continue-current-route` | deterministic 4-way scan after small throughput/topology probe | shard omissions/duplication, HDF5 I/O contention and imbalance | High |
| B · Codex | `replace-component` | new 20-minute 4-way shard-throughput preflight before formal R0 | partial promotion, nondeterministic aggregation and billing waste | High |
| C · Antigravity | failed after three attempts | none | wrapper/official CLI argument incompatibility | n/a |

Consensus: retain exact exhaustive identity semantics; replace serial traversal execution shape; preflight before formal resubmission.

Disagreement: Claude calls this route continuation while Codex calls it component replacement. Both recommend the same practical next step. Claude permits a login-node microbenchmark, but project policy requires Slurm even for the bounded preflight.

Quorum / degraded status: `2/3 DEGRADED_REVIEW`; confidence Medium.

## Reviewer-proposed directions

| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal? | Into cohort? |
|---:|---|---|---|---|---|---|
| 1 | A · Claude | deterministic 4-way exact read-only scan | runtime architecture | independent H5 handles + disjoint topology-balanced shards + strict parent union/count | primary-compatible | yes, as preflight only |
| 2 | A · Claude | 5–6h serial rerun | resource | walltime extension without code change | alternative, not orthogonal | no; fallback only after preflight disproves sharding |
| 3 | A · Claude | resumable serial scan | reliability | frozen cursor/checkpoint and exact continuation | alternative | no; too much semantic complexity for first repair |
| 4 | B · Codex | 20-minute shard throughput/correctness preflight | validity | representative 4-way scan with no recovery terminal and conservative ETA | primary | yes |
| 5 | B · Codex | formal R0 only after throughput floor | submission guard | reject formal run unless p95 projection fits with headroom | dependent | later only |
| 6 | C · Antigravity | no valid proposal | n/a | reviewer failed | n/a | no |

## Is tuning justified?

Premature and inapplicable. This is an asset scanner failed run, not a model or optimization result.

## Architecture hypothesis status

Unknown biologically; exact traversal semantics are supported, while the serial execution component is inadequate for the bounded resource contract.

## DECISION

- [x] **Sanity check first**: implement and independently review `SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1`, then run one 4 CPU/16 GiB/20 min/0 GPU Slurm preflight.

## Why this decision

A direct 5–6h serial rerun would probably complete but knowingly wastes three allocated CPUs and repeats a measured I/O bottleneck. A resumable serial design adds checkpoint identity and merge semantics before demonstrating any throughput benefit. A short, claim-ineligible, deterministic shard preflight is the smallest action that can test both correctness and whether parallel reads actually improve walltime on BeeGFS. It keeps the scientific denominator and identity rules unchanged while preventing another known-mis-sized formal submission.

## Required preflight contract

- New exp/output/log/lock namespace; never write or reuse Job `11525316` partial outputs.
- Freeze a deterministic mapping from canonical dataset paths to four disjoint shards. Synthetic/real-topology tests must prove pairwise intersection zero and union complete.
- Each worker opens its own read-only H5 handle and writes only worker-scoped staging output. The parent aggregates only after every child exits zero.
- Preflight scans representative fixed work, reports one-way/four-way throughput, shard skew and conservative p95/full-scan ETA; it never emits recovered/missing/ambiguous terminal conclusions.
- Preserve exact-case matching, source/layout pins and all old guards. Any HDF5 error, timeout, duplicate/omitted path, nonfinite metric or nondeterministic repeated assignment is semantic failure.
- Resource: `private-teodoro-gpu`, 4 CPU, 16 GiB, 20 min, 0 GPU; fresh code-review gate and smart-sbatch required.
- Stop: if conservative full-scan projection cannot fit a separately reviewed bound with at least 25% publish/cleanup headroom, do not submit formal R0. No automatic serial fallback.

## Parallel cohort

- Primary: the single shard-throughput sanity preflight above.
- Parallel directions: none. R1 full catalog and R2 homology depend causally on R0 and cannot run in parallel; GPU S0/S1 remain blocked.
- Shared-code conflict: no; use a new exp-scoped implementation and hash-pin imported semantics.

## TODO update

- [ ] Implement and test the preflight in a new exp_id.
- [ ] Run fresh `$code-review-gate`.
- [ ] If PASS, run `$smart-sbatch` for exactly one 20-minute CPU preflight.
- [ ] Close its result chain before deciding formal R0 retry.

---

# Pivot Decision: do not submit mathematically unreachable 20-minute preflight

Date: 2026-08-12 CEST

## New pre-submit evidence

- Fresh independent code review remained `BLOCKED` after 24/24 tests.
- Audited serial projection is 15,878 seconds; the contract caps explainable speedup at four workers.
- Therefore the best allowed lower bound is `15,878 / 4 = 3,969.5` seconds.
- The 20-minute allocation with 25% headroom permits only 900 seconds, so `PREFLIGHT_FEASIBLE` is unreachable without running anything.
- No Slurm job, H5 workload or throughput measurement was executed.

## DECISION

- [x] **Replace component / do not submit** `SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1`.
- [x] Preserve its preview and `PRE_SUBMIT_DECISION.json` as a code-review/resource-guard artifact, not an experiment result.
- [ ] Implement a separate resumable 4-worker formal R0 with a 3-hour CPU envelope, 35-unit atomic checkpoints and exact full-denominator terminal gates.

## Why

Submitting a job whose positive branch is mathematically impossible would spend a billed allocation without changing the decision. A 3-hour envelope leaves 8,100 seconds of work budget at 25% headroom and needs about 1.96× speedup over the audited serial projection; this is the narrowest currently defensible formal envelope. Per-unit atomic checkpoints protect against unknown BeeGFS contention without allowing partial recovery/absence claims.

## Hard boundaries

- Checkpoints are retry artifacts only; partial units never authorize catalog, homology, DATA, GPU S0 or S1.
- `RECOVERY_COMPLETE` requires all 35 units, exactly 321,856 unique canonical dataset paths, all attribute/conservation gates and a verified atomic canonical manifest.
- Any source/config/code/layout drift invalidates prior checkpoints.
- The two preflight code blockers must not be copied into the new formal implementation: nonzero must dominate timeout classification, and formal traversal must not rely on an unrepresentative sample.

---
# Pivot Decision: repair cross-node source identity guard after Job 11526687

Date: 2026-08-12 CEST

## Evidence consumed

- Job `11526687`: Slurm FAILED/1:0 in 4 seconds, before H5 dataset enumeration, workers or checkpoints.
- Immutable canonical failure state and `result_semantic_audit.json`.
- `validate_goal=failed_run` stop signal.
- `2/3 DEGRADED_REVIEW`: Claude=`replace-component`; Codex=`run-sanity-check-first`; Antigravity failed headless permission.

## DECISION

- [x] **Run sanity check first by replacing only the source-identity guard component.**
- [x] Make `st_dev` an audit-only per-node observation; bind exact registered alias, symlink target hash, inode, size, mtime, mode, HDF5 metadata/layout/rmlib, and retain pre/post/final TOCTOU checks.
- [ ] Add cross-mount pass and true drift/unknown-alias/TOCTOU fail tests; ensure canonical failure keeps specific `SOURCE_IDENTITY_*` detail.
- [ ] Fresh independent code-review gate over the narrow diff.
- [ ] If and only if the fresh gate passes, allow one repair-only retry with the unchanged 4CPU/48GiB/3h/0GPU profile. This is a new reviewed authorization, not an automatic retry.

## Why

The failed field is a mount namespace identifier, while every stable file/version observation matched. The payload never began, so this repair cannot be confused with tuning after a scientific result. Abandoning the route would discard a valid resumable scanner because of a portable-path guard bug; broadening the repair would create unnecessary comparability risk.

## Hard boundaries

- No changes to the target denominator, occurrence mass, exact matching, X13 handling, resolver, 35-unit traversal, checkpoint semantics or resource request.
- Unknown alias or any stable identity/HDF5 pin drift remains integrity failure.
- Missing 64 GB full-content SHA remains explicit.
- A repair retry terminal state does not automatically authorize full catalog, homology split, GPU S0 or S1.
- Any second pre-payload or execution failure returns to failed-run review; no third submission is implied.

---
# Pivot Decision: close partition-3 exact-name recovery and replace identity source after Job 11526905

Date: 2026-08-12 CEST

## Evidence consumed

- Job `11526905`: Slurm COMPLETED/0:0 in `01:40:52`, 35/35 units, 321,856 unique datasets/objects, exact denominator and manifest closure.
- Valid-negative result: zero exact candidates for 279 frozen targets and all 6,432,583 occurrences; no ambiguous or invalid-metadata target rows.
- `3/3` external CLI tri-review: all reviewers accept the negative; Claude abandons the partition-3 subroute, Codex and Antigravity select identity-source replacement.

## DECISION

- [x] **Replace component**: retire Dfam 3.9 partition-3 case-sensitive exact-name recovery as exhausted.
- [x] Preserve the valid-negative result and immutable artifacts; no more retry or expanded partition-3 scan.
- [ ] Human gate: decide whether to freeze another official accession-backed identity/cross-reference source or stop direct S0 at the current coverage boundary.
- [ ] If replacement is approved, implement it in a new exp_id with an unchanged 279-target denominator, source/version hashes, exact alias/accession rules, conflict accounting, leakage audit and fresh code review before CPU materialization.

## Why

The exhaustive scan answered its registered question. Repeating it cannot change the result. Dropping 279 identifiers would remove 6.43 million annotations and materially alter the task; guessing aliases or deriving identities from held-out genome copies would weaken provenance or introduce circularity. A new official source is a different component and therefore requires a visible contract revision, not a silent fallback.

## Hard boundaries

- Direct RepeatMasker SF labels remain prediction truth; identity/homology never majority-relabels them.
- Ten label-contract exclusions remain U/ignore; `X13_LINE` remains audit-only.
- Homology components are split-only and must be frozen before data materialization; labels may not enter edge construction.
- No full catalog, homology split, DATA retry, GPU S0, S1 or claim is authorized by this pivot.
- The current outdated ACTIVE_GOAL must not drive automatic continuation; any new milestone goal requires an explicit human-gated revision.

---
# Pivot Decision: replace curated-only identity source with one bounded all-family support audit

Date: 2026-08-12 CEST.

- Input: Job `11527999`, terminal `IDENTITY_SOURCE_TYPED_BLOCK`, independently verified 50 unique / 2 ambiguous / 227 missing over 279 identifiers and 6,432,583 occurrences.
- Tri-review quorum: 3/3 accept the result as a scoped valid-negative; judgments were `comparability-blocker`, `PASS_VALID_NEGATIVE`, and `replace-component`.
- Decision: `replace-component` at the evidence-source layer. Close and do not rerun the curated crosswalk route. Run exactly one independent, target-only Dfam 3.9 all-family CPU audit using the frozen official full EMBL.
- Scientific boundary: raw DR is support-only and cannot overwrite curated DF, rewrite direct labels, resolve curated ambiguity by preference, construct homology components or authorize DATA/GPU/S1.
- Stop rule: after a semantically valid all-family audit, any remaining missing/ambiguous/invalid/conflict stops the current direct-S0 data route until a new official explicit cross-reference source is frozen. No copy-derived or heuristic fallback.
# Pivot Decision: grammar sanity repair before closing the all-family source route

Date: 2026-08-12 CEST.

- Input: Job `11528157` source-complete output and post-result 3-way review.
- Decision: `run-sanity-check-first`. Do not accept zero raw support as exhaustive until official PI semicolon-list and DR semicolon-terminator grammar are implemented and audited.
- Authorization: one same-source CPU-only repair attempt after fresh code review; all homology/DATA/GPU/S1 gates remain false.
- Stop boundary: the curated 50/2/227 result already blocks the current data route. The repair only closes publication-grade evidence about raw support; it cannot weaken the blocker or authorize training.
# Pivot Decision: stop Dfam 3.9 exact relation route; propose data-contract replacement

Date: 2026-08-12 CEST.

- Input: final grammar-repair Job `11528267` and 3/3 post-result review.
- Decision: `replace-component`, with a hard stop on partition-3 exact-name, curated EMBL, all-family EMBL and grammar-repair cousins.
- Evidence: 4,121,397 complete records, 4,095,118 raw DR, grammar-complete relation telemetry, zero raw target support, final 50 unique / 2 ambiguous / 227 missing over 6,432,583 occurrences.
- Current route: stop. No more source guessing, parser tuning, resource scaling, denominator shrinkage, copy-derived consensus or GPU work.
- Proposed new route, human-gated: build a new annotation-time accession-preserving benchmark version using a frozen official Dfam library. Direct labels remain RepeatMasker raw classes; versioned accession and official consensus hash are retained at annotation time only to build label-blind homology split components.
- Re-entry: explicit user approval of the new benchmark/data contract, then independent design review and a bounded CPU concordance/accession-retention preflight. GPU S0 remains prohibited until identity coverage, concordance, homology leakage and DATA gates pass; S1 remains after direct-S0 numeric acceptance.
# Pivot Decision: repair scheduler authority before one accession-roundtrip retry

Date: 2026-08-12 CEST.

## Inputs consumed

- Result: `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1`, Job `11528744`.
- Tri-review: `2/3 DEGRADED_REVIEW`; Claude and Codex valid, Antigravity unavailable.
- Profile: CPU-only smoke, claim-ineligible.

## Sanity check

- Run/semantic success: fail before scientific payload.
- Artifact integrity: pass for attempt-local failure; canonical pointer unchanged.
- Leakage/comparability: no result exists; reviewed design remains controlled.
- Tuning: not applicable and forbidden.

## Reviewer-proposed directions

| # | Reviewer | Direction | Major axis | Mechanism delta | Into cohort? |
|---:|---|---|---|---|---|
| 1 | A · Claude | allocation-side scheduler reconciliation | runtime contract | replace optional `SLURM_TIMELIMIT` string with strict `scontrol` facts and pre-pointer revalidation | primary |
| 2 | B · Codex | normalized fail-closed scheduler authority | runtime contract | normalize time/TRES/command facts; cover anomalous/override/zero-payload cases | merged into primary |
| 3 | C · Antigravity | no valid proposal | N/A | reviewer unavailable | no |

## Decision

**Single decision: `sanity check first`.** Replace only the resource-authority guard, add behavioral tests, and require a fresh independent code-review gate. If and only if it passes, allow at most one unchanged 1CPU/4GiB/20m/0GPU retry.

This is not parameter tuning or scientific component replacement: no six-family inputs, headers, labels, geometry evaluator or authorization flags may change. Original retry, representative/full DATA, homology, GPU S0, S1 and claim remain forbidden. A second pre-payload resource failure is a stop condition requiring another result chain rather than automatic repair.

Parallel cohort: F capability code repair may continue independently in its own exp_id, but it remains BLOCKED and cannot submit until fresh review passes.
# Pivot Decision: replace the FamDB aggregation/export component after Job 11528885

## Inputs consumed

- Result: `docs/06_results_log.md`, Job `11528885` entry.
- Validate: `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/validate_goal.11528885.json` = `failed_run`.
- Tri-review: `docs/07_tri_review.md`, `2/3 DEGRADED_REVIEW`.
- Profile: CPU-only smoke, claim-ineligible.

## Sanity check

- Two independent reviewers succeeded: yes.
- Scientific metric/comparability: not evaluable; RepeatMasker did not start.
- Reproducibility: failure artifacts and canonical state are hash-closed.
- Stop rule: binding; the sole repair retry is consumed.
- Tuning: prohibited and irrelevant.

## Tri-review summary

| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | replace-component | Read-only installed-API probe, then leaf adapter or direct HDF5 | `FamDBLeaf.added` aggregation mismatch | High |
| B · Codex | replace-component | New exp-scoped leaf-level exact-access probe, no RM | No third retry; exact-once/schema drift | Medium |
| C · Antigravity | failed | none | Permission-denied, no structured review | n/a |

## Reviewer-proposed directions

| # | Reviewer | Direction | Major axis | Mechanism delta | Into cohort? |
|---:|---|---|---|---|---|
| 1 | A | Installed FamDB API surface probe | data export component | Inspect exact leaf fields for six pinned accessions | yes, primary shape |
| 2 | A | Direct HDF5 fallback | data export component | Bypass unstable high-level API | no, conditional fallback |
| 3 | A | Match official FamDB implementation/version | runtime component | Freeze code+data version pair | no, only if leaf probe fails |
| 4 | A | Official CLI export | data export component | Replace Python API with exact CLI | no, lower priority |
| 5 | B | Leaf-level exact-access adapter | data export component | Exact-once accession/partition/consensus verification | yes, after probe only |
| 6 | B | Stop export route if exact access fails | route stop | No fallback to names/prefix/copies | conditional stop |

## DECISION

**Replace component: current FamDB aggregation/export layer → separately scoped leaf-level exact-access contract probe.**

Why: the scheduler repair worked, but scientific execution still did not begin. The annotation-time accession-preserving hypothesis remains unknown, while the existing aggregation component is now directly falsified against the installed API. Continuing the same exp or changing a line and resubmitting would violate the explicit retry stop rule. This is not grounds to abandon direct-superfamily-first as a scientific route, and it is not a tuning problem.

## Re-entry contract

- New exp_id/output/lock only; do not mutate or resubmit `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1`.
- Probe only the six pinned accessions; no RepeatMasker, no library export used as benchmark, no genome scan, no GPU.
- Exact-once match across partitions; freeze partition path, accession.version, name, raw class, length and consensus SHA. No name/prefix/case/alias/copy fallback.
- Resource ceiling: 1 CPU, 4 GiB, 10 minutes, 0 GPU; fresh implementation and independent code-review gate before Slurm.
- Probe PASS only permits proposing a new leaf-adapter roundtrip preflight. Any exact-access failure closes this export route and returns to data-contract replacement/literature.

Parallel cohort: F Rice T1 information-sufficiency audit is orthogonal and may proceed under its own gate. No S GPU/S1 direction is included.

# Pivot Decision: FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1 — repair reviewed-runtime closure before one sanity retry

## Inputs consumed

- Result: Job `11529694`, `FAILED_RUN_REVIEWED_RUNTIME_CLOSURE`.
- Validate: `failed_run`, no primary metric.
- Tri-review: `2/3 DEGRADED_REVIEW`, both valid reviewers=`run-sanity-check-first`.

## Reviewer record

| Reviewer | Judgment | Proposed direction | Concern | Confidence |
|---|---|---|---|---|
| A · Claude | run-sanity-check-first | Add shared gate hash, delta review, one same-exp retry | Pure gate-installation closure | High |
| B · Codex | run-sanity-check-first | Same repair; no code/config/data change | Runtime set equality and artifact isolation | High |
| C · Antigravity | invalid | none | Non-responsive output | n/a |

## DECISION

**Sanity check first: repair only the machine reviewed-file closure, then permit one same-exp exact-resource retry after fresh independent delta review.**

Why: no scientific input was read and no method code ran. Changing the method, abandoning the new global-evidence hypothesis or returning to an old cousin would be unsupported. Conversely, simply resubmitting the same gate would repeat a deterministic failed run.

Binding repair:

- Add `scripts/pre_submit_gate.py` SHA `4996364f...` to machine `reviewed_files`.
- Re-hash the current experiment doc containing the immutable Job `11529694` result note; no scientific code/config/data/evaluator changes.
- Fresh independent delta review must prove `runtime_code_files ∪ {config} ⊆ reviewed_files` and login/allocation gate compatibility.
- Then one and only one same-exp submission with exact 8CPU/32GiB/2h/0GPU and no CLI override. Any further pre-scientific failure returns to tri-review; no automatic retry.
- Scientific PASS/valid-negative still requires full post-run result chain; no downstream authorization is implied.

Parallel cohort: S leaf-level exact-access API probe implementation may continue in an isolated exp; no shared-code conflict.

# Pivot Decision: abandon standalone consensus-collinearity parent assembly after Job 11531090

Date: 2026-08-12 CEST.

## Inputs consumed

- Result: Job `11531090`, `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`, route-local semantic success.
- Validate: historical-goal schema mismatch gives the required automation stop; independent route-local audit remains valid-negative.
- Tri-review: `2/3 DEGRADED_REVIEW`; Claude and Codex independently choose `abandon-route`; Antigravity failed three bounded CLI retries.
- Profile: Rice T1 positive-only CPU information audit, claim-ineligible.

## Tri-review summary

| Reviewer | Judgment | Next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | abandon-route | Write DEC entry and stop exact component | Low mapping coverage plus biologically invalid standalone consensus-coordinate monotonicity | High |
| B · Codex | abandon-route | Non-compute closure with explicit re-entry | Large bootstrap-stable deficit; evidence is auxiliary, not sufficient | High |
| C · Antigravity | failed | none | Repeatedly misparsed its own CLI flag; no structured review | n/a |

## Reviewer-proposed directions preserved

| # | Reviewer | Direction | Major axis | Status |
|---:|---|---|---|---|
| 1 | A | multi-evidence partial assignment | evidence/model | parked idea only; not authorized |
| 2 | A | evolutionary-state evidence | biological evidence | parked idea only; not authorized |
| 3 | A | long-context/global interval-set prediction | architecture | parked idea only; not authorized |
| 4 | B | copy-consensus boundary voting | richer global evidence | parked idea only; not authorized |
| 5 | B | leakage-safe global CopyGraph/SSL | representation/global graph | parked idea only; must not reuse failed local-graph cousin |
| 6 | both | retain consensus mapping only as auxiliary feature | component role | allowed as a future design note, never as current promotion |

## DECISION

**Abandon route: standalone exact consensus mapping + chromosome-wide consensus-coordinate monotonic DAG/minimum path cover for parent-copy assembly.**

Why: the audit executed cleanly and demonstrated real signal above shuffle, but every practical information, safety and comparator gate failed. Exact recovery, pairwise harmonic and topology deficits are large with wholly negative paired bootstrap intervals; false fusion exceeds the registered ceiling. The result is too far from the comparator to justify tuning and is not repaired by more Rice/Fly/H0 compute.

This decision does **not** abandon the broader TE fragmentation problem or all global biological models. It closes the specific evidence/assembler family and its parameter/species/library variants. Consensus evidence may later be one auxiliary channel inside a genuinely different, independently pre-registered mechanism.

## Binding stop and re-entry boundary

- No more Job11531090 retries, seed/stride/coverage-margin/path-cover tuning, FlyBase/Rice expansion, H0 attachment or GPU work.
- No revival of DEC-001/002 threshold/gap/HMM/CRF/local-fragment-graph/lightweight-head cousins.
- Re-entry requires a new source of global copy/boundary evidence, independent development-family selection, unchanged final Rice T1 gates, immutable leaves/truth isolation, and a new independent code review/human authorization.
- Claim re-entry additionally requires complete biological truth beyond T1 positive-only and leakage-safe cross-species evaluation.

Parallel cohort: continue only the separately scoped S leaf exact-access contract after its independent review. F consumes no further compute.
# Pivot decision: SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1 replace read-mode lifecycle/publication component after Job 11533175

Date: 2026-08-12 CEST  
Decision: `replace-component`  
Review status: `2/3 DEGRADED_REVIEW`

Job `11533175` 是 failed run，不是 exact-access negative。旧实现的科学 72-call probe在内存返回，但 read-mode cleanup错误调用写 finalizer，导致结果在冻结前丢失。两位有效 reviewer 都允许最后一次 close-only repair；选择 `replace-component` 是因为变更对象严格限于 read-mode handle closure 与 result staging/publication，而不是 accession查询或身份判定。

下一轮唯一授权：建立新的 repair exp namespace（不得覆盖 Job11533175状态），保持六 accession × 十二 leaf × 一次调用矩阵、source/gate/scheduler/typed-state 合同不变；移除 read-mode `FamDB.finalize()`，显式关闭底层句柄并在 cleanup 前冻结观察；新增异常注入、exact call-count 和 no-upgrade tests；fresh independent code review 后，最多一次 exact 1CPU/4GiB/10m/0GPU sbatch。

永久 stop rule：该最终 attempt 出现任何 API、lifecycle、runtime、schema、asset、scheduler、gate、manifest 或 publication failure，或出现 missing/duplicate/frozen-drift semantic typed block，即永久关闭 FamDB access/export 路线，不再工程修补。即使 PASS，也只允许另行提议 leaf-adapter CPU preflight；RepeatMasker、representative/full DATA、homology、GPU direct S0 与 S1 仍需各自门禁，绝不自动开放。

---
