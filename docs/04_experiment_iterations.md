# Experiment Iterations

> 由 `/goal` 在每轮迭代结束时维护。每条 iteration 一段。
> Track A 是小样本并行筛架构；Track B 是从 Track A 晋升候选后的 scale-up / full validation。

---

## ITER-20260812-BENCH-HITE-ISOLATED-R1

- Experiment ID: `BENCH-HITE-ISOLATED-20260811-R1`.
- Track/profile: B denominator repair-only isolated runtime-validity smoke; CPU-only, claim-ineligible.
- Execution: Job `11524485`, `private-teodoro-gpu`, 4 CPU/48 GiB/0 GPU, `00:23:04`, Slurm `COMPLETED 0:0`.
- Hypothesis: the exact HiTE 3.3.3 demo that exceeded the parent's 600-second budget can complete within one preregistered 1800-second retry and produce a valid final GFF plus canonical adapter rows.
- Result: `ENGINEERING_PASS`; exact help identity, minimum command rc0 without timeout, 1.20 MB `HiTE.gff`, and 14,315 canonical adapter rows. Peak command RSS was 2,111,456 KiB.
- Reconciliation: byte-verified parent RM cell remains `ENGINEERING_PASS_REUSED_BY_HASH`; parent aggregate remains `FAILED`; two-cell evidence is ready, but `single_successful_run=false` and `claim_eligible=false`.
- Goal status: isolated semantic success, while the route-level five-cell validator returns `failed_run` because `terminal_cell_count` is not and must not be synthesized from this child run. Further B compute stops for tri-review/pivot.
- Tri-review/pivot: complete, 3/3. Accept and archive the isolated HiTE plus immutable parent RM as two-job/two-cell engineering evidence. Parent aggregate remains FAILED; operational retry permission is false; no additional B compute is authorized.
- Links: `outputs/BENCH-HITE-ISOLATED-20260811-R1/`; `docs/experiments/BENCH-HITE-ISOLATED-20260811-R1.md`.

---

## ITER-20260811-S0-IDENTITY-PROVENANCE-R1-RETRY

- Experiment ID: `SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1`.
- Track/profile: S0 prerequisite identity/provenance asset audit; CPU-only smoke, claim-ineligible.
- Execution: repair-only retry Job `11524255`, `private-teodoro-gpu`, 4 CPU/32 GiB/0 GPU, `00:18:32`, Slurm `COMPLETED 0:0`.
- Hypothesis: after freezing the true Dfam H5 index layout, exact name/accession resolution can be evaluated without mistaking a structurally absent partition index for corruption or deleting any P-state occurrence.
- Mechanism delta: exact 12-partition layout contract; only frozen partition 3 may skip `Lookup/ByName`, while present-but-broken objects and query failures remain hard errors.
- Result: semantic-success valid negative. Unique provenance is `6447/6727=0.9583766909`; 279 identifiers are missing and one is ambiguous. P plus explicitly excluded candidate occurrence conservation is exact, with zero silent deletion.
- Goal status: direct-superfamily model goal remains unvalidated (`main4_conditional_macro_f1` absent); no split, leakage screen, training or inference ran.
- Tri-review consensus: complete with 3/3 external CLI quorum. All reviewers accept the audit as a reproducible valid negative and agree that the current exact-name/accession contract is not split-ready. Claude favors a frozen homology supplement, Codex requires a complete contract decision pack, and Antigravity prefers exhausting static exact aliases first.
- Pivot decision: `comparability audit first`; stop at a human gate before choosing static exact aliases versus a sequence-homology supplement. The decision must also freeze `X13_LINE` and the 10 excluded identifiers. GPU S0 and S1 remain prohibited.
- Links: `docs/06_results_log.md`; `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/`; `sbatch/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1.sbatch`.

---

## ITER-20260701: PIPE-TEFM-CAP-FRAGARCH-20260701

- Date (UTC): 2026-06-30 / local 2026-07-01 CEST
- Linked request summary: `$capability-pursue` to upgrade TE fragmentation handling from post-hoc smoothing/weak decoders to a reusable interval-level annotation module.
- Experiment ID(s): `PIPE-TEFM-CAP-FRAGARCH-20260701`
- Track: capability-pursue bounded screen / publication-validation support
- Execution mode: smart-sbatch-style Slurm screen after code-review-gate
- Resource profile: screen
- Claim eligibility: cannot claim SOTA

### Hypothesis Being Tested

Direct interval architectures can convert strong bp-level GENERanno signal into complete TE intervals under strict metrics better than CE raw threshold and unchanged smoothing comparators, without deleting true TE fragments.

### Architecture Changes

- What changed: added two lightweight interval heads on frozen promoted GENERanno 4096 embeddings/logits: `boundary_proposal` with start/end boundary heads and learned interval proposal scoring, and `anchor_free_interval` with center/length interval detection.
- Why structural: the heads directly predict boundaries/proposals/objects rather than tuning thresholds, gap merge, or post-hoc HMM/CRF penalties.
- Which weakness it attacks: strict segment-F1@IoU0.8 and boundary-F1@5bp remain low despite high bp-F1; this tests whether explicit interval prediction improves annotation completeness.

### Sbatch / Run Status

- Job id(s): first report job `9864888`, corrected reference rerun `9865070`.
- Final accepted job: `9865070`, `COMPLETED`, `00:03:01`, `shared-gpu`, RTX 3090.
- Output dir(s): `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/`.
- Log path(s): `logs/PIPE-TEFM-CAP-FRAGARCH-20260701/TEFM_FRAGARCH_9865070.*`.
- Code review: PASS_WITH_WARNINGS; see `outputs/PIPE-TEFM-CAP-FRAGARCH-20260701/code_review_gate.json`.

### Result Summary

- Semantic success: pass.
- Gate status: fail; `gate_pass_panels=[]`.
- Human test: `anchor_free_interval` improves over CE raw segment-F1 (`0.3581` vs `0.1542`) and boundary-F1 (`0.1878` vs `0.0763`), but does not beat CRF-style smoothing (`0.4126`/`0.2087`) and has high deleted true-backed fraction (`0.7419`).
- Mouse quick: neither new architecture beats CRF-style smoothing; `anchor_free_interval` collapses bp-F1 and missed_true_rate.
- Conclusion: first capability round is an engineering success but method failure; do not scale these exact heads.

### Tri-review Consensus

Completed with `3/3` quorum. Reviewers agree the run is semantically valid, current `boundary_proposal` and `anchor_free_interval` components should not be scaled or tuned, and high `deleted_true_backed_fraction` prevents interpreting smoothing/head improvements as solved fragmentation. Claude and Antigravity recommend abandoning the frozen-lightweight head route; Codex recommends replacing the component rather than abandoning interval-aware architecture broadly.

### Pivot Decision

Completed: `replace-component`. The tested frozen-lightweight interval heads are stopped. A second bounded capability round is allowed only if it introduces a genuinely different mechanism such as fragment graph linking or boundary-conditioned span refinement; no threshold/gap/HMM tuning.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-cap-fragarch-20260701`
- metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_metrics.tsv`
- report: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/INTERVAL_ARCHITECTURE_REPORT.md`

---

## ITER-20260701-R2: PIPE-TEFM-CAP-FRAGGRAPH-20260701

- Date (UTC): 2026-06-30 / local 2026-07-01 CEST
- Linked request summary: `$capability-pursue /goal` continuation for TEFM-CAP-FRAGARCH Round 2 using the pivot-selected fragment graph linker.
- Experiment ID(s): `PIPE-TEFM-CAP-FRAGGRAPH-20260701`
- Track: capability-pursue bounded screen / publication-validation support
- Execution mode: Slurm screen after code-review-gate
- Resource profile: screen
- Claim eligibility: cannot claim SOTA

### Hypothesis Being Tested

CE raw fragments contain many true-backed pieces; a learned fragment graph linker can preserve these pieces while filling learned links between adjacent fragments that belong to the same TE interval.

### Architecture Changes

- What changed: raw CE fragments are converted into graph nodes; node/edge features include frozen GENERanno embeddings, CE probabilities, fragment length/position, gap probability, span probability, and embedding similarity. A learned edge classifier predicts adjacent fragment links.
- Why structural: this predicts fragment adjacency/instance structure rather than tuning threshold, gap merge, HMM/CRF penalty, or survival-retention losses.
- Which weakness it attacks: Round 1 heads and smoothing deleted too many true-backed fragments; the primary `fragment_graph_keepall` decode preserves all CE raw fragments and only learns fills.

### Sbatch / Run Status

- Job id: `9866570`, `COMPLETED`, `00:03:48`, `shared-gpu`, RTX 3090.
- Output dir: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/`.
- Log path: `logs/PIPE-TEFM-CAP-FRAGGRAPH-20260701/TEFM_FRAGGRAPH_9866570.*`.
- Code review: PASS_WITH_WARNINGS; see `outputs/PIPE-TEFM-CAP-FRAGGRAPH-20260701/code_review_gate.json`.

### Result Summary

- Semantic success: pass.
- Gate status: fail; `gate_pass_panels=[]`.
- `fragment_graph_keepall`: deletion guardrail preserved (`deleted_true_backed_fraction=0`), but output is identical to CE raw on human and mouse, so the learned links did not improve interval metrics.
- `fragment_graph_keepdrop`: human segment-F1/boundary-F1 improves to `0.4964`/`0.2458`, above CRF-style smoothing, but deleted_true_backed_fraction is `0.8632`; mouse remains below CRF-style smoothing.
- Conclusion: graph-linker Round 2 is an engineering success but method failure.

### Tri-review Consensus

Completed with `3/3` quorum. All reviewers agree the run is semantically valid but method-failed. The preservation-first graph decoder preserves true-backed fragments but does not improve CE raw; the learned keep/drop diagnostic improves human intervals by deleting true-backed fragments and does not transfer cleanly to mouse. All three reviewers recommend stopping the current capability-pursue branch rather than launching a final boundary-conditioned span-refiner.

### Pivot Decision

Completed: `abandon-route` for the current capability branch. `PIPE-TEFM-CAP-FRAGARCH` is closed as future work / negative capability evidence; no further frozen/post-hoc interval reconstruction round should be run under this sprint.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-cap-fraggraph-20260701`
- tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fraggraph-20260701`
- pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-cap-fraggraph-20260701`
- decisions-log: `docs/09_decisions_log.md#dec-002-frozenpost-hoc-interval-reconstruction-modules-for-te-fragmentation`
- metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_metrics.tsv`
- report: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/FRAGMENT_GRAPH_LINKER_REPORT.md`

---

## ITER-20260619: PIPE-TEFM-REPAIR-20260618

- Date (UTC): 2026-06-19
- Linked `/goal` command summary: Confirm and repair surprising low mixed-animal and embedding results using GENERanno 4096 bp, seed 42, with archive-parity, mouse-core, and invertebrate-boost branches.
- Experiment ID(s): `PIPE-TEFM-REPAIR-20260618`
- Track: Track A screen / bounded discovery inside Publication-Validation
- Execution mode: submit-and-handoff, then result processing after jobs completed
- Resource profile: screen
- Claim eligibility: cannot claim SOTA

### Hypothesis being tested

The low A2 mixed-animal score and weak embedding clustering may be caused by protocol mismatch, too-small training scale, held-out sparse-label invertebrates, or metric mismatch rather than a global failure of GENERanno 4096.

### Architecture changes

- What changed: enlarged GENERanno 4096 mixed-animal training branches; added archive-parity/human-dominant branch, mouse-core branch, and invertebrate-boost branch; added pairwise/linear-probe embedding diagnostics; reran segment threshold/postprocess and large 4096 superfamily head.
- Why structural: changes data mixture, evaluation decomposition, and representation metric family rather than tuning a single hyperparameter.
- Which weakness it attacks: resolves whether the previous “mixed animal fails” and “embedding clustering fails” conclusions were real model limitations or evaluation/protocol artifacts.

### Sbatch / run status

- Job id(s): 9107748, 9107749, 9107750, 9107751, 9107761, 9107762, 9107763, 9107764
- Output dir(s): `software_outputs/tefm_repair/PIPE-TEFM-REPAIR-20260618`; `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618`
- Log path(s): `logs/tefm_repair/PIPE-TEFM-REPAIR-20260618`
- Status: completed; all Slurm jobs exit `0:0`

### Result summary

- Primary screen metric: best no-human animal B-panel mean TE-F1 = 0.9351 (`invert_boost_animal_4096`).
- Stress-panel metric: A2 all-species mean TE-F1 remains about 0.57 because honeybee/beetle and distant stress species are weak.
- Segment metric: best segment-F1@IoU0.5 = 0.7339 at threshold 0.35 + `hmm_penalty2`.
- Superfamily metric: main4 macro-F1 = 0.8927; all-6 macro-F1 = 0.7519.
- Embedding metric: C1 length 512 holdout macro-F1 = 0.8784; A1 length 512 = 0.8495; B1 length 512 = 0.5561.
- Semantic success: pass.

### Tri-review consensus

Completed as `SINGLE_REVIEW_CONTINUATION`: quorum 1/3, confidence Low. Codex reviewer recommends scaling to Track B only as a non-claim comparability-lock validation run: freeze data/split/Label-A/inference protocol, promote `invert_boost_animal_4096`, and treat beetle/honeybee as diagnostic appendix rather than part of the main mean claim. Claude produced advisory text but failed structural validation; Antigravity failed due missing OAuth login.

### Pivot decision

Completed: `Comparability audit first`. The model route is supported, but reviewer quorum was only 1/3 and ACTIVE_GOAL/docs19/docs20 are not claim-ready. Next work is to freeze or repair the comparability contract before launching the recommended non-claim Track B validation.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-repair-20260618`
- outputs: `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/`

---

## ITER-LOCK-20260619: primary/stress panel and open-set validation

- Date (UTC): 2026-06-19
- Linked `/goal` command summary: `$reframe $council $master-plan /goal` follow-up to explain distant stress failures, compare embedding/superfamily objectives, improve fragmentation, and evaluate main4+Unknown.
- Experiment ID(s): `PIPE-TEFM-LOCK-20260619`
- Track: Track A screen / non-claim validation
- Execution mode: run-and-evaluate
- Resource profile: screen
- Claim eligibility: cannot claim

### Result summary

- Semantic success: completed.
- Slurm status: prep/train/eval/segment/embedding/summary jobs exited `0:0`.
- Summary status: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/current_status.json`
- Main result: species-specific recovery restores lizard, X. laevis, and honeybee stress performance, but not red flour beetle; base-pretrained SF5 handles Unknown better than binary-H0; HMM smoothing improves multi-species interval metrics but fragmentation/boundary remain open.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-lock-20260619`
- outputs: `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/`

---

## ITER-20260621: PIPE-TEFM-EXTEND-20260620

- Date (UTC): 2026-06-21
- Linked `/goal` command summary: `$reframe $council $master-plan /goal` supplemental screen for embedding strictness, base-pretrained SF5, animal-to-plant transfer, plant/cross PU, stress anchors, PU smoothing, and decay formula extension.
- Experiment ID(s): `PIPE-TEFM-EXTEND-20260620`
- Track: Track A screen / bounded discovery inside Publication-Validation
- Execution mode: submit-and-handoff, then result processing after jobs completed
- Resource profile: screen
- Claim eligibility: cannot claim SOTA

### Hypothesis being tested

The remaining surprising or weak branches can be explained by protocol and label-source structure: family-level embeddings may be easier for kmer than model embeddings; base-pretrained SF5 should preserve Unknown/reject behavior; animal `invert_boost` may transfer to plants better than PU trained without reliable negatives; stress failures may need label/source diagnostics or species-specific recovery rather than broad anchor substitution; and generalization decay needs label-concordance variables.

### Architecture changes

- What changed: added family-level dynamic internal/boundary embedding extraction; added base-pretrained SF5; evaluated animal `invert_boost` on plant and cross panels; trained plant/cross positive-only and PU variants with TV regularization; evaluated PU segment smoothing; trained vertebrate/insect stress anchors; fit decay formulas with label variables.
- Why structural: changes objective, label source, decoder/postprocess, transfer domain, and explanatory formula variables rather than optimizer-only tuning.
- Which weakness it attacks: closes user-requested evidence gaps around embedding rigor, Unknown/reject classification, plant/cross transfer, PU overcalling, stress anchors, and generalization formula.

### Data readiness

- Dataset(s) used: ready-by-design B_animal, C_plantTE, D_cross_kingdom_animal_plant, and stress/eval species from current RepeatMasker/Dfam/UCSC-derived annotations.
- Downloaded this iteration? no.
- Path / version / split source: `software_outputs/repeatmasker_dfam/02_ready_by_design/**`; model outputs under `software_outputs/tefm_extend/PIPE-TEFM-EXTEND-20260620`.

### Sbatch / run status

- Job id(s): `9181624`, `9183885`, `9183892`, `9181897`, `9211006`, `9211007`, `9211008`, `9211010`.
- Output dir(s): `software_outputs/tefm_extend/PIPE-TEFM-EXTEND-20260620`; `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620`.
- Status: completed.

### Result summary

- Primary screen metric: best broad cross-eval mean TE-F1 = 0.5914 for `invert_boost_animal_4096`; plant eval-only mean TE-F1 = 0.7269 for `invert_boost`; SF5 TE-detect F1 = 0.8982; SF5 main4 conditional macro-F1 = 0.8547; Unknown recall = 0.3957; best decay-formula R2 = 0.5249.
- Gates: primary screen complete; SOTA claim fail by design; review decision triggered.
- Semantic success: completed.

### Tri-review consensus

Completed as degraded host self-review / no external quorum. Confidence Low for workflow purposes; cannot support claim, goal revision, or benchmark revision. Directional conclusion: keep GENERanno 4096 + `invert_boost`; keep base-pretrained SF5; keep C1/A1 embedding baselines; treat PU as negative ablation/gated repair; require Dfam consensus FASTA before consensus-vs-genomic claims.

### Pivot decision

Decision: continue the robust annotation route but do not promote this screen to a claim. Plant/cross PU branches are not primary routes; next claim-facing work should lock evaluator/comparability contracts and primary/stress panels.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-extend-20260620`
- tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-extend-20260620`
- pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-extend-20260620`
- outputs: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/FINAL_REPORT.md`

---

## ITER-20260621-CALIB: PIPE-TEFM-CALIB-20260621

- Date (UTC): 2026-06-21
- Linked `/goal` command summary: `$reframe $council $master-plan /goal` continuation after user review; replace PU comparison with standard supervised plant/cross calibration, complete Dfam consensus embedding, test honeybee/beetle/insect anchors, and extend decay formula.
- Experiment ID(s): `PIPE-TEFM-CALIB-20260621`
- Track: Track A screen / bounded discovery inside Publication-Validation
- Execution mode: submit-and-handoff, monitored to completion, then result processing
- Resource profile: screen
- Claim eligibility: cannot claim SOTA

### Hypothesis being tested

The weak plant/cross and insect stress conclusions from previous screens are protocol- and label-source-dependent: normal supervised calibration with reliable negatives should be evaluated separately from PU, Dfam consensus family-level embeddings should be a stricter representation test, and insect anchors may separate recoverable honeybee from beetle source/domain failure.

### Architecture changes

- What changed: trained standard supervised `plant_supervised_4096` and `cross_supervised_4096`; trained direct honeybee/beetle and insect-no-beetle anchors; executed Dfam consensus family-level embedding clustering; fit an extended source-aware decay formula.
- Why structural: changes data mixture, source family, calibration target, and explanatory covariates rather than optimizer-only tuning.
- Which weakness it attacks: closes missing standard supervised plant/cross validation, missing Dfam consensus source, unresolved honeybee/beetle anchor question, and weak distance-only decay formula.

### Sbatch / run status

- Job id(s): `9245610`, `9245611`, `9245618`, `9245619`, `9245620`, `9245621`, `9245622`.
- Output dir(s): `software_outputs/tefm_calib/PIPE-TEFM-CALIB-20260621`; `reports/tefm_calib/PIPE-TEFM-CALIB-20260621`.
- Log path(s): `logs/tefm_calib/PIPE-TEFM-CALIB-20260621`.
- Status: completed; all Slurm jobs exit `0:0`.
- Runtime note: eval array throttle was increased from `%4` to `%8` and then `%12` after checking idle shared-gpu capacity.

### Result summary

- Semantic success: completed.
- Summary status: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/current_status.json`
- Primary screen metrics: `cross_supervised_4096` broad mean TE-F1 0.5786; `animal_invert_boost` broad mean TE-F1 0.5413; `cross_supervised_to_plant_fine` mean TE-F1 0.8568; Dfam consensus A1 ARI 0.2242 vs C1 ARI 0.7083; full decay formula R2 0.7407.
- Main result: standard supervised plant/cross is validated; PU remains abandoned as primary; insect-no-beetle rescues honeybee but not beetle; Dfam consensus embedding keeps C1 as the dominant baseline; decay formula needs label/source variables.

### Tri-review consensus

Completed as degraded host/council synthesis, confidence Low. This review cannot support claim, abandon-route, ACTIVE_GOAL revision, or benchmark revision. Directional conclusion: carry forward panel-specific robust branches and lock evaluator/comparability contracts before claim-grade Track B.

### Pivot decision

Decision: continue robust GENERanno 4096 route with panel-specific reporting. Carry forward `cross_supervised_4096` for plant/cross calibration evidence and `invert_boost_animal_4096` for broad animal/vertebrate transfer; keep insect-no-beetle as honeybee diagnostic; keep PU abandoned as primary.

### Links

- result-log: `docs/06_results_log.md#result-pipe-tefm-calib-20260621`
- tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-calib-20260621`
- pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-calib-20260621`
- outputs: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`

---

## ITER-20260621-ANCHOR: anchor selector, Unknown relabel evidence, insect primary panel

- Date (UTC): 2026-06-21
- Linked `/goal` command summary: single-seed parallel follow-up for kingdom/panel anchor recommendation, Unknown/high-score unannotated sequence interpretation, background-inclusive embedding audit, insect primary panel, and deployable generalization-decay formula.
- Experiment ID(s): `PIPE-TEFM-ANCHOR-20260621`
- Path tested: publication-validation evidence extension
- Milestone: stress/generalization evidence
- Track: screen / diagnostic generalization
- Execution mode: submit-and-handoff
- Resource profile: screen
- Claim eligibility: screen only; cannot claim selector stability until Track B validation

### Hypothesis being tested

Panel/kingdom-specific GENERanno anchors should be recommended through a deployable selector rather than a single universal model. Unknown and high-confidence unannotated segments may contain TE-like sequences that can be reassigned or triaged by SF5 posterior plus embedding evidence, but this must be separated from closed-set accuracy claims.

### Data readiness

- Dataset(s) used: UCSC/RepeatMasker-derived fine_tune/eval_only panels already materialized under `software_outputs/repeatmasker_dfam/02_ready_by_design`, previous TEFM model outputs, and newly generated insect-primary split.
- Downloaded this iteration? no
- Path / version / hash / split source: `configs/pipelines/PIPE-TEFM-ANCHOR-20260621.yaml`

### Sbatch / run status

- Job id(s): `9288894` prep; `9288895` insect train; `9288896` diagnostic extraction; `9288897` eval; `9288900` embedding cluster; `9288901` SF5 initial failed and superseded; `9298759` SF5 CPU retry; `9288902` anchor formula; `9300179` summary; `9316968` public eval race partially completed then cancelled after main eval finished.
- Output dir(s): `software_outputs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621`; `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621`
- Log path(s): `logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621`
- Status: completed / semantic success
- Resume instruction if submit-and-stop: no pending run action. Use `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/FINAL_REPORT.md` and `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summaries/current_status.json` for downstream Track B planning.

### Result summary

- Primary metric: stress-panel mean TE-F1 for `insect_primary_4096` is 0.5197, compared with 0.4520 for `insect_no_beetle_4096`, 0.4248 for `invert_boost_animal_4096`, and 0.4134 for `cross_supervised_4096`.
- Key species result: honeybee is rescued by `insect_primary_4096` to TE-F1 0.9465, but red flour beetle remains near-zero across all anchors.
- Embedding result: C1 basic sequence features + contrastive remains stronger than GENERanno embedding + contrastive even with background included.
- Unknown result: Unknown annotations show main4-like SF5 signal, but high-score strict-background candidates are mostly BG.
- Semantic success: yes.

### Current review note

Council consensus requires four separations in interpretation: primary vs stress species, deployable-only vs annotation-aware anchor formula, Unknown relabel candidates vs validated corrected labels, and insect primary panel vs beetle-style annotation/library failure cases.

### Links

- config: `configs/pipelines/PIPE-TEFM-ANCHOR-20260621.yaml`
- status/report: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621`
- evidence register: `docs/15_evidence_register.md#e052`
- result-log: `docs/06_results_log.md#result-pipe-tefm-anchor-20260621`
- tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-anchor-20260621`
- pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-anchor-20260621`

---

## ITER-20260630-GENOMEDECAY-FRAGMENT: genome-derived selector and fragmentation council

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: enrich the deployable generalization-decay / anchor selector with genome-derived variables and convene tri-review/council on strict segment fragmentation, decoder replacement, and double-strand prediction.
- Experiment ID(s): `PIPE-TEFM-FINAL-GENOMEDECAY-20260630`, `PIPE-TEFM-FINAL-FRAGSANITY-20260630`
- Track: publication-validation support screen / pipeline design.
- Execution mode: run-and-evaluate plus external council.
- Resource profile: local CPU screen; no GPU training.
- Claim eligibility: cannot claim; bounded k-mer sampling is screen-grade and Mash/sourmash were unavailable.

### Hypothesis being tested

Genome-derived variables that can be computed before TE annotation, especially k-mer shift to candidate anchors, may improve the deployable anchor selector beyond the current distance/GC/group proxy model. For fragmentation, the next useful improvement may require interval-aware or boundary-aware components rather than more threshold/gap/HMM/CRF tuning.

### Result summary

- Added `genome_decay_selector.py` and generated 22 species-level genome feature rows plus 156 anchor-pair rows.
- Baseline deployable selector leave-species-out RMSE reproduced at `0.3042`.
- Adding assembly stats alone worsened leave-species-out RMSE to `0.3441`.
- Adding bounded sampled k-mer shift improved leave-species-out RMSE to `0.2666`.
- Adding assembly plus k-mer worsened to `0.3493`, consistent with overfitting or noisy assembly features in this small panel.
- `mash` and `sourmash` were not installed, so no MinHash distances were used.
- Fragment council reached 3/3 agreement that double-strand prediction is a cheap sanity check, not the main fix; priority is frozen interval refiner, then boundary-aware head.
- Added and ran bounded mouse chr1 fragment sanity on `ntv2_250m@4096` for forward/RC/mean/max/consensus merges plus oracle same-true interval repairs.
- Forward raw segment-F1@IoU0.8/boundary5 was `0.3062`; forward CRF was `0.3569`; best non-oracle was `consensus_min + crf_style_penalty4` with segment-F1 `0.4149`, boundary-F1 `0.1267`, and missed true rate `0.0929`.
- Truth-aware oracle fill of supported true intervals reached segment-F1/boundary-F1 `0.9711`, showing the bp model often touches true TE intervals and a learned interval refiner has high potential.
- A full 1200-window mouse chr1 job (`9856510`) was cancelled after completing inference but stalling in the Python full-length metric loop; bounded 120-window job `9856508` is the valid screen result.

### Links

- report: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/GENOME_DECAY_REPORT.md`
- selector JSON: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/selector_genome_feature_results.json`
- feature table: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/genome_feature_table.tsv`
- council report: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/FRAGMENT_COUNCIL_REPORT.md`
- fragment sanity report: `reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/FRAGMENT_SANITY_REPORT.md`

---

## ITER-20260629-FINAL-NTV3: NTv3 recovery and final model-size matrix closure

- Date (UTC): 2026-06-29
- Linked `/goal` command summary: final pipeline supplementation; complete NTv2/NTv3 model-size x window matrix, then prepare error-bar/multi-anchor/decay follow-ups.
- Experiment ID(s): `PIPE-TEFM-FINAL-20260623`, NTv3 train jobs `9839610`/`9839611`, eval retry jobs `9845158`/`9845159`.
- Track: Publication-validation screen / model-size matrix.
- Execution mode: run-and-evaluate.
- Resource profile: screen.
- Claim eligibility: cannot claim; single seed and one chromosome per eval species.

### Hypothesis being tested

Additional NTv2/NTv3 model sizes and NTv3 8kb/non-8kb checkpoints may improve human H0 TE detection and cross-species generalization relative to the existing NTv2/GENERanno/GFMs, and model parameter size may correlate with TE annotation performance.

### Architecture changes

- Added/recovered NTv3 8M/100M/650M pre and pre_8kb checkpoints under the same human H0 single-seed protocol.
- Fixed NTv3 single-base token/label alignment with `token_label_mode=ntv3_single`.
- Fixed NTv3 checkpoint reload by filtering regenerated rotary embedding cache buffers before strict state-dict loading.

### Data readiness

- Human H0 train/val/test windows: existing UCSC strict-TE 512/1024/2048/4096/8192 prepared data.
- Generalization panels: `animal_fine` 6 species and `plant_fine` 5 species, one chromosome/species/window.
- Split and labels: inherited from `PIPE-TEFM-FINAL-20260623`; U/unknown labels remain ignored, not negative.

### Sbatch / run status

- Download/smoke: `9838465`, `9838992`, completed.
- Corrected train: `9839610`, `9839611`, completed 30/30 rows.
- First eval: `9844255`, `9844256`, failed before metrics from rotary cache state-dict mismatch; superseded.
- Corrected eval retry: `9845158`, `9845159`, completed 330/330 NTv3 matrix JSONs.
- Summary: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`, 495 total matrix rows.

### Result summary

- Human H0 best overall: `ntv2_250m_H0_w4096_seed42`, TE-F1 `0.93494`.
- Human H0 best NTv3: `ntv3_650m_pre_H0_w4096_seed42`, TE-F1 `0.91962`.
- Best animal_fine mean: `ntv2_250m@4096`, mean TE-F1 `0.64823`.
- Best plant_fine mean: `ntv3_100m_pre@2048`, mean TE-F1 `0.39802`.
- Semantic success: pass after repair; initial failed eval jobs are non-evidence runtime failures.

### Tri-review consensus

Pending. This matrix should be reviewed before promoting any backbone/window to error-bar repeats or multi-anchor construction.

### Pivot decision

Pending. Provisional interpretation is panel-specific: `ntv2_250m@4096` is the animal/generalization screen leader; `ntv3_100m_pre@2048` is a plant/combined challenger.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-final-20260623-ntv3-recovery-and-model-size-matrix-closure
- code review/runtime: docs/21_code_review_log.md
- matrix summary: reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv

---

## ITER-FINAL-TRACKB-SUPPORT-20260629: chromosome-repeat error bars, plant QC, strict segment

- Date (UTC): 2026-06-30
- Experiment ID(s): `PIPE-TEFM-FINAL-EBAR-20260629`, `PIPE-TEFM-FINAL-PLANTQC-20260629`, `PIPE-TEFM-FINAL-STRICTSEG-20260629`
- Track: Publication-validation support screen.
- Execution mode: run-and-evaluate.
- Resource profile: screen.
- Claim eligibility: cannot claim; chromosome-repeat and strict segment support the panel-specific anchor decision.

### Hypothesis being tested

The final model-size/window screen should remain stable across alternative chromosomes, plant transfer should be interpreted with label-source QC, and strict interval metrics should expose whether smoothing improves usability beyond bp-level TE detection.

### Architecture / evaluator changes

- Error bars use repeated chromosomes rather than repeated seeds.
- Strict evaluator now reports IoU `0.5/0.7/0.8/0.9` and boundary tolerances `5/10/25/50/100` bp.
- Strict evaluator repairs: NTv3 uses `ntv3_single` max_length=`window`; NTv2 k-mer outputs are projected back to bp spans using tokenizer offsets or explicit `EsmTokenizer` token spans.

### Sbatch / run status

- Error-bar prep/eval: `9849317` -> `9849318`, completed 66/66.
- Strict segment: initial `9849319`, NTv3 retry `9850150`, NTv2 corrected retry `9852364`, completed 66/66 final rows.
- Plant QC: local summary from `SELF_LABELA_VS_UCSC_CURRENT_READY_RERUN_20260629_V6`.

### Result summary

- Error bars: `ntv2_250m@4096` remains animal_fine leader (mean TE-F1 `0.6431`); `ntv3_100m_pre@2048` remains plant_fine leader (mean TE-F1 `0.3833`).
- Plant QC: mean plant Label-A/UCSC Jaccard `0.0784`, supporting label-source caveats for plant claims.
- Strict segment, IoU `0.8`, boundary `5` bp: animal `ntv2_250m@4096` + CRF-style smoothing has bp-F1 `0.6453`, segment-F1 `0.2557`, boundary-F1 `0.0989`; plant `ntv3_100m_pre@2048` + gap100/min100 has bp-F1 `0.4585`, segment-F1 `0.0305`, boundary-F1 `0.0033`.
- Semantic success: pass after evaluator repairs.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-final-ebarstrictsegplantqc-20260629
- strict summary: reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/strict_segment_summary.tsv
- error-bar summary: reports/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/summaries/eval_panel_summary.tsv

---

## ITER-FINAL-SELECTOR-20260630: multi-anchor selector and NTv2-500M species-probe audit

- Date (UTC): 2026-06-30
- Experiment ID(s): `PIPE-TEFM-FINAL-SELECTOR-20260630`
- Track: Publication-validation support screen.
- Execution mode: local synthesis from completed evidence.
- Resource profile: screen.
- Claim eligibility: cannot claim; selector remains a triage/screen component.

### Hypothesis being tested

Validated candidate models should be organized as panel-specific anchors rather than a single universal model, and NTv2-500M species-specific recovery can serve as a soft annotation-quality audit.

### Inputs

- `PIPE-TEFM-FINAL-20260623` species-probe and matrix summaries.
- `PIPE-TEFM-FINAL-EBAR-20260629` chromosome-repeat summaries.
- `PIPE-TEFM-CALIB-20260621` and `PIPE-TEFM-ANCHOR-20260621` anchor eval summaries.
- Current-ready Label-A/UCSC concordance summary.

### Result summary

- Species-probe audit: 22 rows. Poor after species-specific NTv2-500M fine-tuning: `red_flour_beetle` TE-F1 `0.1494`, `thale_cress` TE-F1 `0.4168`.
- Partial recovery: `soybean` TE-F1 `0.5797`, `c_elegans` TE-F1 `0.7667`.
- Multi-anchor observed oracle mean over 22 species: `0.7787`.
- Best broad single model with at least five rows: `cross_supervised_4096`, mean TE-F1 `0.5432`.
- Deployable selector RF: in-sample R2 `0.8203`, leave-species-out RMSE `0.3040`.
- Semantic success: pass; local synthesis only, no new training.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-final-selector-20260630
- final report: reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/FINAL_REPORT.md
- selector formula: reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/selector_formula_results.json

---

## ITER-FINAL-INTERPRET-20260630: short high-confidence fragment interpretability screen

- Date (UTC): 2026-06-30
- Experiment ID(s): `PIPE-TEFM-FINAL-INTERPRET-20260630`
- Track: Publication-validation support screen.
- Execution mode: local synthesis from completed fragment/SF5 evidence.
- Resource profile: screen.
- Claim eligibility: cannot claim; matched-control/k-mer screen is complete, but model-level attribution remains pending.

### Hypothesis being tested

Short, high-confidence binary TE predictions in strict-background regions may either indicate hidden TE-like signal or binary-model artifacts; Unknown-annotation fragments may contain main4-like superfamily signal useful for annotation audit.

### Inputs

- `software_outputs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/fragments/unknown_highscore_len512.jsonl.gz`
- `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_candidate_predictions.tsv`
- Existing fragment labels: known main4, Unknown annotation, strict background negatives, high-score strict background.

### Result summary

- Parsed 1409 fragment rows: 880 known main4, 260 Unknown annotation, 260 strict background negatives, and 9 high-score strict-background candidates.
- High-score strict-background candidates have mean binary TE probability `0.8893`, but mean SF5 BG fraction `0.9974`; this does not support a hidden-TE discovery claim.
- Unknown annotation fragments have mean best-main4 SF5 fraction `0.4706`, supporting them as annotation-audit candidates.
- Semantic success: pass; local synthesis only, no new training.

### Tri-review consensus

- 3/3 reviewers returned successfully.
- Consensus judgment: `run-sanity-check-first`.
- Safe conclusion: reject hidden-TE language for the 9 strict-BG candidates; continue Unknown-main4-like annotation audit only with matched controls and attribution/motif analyses.

### Matched-control addendum

- Matched strict-BG controls completed for 9/9 high-score strict-BG candidates from same-species/same-chromosome honeybee `GroupUn` controls.
- Matched human known-main4 controls completed for 32/32 Unknown-main4-like candidates at SF5 best-main4 fraction `>=0.8`.
- Match-quality result changes the interpretation: high-score strict-BG is acceptable only as a small false-positive trigger screen; Unknown-main4-like is flagged `POOR_GC_MATCH` and should be treated as high-GC/SVA/model-bias audit before any annotation relabeling.
- PDF extraction with `pypdf` succeeded for all three requested PDFs at keyword/method-scoping level.

### Occlusion smoke addendum

- Slurm occlusion job `9853298` completed successfully after cancelling two slower pre-repair attempts.
- Output status: 34 fragments, 612 detail rows, chunk size 64 bp, CUDA device.
- Strict-BG high-score candidates do not reproduce as high-score in 512 bp fragment context: original binary mean `0.0205`, SF5 main4 score `0`.
- Unknown-main4-like cases show strong SF5 occlusion sensitivity (mean delta `0.3028`), but the GC-control failure means this remains high-GC/SVA-like/model-bias audit rather than annotation correction.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-final-interpret-20260630
- tri-review: docs/07_tri_review.md#tri-review-pipe-tefm-final-interpret-20260630
- report: reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/INTERPRETABILITY_REPORT.md
- matched-control report: reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/MATCHED_CONTROL_REPORT.md
- occlusion smoke report: reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/OCCLUSION_SMOKE_REPORT.md
- status: reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/current_status.json

---

## ITER-20260630-INTERVALREFINER: frozen bp interval refiner smoke

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: after genome-decay selector and fragment council, test whether a deployable frozen-bp interval refiner can approximate the truth-aware oracle repair without changing the base model.
- Experiment ID(s): `PIPE-TEFM-FINAL-INTERVALREFINER-20260630`
- Track: publication-validation support screen / fragment decoder prototype.
- Execution mode: Slurm GPU bounded smoke after cancelling slow 120-window prototypes.
- Resource profile: smoke.
- Claim eligibility: cannot claim; 40-window mouse chr1 smoke only.

### Hypothesis being tested

Local interval/gap features computed from frozen bp probabilities may learn keep/drop and small-gap merge decisions that improve strict segment-F1 over consensus+CRF while preserving true-backed fragments.

### Result summary

- Accepted job `9856944` completed in `00:00:53` with exit code `0:0`.
- Earlier 120-window jobs `9856920`, `9856939`, and `9856942` were cancelled before evidence generation after model inference; they are runtime diagnostics only.
- Smoke used mouse chr1 first 40 windows, `consensus_min` probability track, coordinate split 60% train / 40% test, IoU `0.8`, boundary tolerance `5 bp`.
- Training candidates were small enough for a bounded prototype: 152 segment candidates and 151 gap candidates.
- `consensus_min_raw` test segment-F1 was `0.4462`; `consensus_min_crf` was `0.4685`.
- Deployable refiner variants did not beat CRF: `refiner_keep_drop` `0.4603`, `refiner_gap_merge` `0.4553`, `refiner_keep_drop_gap_merge` `0.4667`.
- Truth-aware `oracle_fill_supported_true` reached segment-F1 `0.9919` and boundary-F1 `0.9919`.

### Interpretation

- The current deployable lightweight post-hoc refiner is not sufficient; it gives no meaningful gain over consensus+CRF under strict IoU/boundary metrics.
- The oracle result remains the strongest signal: bp logits often touch true TE intervals, but a deployable component needs richer interval/boundary supervision rather than threshold/gap/HMM/CRF tuning.
- Next fragment route should be boundary-aware head, segment-aware decoder, interval proposal/refiner with richer features, or semi-Markov/duration-aware decoding. The 120-window metric/runtime loop should be optimized before any larger screen.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-final-intervalrefiner-20260630
- report: reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/INTERVAL_REFINER_REPORT.md
- metrics: reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/interval_refiner_metrics.tsv
- status: reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/interval_refiner_status.json

---

## ITER-20260630-STRUCTDEC: joint backbone structured decoder smoke

- Date (UTC): 2026-06-30
- Linked user request summary: test whether CRF/HMM/semi-Markov style decoders have been tried as trainable backend components attached to the backbone rather than post-hoc smoothing; run one seed.
- Experiment ID(s): `PIPE-TEFM-STRUCTDEC-20260630`
- Track: bounded Discovery / fragmentation decoder smoke.
- Execution mode: Slurm GPU smoke.
- Resource profile: smoke.
- Claim eligibility: cannot claim; bounded human H0 quick-data smoke only.

### Hypothesis being tested

The previous failures only covered post-hoc smoothing, lightweight frozen-bp interval refiner, and frozen-logit trainable decoders. A structured loss attached to model logits during fine-tuning may improve strict segment/boundary metrics because gradients can update the model/head.

### Result summary

- First job `9860192` failed before training because compute-node default `python3` was Python 3.9 and GENERanno remote code requires Python 3.10+ typing support.
- Sbatch was repaired to use `/home/users/j/jwang/.conda/envs/te_benchmark/bin/python`.
- Retry job `9860193` completed successfully in `00:10:32`, exit code `0:0`, MaxRSS about `5.6 GB`.
- The run used seed `42`, `TFSUPP_generanno_H0_w4096_seed42` initialization, human H0 4096 quick data, no backbone freezing, `max_train_samples=96`, `max_eval_samples=40`, and `max_steps=40`.
- Test segment-F1@IoU0.8/boundary5: CE baseline `0.3069`, joint HMM `0.3836`, joint CRF `0.3631`, joint semi-Markov proxy `0.4258`.
- Test boundary-F1: CE baseline `0.1414`, joint HMM `0.2046`, joint CRF `0.0921`, joint semi-Markov proxy `0.2105`.

### Interpretation

- This direction had not previously been tested in the required sense: structured decoder losses were attached during training, not applied only after inference.
- The direction shows positive signal: all structured variants improved strict segment-F1 over the same CE smoke baseline, with the semi-Markov proxy best on segment and boundary metrics.
- The signal is not clean enough to promote as solved. HMM and semi-Markov proxy both increased missed_true_rate to `0.3033`; joint CRF had lower missed_true_rate `0.1721` but weak boundary-F1.
- Next bounded iteration should keep joint training but add explicit boundary loss and true-retention penalty, then evaluate on the same mouse strict segment panel used by previous fragment screens.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-structdec-20260630
- report: reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/JOINT_STRUCTURED_DECODER_REPORT.md
- metrics: reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/joint_structured_decoder_metrics.tsv
- status: reports/tefm_final/PIPE-TEFM-STRUCTDEC-20260630/joint_structured_decoder_status.json
- code review: docs/21_code_review_log.md#code-review-gate-pipe-tefm-structdec-20260630

---

## ITER-20260630-NEXT-DECAY-FRAG: selector calibration and trainable fragmentation decoder smoke

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: continue iterating the generalization-decay / anchor selector until it can guide new-species trust, and test trainable fragmentation components beyond post-hoc HMM/CRF while retaining true-backed fragment guardrails.
- Experiment ID(s): `PIPE-TEFM-NEXT-DECAY-FRAG-20260630`
- Track: publication-validation support screen / selector usability + fragment decoder prototype.
- Execution mode: local selector calibration and Slurm bounded decoder smoke.
- Resource profile: smoke.
- Claim eligibility: cannot claim; selector is still screen-grade and decoder used only 40 mouse chr1 windows from frozen bp tracks.

### Hypothesis being tested

The existing genome-derived selector may become useful if reframed from exact F1 prediction into calibrated risk/action guidance, and a small trainable boundary/CRF/duration decoder on frozen bp tracks may reduce strict fragmentation better than post-hoc CRF.

### Result summary

- `$tri-review` completed with 3/3 quorum, and `$council` completed two adversarial rounds. Consensus: do not launch one coupled large project; build asymmetric MVPs and keep abstention/guardrail metrics central.
- Point-estimate selector remains unusable as an exact confidence formula. Best row was `baseline_plus_kmer / leave_species_out`, RMSE `0.2642`, MAE `0.2194`, top-1 anchor accuracy `0.4545`, top-2 accuracy `0.6818`, mean regret `0.0680`; leave-clade-out RMSE stayed around `0.40-0.42`.
- Conservative selector action policy is screen-usable only as a top-2 shortlist plus local-probe warning. Best row contains true best/top2 anchor in `0.8636` of species and has mean regret after action `0.0071`, but single-anchor high-confidence coverage is `0.0`.
- Trainable decoder Slurm job `9858072` completed in `00:01:34` with exit code `0:0`.
- Frozen-logit trainable decoders did not beat post-hoc CRF at IoU `0.8` / boundary `5 bp`: `consensus_min_crf_posthoc` segment-F1 `0.4685`, `trainable_boundary_cnn` `0.2778`, `duration_prior_decoder` `0.2366`, and `trainable_linear_crf` `0.1798`.

### Interpretation

- The user concern is confirmed: the current formula cannot tell a new user “this model will be trustworthy on your species” as a calibrated point estimate, especially for leave-clade-out cases.
- The only deployable selector form currently defensible is conservative routing: give a top-2 anchor shortlist and require a small chromosome-level local probe before trusting exact F1.
- The trainable HMM/CRF idea is not rejected in principle, but a tiny decoder trained after frozen probabilities is too weak. The next fragmentation attempt must move closer to backbone embeddings or use a richer interval proposal/scorer with boundary supervision.
- Duration priors alone are unsafe: they reduce fragments but delete true-backed signal and worsen missed true rate.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-next-decay-frag-20260630
- tri-review: docs/07_tri_review.md#tri-review-pipe-tefm-next-decay-frag-20260630
- report: reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/FINAL_REPORT.md
- selector calibration: reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration/SELECTOR_CALIBRATION_REPORT.md
- action policy: reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_action_policy/SELECTOR_ACTION_POLICY_REPORT.md
- decoder report: reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/trainable_fragment_decoders/TRAINABLE_FRAGMENT_DECODERS_REPORT.md

---

## ITER-20260630-PURSUE-DECAY-STRUCT: conservative selector router and boundary/retention structured decoder

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: bounded single-seed `$pursue` iteration for A) deployable generalization-decay/anchor selector as conservative trust router and B) GENERanno 4096 joint structured decoder with boundary-aware and true-retention training.
- Experiment ID(s): `PIPE-TEFM-PURSUE-SELECTOR-20260630`, `PIPE-TEFM-PURSUE-STRUCTDEC-20260630`
- Path tested: publication-validation support screen, not claim-bearing SOTA.
- Milestone: selector conservative routing + structured decoder guardrail test.
- Track: bounded screen.
- Execution mode: selector local run-and-evaluate; decoder Slurm run-and-evaluate.
- Resource profile: screen.
- Claim eligibility: cannot claim.

### Hypothesis being tested

The existing point selector may still be useful if reframed as a conservative top-2/local-probe router with leave-clade abstention, and boundary/retention losses may improve strict interval usability over CE while controlling missed_true_rate.

### Architecture changes

- Selector: added `selector_conservative_router.py`, using existing deployable genome-derived prediction rows but enforcing no single-anchor high-confidence route, top-2 shortlist/local-probe for in-panel species, and leave-clade abstention.
- Decoder: added `boundary_aux` and `semimarkov_retention` training-time losses to the prior joint CE/HMM/CRF/semi-Markov cohort, plus CE-relative deleted true-backed vs false-fragment diagnostics.
- Why structural: the decoder loss is attached to model logits during fine-tuning; it is not threshold/gap/post-hoc smoothing.

### Data readiness

- Selector source: `reports/tefm_final/PIPE-TEFM-NEXT-DECAY-FRAG-20260630/selector_calibration/selector_row_predictions.tsv`.
- Decoder data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`.
- Decoder init: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`.
- Seed: `42`.

### Sbatch / run status

- Selector: local completed.
- Decoder job: `9860400`, `shared-gpu`, A100 80GB, completed; status `outputs/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/STATUS`.
- Output dirs: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/`, `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/`.

### Result summary

- Selector in-panel/leave-species router: top-2 contains-best `0.8636`, mean regret `0.0071`, p90 regret `0.0008`, ECE `0.0372`, single-anchor high-confidence coverage `0.0`; gate passed as conservative router.
- Selector leave-clade: explicit abstention/local-probe for all held-out clades; top-2 formula itself remains insufficient (`0.6364` contains-best), so new clades require local probe/new anchor.
- Decoder CE baseline: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- Best decoder: `semimarkov_retention`, segment-F1 `0.4439`, boundary-F1 `0.2290`, missed_true_rate `0.3525`; promotion gate failed because missed_true_rate rose by `0.0902`.
- Semantic success: yes; method success: selector conservative-router yes, decoder promotion no.

### Tri-review consensus

Completed with 3/3 quorum. Consensus: selector is acceptable only as a conservative top-2/local-probe router with leave-clade abstention; decoder cannot be promoted because missed_true_rate and deleted true-backed fragments fail the retention gate.

### Pivot decision

Completed. Decision: carry selector forward as conservative router; do not scale current decoder; any continuation must change objective/loss toward interval-level true-retention or fragment-survival constraints.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-pursue-decay-struct-20260630
- tri-review: docs/07_tri_review.md#tri-review-pipe-tefm-pursue-decay-struct-20260630
- pivot: docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-pursue-decay-struct-20260630
- selector report: reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/SELECTOR_CONSERVATIVE_ROUTER_REPORT.md
- decoder report: reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/JOINT_STRUCTURED_DECODER_REPORT.md
- decoder metrics: reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/joint_structured_decoder_metrics.tsv

---

## ITER-20260630-minhash-intervalsurv: selector MinHash + interval-survival decoder

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: continue active milestone `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC` with conservative selector router and structured decoder objective/loss changes only.
- Experiment ID(s): `PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630`, with selector output `PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630` and decoder output `PIPE-TEFM-PURSUE-INTERVALSURV-20260630`.
- Path tested: publication-validation support / conservative trust router + joint structured decoder.
- Milestone: `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC`.
- Track: bounded screen.
- Execution mode: selector local run-and-evaluate; decoder smart-sbatch run-and-evaluate.
- Resource profile: screen.
- Claim eligibility: cannot claim; non-SOTA publication-support evidence only.

### Hypothesis being tested

Genome-wide MinHash-equivalent k-mer distance may improve deployable anchor routing, especially leave-clade risk handling, and an interval-level survival objective may preserve true TE segments better than the prior semi-Markov retention proxy.

### Architecture changes

- Selector: added deterministic bottom-k MinHash-equivalent sketches from genome FASTA windows and merged the resulting Jaccard/Mash-like distances into the existing deployable selector rows.
- Decoder: added interval-level true-retention / fragment-survival loss plus a segment-aware evidence-preserving decoder variant.
- Why structural: selector uses new genome-derived distance features; decoder modifies the training objective attached to GENERanno logits rather than tuning threshold/gap/post-hoc HMM/CRF.

### Data readiness

- Selector source: `software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv` and `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/anchor_pair_genome_features.tsv`.
- Decoder data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`.
- Decoder init: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`.
- Seed: `42`.

### Sbatch / run status

- Selector: local completed.
- Decoder job: `9861062`, `shared-gpu`, A100 80GB, completed; status `outputs/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/STATUS`.
- Output dirs: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/`, `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/`.

### Result summary

- Selector in-panel policy remains `baseline_plus_kmer`: top-2 contains-best `0.8636`, mean regret `0.0071`, confidently-wrong single-anchor rate `0.0`.
- MinHash improves leave-clade RMSE/top-2 relative to baseline (`0.3716` RMSE and `0.8182` top-2), but remains below deployment threshold, so leave-clade/new-clade mode still abstains.
- Decoder CE baseline: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- `interval_survival_decoder`: segment-F1 `0.3756`, boundary-F1 `0.1805`, missed_true_rate `0.2910`, all primary decoder gates passed.
- Guardrail failed: deleted_true_backed_fraction `0.4592` exceeds `0.15`; validator status `not_yet`.

### Tri-review consensus

Completed with 3/3 quorum. Consensus: selector formula direction stops as triage-only; current decoder cannot be promoted because true-backed deletion guardrail fails. Disagreement: Claude recommends stopping decoder now, while Codex/Antigravity allow one final bounded objective/loss attempt.

### Pivot decision

Completed. Decision: stop selector compute; run exactly one final decoder-only `retention_constrained_interval_loss` screen. If it fails `deleted_true_backed_fraction <= 0.15`, stop decoder direction and write future work.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-pursue-minhash-intervalsurv-20260630
- selector report: reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/SELECTOR_MINHASH_ROUTER_REPORT.md
- decoder report: reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/JOINT_STRUCTURED_DECODER_REPORT.md
- decoder metrics: reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/joint_structured_decoder_metrics.tsv

---

## ITER-20260630-retconstr: final retention-constrained decoder screen

- Date (UTC): 2026-06-30
- Linked `/goal` command summary: final decoder-only objective/loss attempt after tri-review/pivot; selector frozen as triage-only.
- Experiment ID(s): `PIPE-TEFM-PURSUE-RETCONSTR-20260630`.
- Path tested: joint structured decoder / true-backed retention constraint.
- Milestone: `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC`.
- Track: bounded screen.
- Execution mode: smart-sbatch run-and-evaluate.
- Resource profile: screen.
- Claim eligibility: cannot claim; non-SOTA publication-support evidence only.

### Hypothesis being tested

A retention-constrained interval objective with raw-evidence veto might preserve true-backed fragments while retaining segment-F1 and boundary-F1 improvements over CE.

### Architecture changes

- Added `retention_constrained_interval_loss`, making low-confidence valleys inside true TE intervals and per-interval retention part of the training objective.
- Added `retention_constrained_decode`, a raw-evidence veto intended to prevent structured smoothing from erasing candidate TE islands.
- Added internal promotion gate requiring `deleted_true_backed_fraction <= 0.15`.

### Data readiness

- Decoder data: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick`.
- Decoder init: `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42`.
- Seed: `42`.

### Sbatch / run status

- Initial 80GB-specific submission failed before job creation because requested node configuration was unavailable.
- Sbatch was revised to request one 24GB `nvidia_geforce_rtx_3090`.
- Decoder job: `9862135`, `shared-gpu`, completed; status `outputs/PIPE-TEFM-PURSUE-RETCONSTR-20260630/STATUS`.
- Output dir: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/`.

### Result summary

- CE baseline: segment-F1@IoU0.8 `0.3069`, boundary-F1@5bp `0.1414`, missed_true_rate `0.2623`.
- `retention_constrained_decoder`: segment-F1 `0.2534`, boundary-F1 `0.0856`, missed_true_rate `0.2541`, deleted_true_backed_fraction `0.2727`.
- Validator status: `not_yet`; selector criteria pass, but decoder segment/boundary criteria fail and true-backed deletion guardrail remains above `0.15`.
- Semantic success: yes; method success: no.

### Tri-review consensus

Completed with 3/3 quorum. Consensus: engineering success but method failure; stop decoder direction now as future work.

### Pivot decision

Completed. Decision: abandon structured decoder fragmentation objective route for this milestone and record `DEC-001` in docs/09. Carry selector forward only as conservative router.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-pursue-retconstr-20260630
- decoder report: reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/JOINT_STRUCTURED_DECODER_REPORT.md
- decoder metrics: reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/joint_structured_decoder_metrics.tsv

---

## ITER-20260701: threshold and length-adaptive fragmentation diagnostic

- Date (UTC): 2026-07-01
- Linked `/goal` command summary: `$capability-pursue` diagnostic prompted by user concern that strict thresholds may be too harsh and that short-vs-long TE fragments may need different postprocess handling.
- Experiment ID(s): `PIPE-TEFM-CAP-POSTPROC-20260701`
- Track: Capability support diagnostic / comparator audit
- Execution mode: smart-sbatch bounded screen
- Resource profile: small human/mouse panel, seed `42`
- Claim eligibility: cannot claim; no capability promotion

### Hypothesis being tested

Strict thresholding and uniform smoothing may be over-pruning biologically real fragmented TE annotations. A multi-threshold view and length-adaptive short-raw/long-HMM strategy might reveal a safer practical postprocess rule.

### Architecture changes

- No new model architecture and no training.
- Compared raw threshold curves, gap/min-length heuristics, fixed HMM-style smoothing, HMM plus short-fragment rescue, and length-adaptive short-raw/long-HMM rules.
- This is diagnostic evidence only because `DEC-001` and `DEC-002` already stop threshold/gap/HMM/CRF/post-hoc tuning as the main capability route.

### Sbatch / run status

- Job id(s): `9880686`
- Output dir(s): `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/`
- Status: completed

### Result summary

- Human strict-safe best: `raw_t0.20`, segment-F1@IoU0.8 `0.2422`, boundary-F1@5bp `0.1143`, missed_true_rate `0.2541`, deleted_true_backed_fraction `0.0000`.
- Mouse strict-safe best: `gap25_min40_t0.50`, segment-F1 `0.4589`, boundary-F1 `0.1575`, missed_true_rate `0.1133`, deleted_true_backed_fraction `0.1042`.
- Best observed HMM/length-adaptive rows improved segment metrics but failed true-backed deletion guardrails, especially human deleted_true_backed_fraction around `0.84-0.86`.
- Semantic success: yes.

### Review-board / council consensus

3/3 review-board and 3/3 council consensus: keep as postprocess sensitivity/tradeoff audit only. Do not choose an "optimal threshold" from this panel or promote HMM/gap/length-adaptive rules as a solved method.

### Decision

Answered as diagnostic. Use multi-threshold curves in support material; keep interval reconstruction as limitation/future work unless a substantially new global interval mechanism is proposed.

### Links

- result-log: docs/06_results_log.md#result-pipe-tefm-cap-postproc-20260701
- report: reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/POSTPROCESS_THRESHOLD_REPORT.md
- review summary: reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/REVIEW_COUNCIL_SUMMARY.md

---

## ITER-20260811-BENCH5: five-workflow fail-closed identity smoke

- Date: 2026-08-11 CEST.
- Experiment ID: `BENCH-5TOOL-SMOKE-20260811-R1`.
- Path / milestone: bounded cohort order 1; external-workflow denominator identity gate.
- Track: baseline smoke; execution mode `run-and-evaluate`.
- Hypothesis: the intended five workflows can be invoked with exact frozen identities, required databases and canonical adapters without silent substitution.
- Mechanism delta: independent digest-pinned workflow runner with zero-based half-open adapters and explicit `ENGINEERING_PASS / FOUNDATIONAL_TYPED_BLOCK / VERSION_MISMATCH / INVALID_RUN` states.
- Data: hash-frozen official tiny installation fixtures; no train/validation/test split and no biological performance claim.
- Sbatch: Job `11519312`, `private-teodoro-gpu`, CPU-only zero-GRES, 8 CPU/64 GB, `COMPLETED` in `00:15:13`, exit `0:0`, 0 GPU.
- Result: semantic PASS for a complete fail-closed matrix; primary engineering pass fraction `0.0` (0/5), four typed blocks, one version mismatch, zero invalid cells.
- Tri-review consensus: `3/3`; valid fail-closed engineering result, no scientific metric, no route may be promoted/tuned/scaled.
- Pivot: comparability audit first; close B exact runtime/database denominator before any biological comparator run.
- Links: `docs/06_results_log.md#result-bench-5tool-smoke-20260811-r1`; `outputs/BENCH-5TOOL-SMOKE-20260811-R1/metrics.json`; `docs/experiments/BENCH-5TOOL-SMOKE-20260811-R1.md`.

---

## ITER-20260811-ASSET-GATES: F/S/G/E fail-closed route collection

- Date: 2026-08-11 CEST.
- Experiment IDs: `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`, `SF-HIER-OPENSET-SCREEN-20260811-R1`, `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`, `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`.
- Track/profile: four requested Track-A screens stopped at independent asset-gate smoke.
- Hypothesis: each new mechanism can start only if its truth/split/provenance/binding contract is independently reproducible.
- Mechanism delta: no scientific method was implemented because all four prerequisite gates are false; deterministic verifiers bind evidence/config/code hashes and turn drift into `INVALID_RUN`.
- Allocations: Job `11519717` F/G audit (`COMPLETED`, 1 second, 1 CPU/1 GB, 0 GPU) and Job `11519729` S/E audit (`COMPLETED`, 2 seconds, 1 CPU/1 GB, 0 GPU).
- Result: all four are semantically valid `FOUNDATIONAL_TYPED_BLOCK`, `asset_gate_pass=0.0`, `scientific_screen_executed=false`, claim-ineligible.
- Code review: all four final source packages PASS after initial S/E schema/stale-state blockers and fail-closed repairs; machine gates in each output directory.
- Tri-review / pivot: `3/3`; keep all four routes asset-gated. Primary next dependency is B denominator closure; F/S/G/E require separate gate repair and authorization.
- Links: four `docs/experiments/<exp_id>.md`; four `outputs/<exp_id>/metrics.json`; `docs/21_code_review_log.md`.

---

## ITER-20260811-F-REGISTRY-R2: fragmentation evidence-registry closure

- Date: 2026-08-11 CEST.
- Experiment ID: `FRAG-EVIDENCE-REGISTRY-20260811-R2`.
- Track/profile: publication-validation support; bounded CPU asset-audit smoke; claim-ineligible.
- Hypothesis: the fragmentation route can close its H0/truth/comparator identity contract without reviving deletion-based postprocessing or pretending that a gap merge is the proposed typed-parent lattice.
- Implementation: deterministic H0 directory inventory, T0/T1/T2 registry, positive-only truth guard, same-input window aggregation, RAW/CENTER70/HMM2/MERGE comparator probes, command/input/output hash manifests, and fail-closed Slurm-only state machine.
- Independent code review: PASS for asset-audit submission only; scientific lattice/screen explicitly unauthorized.
- Jobs: `11521393` failed before payload in 1 second during Conda activation under early nounset; bounded environment repair was independently re-reviewed. Retry `11521479` completed `0:0` in 14 seconds, 1 CPU/4 GB, 0 GPU.
- Result: semantic success with `integrity_check_count_passed=6/6`; terminal status `FOUNDATIONAL_TYPED_BLOCK`; no inference or biological screen.
- Interpretation: HMM2 is historical-only; accepted postprocessor count=0; scientific lattice count=0. T1 remains positive-only, and future scientific execution additionally needs same-input H0 probability tracks.
- Validation: route-local goal validator returned `progress`, not scientific success or claim authorization.
- Chain status: result-log and evidence capture complete; Wave-1 cohort tri-review/pivot pending B and S0 collection.

---

## ITER-20260811-B-DENOMINATOR-R2: exact five-workflow closure attempt

- Date: 2026-08-11 CEST.
- Experiment ID: `BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2`.
- Track/profile: bounded CPU engineering smoke; claim-ineligible; no biological benchmark.
- Jobs: preparation `11522328`/`11522329`/`11522330`; main `11522405`; all 0 GPU; Pfam action not submitted.
- Artifact result: five terminal cell records and 778/778 artifact hashes verified.
- Semantic audit: `FAILED_RUN`. The collector incorrectly classified four executed runtime/integration failures as foundational; audited counts are four `INVALID_RUN`, one valid TEtrimmer/Pfam `FOUNDATIONAL_TYPED_BLOCK`, zero engineering passes.
- Validator: route-local `validate_goal.py` with audited status returned `failed_run`.
- Decision: stop and notify; no immediate rerun. Repair classifier plus RM identity, Earl Grey FamDB discovery, HiTE launcher and EDTA runtime integration, then fresh code review.

---

## ITER-20260811-S0-DATA-R2: direct-superfamily leakage-safe data gate

- Date: 2026-08-11 CEST.
- Experiment ID: `SF-DIRECT-BASELINE-SCREEN-20260811-R2`.
- Track/profile: CPU DATA stage for a leakage-safe S0 direct-superfamily screen; 0 GPU; claim-ineligible.
- Independent code review: PASS for CPU DATA only; GPU and S1 excluded.
- Job: `11522718`, 16 CPU/96 GiB/12h limit, 0 GPU.
- Result: `DATA_FAILED` before materialization. Python `csv.DictReader` hit its 131072-byte field limit on the frozen chunk manifest; no DATA PASS, training, inference or scientific metric exists.
- Validator: `failed_run`; `hierarchical_stage_authorized=false` remains binding.
- Decision: stop and notify. Add a bounded field-size contract and regression test, re-review, then only a CPU DATA retry may be considered.
- Repair-only retry: bounded 2,000,000-character reader, true-shape probe and 15/15 tests passed fresh review. Job `11523252` used 16 CPU/96 GiB/0 GPU for about 21 minutes and advanced past CSV parsing, then terminated `DATA_TYPED_BLOCK` because not every frozen RepeatMasker P-state family name resolves one-to-one to a Dfam 3.9 accession/consensus.
- Retry result: no DATA PASS, split/leakage audit, training or S0 metric. `validate_goal=failed_run`; 3/3 external tri-review completed with two `comparability-blocker` and one `replace-component` judgment.
- Pivot: comparability audit first. Build a bounded CPU-only source-library/consensus provenance audit without changing the goal or building splits; only a 100% unique mapping can permit another S DATA repair. Any new homology-cluster definition requires a separate human-gated contract revision. GPU/S1 remain unauthorized.
- Follow-up exp `SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1`, Job `11523938`: allocation-side tests passed, but formal canonical audit ended `AUDIT_FAILED` after about 2m07s. The leaf-level resolver incorrectly assumed every Dfam 3.9 H5 partition had `Lookup/ByName`; partition 3 legitimately lacks it and raised `KeyError`. No provenance output exists; validator=`failed_run`. Stop for tri-review/pivot and fresh code review before any retry.
- Failed-run chain: 3/3 external reviewers unanimously selected `run-sanity-check-first`. Pivot allows one narrow structural-index repair: freeze real partition layout; skip only structurally absent `ByName`; present-but-broken remains failure; denominator unchanged. Fresh review is mandatory before at most one CPU retry. S0 GPU/S1 remain forbidden.

## ITER-BENCH-RM-HITE-VALIDITY-20260811-R1

- Date: 2026-08-11 CEST.
- Experiment ID: `BENCH-RM-HITE-VALIDITY-20260811-R1`; bounded offline CPU validity smoke, 0 GPU, claim-ineligible.
- Job `11523819`, about 18m32s: RM2 `2.0.9` + RM `4.2.4` + Dfam `4.0` reached `ENGINEERING_PASS` and yielded 43 canonical adapter rows. HiTE exact `3.3.3` launched correctly but timed out at 600s during step 3.3 before final GFF, so it is `INVALID_RUN`.
- Aggregate: 1/2 pass, semantic false, `STATUS=FAILED`, validate=`failed_run`; artifacts 334/334 hashes verified.
- Decision: stop pending tri-review/pivot. Do not automatically rerun the paired job or expand to other workflows.
- Tri-review/pivot: 3/3 High-confidence consensus chooses an isolated HiTE-only continuation with exact frozen inputs, 1800s cap and 1h/0GPU allocation. RM pass is retained as an immutable cell artifact; original R1 remains failed. A second HiTE timeout is a hard stop.

---

## ITER-<N>: <short description>

- Date (UTC):
- Linked `/goal` command summary:
- Experiment ID(s):
- Path tested: <docs/03 §7.3 Path N>
- Milestone: <M1 / M2 / M3 / M4 / M5>
- Track: <Track A screen / Track B scale-up / baseline / generalization>
- Execution mode: <run-and-evaluate / submit-and-stop>
- Resource profile: <smoke / screen / full / scale>
- Claim eligibility: <cannot claim / claim candidate / robust claim support>

### Track A screen setting (if applicable)

| exp_id | Path | Architecture change | sample_fraction | epochs | patience | seed | config | output_dir |
|---|---|---|---:|---:|---:|---:|---|---|

Promotion rule to Track B:

### Track B scale-up setting (if applicable)

- Promoted from Track A exp_id:
- Promotion reason:
- Scale-up change:
- Success criterion:
- Fallback if fails:

### Hypothesis being tested

### Architecture changes

- What changed:
- Why this is structural rather than hyperparameter tuning:
- Which SOTA weakness it attacks:

### Data readiness

- Dataset(s) used:
- Downloaded this iteration? yes / no
- Path / version / hash / split source:

### Sbatch / run status

- Job id(s):
- Output dir(s):
- Log path(s):
- Status: submitted / running / completed / failed / waiting-for-job
- Resume instruction if submit-and-stop:

### Result summary (if run-and-evaluate or completed job)

- Primary metric: <value> (SOTA: <value>, gap: <abs>)
- Gates: primary <pass/fail>, sota_claim <pass/fail>, review_decision <triggered/not>
- Semantic success: ✅/❌

### Tri-review consensus

### Pivot decision

### Links

- result-log: docs/06_results_log.md#<exp_id>
- tri-review: docs/07_tri_review.md#<ref>
- pivot: docs/08_pivot_decisions.md#<ref>
- decisions-log if abandoned: docs/09_decisions_log.md#<ref>

---

## ITER-20260812-S0-P3-R0: partition-3 index-independent identity recovery

- Date: 2026-08-12 CEST.
- Experiment ID: `SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1`.
- Track/profile: S0 pre-data R0 identity recovery; bounded CPU asset smoke; claim-ineligible.
- Execution mode: run-and-evaluate.
- Hypothesis: many of the 279 exact-name misses may be recoverable from canonical `Families/...` dataset attributes in the sole Dfam 3.9 partition lacking `Lookup/ByName`.
- Mechanism delta: exhaustive exact case-sensitive metadata scan; no prefix/case/copy fallback, clustering, split, model or GPU work.
- Job: `11525316`, `private-teodoro-gpu`, 4 CPU/48 GiB/2h/0 GPU.
- Result: `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`. The healthy scan reached 30,000/321,856 datasets in about 1,480 seconds; projected full time was about 4.41 hours, so it was cancelled early rather than allowed to hit a certain 2-hour timeout. Partial zero-hit telemetry is not evidence.
- Semantic success: fail; `validate_goal=failed_run`; scientific recovery and all downstream authorizations remain false.
- Tri-review consensus: `2/3 DEGRADED_REVIEW`; both successful reviewers preserve exact exhaustive semantics and require a deterministic shard-throughput preflight before formal R0.
- Pivot decision: `sanity check first`; implement/review one 4CPU/16GiB/20min/0GPU preflight in a new namespace. R1/R2/GPU/S1 remain blocked.
- Links: `docs/06_results_log.md`; `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`; `sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch`.

---
# ITER-20260812-S0-P3-R2-PRESCAN

- Experiment: `SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2`, Job `11526687`.
- Result: failed-run in 4 seconds before H5 enumeration; login/compute `st_dev` mismatch with all stable identity fields equal.
- Validation: `failed_run`, semantic false; no identity result or checkpoint.
- Tri-review: 2/3 degraded; both valid reviewers identify an execution-environment identity-contract bug. Claude=`replace-component`, Codex=`run-sanity-check-first`.
- Pivot: narrow `st_dev` audit-only/explicit alias repair, behavior tests and fresh review; at most one separately authorized repair retry. No downstream authorization.

---
# ITER-20260812-S0-P3-R2-VALID-NEGATIVE

- Experiment: `SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2`, final authorized repair Job `11526905`.
- Result: semantic-successful valid negative. 35/35 units exhaustively covered 321,856 unique datasets/objects; zero exact candidates for all 279 frozen targets (6,432,583 occurrences).
- Integrity: current immutable state, 64-file attempt payload and 35 two-level checkpoint manifests independently rehashed with zero mismatch; target and occurrence conservation deltas are zero.
- Validation: old ACTIVE_GOAL returns `failed_run` only as a mismatched-goal stop signal; no performance or SOTA comparison exists.
- Tri-review: 3/3 accepts result validity. Claude=`abandon-route` for the partition-3 exact-name subroute; Codex/Antigravity=`replace-component`; all converge on closing this scan and requiring a human-gated official identity-source replacement.
- Pivot: `replace-component`. No repeat scan, full-catalog/homology construction, S0 GPU or S1 until the identity-source contract is explicitly revised and freshly reviewed.

---
## ITER-20260812-S0-DFAM39-CURATED-CROSSWALK

- Experiment: `SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1`; profile `cpu_authoritative_identity_crosswalk_audit`.
- Hypothesis: Dfam 3.9 curated EMBL exact same-record relations may close the 279-identifier identity gate without changing direct superfamily labels.
- Job `11527999`: completed in 14 seconds, 1 CPU/2 GiB/0 GPU.
- Result: valid-negative typed block. Only 50/279 identifiers resolve uniquely, 2 are ambiguous and 227 remain missing; denominator and occurrence mass are conserved.
- No homology clustering, split, dataset build, training, GPU work or S1 execution occurred. Next action requires post-result tri-review/pivot and a separately reviewed all-family source audit if pursued.
## ITER-20260812-S0-DFAM39-ALLFAMILY-CROSSWALK

- Experiment: `SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1`; Job `11528157`.
- Mechanism delta: complete official Dfam 3.9 DF+DR target-only streaming audit, with exact DF reconciliation and raw-DR support-only semantics.
- Raw output reported zero support across 4,095,118 DR records, but tri-review found official PI semicolon-list and DR semicolon-terminator grammar were not completely implemented. The raw-support conclusion is reclassified as a grammar-comparability failed run. Curated 50/2/227 remains unchanged and independently blocks downstream work.
- No split, catalog, clustering, DATA, training or GPU work occurred. The official Dfam 3.9 exact-relation route now satisfies its stop rule and requires post-result tri-review/pivot before any further action.

- Grammar-repair Job `11528267` closed the PI/DR parser caveat. Raw DR grammar telemetry is NM=2,795 with zero target hits and PI/SN/DR=0 lines. The all-family result is now a final valid-negative; same-source repair budget is exhausted.

## ITER-20260812-S0-ACCESSION-ROUNDTRIP-FIRST-ATTEMPT

- Experiment: `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1`; Job `11528744`; CPU-only smoke, claim-ineligible.
- Hypothesis: paired name-header and accession-header custom libraries preserve identical RepeatMasker geometry/raw-class labels while the accession arm retains `accession.version`.
- Allocation: `private-teodoro-gpu`, exact 1 CPU/4 GiB/20m/0GPU; status `FAILED`, exit `2:0`, elapsed 2 seconds.
- Result: `FAILED_RUN_RESOURCE_GUARD`. Pre-submit and 33/33 tests passed, but the formal runner rejected its `SLURM_TIMELIMIT` environment assumption before FamDB or RepeatMasker execution. No scientific metric or valid negative exists.
- Integrity: canonical pointer unchanged; attempt-local failure evidence and post-run audited manifest close without hash mismatch.
- Tri-review/pivot: `2/3 DEGRADED_REVIEW`; both valid reviewers choose `run-sanity-check-first`. Pivot permits only a narrow `scontrol`-backed resource reconciliation repair and fresh review, followed by at most one separately authorized retry. Representative-window/full DATA/homology/GPU/S1 remain blocked.
- Links: `docs/06_results_log.md`; `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/`; `sbatch/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1.sbatch`.

## ITER-20260812-S0-ACCESSION-ROUNDTRIP-REPAIR-RETRY

- Experiment: `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1`; authorized repair retry Job `11528885`; CPU-only smoke, claim-ineligible.
- Mechanism delta: replace the non-portable `SLURM_TIMELIMIT` guard with bounded, exact allocation-side `scontrol` authority reconciliation; the six-family/RM scientific contract is unchanged.
- Allocation: `private-teodoro-gpu`, exact 1 CPU/4 GiB/20m/0GPU; status `FAILED`, exit `2:0`, elapsed 10 seconds.
- Result: `FAILED_RUN_FAMDB_API_COMPATIBILITY`. Strict scheduler reconciliation and 37/37 tests passed; construction of the pinned official FamDB object then raised `AttributeError: 'FamDBLeaf' object has no attribute 'added'`. RepeatMasker did not start, so no roundtrip geometry result or valid negative exists.
- Integrity: canonical `PREFLIGHT_FAILED` bundle and attempt-local evidence are hash-closed by `AUDITED_MANIFEST_11528885.sha256`; all downstream authorization remains false.
- Tri-review/pivot: `2/3 DEGRADED_REVIEW`, unanimous among valid reviewers for `replace-component`. No third retry; only a new exp-scoped, no-RepeatMasker leaf-level exact-access contract probe may re-enter after fresh review.
- Links: `docs/06_results_log.md`; `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/`; `sbatch/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1.sbatch`.

## ITER-20260812-F-CONSENSUS-COLLINEARITY-FIRST-ATTEMPT

- Experiment: `FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1`; Track F capability falsification; CPU-only smoke, claim-ineligible.
- Hypothesis: immutable T1 Rice fragments plus label-blind consensus-coordinate collinearity may contain enough information to reconstruct fragmented positive parent groups without gap/threshold/HMM cousins.
- Allocation: Job `11529694`, `private-teodoro-gpu`, 8 CPU/32 GiB/2h/0GPU; `FAILED 1:0`, elapsed 0 seconds.
- Result: `FAILED_RUN_REVIEWED_RUNTIME_CLOSURE`. The allocation-side guard found `scripts/pre_submit_gate.py` in the frozen runtime list but absent from machine `reviewed_files`; it stopped before tests, Rice inputs or scientific payload.
- Scientific result: absent; no method metrics, valid negative or information-sufficiency verdict exists.
- Tri-review/pivot: `2/3 DEGRADED_REVIEW`; both valid reviewers chose `run-sanity-check-first`. Pivot permits only reviewed-files closure repair plus fresh delta review, then one exact-resource same-exp retry.
- Links: `docs/06_results_log.md`; `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/`; `sbatch/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.sbatch`.

## ITER-20260812-F-CONSENSUS-COLLINEARITY-FINAL-RETRY

- Experiment: `FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1`; final one-shot scientific retry Job `11531090`; Rice T1 positive-only CPU audit, claim-ineligible.
- Mechanism delta from Job `11529694`: scientific code and frozen inputs were unchanged; only the independently reviewed machine reviewed-runtime closure was repaired to include the shared pre-submit dependency.
- Allocation: `private-teodoro-gpu`, 8 CPU/32 GiB/2h/0GPU; `COMPLETED 0:0` in 25 seconds.
- Result: `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`. Candidate exact recovery=`0.138889`, pairwise harmonic=`0.308188`, topology=`0.105263`, false-fusion=`0.075862`, mapped-leaf fraction=`0.555102`, leaf retention=`1.0`.
- Comparator result: GAP100 exact recovery=`0.371693`, harmonic=`0.669109`, topology=`0.473684`; paired bootstrap candidate-minus-comparator intervals are wholly negative for exact recovery, pairwise harmonic and topology.
- Interpretation: exact consensus-coordinate/strand evidence is informative versus the shuffled null but insufficient for this parent-assembly mechanism. No threshold tuning, Fly/H0 extension, GPU or capability promotion is allowed; tri-review/pivot is pending.
- Links: `docs/06_results_log.md`; `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/`.

## ITER-20260812-S0-FAMDB-LEAF-EXACT-ACCESS-PROBE

- Experiment: `SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1`; Job `11533175`; isolated CPU API probe, claim-ineligible.
- Hypothesis: the installed FamDB 3.9 leaf API can retrieve six frozen versioned accessions exact-once across 12 partitions without name/alias/prefix fallback.
- Allocation: `private-teodoro-gpu`, exact 1 CPU/4 GiB/10m/0GPU; `FAILED 2:0` in 17 seconds.
- Result: `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`. Scheduler, gate and 23/23 tests passed. The 72-call probe returned in memory, but read-mode cleanup invoked a write finalizer and raised on missing `FamDBLeaf.added` before observations were published.
- Scientific interpretation: unknown; neither PASS nor typed block can be inferred. All annotation, homology, DATA, GPU S0 and S1 authorization remains false.
- Next binding step: post-result tri-review and pivot. The consumed one-shot gate cannot authorize a retry.
- Tri-review/pivot: `2/3 DEGRADED_REVIEW`, action consensus is one final separately reviewed close-only lifecycle repair; pivot=`replace-component`. Any subsequent failure/typed block permanently closes this route.
- Links: `docs/06_results_log.md`; `outputs/SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1/`.

## ITER-20260812-S0-FAMDB-LEAF-CLOSE-ONLY-REPAIR

- Experiment: `SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1`; final one-shot Job `11534847`; isolated CPU component repair, claim-ineligible.
- Mechanism delta from Job `11533175`: scientific 6×12 exact-access probe unchanged; remove the read-mode write finalizer, freeze observations before cleanup, and explicitly close exactly 12 unique `leaf.file` handles under a termination-safe lifecycle.
- Allocation: `private-teodoro-gpu`, exact 1 CPU/4 GiB/10m/0GPU; `COMPLETED 0:0` in 25 seconds; peak RSS `83,432 KiB`.
- Result: `LEAF_CLOSE_ONLY_PASS`. All six frozen accessions resolved with exact expected identity/partition, 72/72 calls executed once, fallback count 0, and 12/12 HDF5 handles closed once without error. Terminal and observation manifests rehash exactly.
- Interpretation: component-level API/lifecycle feasibility is established. No annotation, RepeatMasker, catalog, homology, DATA, training or GPU work ran; S0 numerical quality and S1 remain unanswered.
- Next binding step: post-result tri-review/pivot. At most a new, separately reviewed CPU leaf-adapter preflight may be proposed; this consumed gate cannot be reused.
- Links: `docs/06_results_log.md`; `outputs/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/`.

## ITER-20260812-S0-FAMDB-LEAF-ADAPTER-PREFLIGHT

- Experiment: `SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1`; Job `11535362`; CPU-only six-record syntax component, claim-ineligible.
- Mechanism delta: build paired canonical-name and accession.version FASTA/header views from the same exact six leaf records, with output-derived manifests; no RepeatMasker or genome input.
- Allocation: `private-teodoro-gpu`, 1 CPU/4 GiB/10m/0GPU; `COMPLETED 0:0` in 20 seconds; MaxRSS `81,388 KiB`.
- Result: `LEAF_ADAPTER_PREFLIGHT_PASS`. Both views contain 6 records and have identical ordered sequence/class semantic hash; 72 exact calls and 12-handle cleanup close. DR empty-name fallback is explicit and correct.
- Interpretation: syntactic adapter component only; no annotation/concordance/geometry or model result. Post-result tri-review/pivot is required before any representative CPU proposal.
- Links: `docs/06_results_log.md`; `outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/`.
