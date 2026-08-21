# Tri-Review Log

> 由 tri-review append。每个 experiment_id 一段。
> Reviewer A=Claude CLI / B=Codex CLI / C=Antigravity CLI（agy，替代 Gemini）。
> 三方不是固定角色分工；每个 reviewer 都必须独立完整审阅 fairness、comparability、semantic success、leakage/reproducibility、architecture hypothesis、Track A/B decision、next SOTA step。
> 任一 reviewer 失败后重试一次；若仍失败,两方成功即可继续但标记 DEGRADED_REVIEW。

每个 entry 用 `# Tri-Review: <exp_id>` 开头。模板见 tri-review SKILL.md。

# Tri-Review: PIPE-TEFM-SUPP-20260617

Date: 2026-06-18

Verdict: PASS_WITH_WARNINGS.

Review summary:

- Semantic success: all requested runnable branches completed and produced parseable finite metrics. NTv3/Evo2 are blocked by local checkpoint adapter/code issues, not counted as failed model results.
- Fairness/comparability: acceptable only as a screen. The experiment is single-seed, token-level proxy, one-chromosome transfer evaluation, and uses quick `max_windows` truncation that can overrepresent the first eligible chromosome per split/species.
- Model/window decision: H0 window screen favors `ntv2_500m@4096`; B/C 2048 transfer mean favors `generanno`; 4096 paired transfer favors `ntv2_500m`. Keeping both `generanno` and `ntv2_500m` at window=4096 for bp-level follow-up is the defensible decision.
- Downstream interpretation: mouse-only transfer to close vertebrates is strong for both candidates; A2 mixture is reasonable on vertebrates but fails on held-out invertebrates. Do not continue automatic tuning for A2 invertebrate failure; it needs a design/pivot review.
- Fragmentation/edge handling: edge-position analysis shows real non-overlap boundary degradation, especially at 512 and some 1024 windows. For final prediction, implement overlap sliding plus center-weight merge before CRF/HMM or heuristic smoothing.
- Decay formula: ordinal distance vs TE-F1 is negatively correlated, but this is a sanity pattern only. The current data mix cannot support a formal decay formula because label-source quality, kingdom/domain shift, and coarse distance encoding are confounded.

Required caveats before any claim:

- Replace token proxy with bp-level/segment-level evaluator.
- Rebuild split sampling to avoid first-chromosome truncation artifacts.
- Validate overlap-merged prediction instead of non-overlap windows.
- Treat plant/invertebrate comparator coverage separately from vertebrate findings.

# Tri-Review: PIPE-TEFM-SEG-SF-20260618

Date: 2026-06-18

Verdict: PASS_WITH_WARNINGS.

Review summary:

- Semantic success: all requested branches completed with parseable finite outputs: 72 overlap/postprocess rows, 60 edge-bin rows, 2 superfamily result rows, and 48 embedding clustering result rows.
- Overlap/fragmentation conclusion: raw threshold preserves bp-F1 but leaves poor interval quality. HMM-style smoothing is the current best postprocess, with 4096 stride 2048 segment-F1@IoU0.5 0.7442 and boundary-F1@100bp 0.6261.
- Window decision: 4096 remains the defensible main setting. It is best for segment-level postprocess and outperforms 2048 in superfamily classification.
- Superfamily conclusion: the 4096 head improves TE detection and class macro-F1, but rare/Other class handling remains a screen caveat because Other has zero support in this test split.
- Embedding conclusion: C1 basic sequence features plus contrastive projection is a strong baseline and outperforms the current GENERanno embedding variants on balanced 128/256/512 bp fragments. Do not claim embedding superiority without beating C1 and auditing species/class stratification.
- Engineering reliability: retries were necessary for CRLF command parsing, 12 GB GPU OOM, and unsupported Blackwell GPU placement. These are now documented, but future runs should encode high-memory/exclude constraints directly in sbatch.

Required caveats before any claim:

- Segment and boundary metrics are still quick-screen single-chromosome/sampled evaluations, not final claim-bearing full-panel evaluation.
- HMM/heuristic smoothing improves intervals but must be audited for overmerge and cross-family bridge errors.
- Embedding C1 uses supervised contrastive labels on a train split and evaluates holdout assignment, so it is not a purely unsupervised biology claim.
- Superfamily classification should freeze a target-set contract and rare-class policy before publication-level evaluation.

# Tri-Review: PIPE-TEFM-REPAIR-20260618

Date: 2026-06-19

## Review mode

- Mode: independent_parallel_cli
- Prompt: one full-scope shared prompt plus compact retry prompt under `/tmp/tri_review_PIPE-TEFM-REPAIR-20260618/`
- Reviewer A: Claude CLI · failed after 3 attempts. It produced advisory text, but did not satisfy the required structured `Overall judgment` validation and mislabeled reviewer identity; raw outputs are preserved but not counted toward quorum.
- Reviewer B: Codex CLI · success
- Reviewer C: Antigravity CLI · failed after 3 attempts because `agy` requires Google OAuth login.
- Quorum: `1/3 SINGLE_REVIEW_CONTINUATION`
- Confidence: Low, by workflow rule. This entry cannot support SOTA claim, abandon-route, goal revision, or benchmark revision.
- manual_intervention_recommended: true

## Inputs

- Experiment: `PIPE-TEFM-REPAIR-20260618`
- Track: Track A screen / bounded Discovery
- Resource profile: screen
- Current metric: `invert_boost_animal_4096` B-panel mean TE-F1 0.9351; A1 mean TE-F1 0.8985; A2 all-species mean TE-F1 0.5750; segment-F1@IoU0.5 0.7339 with threshold 0.35 + `hmm_penalty2`; superfamily main4 macro-F1 0.8927.
- SOTA metric: absent / not configured in ACTIVE_GOAL; screen profile cannot claim.
- Gap: unknown.

## Reviewer B · Codex

Judgment: `scale-to-track-b`.

Compact summary:

- Semantic success is strong: summary TSVs are parseable, numeric metrics are finite, and run artifacts/logs are sufficient for a screen-level result.
- The low A2 mixed-animal mean is not evidence of a global animal-model failure. It is driven by beetle/honeybee and distant stress species; close vertebrates and training-domain animal species are strong.
- `invert_boost_animal_4096` is the best no-human animal branch for promotion: B-panel mean TE-F1 0.9351 and A1 mean TE-F1 about 0.8985.
- HMM/postprocess is a real architecture/decoder result, not cosmetic tuning: raw threshold keeps bp-F1 high but segment and boundary metrics collapse.
- Superfamily should be claimed only for the main four TE superfamilies for now; `Other` class is a known failure.
- Representation work should not continue with binary token fine-tuned embeddings alone; C1 and A1 are the baselines to beat.

Reviewer B next action:

> Start a Track B comparability-lock validation run: freeze data version, chromosome split, RepeatMasker/Dfam version, windowing, threshold 0.35 + `hmm_penalty2` inference protocol, and run GENERanno 4096 on the main vertebrate/B-panel. Treat beetle/honeybee as independent diagnostic appendix, not part of the main mean claim.

## Reviewer A · Claude

Failed-after-retry. Raw outputs contain useful advisory text but are not counted as an independent reviewer because they failed the required structural validation. Main advisory content was broadly consistent with Reviewer B: continue/scale the current GENERanno 4096 direction, lock benchmark comparability before claim, and treat honeybee/beetle as label/source stress diagnostics.

## Reviewer C · Antigravity

Failed-after-retry. `agy` requested Google OAuth login and timed out on all attempts. It contributed no valid review.

## Cross-reviewer agreement

- Only one valid reviewer succeeded, so there is no formal cross-reviewer consensus.
- The failed Claude advisory output is directionally consistent with the valid Codex review, but it is not counted toward quorum.

## Disagreements

- No valid multi-reviewer disagreement can be assessed because quorum is 1/3.

## Aggregated recommendation to pivot

- [ ] Continue current route
- [ ] Tune current architecture
- [x] Scale to Track B, but only as a non-claim comparability-lock validation run
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [ ] Sanity check first
- [ ] Comparability blocker first
- [ ] Abandon route
- [ ] Return to literature

## Required prerequisites before next run

- [ ] Freeze the data version, split manifest, Label-A source, and RepeatMasker/Dfam version used for the validation panel.
- [ ] Freeze the inference protocol: GENERanno 4096, overlap/center merge, threshold 0.35, and `hmm_penalty2`.
- [ ] Define the primary claim panel separately from stress diagnostics. Beetle/honeybee should be diagnostic appendix unless label-source repair is explicitly tested.
- [ ] Freeze the superfamily target policy: main four TE superfamilies can be primary; `Other` remains excluded or reject/unknown until repaired.
- [ ] Do not claim SOTA from the next run unless ACTIVE_GOAL/SOTA benchmark and docs/19 comparability contract are repaired first.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-REPAIR-20260618/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-REPAIR-20260618/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-REPAIR-20260618/output_c_antigravity.md`
- `/tmp/tri_review_PIPE-TEFM-REPAIR-20260618/quorum.txt`

# Tri-Review: PIPE-TEFM-EXTEND-20260620

Date: 2026-06-21

## Review mode

- Mode: degraded host self-review plus council synthesis.
- Reason for degradation: external multi-agent review quorum was not available in this closing pass. This entry is not an independent 2/3 or 3/3 tri-review.
- Quorum: `0/3 DEGRADED_SELF_REVIEW`
- Confidence: Low, by workflow rule. This entry cannot support SOTA claim, abandon-route, ACTIVE_GOAL revision, or benchmark revision.
- manual_intervention_recommended: true before any claim-grade promotion.

## Inputs

- Experiment: `PIPE-TEFM-EXTEND-20260620`
- Track: Track A screen / bounded discovery
- Resource profile: screen
- Result-log: `docs/06_results_log.md#result-pipe-tefm-extend-20260620`
- Final report: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/FINAL_REPORT.md`
- Current metrics: plant eval-only mean TE-F1 0.7269 for `invert_boost`; cross-eval mean TE-F1 0.5914 for `invert_boost`; SF5 TE-F1 0.8982; SF5 main4 conditional macro-F1 0.8547; Unknown recall 0.3957; best decay R2 0.5249.
- SOTA metric: absent / not configured in ACTIVE_GOAL; screen profile cannot claim.

## Host self-review

Judgment: `continue-current-route` with claim lock required.

Key findings:

- Semantic success passes for screen: all requested train/eval/segment/embedding/formula/summary jobs completed, summary files are parseable, and final logs have no failure signatures.
- `invert_boost_animal_4096` remains the strongest broad annotation branch. It transfers better than plant/cross PU in most aggregate metrics and has usable plant performance in several species.
- Plant/cross positive-only and PU branches overcall TE because they lack reliable negatives. TV and HMM/CRF-style smoothing reduce fragmentation but do not repair the precision problem enough for a primary route.
- Base-pretrained SF5 supports the main4+Unknown/reject design and replicates the previous Unknown-recall advantage over binary-H0 initialization.
- Family-level embedding remains conservative: A1 pretrained GENERanno + contrastive is useful, but C1 basic sequence features + contrastive is stronger. Do not claim model embedding superiority yet.
- Dfam consensus vs genomic source comparison is incomplete because the consensus FASTA was missing. This is a data-source blocker, not a model result.
- Generalization decay formula improves when label-concordance variables are added, so any paper-level decay model must include annotation completeness/source variables rather than genetic distance alone.

## Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | Pass for screen | Uses current ready-by-design entrypoint and recorded run outputs. |
| Official split / same split | Screen only | One-chromosome / capped-window screens are not claim-grade. |
| Metric implementation | Pass for screen | TSV/JSON summaries are parseable and finite. |
| Preprocessing | Pass for screen | Dfam consensus branch explicitly skipped when source missing. |
| External weights / pretrained backbone version | Pass for screen | GENERanno 4096 route and `invert_boost` reuse are recorded. |
| Test-time inference protocol | Screen only | Transfer and PU comparisons are useful but not locked full-panel inference. |
| Resource profile supports claim? | Fail | Single seed screen with draft ACTIVE_GOAL/docs19/docs20. |

## Aggregated recommendation to pivot

- [x] Continue current route
- [ ] Tune current architecture
- [ ] Scale to Track B now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [ ] Sanity check first
- [x] Comparability blocker first before claim
- [ ] Abandon route
- [ ] Return to literature

## Required caveats before any claim

- Supply and audit a Dfam consensus FASTA before claiming consensus-vs-genomic embedding differences.
- Freeze primary/stress panels and do not average beetle/honeybee/low-concordance plants into one headline mean.
- Add reliable RN/hardN negatives or calibrated thresholding before retrying PU as a primary training route.
- Keep C1/A1 embedding baselines and leak-free split controls.
- Repair ACTIVE_GOAL, docs/19 evaluator contract, and docs/20 baseline ledger before claim-grade validation.

# Tri-Review: PIPE-TEFM-CALIB-20260621

Date: 2026-06-21

## Review mode

- Mode: degraded host synthesis plus prior council constraints.
- Reason for degradation: this closeout is a screen result and external independent reviewer quorum was not re-run to completion in this pass. The entry is an audit trail and next-step recommendation, not independent claim support.
- Quorum: `0/3 DEGRADED_SELF_REVIEW`
- Confidence: Low, by workflow rule. This entry cannot support SOTA claim, route abandonment, ACTIVE_GOAL revision, or benchmark revision.
- manual_intervention_recommended: true before any claim-grade promotion.

## Inputs

- Experiment: `PIPE-TEFM-CALIB-20260621`
- Track: Track A screen / calibration supplement
- Resource profile: screen
- Result-log: `docs/06_results_log.md#result-pipe-tefm-calib-20260621`
- Final report: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`
- Current metrics: `cross_supervised_4096` broad mean TE-F1 0.5786; `animal_invert_boost` broad mean TE-F1 0.5413; `cross_supervised_to_plant_fine` mean TE-F1 0.8568; insect-no-beetle honeybee TE-F1 0.7983 and beetle 0.0059; Dfam consensus A1 ARI 0.2242 vs C1 ARI 0.7083; full decay formula R2 0.7407.
- SOTA metric: absent / not configured in ACTIVE_GOAL; screen profile cannot claim.

## Host self-review

Judgment: `continue-current-route` with panel-specific branch carry-forward and claim lock required.

Key findings:

- Semantic success passes for screen: all requested prep/train/eval/embedding/formula/summary stages completed, all expected outputs are present, numeric metrics are finite, and final logs have no failure signatures.
- Standard supervised plant/cross training should replace PU as the main plant/cross calibration evidence. It improves plant held-out species and validates the user's critique that PU comparison alone was not meaningful.
- `cross_supervised_4096` is the best broad mean and best plant-fine branch, but `animal_invert_boost` remains slightly stronger on broad cross-eval and stress means. Results must be reported by panel rather than as one universal average.
- `insect_no_beetle_4096` is useful for honeybee but not beetle. This supports honeybee as calibratable domain/label shift and beetle as hard label/library/domain failure.
- Direct honeybee/beetle base-pretrained fixed-threshold fine-tunes are not successful recovery results. Honeybee has AUPRC signal; beetle does not.
- Dfam consensus family-level embedding is now complete. A1 improves over A0, but C1 remains dominant; no FM embedding superiority claim.
- Extended decay formula strongly supports source-aware explanatory variables. Distance-only decay is too weak.

## Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | Pass for screen | Uses current ready-by-design entrypoint and recorded run config. |
| Official split / same split | Screen only | One-chromosome/capped-window protocol is not claim-grade. |
| Metric implementation | Pass for screen | JSON/TSV summaries are parseable, finite, and complete. |
| Preprocessing | Pass for screen | Dfam consensus source is now present and executed. |
| External weights / pretrained backbone version | Pass for screen | GENERanno base and `invert_boost` paths are recorded. |
| Test-time inference protocol | Screen only | Transfer eval is useful, but claim-grade panel/inference contract remains draft. |
| Resource profile supports claim? | Fail | Single seed screen with draft ACTIVE_GOAL/docs19/docs20. |

## Aggregated recommendation to pivot

- [x] Continue current route
- [ ] Tune current architecture
- [ ] Scale to Track B now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability blocker first before claim
- [ ] Sanity check first
- [ ] Abandon route
- [ ] Return to literature

## Required caveats before any claim

- Pre-register primary and stress panels; do not average beetle/honeybee/low-concordance plants into one headline mean.
- Keep cross-supervised and animal invert-boost as complementary branches until a locked Track B validation chooses the claim branch.
- PU remains abandoned as primary unless reliable RN/hardN negatives and U-control are added.
- Keep C1 and A1 baselines for any representation claim.
- Keep label/source variables in decay formula and present it as descriptive until validated on locked panels.

# Tri-Review: PIPE-TEFM-ANCHOR-20260621

Date: 2026-06-22

## Review mode

- Mode: degraded host synthesis plus prior 3/3 council constraints.
- Reason for degradation: this closeout reviews a completed screen and does not rerun independent external CLI reviewers. It is an audit trail and next-step recommendation, not independent claim support.
- Quorum: `0/3 DEGRADED_SELF_REVIEW`
- Confidence: Low, by workflow rule. This entry cannot support SOTA claim, route abandonment, ACTIVE_GOAL revision, or benchmark revision.
- manual_intervention_recommended: true before any claim-grade promotion.

## Inputs

- Experiment: `PIPE-TEFM-ANCHOR-20260621`
- Track: Track A screen / anchor-selector supplement
- Resource profile: screen
- Council basis: `docs/00_active_goal.md#council_2026-06-21_anchor_selector`
- Result-log: `docs/06_results_log.md#result-pipe-tefm-anchor-20260621`
- Final report: `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/FINAL_REPORT.md`
- Current metrics: `insect_primary_4096` stress mean TE-F1 0.5197; honeybee TE-F1 0.9465; red flour beetle remains about 0.003-0.006 across anchors; BG+main4 C1 ARI 0.8353 vs A1 ARI 0.4067; Unknown/high-score C1 ARI 0.8600 vs A1 ARI 0.4049; Unknown segments mean best-main4 fraction 0.4706; high-score strict-BG candidates mean BG fraction 0.9974; deployable random forest R2 0.7631 with leave-species-out RMSE 0.3467.
- SOTA metric: absent / not configured in ACTIVE_GOAL; screen profile cannot claim.

## Host self-review

Judgment: `continue-current-route` with panel-specific anchor reporting and claim lock required.

Key findings:

- Semantic success passes for screen: accepted prep/train/diagnostic/eval/embedding/SF5 retry/formula/summary stages completed, metric files are parseable, and the only failed SF5 job was superseded by a successful CPU retry.
- The anchor recommendation should be panel-specific. `insect_primary_4096` recovers honeybee strongly, while existing animal/cross branches remain appropriate for other panels.
- Red flour beetle remains a hard stress failure across anchors. It should not enter headline primary means until label/library/domain evidence is repaired.
- Unknown annotations have main4-like signal under SF5, especially DNA/SINE-like calls, but the mixture of main4, BG, and Unknown means this is an audit queue rather than automatic relabeling.
- High-score strict-background candidates are not supported as hidden TE discoveries in this screen because SF5 calls them almost entirely BG.
- Background-inclusive embedding does not rescue the FM embedding superiority claim. C1 basic sequence/kmer features plus contrastive remain stronger than GENERanno embedding plus contrastive.
- The deployable anchor selector is promising as a screen, but leave-species-out error is too large for a stable deployment claim. Annotation-aware variables are explanatory controls only.

## Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | Pass for screen | Uses current ready-by-design entrypoint and recorded run config. |
| Official split / same split | Screen only | One-chromosome/capped-window protocol is not claim-grade. |
| Metric implementation | Pass for screen | JSON/TSV summaries are present and parseable. |
| Preprocessing | Pass for screen | Unknown/high-score/BG diagnostics are separated from binary eval and embedding summaries. |
| External weights / pretrained backbone version | Pass for screen | GENERanno 4096 branches and reused model paths are recorded. |
| Test-time inference protocol | Screen only | Selector evidence is exploratory; deployment protocol is not locked. |
| Resource profile supports claim? | Fail | Single seed screen with draft ACTIVE_GOAL/docs19/docs20. |

## Aggregated recommendation to pivot

- [x] Continue current route
- [ ] Tune current architecture
- [ ] Scale to Track B now
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [x] Comparability blocker first before claim
- [ ] Sanity check first
- [ ] Abandon route
- [ ] Return to literature

## Required caveats before any claim

- Report animal/vertebrate, plant/cross, and insect-primary anchors separately; do not average them into one universal headline mean.
- Keep beetle as stress/audit unless label/library evidence is repaired.
- Treat Unknown/high-score unannotated calls as candidate audit, not corrected labels or novel TE discovery.
- Keep C1 as the mandatory embedding baseline.
- Validate any deployable selector on locked held-out panels and avoid target TE-annotation-derived variables.

---

# Tri-review: S FamDB leaf close-only component PASS — Job 11534847

Date: 2026-08-12 CEST. Experiment: `SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1`.

## Review mode and quorum

- Reviewer A: Claude CLI, valid `PASS`, action=`continue-current-route`, confidence High.
- Reviewer B: independent separate Codex reviewer, valid `PASS_WITH_WARNINGS`, action=`continue-current-route`, confidence High. The external Codex CLI was also attempted three times but its account usage limit stopped every attempt before review.
- Reviewer C: Antigravity invalid after three bounded attempts (`--print-timeout` unrelated text or headless command denial).
- Quorum: `2/3 DEGRADED_REVIEW`; confidence capped at Medium by workflow policy despite both valid reviewers reporting High.

## Shared judgment

- The component result is trustworthy: 72/72 exact-once calls cover six frozen accessions across 12 partitions, with 0 fallback and exact accession/name/class/length/consensus-hash matches.
- The lifecycle/result closure is trustworthy: observations were frozen before cleanup; 12/12 unique HDF5 handles closed once; terminal, observation, source and scheduler hashes reconcile.
- The stale `ACTIVE_GOAL` selector/decoder failure is an automation/schema stop, not contradictory scientific evidence.
- The result establishes only leaf exact access and read cleanup. It does not establish header/library export, RepeatMasker geometry, representative/full annotation, homology-safe DATA or model quality.

## Aggregated recommendation

`continue-current-route`, but only to **one new, separately implemented and fresh-reviewed CPU leaf-adapter preflight proposal using the same six records**. The Job `11534847` gate is consumed. No representative/full annotation, RepeatMasker benchmark run, homology construction, DATA materialization, GPU direct S0, hierarchical S1 or claim is authorized.

Raw review pack: `reports/tefm_new_directions/SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1/job_11534847_tri_review/`.

# Tri-review: S six-record leaf-adapter syntactic PASS — Job 11535362

Date: 2026-08-12 CEST. Experiment: `SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1`.

- Reviewer A (Claude): valid `PASS_WITH_WARNINGS`, action=`continue-current-route`, confidence High.
- Reviewer B (separate Codex): valid `PASS_WITH_WARNINGS`, action=`continue-current-route`, confidence High. External Codex CLI was quota-blocked on three attempts.
- Reviewer C (Antigravity): invalid after three bounded attempts.
- Quorum: `2/3 DEGRADED_REVIEW`; workflow confidence capped at Medium.

Both valid reviewers accept the six-record syntactic component result: exact scheduler facts, 72 exact calls/0 fallback, 12-handle cleanup, identical ordered sequence/raw-class semantics, correct DR empty-name fallback, output-derived record manifest and exact-set hash closure. Both explicitly reject any interpretation as representative concordance, RepeatMasker compatibility, annotation geometry, DATA readiness or model quality.

Aggregated action is `continue-current-route`, but only to make **one new representative CPU proposal** human-gate eligible. That proposal requires a new exp/contract/implementation/fresh review/smart-sbatch and cannot reuse the consumed gate. It cannot execute until the stale `ACTIVE_GOAL` schema is reconciled through the human-gated goal revision process. No RepeatMasker, representative/full annotation, catalog, homology, DATA, training, GPU S0, S1 or claim is authorized by this review.

Raw pack: `reports/tefm_new_directions/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/job_11535362_tri_review/`.

# Tri-Review: PIPE-TEFM-FINAL-20260623

Date: 2026-06-29

## Review mode

- Mode: independent_parallel_cli
- Prompt: one self-contained full-scope prompt shared by all reviewers; only reviewer identity differed.
- Reviewer A: Claude CLI · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-20260623/output_a_claude.md`
- Reviewer B: Codex CLI · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-20260623/output_b_codex.md`
- Reviewer C: Antigravity (`agy`) · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-20260623/output_c_antigravity.md`
- Quorum: `3/3`
- Confidence: High for screen-to-Track-B promotion; no SOTA claim.

## Inputs

- Experiment: `PIPE-TEFM-FINAL-20260623`
- Track: Track A screen / model-size-window matrix closeout
- Resource profile: screen
- Result-log: `docs/06_results_log.md#result-pipe-tefm-final-20260623-ntv3-recovery-and-model-size-matrix-closure`
- Matrix summary: `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`
- Current metrics: human H0 best `ntv2_250m@4096` TE-F1 0.93494; animal_fine mean best `ntv2_250m@4096` TE-F1 0.64823; plant_fine mean best `ntv3_100m_pre@2048` TE-F1 0.39802; combined animal+plant diagnostic mean best `ntv3_100m_pre@2048` TE-F1 0.49850.
- SOTA metric: absent / not claimable from this screen.

## Reviewer A · Claude

Judgment: `scale-to-track-b`.

Key recommendations:

- Promote the matrix results to chromosome-repeat validation; do not continue broad screen or tune hyperparameters.
- Carry forward `ntv2_250m@4096` and `ntv2_250m@2048` for NTv2 window stability, plus `ntv3_100m_pre@2048` as the plant challenger.
- Treat `ACTIVE_GOAL`/SOTA benchmark and evaluator contract as blockers before any claim.
- Add plant label-concordance audit and strict segment/boundary/fragmentation metrics before publication-facing claims.

## Reviewer B · Codex

Judgment: `scale-to-track-b`.

Key recommendations:

- Minimal promotion set: `ntv2_250m@4096` for human/animal and `ntv3_100m_pre@2048` for plant.
- Build a panel-specific multi-anchor selector rather than a single universal model.
- Freeze NTv3 single-base token-label mode and rotary-cache filtering in the reproducibility contract.
- Do not treat the combined animal+plant mean as headline evidence.

## Reviewer C · Antigravity

Judgment: `scale-to-track-b`.

Key recommendations:

- Promote both `ntv2_250m@4096` and `ntv3_100m_pre@2048` to Track B multi-chromosome evaluations.
- Optional fallback only if needed: `ntv2_250m@8192`; do not expand the whole matrix.
- Add strict segment/boundary/fragmentation metrics and keep stress species isolated from primary means.
- The screen is semantically successful and the NTv3 runtime repairs are accepted.

## Cross-reviewer agreement

- 3/3 reviewers recommend `scale-to-track-b`.
- No reviewer supports more broad model/window screening or hyperparameter tuning.
- All reviewers agree the result supports panel-specific anchors: NTv2-250M/4096 for human/animal and NTv3-100M-pre/2048 for plant.
- All reviewers agree this is screen evidence only; chromosome-repeat error bars and locked evaluator/comparability contracts are required before claim language.

## Disagreements

- Candidate breadth: Claude recommends including `ntv2_250m@2048` as a stability/shared-anchor check; Codex and Antigravity prefer the minimal two-candidate set and keep extra NTv2 windows optional.
- `ntv2_250m@8192`: Antigravity names it as an optional fallback; Claude explicitly deprioritizes it because cost/OOM risk is not justified by a tiny screen gain.

## Aggregated recommendation to pivot

- [ ] Continue current route
- [ ] Tune current architecture
- [x] Scale to Track B
- [ ] Replace component
- [ ] Change backbone
- [ ] Change objective / loss
- [ ] Sanity check first
- [x] Comparability/evaluator contract before claim
- [ ] Abandon route
- [ ] Return to literature

## Required prerequisites before next claim-bearing run

- [ ] Lock bp-level and strict segment/boundary/fragmentation evaluator contract.
- [ ] Run chromosome-repeat error bars for promoted candidate(s), using different chromosomes rather than extra seeds.
- [ ] Keep animal and plant panels separated in reporting and routing.
- [ ] Preserve NTv3 tokenizer/checkpoint-load runtime repairs in the reproducibility contract.
- [ ] Do not use failed/superseded eval arrays `9844255`/`9844256` as evidence.

## Confidence

High for promotion to repeat validation; low/none for SOTA claim because this is a single-seed, one-chromosome screen.

---

# Tri-Review: PIPE-TEFM-FINAL-INTERPRET-20260630

Date: 2026-06-30

## Review mode

- Mode: independent_parallel_cli
- Prompt: focused screen-level prompt for the short-fragment interpretability result.
- Reviewer A: Claude CLI · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-INTERPRET-20260630/output_a_claude.md`
- Reviewer B: Codex CLI · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-INTERPRET-20260630/output_b_codex.md`
- Reviewer C: Antigravity (`agy`) · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-INTERPRET-20260630/output_c_antigravity.md`
- Quorum: `3/3`
- Confidence: High for screen interpretation; no claim support.

## Inputs

- Experiment: `PIPE-TEFM-FINAL-INTERPRET-20260630`
- Track: publication-validation support screen.
- Result-log: `docs/06_results_log.md#result-pipe-tefm-final-interpret-20260630`
- Report: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/INTERPRETABILITY_REPORT.md`
- Status: `reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/current_status.json`
- Current metrics: 9 high-score strict-BG rows, mean binary TE probability 0.8893 and mean SF5 BG fraction 0.9974; 260 Unknown rows, mean best-main4 SF5 fraction 0.4706.

## Reviewer A · Claude

Judgment: `run-sanity-check-first`.

Key recommendations:

- Do not interpret the 9 strict-BG candidates as hidden TE. They are all from `western_honey_bee GroupUn`, are AT-rich/low-complexity, and have SF5 BG fraction near 1.0.
- Continue the Unknown annotation branch only with matched controls because Unknown rows are high-GC and may be confounded.
- Build same-species/same-chromosome/GC-matched controls before saliency or manuscript wording.
- Complete PDF method alignment before external interpretability claims.

## Reviewer B · Codex

Judgment: `run-sanity-check-first`.

Key recommendations:

- The strict-BG branch is likely a binary-head artifact or composition trigger, not hidden TE evidence.
- Unknown fragments support an annotation-audit candidate pool, not automatic relabeling.
- Add matched BG controls, saliency/occlusion, k-mer motif enrichment, and coordinate-level RepeatMasker/Dfam/UCSC audit for top Unknown-main4-like cases.
- Repeat tri-review after attribution analyses if this becomes claim-grade.

## Reviewer C · Antigravity

Judgment: `run-sanity-check-first`.

Key recommendations:

- Pause hidden-TE language for strict-BG candidates; SF5 almost entirely rejects them as main4 TE.
- Shift emphasis to Unknown sequence audit, where the signal is stronger and sample size is larger.
- Install a PDF text parser and align the analysis with the three referenced methods before claiming interpretability.
- Use strict matched controls for saliency/occlusion and k-mer enrichment.

## Cross-reviewer agreement

- 3/3 reviewers reject a hidden-TE claim from the 9 high-score strict-BG candidates.
- 3/3 reviewers support Unknown-main4-like fragments as the better annotation-audit follow-up.
- 3/3 reviewers require matched controls before mechanistic interpretation.
- 3/3 reviewers agree this is screen evidence only and should not support SOTA, novel TE discovery, or annotation-correction claims.

## Disagreements

- Reviewer A recommends parking the high-score strict-BG branch until matched controls exist; Reviewers B/C phrase it as continue only as a false-positive/interpretability sanity check.
- Reviewer A emphasizes the `western_honey_bee GroupUn` single-source confound more strongly; Reviewers B/C emphasize SF5 disagreement and sample size.

## Aggregated recommendation

- [ ] Continue current route as claim-ready
- [x] Run sanity check first
- [ ] Tune current architecture
- [ ] Replace component
- [ ] Change objective / loss
- [ ] Comparability blocker
- [ ] Abandon route
- [ ] Return to literature

## Required prerequisites before claim-grade interpretability

- [ ] Build matched strict-BG controls by species/chromosome/GC/entropy/low-complexity features.
- [ ] Build matched human known-main4 controls for Unknown-main4-like candidates.
- [ ] Run saliency/occlusion and k-mer motif enrichment on both contrasts.
- [ ] Complete PDF method alignment for the three referenced inputs.
- [ ] Repeat tri-review after these analyses if the branch is promoted to a manuscript claim.

## Confidence

High for the conservative screen interpretation; none for hidden-TE discovery or formal annotation correction claims.

---

# Tri-Review: PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630

Date: 2026-06-30

## Review mode

- Mode: independent_parallel_cli
- Prompt: one identical full-scope prompt covering deployable generalization decay / anchor selector, strict segment-fragmentation, and short-fragment interpretability.
- Reviewer A: Claude CLI · failed/degraded · first output lacked required `Overall judgment`; retry stalled and was manually stopped after Reviewer B/C succeeded.
- Reviewer B: Codex CLI · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630/output_b_codex.md`
- Reviewer C: Antigravity (`agy`) · success · raw output `/tmp/tri_review_PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630/output_c_antigravity.md`
- Quorum: `2/3 DEGRADED_REVIEW`
- Confidence cap: Medium.

## Inputs

- Experiments reviewed: `PIPE-TEFM-FINAL-SELECTOR-20260630`, `PIPE-TEFM-FINAL-STRICTSEG-20260629`, `PIPE-TEFM-FINAL-INTERPRET-20260630`
- Track: publication-validation support screen / non-claim meta-review.
- Current selector metric: deployable RF in-sample R2 `0.8203`, leave-species-out RMSE `0.3040`; annotation-aware control leave-species-out RMSE `0.2791`.
- Current strict segment metric: animal `ntv2_250m@4096 + crf_style_penalty4`, IoU `0.8`, boundary `5bp`: bp-F1 `0.6453`, segment-F1 `0.2557`, boundary-F1 `0.0989`; plant `ntv3_100m_pre@2048 + gap100_min100`: bp-F1 `0.4585`, segment-F1 `0.0305`, boundary-F1 `0.0033`.
- Current interpretability metric: strict-BG hidden-TE branch rejected by SF5/occlusion; Unknown-main4-like branch has SF5 sensitivity but poor GC-matched controls.

## Reviewer B · Codex

Judgment: `replace-component`.

Key recommendations:

- Do not keep tuning thresholds/gap merge as the main answer to strict segment failure. The limiting component is the bp-probability-to-interval decoder/objective.
- Add a boundary-aware multi-task head, interval proposal/refinement stage, or learned duration-aware decoder such as semi-Markov/HMM/CRF with explicit duration and boundary constraints.
- Selector is useful but should be upgraded with deployable genome-only features beyond the current distance/GC/group proxies: k-mer or Mash/sourmash distance, GC/k-mer shift, genome size, N50, and unsupervised repeat-landscape proxies.
- Interpretability should not continue as a hidden-TE branch. Unknown-main4-like fragments can remain an annotation-audit branch only after better GC-matched controls and coordinate-level audit.

## Reviewer C · Antigravity

Judgment: `replace-component`.

Key recommendations:

- Current strict segment and boundary gap is too large for tuning; replace or augment the decoder/head with a structure-aware decoder and boundary-aware objective.
- Add pure-genome feature extraction to the anchor selector, especially whole-genome k-mer shift and Mash/sourmash MinHash signatures. The goal is to approximate the benefit of annotation-aware variables without using target annotations.
- Do not promote any part to claim-facing Track B now because plant labels are strongly confounded and segment metrics are weak.
- Interpretability currently hits GC bias; strict-BG spikes should be treated as false-positive/context-trigger diagnostics, not hidden TE discovery.

## Cross-reviewer agreement

- 2/2 successful reviewers choose `replace-component`.
- 2/2 agree the next useful iteration is not optimizer tuning and not more threshold sweeping.
- 2/2 prioritize a segment-aware decoder/refiner for task 6.
- 2/2 recommend enriching the deployable selector with genome-only features such as k-mer/Mash/sourmash and assembly/genome statistics.
- 2/2 agree task 7 should not be promoted as a hidden-TE or annotation-correction claim; at most it remains a controlled annotation-audit/false-positive-analysis branch.

## Disagreements

- Reviewer B frames the next segment step as a frozen-bp-model interval refiner or boundary-aware decoder with strict segment metrics as the validation objective.
- Reviewer C puts slightly more emphasis on the selector feature-engineering iteration as the immediate low-cost experiment.
- Both are compatible: run selector feature enrichment cheaply, and only then spend GPU on a segment-aware refiner if the segment claim remains important.

## Aggregated recommendation to pivot

- [ ] Continue current route unchanged
- [ ] Tune current architecture
- [ ] Scale to Track B
- [x] Replace component: segment/boundary decoder or interval refiner
- [ ] Change backbone
- [x] Change objective / loss: boundary-aware / duration-aware / interval-level objective
- [x] Sanity check first: enrich deployable selector with genome-only features and nested leave-species-out validation
- [ ] Comparability blocker first
- [ ] Abandon route
- [ ] Return to literature

## Required prerequisites before next run

- [ ] For decay/selector: add deployable genome-only features that do not require target TE annotations: k-mer spectra, Mash/sourmash/MinHash distances to anchors, GC/k-mer shift, genome size, N50/contiguity, optional public phylogenetic distance table if available.
- [ ] Evaluate selector with nested leave-species-out or leave-clade-out, not only in-sample RF importance.
- [ ] For strict segment: freeze the bp model and test a small interval refiner/decoder using bp probabilities plus local sequence/genome features; score on IoU `0.8/0.9` and boundary `5/10/25bp`.
- [ ] Keep plant strict segment claims separate until label-source confounding is handled.
- [ ] For interpretability: stop hidden-TE language; only continue if better GC-matched controls and coordinate-level RepeatMasker/Dfam/UCSC audit are available.

## Confidence

Medium. Reviewer quorum is `2/3 DEGRADED_REVIEW`, and the reviewed evidence is screen/support rather than claim-grade. The recommendation is nevertheless robust for non-claim planning because both successful reviewers independently converge on the same component-level diagnosis.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630/output_c_antigravity.md`
---

# Council / Tri-Review Addendum: PIPE-TEFM-FINAL-GENOMEDECAY-20260630

Date: 2026-06-30

## Review mode

- Mode: targeted council plus prior tri-review carry-forward.
- Prompt: `pipelines/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/fragment_council_prompt.md`.
- Claude CLI: success, raw output `/tmp/fragment_council_20260630_claude.md`.
- Codex CLI: success after retry; first sandbox snapshot warning was non-blocking, raw output `/tmp/fragment_council_20260630_codex.md`.
- Antigravity CLI: success after prompt retry, raw output `/tmp/fragment_council_20260630_agy.md`.
- Quorum: `3/3`.

## Inputs

- Strict segment result: `PIPE-TEFM-FINAL-STRICTSEG-20260629`.
- Genome selector addendum: `PIPE-TEFM-FINAL-GENOMEDECAY-20260630`.
- Prior degraded tri-review: `PIPE-TEFM-FINAL-DECAY-SEG-INTERPRET-REVIEW-20260630`, which already recommended replacing the segment/boundary component and enriching deployable selector features.

## Consensus

- 3/3 reviewers agree strict fragmentation is primarily an interval-structure problem, not a threshold/gap/HMM/CRF tuning problem.
- 3/3 reviewers recommend a learned or structured interval/boundary component. The most practical first step is a frozen bp model plus lightweight interval refiner; boundary-aware multi-task head is the next training-level option.
- 3/3 reviewers treat double-strand prediction as a cheap sanity check only. It may expose strand asymmetry, but simple OR/union can inflate false positives and is unlikely to solve internal TE probability valleys by itself.
- 3/3 reviewers require guardrail metrics proving that fragment reduction preserves true-backed short TE rather than deleting them.

## Selector review addendum

The genome-derived selector screen supports the earlier reviewer request for pure genome features:

- bounded k-mer shift improves leave-species-out RMSE from `0.3042` to `0.2666`;
- assembly stats alone worsen RMSE to `0.3441`;
- Mash/sourmash remain unavailable and should be installed/versioned before claim-grade selector work.

## Aggregated recommendation

- [x] Replace component: interval refiner or boundary-aware head.
- [x] Run sanity check first: double-strand forward/RC merge and oracle gap upper bound.
- [x] Enrich deployable selector with genome-wide k-mer/Mash/sourmash before claim-grade anchor selection.
- [ ] Continue threshold/gap/HMM/CRF tuning as primary route.
- [ ] Promote hidden-TE or segment-complete claims.

## Links

- summary report: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/FRAGMENT_COUNCIL_REPORT.md`
- selector report: `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/GENOME_DECAY_REPORT.md`

---

# Tri-Review: PIPE-TEFM-NEXT-DECAY-FRAG-20260630

Date: 2026-06-30

## Review mode

- Mode: independent_parallel_cli plus council route review.
- Prompt: `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success.
- Reviewer C: Antigravity CLI · success.
- Quorum: `3/3`.

## Inputs

- Previous selector evidence: `PIPE-TEFM-FINAL-SELECTOR-20260630`, `PIPE-TEFM-FINAL-GENOMEDECAY-20260630`.
- Previous fragmentation evidence: `PIPE-TEFM-FINAL-FRAGSANITY-20260630`, `PIPE-TEFM-FINAL-INTERVALREFINER-20260630`.
- New user request: make the generalization selector usable for new-species trust guidance and replace post-hoc HMM/CRF smoothing with trainable/structural fragmentation components.

## Reviewer consensus

- 3/3 reviewers agree the current selector is only partially usable. It has genome-derived signal, but point TE-F1 prediction is not reliable enough for deployment trust.
- 3/3 reviewers recommend evaluating anchor top-1/top-2 accuracy, regret, calibrated risk bins, uncertainty coverage, abstention/new-anchor triggers, and leave-clade-out splits.
- 3/3 reviewers agree fragmentation is a component/objective problem, not a penalty-tuning problem. The next useful work is trainable boundary/interval decoding, not more post-hoc CRF/HMM grid search.
- Reviewers differ on exact priority: Claude emphasizes trainable CRF first; Codex emphasizes segment-aware decoder and stronger interval scorer first; Antigravity emphasizes boundary head + trainable CRF + conformal selector. All agree strict truth-backed guardrails are mandatory.

## Council synthesis

- Council round 1 and round 2 completed with 3/3 outputs.
- Final synthesis: do not launch one large coupled project. Run independent MVPs:
  - selector: risk/abstention/top-k regret first, calibration only after leave-clade-out signal is acceptable;
  - fragmentation: lightweight but structural boundary/interval MVPs with strict missed-true and true-backed deletion audits.
- Downgrade heavy semi-Markov/full neural CRF/Mash expansion until MVP gates pass.

## Aggregated recommendation

- [x] Replace component: post-hoc smoothing is insufficient; move toward boundary/interval decoder.
- [x] Run sanity/action-policy first for selector: top-k regret, risk/abstention, uncertainty intervals.
- [x] Do not claim exact selector confidence yet.
- [x] Do not scale frozen-logit weak decoders unless they beat post-hoc CRF.
- [ ] Continue HMM/CRF penalty tuning as the primary fragmentation route.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-NEXT-DECAY-FRAG-20260630/output_c_antigravity.md`
- `/tmp/council_tefm_decay_fragment_20260630/round1_proponent_claude.md`
- `/tmp/council_tefm_decay_fragment_20260630/round1_opponent_codex.md`
- `/tmp/council_tefm_decay_fragment_20260630/round1_referee_agy.md`
- `/tmp/council_tefm_decay_fragment_20260630/round2_proponent_claude.md`
- `/tmp/council_tefm_decay_fragment_20260630/round2_opponent_codex.md`
- `/tmp/council_tefm_decay_fragment_20260630/round2_referee_agy.md`

---

# Tri-Review: PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630

Date: 2026-06-30

## Review mode

- Mode: independent parallel CLI reviewers.
- Prompt: `/tmp/tri_review_PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success, with sandbox warning (`No space left on device` while trying to read local skill); produced a complete structured review from the supplied prompt and metrics.
- Reviewer C: Antigravity CLI · success.
- Quorum: `3/3`.

## Inputs

- Experiment cohort: `PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630`.
- Selector artifacts: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/`.
- Decoder artifacts: `reports/tefm_final/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/`.
- Result log: `docs/06_results_log.md#result-pipe-tefm-pursue-decay-struct-20260630`.
- Resource profile: bounded screen; not claim-bearing.

## Reviewer A · Claude

- Overall judgment: `replace-component` for the decoder retention component; selector remains triage-only.
- Selector: passes the conservative router gates: top2 contains-best `0.8636`, mean regret `0.00708`, explicit leave-clade abstention, no confidently wrong anchors.
- Decoder: segment-F1 and boundary-F1 both improve, but missed_true_rate fails by rising from `0.2623` to `0.3525`.
- Main concern: `semimarkov_retention` deleted `168` CE fragments, `83` of them true-backed; deleted_true_backed_fraction `0.494`.
- Next action: replace token-level weak retention with interval-level true-retention / fragment-survival objective; do not scale.
- Confidence: Medium.

## Reviewer B · Codex

- Overall judgment: `change-objective-or-loss`.
- Selector: conditionally passes as conservative router only. It cannot be described as exact F1 predictor or automatic single-anchor selector.
- Decoder: promotion/scaling not allowed because missed_true_rate exceeds CE by `0.0902`; current improvement looks like stronger fragment suppression rather than reliable TE retention.
- Main concern: local probe/abstention wording must remain explicit, and decoder best-variant selection must treat the missed_true_rate gate as hard.
- Next action: run only a true-retention-constrained structured decoder sanity test where violating `missed_true_rate <= CE + 0.03` disqualifies a variant even if segment-F1 is higher.
- Confidence: High.

## Reviewer C · Antigravity

- Overall judgment: `change-objective-or-loss`.
- Selector: passes top2/regret gates and has adequate leave-clade abstention; acceptable as conservative triage/router.
- Decoder: segment-F1 and boundary-F1 improve, but missed_true_rate fails; deleted true-backed diagnosis shows 83 true-backed fragments removed by `semimarkov_retention`.
- Next action: stop expanding current training and design stronger true-retention penalties or decoding constraints.
- Confidence: High.

## Cross-reviewer agreement

- 3/3 agree selector should be carried forward only as conservative trust router: in-panel top2 shortlist plus local chromosome probe; leave-clade/new clade abstains until local probe/new anchor.
- 3/3 agree decoder cannot be promoted or scaled because missed_true_rate and deleted true-backed fragments fail the user gate.
- 3/3 recommend changing the objective/loss or replacing the weak retention component with interval-level true-retention constraints.

## Disagreements

- Claude frames the next decoder decision as `replace-component`; Codex and Antigravity frame it as `change-objective-or-loss`.
- This affects wording, not action: all three converge on replacing the weak retention proxy with a stronger true-retention / interval-level objective before any scaling.

## Aggregated recommendation to pivot

- [x] Change objective / loss: stronger true-retention or interval-level fragment-survival objective.
- [x] Keep selector as conservative router, not point-estimate formula.
- [x] Do not scale current decoder variant.
- [ ] Continue threshold/gap/post-hoc tuning.
- [ ] Claim selector as new-species F1 confidence formula.

## Required prerequisites before next run

- [ ] If decoder continues, predefine hard model-selection rule: any variant with missed_true_rate > CE + 0.03 is disqualified.
- [ ] Add interval-level/deleted-true-backed penalty or constrained decoding; do not re-run the same weak proxy at larger scale.
- [ ] Preserve selector leave-clade abstention wording in publication-facing docs.

## Confidence

High for the negative promotion decision; Medium for the exact next architecture because the best true-retention formulation remains untested.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630/output_c_antigravity.md`

---

# Tri-Review: PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630

Date: 2026-06-30

## Review mode

- Mode: independent parallel CLI reviewers.
- Prompt: `/tmp/tri_review_PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; output includes Codex wrapper/prompt echo but contains a complete structured review.
- Reviewer C: Antigravity CLI · success via `agy --print`.
- Quorum: `3/3`.

## Inputs

- Experiment cohort: `PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630`.
- Selector artifacts: `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630/`.
- Decoder artifacts: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/`.
- Result log: `docs/06_results_log.md#result-pipe-tefm-pursue-minhash-intervalsurv-20260630`.
- Validator metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-INTERVALSURV-20260630/pursue_combined_metrics.json`.
- Resource profile: bounded screen; not claim-bearing.

## Reviewer A · Claude

- Overall judgment: `abandon-route`.
- Selector: stop as triage-only; it meets the conservative in-panel top-2/local-probe contract and MinHash did not make leave-clade deployable.
- Decoder: stop as future work because two structured attempts failed the same true-backed deletion guardrail.
- Main concern: `deleted_true_backed_fraction` stayed very high (`0.4940` previous round, `0.4592` this round), so segment/boundary gains are not clean false-fragment cleanup.
- Next action: pivot to terminate selector formula and decoder structured route, record limitation/future work.
- Confidence: High.

## Reviewer B · Codex

- Overall judgment: `change-objective-or-loss`.
- Selector: freeze as conservative router only; do not continue formula work or claim cross-clade confidence.
- Decoder: primary gates now pass, but true-backed deletion guardrail fails; this is specific enough to justify one final decoder-only objective/loss screen.
- Main concern: `deleted_true_backed_fraction=0.4592` cannot be hidden behind the missed_true_rate delta passing by a narrow margin.
- Next action: run one bounded `retention_constrained_interval_loss` experiment where deleted true-backed fragments are part of the training objective and hard gate.
- Confidence: Medium-High.

## Reviewer C · Antigravity

- Overall judgment: `change-objective-or-loss`.
- Selector: validated as conservative triage/router; spend no more compute on selector.
- Decoder: survival/retention objectives structurally prune true short fragments; one final attempt is only justified if it fundamentally changes away from survival/retention, such as center-offset regression or joint bp-CE constrained objective.
- Main concern: persistence with Markov/survival decoder variants is a compute sink unless the objective directly protects true-backed fragments.
- Next action: lock selector and launch exactly one final bounded decoder experiment with a different objective, then stop if guardrail still fails.
- Confidence: High.

## Cross-reviewer agreement

- 3/3 agree the selector formula direction should stop and be written as a conservative router limitation: known/in-panel top-2 shortlist plus local chromosome probe; leave-clade/new clade abstain.
- 3/3 agree the current interval-survival decoder cannot be promoted because deleted true-backed fragments remain far above the guardrail.
- 3/3 reject threshold/gap/post-hoc HMM/CRF tuning as the main next route.

## Disagreements

- Claude recommends stopping the decoder route now as future work.
- Codex and Antigravity recommend one final bounded objective/loss iteration because this round newly controls missed_true_rate within `+0.03`; the remaining failure is a targeted true-backed deletion guardrail.
- This disagreement matters only for whether to run one more low-cost decoder-only screen. It does not affect claim language: no decoder result is currently deployable.

## Aggregated recommendation to pivot

- [x] Stop selector formula direction; carry only conservative router wording.
- [x] Do not promote or scale `interval_survival_decoder`.
- [x] Permit at most one final decoder-only objective/loss screen focused on true-backed retention, because 2/3 reviewers judged the remaining guardrail failure targeted and bounded.
- [ ] Continue selector formula/MinHash iteration.
- [ ] Continue threshold/gap/post-hoc smoothing.
- [ ] Claim fragmentation solved.

## Required prerequisites before next run

- [ ] Predefine `deleted_true_backed_fraction <= 0.15` as a hard primary guardrail, not a secondary diagnostic.
- [ ] Keep CE baseline in the same job and same split.
- [ ] Do not include selector in the next compute round.
- [ ] If the final decoder screen fails the true-backed deletion guardrail, stop decoder direction and write future work.

## Confidence

High for selector stop and current decoder non-promotion; Medium for allowing one final decoder-only objective/loss attempt.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630/output_c_antigravity.md`

---

# Tri-Review: PIPE-TEFM-PURSUE-RETCONSTR-20260630

Date: 2026-06-30

## Review mode

- Mode: independent parallel CLI reviewers.
- Prompt: `/tmp/tri_review_PIPE-TEFM-PURSUE-RETCONSTR-20260630/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; output includes sandbox namespace warning but produced complete structured review.
- Reviewer C: Antigravity CLI · success via `agy --print`.
- Quorum: `3/3`.

## Inputs

- Experiment: `PIPE-TEFM-PURSUE-RETCONSTR-20260630`.
- Decoder artifacts: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/`.
- Result log: `docs/06_results_log.md#result-pipe-tefm-pursue-retconstr-20260630`.
- Validator metrics: `reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630/pursue_combined_metrics.json`.
- Resource profile: bounded screen; not claim-bearing.

## Reviewer A · Claude

- Overall judgment: `abandon-route`.
- Semantic success: engineering success; job completed and metrics are parseable.
- Method gate: failed segment-F1 delta, boundary-F1 delta, and deleted true-backed guardrail.
- Stop recommendation: stop decoder direction now under the pre-registered final-attempt rule.
- Publication wording: selector is triage-only; structured decoder objectives showed signal but did not simultaneously meet strict interval and true-retention guardrails.
- Confidence: High.

## Reviewer B · Codex

- Overall judgment: `abandon-route`.
- Semantic success: engineering success, not a failed run.
- Method gate: `retention_constrained_decoder` lowered missed_true_rate but regressed segment/boundary and still failed `deleted_true_backed_fraction<=0.15`.
- Stop recommendation: stop decoder objective/loss route as future work; do not continue bounded decoder attempts.
- Publication wording: trust router should be described as in-panel top-2/local-probe with leave-clade abstention; decoder is not solved.
- Confidence: High.

## Reviewer C · Antigravity

- Overall judgment: `abandon-route`.
- Semantic success: engineering success, experimental/method failure.
- Method gate: failed both performance gates and deletion guardrail.
- Stop recommendation: immediately stop decoder direction as future work.
- Publication wording: standard CE baseline remains the robust default; alternative structural objectives are future work.
- Confidence: High.

## Cross-reviewer agreement

- 3/3 agree the final decoder-only attempt is semantically valid but methodologically failed.
- 3/3 agree the pre-registered stop rule is triggered and no further decoder objective/loss iterations should be run for this milestone.
- 3/3 agree selector should remain conservative triage-only and not be overclaimed as a point formula.

## Disagreements

- None material. All reviewers converge on `abandon-route` for the decoder route and selector limitation language.

## Aggregated recommendation to pivot

- [x] Abandon decoder structured objective/loss route for this milestone and record as future work.
- [x] Freeze selector as conservative router-only.
- [x] Do not claim fragmentation solved.
- [ ] Run another decoder objective/loss tweak.
- [ ] Continue threshold/gap/post-hoc smoothing.

## Required prerequisites before next run

- No next decoder run under this milestone.
- Any future re-entry must use a substantially different approach, not another Markov/survival/retention tweak, and must have an explicit re-entry criterion.

## Confidence

High.

## Raw outputs

- `/tmp/tri_review_PIPE-TEFM-PURSUE-RETCONSTR-20260630/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-RETCONSTR-20260630/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-PURSUE-RETCONSTR-20260630/output_c_antigravity.md`

---

# Tri-Review: PIPE-TEFM-CAP-FRAGARCH-20260701

Date: 2026-07-01

## Review Mode

- Mode: independent parallel CLI reviewers.
- Prompt: `/tmp/tri_review_PIPE-TEFM-CAP-FRAGARCH-20260701/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; output includes a sandbox namespace warning but produced complete structured review.
- Reviewer C: Antigravity CLI · success via `agy --print`.
- Quorum: `3/3`.

## Inputs

- Experiment: `PIPE-TEFM-CAP-FRAGARCH-20260701`.
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_metrics.tsv`.
- Status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGARCH-20260701/interval_arch_status.json`.
- Result log: `docs/06_results_log.md#result-pipe-tefm-cap-fragarch-20260701`.
- Resource profile: bounded capability-pursue screen; not claim-bearing.

## Reviewer A · Claude

- Overall judgment: `abandon-route`.
- Semantic success: engineering success; job completed, metrics are parseable, code-review gate passed.
- Method interpretation: both lightweight interval heads fail in a way similar to DEC-001 tradeoff; they improve or reshape segments by deleting many true-backed fragments rather than reliably reconstructing intervals.
- Main concern: `boundary_proposal` degrades bp-F1 and boundary-F1; `anchor_free_interval` partially works on human but collapses on mouse.
- Next action: stop this lightweight frozen-feature head route; if revisiting interval-aware models, use a fundamentally different mechanism such as end-to-end set prediction or graph/instance-level modeling.
- Confidence: High.

## Reviewer B · Codex

- Overall judgment: `replace-component`.
- Semantic success: technical success with sufficient strict metrics for a capability-pursue decision.
- Method interpretation: current heads are too shallow and lack true-fragment preservation/linking; this does not falsify interval-aware architecture generally.
- Main concern: high `deleted_true_backed_fraction` means apparent segment-F1 gains can be false cleanup rather than true interval repair.
- Next action: replace the component with a fragment graph linker or boundary-conditioned span refinement; do not scale or tune the current heads.
- Confidence: Medium.

## Reviewer C · Antigravity

- Overall judgment: `abandon-route`.
- Semantic success: technical success; no evaluator/data leakage blocker observed.
- Method interpretation: frozen CE-optimized embeddings plus lightweight coordinate/boundary heads are the failed route. The heads act as filters that erase difficult true fragments rather than instance repair modules.
- Main concern: mouse quick collapse and 70-80% true-backed deletion on human indicate the current patch-style route is at a dead end.
- Next action: abandon frozen-lightweight head route; consider end-to-end multi-task interval detector or contrastive fragment linkage if a new mechanism is pursued.
- Confidence: High.

## Cross-reviewer Agreement

- 3/3 agree the run is semantically valid and not an engineering failure.
- 3/3 agree the tested `boundary_proposal` and `anchor_free_interval` implementations should not be scaled or tuned.
- 3/3 agree high `deleted_true_backed_fraction` is central and prevents interpreting segment-F1 improvement as solved fragmentation.
- 3/3 agree any continuation must be a new mechanism, not threshold/gap/post-hoc HMM/CRF or another shallow frozen-head tweak.

## Disagreements

- Claude and Antigravity use `abandon-route` for the current frozen-lightweight head route.
- Codex uses `replace-component`, arguing interval-aware architecture broadly is not falsified, only the tested heads are.
- Practical convergence: stop current component; optionally allow one second bounded round only if the component is substantially replaced by fragment graph/linking, boundary-conditioned span refinement, end-to-end set prediction, or contrastive instance linkage.

## Aggregated Recommendation To Pivot

- [x] Do not scale current `boundary_proposal` or `anchor_free_interval`.
- [x] Do not tune thresholds/gaps/HMM penalties.
- [x] Treat Round 1 as engineering success and method failure.
- [x] If continuing capability-pursue, replace the component with a fundamentally different interval/instance mechanism and keep the same strict retention guardrails.
- [ ] Claim fragmentation solved.

## Confidence

Medium-high for stopping the current components; medium for allowing a second bounded round because the reviewers differ on abandon-vs-replace wording.

## Raw Outputs

- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGARCH-20260701/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGARCH-20260701/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGARCH-20260701/output_c_antigravity.md`

---

# Tri-Review: PIPE-TEFM-CAP-FRAGGRAPH-20260701

Date: 2026-07-01

## Review Mode

- Mode: independent parallel CLI reviewers.
- Prompt: `/tmp/tri_review_PIPE-TEFM-CAP-FRAGGRAPH-20260701/prompt_full_scope.md`.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; output includes a sandbox namespace warning but produced complete structured review.
- Reviewer C: Antigravity CLI · success via `agy --print`.
- Quorum: `3/3`.

## Inputs

- Experiment: `PIPE-TEFM-CAP-FRAGGRAPH-20260701`.
- Metrics: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_metrics.tsv`.
- Status: `reports/tefm_capability/PIPE-TEFM-CAP-FRAGGRAPH-20260701/fragment_graph_status.json`.
- Result log: `docs/06_results_log.md#result-pipe-tefm-cap-fraggraph-20260701`.
- Resource profile: bounded capability-pursue screen; not claim-bearing.

## Reviewer A · Claude

- Overall judgment: `abandon-route`.
- Semantic success: engineering success; job completed, metrics are parseable, and no evaluator/data blocker is apparent.
- Method interpretation: this is the second distinct mechanism in the capability branch to fail after Round 1 frozen interval heads. The preservation-first graph decoder is identical to CE raw, while the keep/drop variant improves human interval metrics by deleting true-backed fragments.
- Main concern: positive edge sparsity and weak local graph features mean learned links do not fire under the safe keep-all decoder; the unsafe decoder recreates the deletion failure.
- Next action: stop the capability route and write interval reconstruction as future work / limitation.
- Confidence: High.

## Reviewer B · Codex

- Overall judgment: `abandon-route`.
- Semantic success: valid screen result with sufficient strict metrics and guardrails.
- Method interpretation: `fragment_graph_keepall` does no interval repair; `fragment_graph_keepdrop` is deletion-driven, not robust, and fails mouse smoothing comparison.
- Main concern: the only apparent interval gain comes with `deleted_true_backed_fraction=0.8632` on human and remains weak on mouse.
- Next action: stop `PIPE-TEFM-CAP-FRAGARCH` capability-pursue; record graph linker as negative ablation / future-work limitation; do not start a boundary-conditioned span-refiner round.
- Confidence: High.

## Reviewer C · Antigravity

- Overall judgment: `abandon-route`.
- Semantic success: technical success; experimental method failure.
- Method interpretation: the keep-all graph collapsed to CE raw, while keep/drop became an aggressive survival-like filter that deletes true-backed fragments.
- Main concern: mouse panel failure and high true-backed deletion show this is not a deployable interval-aware annotation module.
- Next action: terminate joint structured / interval-aware decoder capability for this sprint; keep existing overlap/smoothing only as a fixed comparator, not as a solved capability.
- Confidence: High.

## Cross-reviewer Agreement

- 3/3 agree the run is semantically valid and not an engineering failure.
- 3/3 agree `fragment_graph_keepall` preserves true-backed fragments but does not improve interval metrics.
- 3/3 agree `fragment_graph_keepdrop` cannot be promoted because the gain is deletion-driven and does not transfer cleanly to mouse.
- 3/3 recommend `abandon-route` for the current capability-pursue branch rather than running another bounded refiner round.

## Disagreements

- None material. All reviewers converge on stopping the current TEFM-CAP-FRAGARCH interval reconstruction capability line.

## Aggregated Recommendation To Pivot

- [x] Treat Round 2 as engineering success and method failure.
- [x] Do not scale the fragment graph linker.
- [x] Do not launch a final boundary-conditioned span-refiner round under this capability-pursue sprint.
- [x] Record frozen/post-hoc interval reconstruction modules as future work / abandoned component for now.
- [ ] Claim fragmentation solved.

## Confidence

High.

## Raw Outputs

- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGGRAPH-20260701/output_a_claude.md`
- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGGRAPH-20260701/output_b_codex.md`
- `/tmp/tri_review_PIPE-TEFM-CAP-FRAGGRAPH-20260701/output_c_antigravity.md`

---

# Tri-Review: TEFM-NEW-DIRECTIONS-PILOTS-20260811

Date: 2026-08-11 CEST

## Review mode and quorum

- Mode: independent parallel full-scope CLI review after result-log.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; it reported a local read-only namespace failure and correctly limited conclusions to the self-contained pack.
- Reviewer C: Antigravity CLI · success.
- Quorum: `3/3`.
- Claim status: non-claim bounded evidence cohort; no scientific screen ran.
- Experiments reviewed: `BENCH-5TOOL-SMOKE-20260811-R1`, `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`, `SF-HIER-OPENSET-SCREEN-20260811-R1`, `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`, `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`.

## Reviewer conclusions

| Reviewer | Judgment | Next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `run-sanity-check-first` | Configure and freeze Dfam 4.0 FamDB for RM2+RM and Earl Grey; optionally acquire exact HiTE 3.3.3 SIF and build F truth registry | Denominator identity/database closure is the dependency root; all routes remain asset-gated | High |
| B · Codex | `comparability-blocker` | Freeze `F Evidence Input Registry v1`; optionally close B runtime/database and materialize S ontology/split | F truth/comparator comparability and S/E homology leakage firewalls are absent | Medium |
| C · Antigravity | `comparability-blocker` | Close B Dfam/FamDB, exact HiTE and EDTA patch identity; optionally freeze S/E splits and G provenance | No scientific metric exists; foundational identities and split/provenance contracts are incomplete | High |

## Agreement

- 3/3: all five result packages are semantic successes of fail-closed engineering, not scientific/model results.
- 3/3: no B/F/S/G/E candidate may be promoted, tuned or scaled; Current/SOTA/gap are all N/A.
- 3/3: typed blocks arise from runtime/data/evaluator/provenance/backend contracts, not evidence that an architecture hypothesis failed.
- 3/3: no silent dependency substitution, stale terminal status, claim inflation or resource violation was observed; future S/E/F screens still require homology/group leakage audits.
- 3/3: the next action must resolve a foundational contract and rerun its gate before any scientific screen.

## Disagreement

- A and C prioritize the B five-workflow denominator because it is the shared comparison substrate.
- B prioritizes F's biological truth and same-input comparator registry because that is the strictest scientific comparability blocker.
- This is an ordering disagreement, not a disagreement about whether either gate may be waived.

## Aggregated recommendation to pivot

Choose one comparability/sanity repair as primary. Protocol dependency order favors B denominator closure first; keep F/S/G/E parked and retain F registry, exact HiTE acquisition, S split materialization and G provenance reconstruction as reviewer-proposed future/optional directions. Do not submit model training or a biological benchmark until the corresponding gate passes.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/tri_review/context.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/tri_review/output_c_antigravity.md`

---

# Tri-Review: TEFM-NEW-DIRECTIONS Wave-1 failed runs

Date: 2026-08-11 CEST

## Review mode and quorum

- Mode: three independent read-only Codex subagents with separate focuses after result-log and deterministic `failed_run` validation.
- Reviewer A: semantic/comparability.
- Reviewer B: data/runtime integrity.
- Reviewer C: research strategy/resource.
- Quorum: `3/3`; all returned complete structured reviews.
- Experiments: `BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2` Job `11522405`; `SF-DIRECT-BASELINE-SCREEN-20260811-R2` CPU DATA Job `11522718`.

## Reviewer conclusions

| Reviewer | Judgment | B verdict | S0 verdict | Next action | Confidence |
|---|---|---|---|---|---|
| A · semantic | `run-sanity-check-first` | audited failed run: 4 invalid + 1 valid typed block | DATA failed; leakage unknown | repair-only validity iteration | High |
| B · integrity | `run-sanity-check-first` | raw artifacts intact but original semantic truth rejected | deterministic pre-materialization parser failure | canonical audited B manifest; bounded local CSV limit + tests | High |
| C · strategy | `run-sanity-check-first` | split repair into cheap identity/launcher, integration, then Pfam batches | repair CPU DATA first; GPU only after PASS | short CPU repairs; preserve direct-before-S1 order | High |

## Agreement

- 3/3: both routes are `failed_run`; neither contains a model/tool scientific result.
- 3/3: B must not treat `terminal_cell_count=5` or raw `semantic_success=true` as valid semantics. RM/EarlGrey/HiTE/EDTA are invalid runtime/integration cells; only TEtrimmer's unlaunched immutable-Pfam absence is a valid foundational block.
- 3/3: S0 failed before Dfam-component split/leakage materialization. No direct-superfamily acceptance metric exists; leakage status is Unknown, and GPU/S1 remain forbidden.
- 3/3: no immediate rerun, tuning, scaling or claim. Any retry requires code-bearing bounded repair and fresh independent code review.
- 3/3: the user's direct-superfamily-first order remains binding and has not yet been scientifically satisfied.

## Aggregated recommendation to pivot

`run-sanity-check-first` with a single repair-only validity iteration after the user-visible failed-run stop. First repair S0's manifest reader using a local bounded two-million-character field limit plus real-shape/over-limit tests; in parallel only the cheapest B collector/RM/HiTE fixes may be implemented. Then re-review and rerun CPU gates only. Earl Grey/EDTA and Pfam/TEtrimmer remain later isolated batches. GPU S0 requires formal DATA PASS; S1 remains locked until the full S0 numeric gate passes.

## Raw outputs

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/wave1_failed_run_tri_review/reviewer_a_semantic.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/wave1_failed_run_tri_review/reviewer_b_integrity.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/wave1_failed_run_tri_review/reviewer_c_strategy.md`

---

# Tri-Review: S0 identity-layer typed block (Job 11523252)

Date: 2026-08-11 CEST

## Review mode and quorum

- Mode: three independent external CLI reviewers consuming the same frozen result/evaluator/protocol pack.
- Reviewer A: Claude CLI; Reviewer B: Codex CLI; Reviewer C: Antigravity CLI.
- Quorum: `3/3`; all three reviews completed successfully.
- Result under review: `SF-DIRECT-BASELINE-SCREEN-20260811-R2` CPU DATA repair Job `11523252`.
- Claim boundary: no DATA PASS, leakage audit, model training, inference or S0 metric exists.

## Reviewer conclusions

| Reviewer | Judgment | Recommended next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `replace-component` | Replace name-only identity resolution with a frozen consensus provenance/hash-or-cluster identity layer | Custom/ambiguous RepeatMasker names cannot be assumed to map uniquely to Dfam | High |
| B · Codex | `comparability-blocker` | Run a bounded identity-provenance audit from annotation record to unique source-library entry, consensus SHA and preregistered sequence component | Exact SHA alone does not group homologous but non-identical consensuses; any clustering must be frozen before metrics | High |
| C · Antigravity | `comparability-blocker` | Audit consensus/source provenance first; use exact names only as an audit field or comparator | Exact-name components are brittle and create family/homology leakage risk | High |

## Agreement

- 3/3: `DATA_TYPED_BLOCK` is a valid fail-closed result, not a model or direct-superfamily performance result.
- 3/3: no immediate S0 DATA retry, GPU S0, S1, tuning, scaling or claim is permitted.
- 3/3: unresolved positives must not be deleted, coerced to `Unknown`, randomly split, or assigned by string-prefix guesses.
- 3/3: consensus/source-library provenance is the preferred identity substrate; exact RepeatMasker family name may remain an audit field but is not a defensible primary homology component.
- 3/3: the user-required direct-superfamily-first order remains binding and unresolved.

## Disagreement and resolution

- Reviewer A labels the next move `replace-component`; Reviewers B/C label it `comparability-blocker`. Operationally they agree on ordering: first audit whether every P-state annotation has a unique frozen source consensus, then decide the component definition.
- Reviewer B adds the strongest constraint: identical-consensus SHA is sufficient for exact duplicates but not for homologous non-identical consensuses. If sequence clustering is required, its algorithm, threshold, input universe and hashes must be preregistered before materialization.
- Therefore the audit itself may proceed without changing the active S goal, but any change from the current Dfam-accession component contract to a new sequence-cluster contract requires the project’s human-gated goal/contract revision before another S DATA run.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_tri_review/prompt_common.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_tri_review/output_c_antigravity.md`

---

# Tri-Review: S0 provenance audit failed run (Job 11523938)

Date: 2026-08-11 CEST

## Review mode and quorum

- Three independent external CLI reviewers consumed the same frozen failed-run evidence pack: Claude, Codex and Antigravity.
- Quorum: `3/3`; all returned complete verdicts.
- Scope: claim-ineligible CPU asset audit; no scientific result existed.

## Reviewer conclusions

| Reviewer | Judgment | Repair verdict | Mandatory emphasis | Confidence |
|---|---|---|---|---|
| A · Claude | `run-sanity-check-first` | Explicit structural presence check is valid | Freeze actual partition-index layout; absent-vs-corrupt tests; at most one retry | High |
| B · Codex | `run-sanity-check-first` | Narrow leaf check is preferable to broad top-level exception swallowing | Do not change inventory denominator; present-but-broken index must fail | High |
| C · Antigravity | `run-sanity-check-first` | Explicit group-presence check is valid | Pinned real-layout regression plus corrupt/unreadable hard failure | High |

## Agreement

- 3/3: Job `11523938` is a deterministic `failed_run`, not a provenance typed block, valid negative or S0 result.
- 3/3: the candidate repair is admissible only when it skips name lookup for a leaf whose pinned H5 structure truly lacks `Lookup/ByName`; broad exception suppression is forbidden.
- 3/3: `Lookup/ByName` present-but-unreadable/corrupt/wrong-type/query-failing must remain `AUDIT_FAILED`.
- 3/3: add a regression over the actual frozen Dfam 3.9 partition layout and synthetic absent-vs-corrupt cases, then fresh independent review before one CPU retry.
- 3/3: direct-S0-first/S1-locked ordering is unchanged; no GPU, split, cluster, training or goal revision is authorized.

## Aggregated recommendation

`run-sanity-check-first`: implement only the structural-index compatibility repair and its real-layout/fail-closed regression package. Retain the full identifier and occurrence denominators. If the audit then reaches a valid typed block, return to the human-gated identity-contract decision; if it fails again, stop rather than auto-running a third attempt.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_failed_run_tri_review/prompt_common.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_failed_run_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_failed_run_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_failed_run_tri_review/output_c_antigravity.md`

---

# Tri-Review: RM+HiTE validity failed run (Job 11523819)

Date: 2026-08-11 CEST

Experiment: `BENCH-RM-HITE-VALIDITY-20260811-R1`.

## Review mode and quorum

- Independent external CLI reviewers: Claude, Codex and Antigravity.
- Quorum: `3/3`; all complete, confidence High.
- Evidence boundary: runtime validity only; original aggregate remains `FAILED`.

## Reviewer conclusions

| Reviewer | Judgment | RM reuse | Preferred option | Stop rule | Confidence |
|---|---|---|---|---|---|
| A · Claude | continue | defensible immutable cell artifact | A · isolated HiTE-only | 1800s timeout again => stop | High |
| B · Codex | `run-sanity-check-first` | reusable with explicit two-job reconciliation | A · isolated HiTE-only | no second timeout extension | High |
| C · Antigravity | continue | cryptographically bound and reusable | A · isolated HiTE-only | strict rc0/GFF/adapter only | High |

## Agreement

- 3/3: RM2+RepeatMasker+Dfam4 is a valid cell-level `ENGINEERING_PASS`; do not erase or rerun it merely because the paired aggregate failed.
- 3/3: HiTE is a timeout/incomplete execution, not version mismatch, foundational block or tool-quality result.
- 3/3: choose a new isolated HiTE-only namespace with byte-identical SIF/fixture/argv/offline contract, 4CPU/48GiB/0GPU/1h, preregistered 1800s command timeout and at least 10m cleanup/publish headroom.
- 3/3: success requires rc0, exact identity, final non-empty parseable `HiTE.gff`, canonical adapter pass and verified manifest.
- 3/3: retain the original R1 aggregate failure and reconcile later by citing both reviewed jobs and verifying all shared pins; this is traceable reuse, not replacement/cherry-picking.
- 3/3: if 1800s still times out, stop; no automatic extension or paired rerun.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/rm_hite_failed_run_tri_review/prompt_common.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/rm_hite_failed_run_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/rm_hite_failed_run_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/rm_hite_failed_run_tri_review/output_c_antigravity.md`

---

# Tri-Review: S0 identity/provenance valid negative (Job 11524255)

Date: 2026-08-11 CEST

Experiment: `SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1`.

## Review mode and quorum

- Independent external CLI reviewers: Claude, Codex and Antigravity.
- Quorum: `3/3`; all complete with High confidence.
- Evidence boundary: CPU-only identity/provenance audit; no split, training, inference or model metric.

## Reviewer conclusions

| Reviewer | Judgment | Preferred contract direction | Shared stop condition | Confidence |
|---|---|---|---|---|
| A · Claude | `replace-component` | Frozen sequence-homology supplement | No S0 DATA/GPU/S1 before a complete identity contract | High |
| B · Codex | `comparability-blocker` | Human-gated full-universe contract; homology only if fully frozen | No denominator shrinkage or scientific progression | High (`0.97`) |
| C · Antigravity | `comparability-blocker` | Curated static exact aliases first | No S0 DATA/GPU/S1 before explicit alias/ambiguity/exclusion rules | `10/10` |

## Agreement

- 3/3: Job `11524255` is a semantically valid, reproducible asset-level negative; it is neither a failed run nor a model-quality result.
- 3/3: exact Dfam name/accession resolution of 6,447/6,727 identifiers is insufficient for a leakage-safe full S0 split. The 279 missing identifiers cannot be silently dropped, especially because several have very large occurrence counts.
- 3/3: the single ambiguous identifier `X13_LINE` and all 10 label-contract-excluded identifiers require explicit, frozen treatment.
- 3/3: do not run another S0 DATA job, GPU S0, hierarchical/open-set S1, tuning, scaling or a claim under the current contract.
- 3/3: the next action is a human-gated identity-contract decision package, not compute.

## Preserved disagreement

- Claude prefers replacing exact-only identity with a sequence-homology component.
- Antigravity prefers first exhausting a curated static exact-alias mapping.
- Codex treats both as admissible only if the chosen route covers the complete intended universe and freezes its source, algorithm/rules, evaluator and zero-overlap proof.

This disagreement is material and is intentionally not resolved by the driver. It is the next human gate.

## Aggregated recommendation

`comparability audit first`: prepare one decision package with two mutually exclusive options—curated exact aliases versus frozen sequence-homology components—and explicit sub-decisions for `X13_LINE` and the 10 excluded identifiers. Do not submit further S compute until the selected contract receives its own implementation/review/data gates.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/prompt_common.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/output_c_antigravity.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/quorum.json`

---

# Tri-Review: isolated HiTE engineering pass (Job 11524485)

Date: 2026-08-12 CEST

Experiment: `BENCH-HITE-ISOLATED-20260811-R1`.

## Review mode and quorum

- Independent external CLI reviewers: Claude, Codex and Antigravity.
- Quorum: `3/3`; all complete with High confidence.
- Scope: isolated runtime-validity engineering evidence and cross-run reconciliation only.

## Reviewer conclusions

| Reviewer | Semantic verdict | Reconciliation verdict | Judgment | Single next action | Confidence |
|---|---|---|---|---|---|
| A · Claude | PASS | Defensible as two-job/two-cell evidence | `continue` | Archive 2/5 and stop at human authorization | High |
| B · Codex | PASS | Defensible; never a successful aggregate | `continue` | Supersede operational retry permission to false; no job | High (`0.96`) |
| C · Antigravity | PASS | Defensible with parent FAILED preserved | `continue` | Escalate incomplete five-cell state to human; no metric synthesis | High (`100%`) |

## Agreement

- 3/3: the isolated exact HiTE 3.3.3 `ENGINEERING_PASS` is semantically valid and reproducible.
- 3/3: retaining the immutable parent RM pass and combining it with isolated HiTE is scientifically/auditably defensible only as two-job/two-cell evidence.
- 3/3: the parent aggregate remains `FAILED`; `single_successful_run=false`, `accuracy_claim=false` and `claim_eligible=false` remain binding.
- 3/3: the evidence closes only RM and HiTE. It does not close the five-cell denominator, authorize another denominator run, or permit a synthesized `terminal_cell_count`.
- 3/3: raw `further_retry_allowed=true` is a semantic warning because the sole human-authorized isolated attempt has been consumed. No retry is operationally authorized.
- 3/3: no GPU, biological benchmark, S0/S1, other tool or automatic rerun follows from this result.

## Aggregated recommendation

`continue` means accept and archive the two-cell engineering evidence, close the result chain, and return the remaining denominator scope to a human gate. It does not mean continue compute. Preserve the raw reconciliation and add an immutable post-run review that sets operational retry authorization to false.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/hite_isolated_tri_review/prompt_common.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/hite_isolated_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/hite_isolated_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/hite_isolated_tri_review/output_c_antigravity.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/hite_isolated_tri_review/quorum.json`
- `outputs/BENCH-HITE-ISOLATED-20260811-R1/reconciliation_review.json`
- `outputs/BENCH-HITE-ISOLATED-20260811-R1/postrun_review_manifest.json`

---

# Tri-Review: partition-3 identity recovery resource failed run (Job 11525316)

Date: 2026-08-12 CEST

Experiment: `SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1`.

## Review mode and quorum

- Mode: independent parallel external CLI review with one identical full-scope prompt.
- Reviewer A · Claude: success.
- Reviewer B · Codex: success; its internal read-only shell sandbox failed from namespace exhaustion, but it completed the requested review from the self-contained pack.
- Reviewer C · Antigravity: failed after all three mandated attempts. Original and first retry treated wrapper flag `--print-timeout` as the prompt; compressed explicit-wrapper retry exposed an incompatible `-p` argument contract. None contained an Overall judgment, so none is counted.
- Quorum: `2/3 DEGRADED_REVIEW`; confidence capped at Medium.
- Scope: claim-ineligible CPU resource/identity audit only. `validate_goal=failed_run`; no scientific identity result exists.

## Reviewer conclusions

| Reviewer | Judgment | Preferred repair | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `continue-current-route` | Deterministic 4-way read-only disjoint scan; serial 5–6h only fallback | shard coverage/count/output guards and I/O contention | High |
| B · Codex | `replace-component` | Replace serial traversal with a separately reviewed 4-way shard-throughput preflight before formal R0 | partial-result promotion, shard omission/duplication, storage bandwidth and billing waste | High |
| C · Antigravity | failed | none | CLI wrapper/official `agy -p` argument incompatibility after three attempts | n/a |

## Cross-reviewer agreement

- 2/2 successful reviewers: Job `11525316` is an auditable resource/implementation-shape failed run, not a biological or identity negative.
- 2/2: the exact, case-sensitive, exhaustive identity route remains justified; do not change the 279-identifier denominator, direct-label contract or forbidden fallbacks.
- 2/2: a 5–6h serial rerun is technically simplest but inefficient and should not be the first repair.
- 2/2: implement deterministic disjoint read-only shards and first run a short CPU-only throughput/correctness preflight. Each dataset must belong to exactly one shard; child counts must sum to 321,856; any missing/duplicate/failed shard must fail the whole run; only the parent may atomically aggregate.
- 2/2: four-way shared-HDF5 reading may fail to scale because the bottleneck is storage latency, so the preflight must measure cold/representative one-way versus multi-way throughput and refuse formal submission if the conservative projection does not fit with headroom.
- 2/2: R1 full catalog, R2 homology graph/split, GPU S0, S1 and claim remain forbidden.

## Preserved differences

- Claude calls the route itself `continue-current-route` because exact traversal semantics are correct; Codex calls the serial traversal implementation a component that must be replaced. This is wording rather than a scientific disagreement: both prescribe the same 4-way preflight before another exhaustive run.
- Claude would allow a very small login-node benchmark. Project compute discipline is stricter, so the host will run even the preflight through reviewed CPU Slurm allocation, not on the login node.
- Codex proposes a 20-minute preflight and an explicit throughput floor; Claude proposes a 5-minute topology/throughput probe. The pivot must select one bounded Slurm envelope and require measured projection plus cleanup headroom.

## Aggregated recommendation

`run-sanity-check-first`: implement a new isolated shard-throughput preflight, 4 CPU/16 GiB/20 min/0 GPU, with representative disjoint shards and no recovery/absence terminal semantics. Fresh code review is mandatory. Only if the preflight proves exact union/intersection/count determinism and a conservative full-scan projection within a separately reviewed walltime may a formal R0 retry be considered.

## Required prerequisites before next run

- [ ] New exp_id/output/log/lock namespace; no overwrite or reuse of Job `11525316` partial state.
- [ ] Frozen shard assignment derived from canonical dataset paths, pairwise intersection zero and union complete on synthetic/real-topology probes.
- [ ] Child-isolated outputs; any shard error/timeout/truncation causes semantic failure and no aggregate result.
- [ ] Exact-case/unique-accession/consensus rules and all existing count/conservation guards retained.
- [ ] Preflight reports one-way and four-way throughput, skew and conservative p95/full-scan ETA; no identity candidates are promoted.
- [ ] Fresh independent code review and smart-sbatch; 0 GPU.

## Raw evidence

- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_recovery_failed_run_tri_review/prompt_full_scope.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_recovery_failed_run_tri_review/output_a_claude.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_recovery_failed_run_tri_review/output_b_codex.md`
- `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_recovery_failed_run_tri_review/output_c_antigravity{,.retry1,.retry2}.md`
# Tri-review: sharded P3 recovery pre-scan failed run (Job 11526687)

Date: 2026-08-12 CEST

Quorum: `2/3 DEGRADED_REVIEW`. Claude and Codex returned valid independent reviews; Antigravity failed because its headless command permission was auto-denied.

Both successful reviewers classify the event as an execution-environment identity-contract bug, not content drift: symlink-target hash, inode, size, mtime and mode matched, while only mount-namespace-dependent `st_dev` differed. Both preserve the failed-run state and all scientific/downstream prohibitions. Both accept exactly one narrow repair-only path after behavior tests and fresh code review; neither authorizes an automatic retry.

Reviewer A chooses `replace-component`: replace only the source identity guard by making `st_dev` audit-only and explicitly normalizing the registered `/home`↔`/srv` alias. Reviewer B chooses `run-sanity-check-first`: apply the same narrow repair, test cross-namespace equality plus real drift/TOCTOU failures, then return to submission gating. The disagreement is naming, not the technical action.

Hard comparability boundary: no change to 279 targets, 6,432,583 occurrences, exact case-sensitive name semantics, X13 audit-only, candidate resolution, 35-unit traversal, checkpoint schema, resource profile, split or GPU/S1 gates.

Raw review pack: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_sharded_pre_scan_failed_run_tri_review/`.

---
# Tri-review: partition-3 exhaustive identity-recovery valid negative (Job 11526905)

Date: 2026-08-12 CEST

## Review mode

- Mode: independent parallel external CLI review with one identical self-contained prompt.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success.
- Reviewer C: Antigravity CLI · success after three bounded invocation retries; the first two responses misread CLI flags and were retained as invalid raw outputs.
- Quorum: `3/3`.

## Inputs and validity

- Claim-ineligible CPU asset run, 4 CPU/48 GiB/1:40:52/0 GPU.
- 35/35 units; exactly 321,856 unique Families paths/objects; 321,856 consensus and 321,818 model attrs.
- Frozen 279 identifiers/6,432,583 occurrences, exact conservation; exact candidates=0 and all 279 remain missing.
- Immutable state, attempt payload and checkpoint manifests independently verified; X13 remains audit-only.

## Reviewer judgments

- Claude: result is a high-confidence valid negative; choose `abandon-route` specifically for the Dfam 3.9 partition-3 exact-name subroute, while preserving direct S0 as a possible separate route with a new identity contract.
- Codex: result is valid and exhaustive under the frozen contract; choose `replace-component` with an official accession-backed identity/cross-reference source. Do not weaken matching or drop the denominator.
- Antigravity: result is valid and closes the partition-3 exact-name hypothesis; choose `replace-component` and draft a human-gated alternative official identity source.

## Agreement and bounded disagreement

- All three accept the run as semantic-successful valid-negative evidence and reject any further partition-3 scan/retry.
- All three limit the scientific statement to “no exact case-sensitive name match in partition 3”; none interprets this as biological absence.
- All three forbid prefix/case/suffix/genome-copy fallback, relabeling, GPU S0 and S1.
- Claude's `abandon-route` and the other two reviewers' `replace-component` differ only in level: abandon this resolver/subroute, replace the identity-source component if direct S0 is retained.

## Aggregated recommendation

`replace-component`: close the partition-3 exact-name resolver, then place a human gate before any new official accession/alias source is frozen. The 279 targets, direct RepeatMasker labels, ten U/ignore exclusions and X13 audit stratum must remain unchanged. Sequence homology may define split components only and cannot rewrite labels.

Raw review pack: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/p3_sharded_recovery_valid_negative_tri_review/`.

---
# Tri-review: Dfam 3.9 curated authoritative crosswalk — Job 11527999

Date: 2026-08-12 CEST. Experiment: `SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1`.

## Quorum and independent judgments

- Reviewer A (scientific semantics/comparability): `comparability-blocker`; accepts Job 11527999 as a scoped valid-negative and permits only an independent all-family raw-DR support audit.
- Reviewer B (data/runtime integrity): `PASS_VALID_NEGATIVE`; runtime, source, denominator and manifest closure pass; recommends `replace-source-with-independent-sibling-audit`.
- Reviewer C (mechanism/strategy): `replace-component`; recommends one label-blind, target-only Dfam 3.9 all-family audit as the last high-information official-source check.

## Consensus

The curated source is authoritative but insufficient: 50/279 identifiers resolve uniquely, 2 remain ambiguous and 227 remain missing. This does not evaluate direct-superfamily prediction quality and does not authorize homology construction, DATA, GPU S0 or S1. The curated subroute is closed and Job 11527999 must not be rerun.

The only approved next action is a separately named, independently reviewed, CPU-only all-family Dfam 3.9 audit. Raw DR records are support-only: they cannot overwrite curated DF identities, choose among curated ambiguity, change RepeatMasker direct labels or authorize downstream work. Any incomplete scan, source mismatch, timeout, parser failure or reconciliation drift is an engineering failed run, not a valid negative.

## Re-entry boundary

Even complete raw support does not automatically authorize homology. A new human-reviewed identity-contract decision is required. If the all-family audit still contains any missing, ambiguous, invalid or cross-source conflict, the current direct-S0 data route stops until a new official, version-frozen, explicit identifier-to-accession source exists. Copy-derived, prefix/case-fold, taxonomy and current-API fallbacks remain prohibited.
# Tri-review: all-family target crosswalk — Job 11528157

- Reviewer B accepted runtime/data closure and Reviewer C recommended replacing the data contract, but Reviewer A identified a reproducible official-field grammar gap.
- Binding adjudication: `run-sanity-check-first`. Complete gzip/hash/record scanning is accepted; exhaustive zero raw support is not accepted because PI semicolon lists and semicolon-terminated DR primary IDs were not fully tokenized.
- Current direct-S0 homology/DATA/GPU/S1 route remains stopped from the independent curated 50/2/227 blocker.
- Exactly one same-source, same-denominator, CPU-only grammar-repair audit may run after fresh code review. It must report DF/DR-by-field line/token/terminator/hit counts. No result can auto-authorize a downstream stage.
# Final tri-review: grammar-repaired all-family audit — Job 11528267

- Reviewer A: `replace-component`; accepts final valid-negative and closes the Dfam 3.9 exact relation route.
- Reviewer B: `PASS`; runtime/source/grammar/denominator/artifact closure all pass and stop rule is satisfied.
- Reviewer C: stop current annotation-dataset S0 route; preserve the direct-first question by replacing the data contract with annotation-time accession retention.
- Consensus: 3/3. Raw DR has 2,795 NM relations and no PI/SN/DR relations, with zero target hits. The final 50 unique / 2 ambiguous / 227 missing result is authoritative for this route. No homology, DATA, GPU S0 or S1 is authorized.
- Human gate: a new accession-preserving annotation benchmark is a benchmark/data-contract revision, not an implementation detail. It requires explicit approval before CPU preflight work.
# Tri-review: accession-preserving annotation preflight failed run, Job 11528744

- Date: 2026-08-12 CEST.
- Experiment: `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1`.
- Quorum: `2/3 DEGRADED_REVIEW`; Claude and Codex returned valid independent reviews; Antigravity failed headless permission/CLI compatibility attempts and is excluded.
- Shared result fact: Job `11528744` failed `2:0` in 2 seconds after pre-submit and 33/33 tests, before FamDB or RepeatMasker. Canonical `CURRENT` remained `IMPLEMENTED_NOT_RUN`; the result is a failed run, not a valid-negative.

| Reviewer | Judgment | Next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `run-sanity-check-first` | strict `scontrol` resource reconciliation, expanded tests, fresh review, one CPU retry | optional Slurm environment representation caused a false rejection; do not broaden the guard or stages | High |
| B · Codex | `run-sanity-check-first` | normalized scheduler facts, pre-pointer requery, fresh review, one CPU retry | scheduler output/SubmitLine/TRES must be semantic and fail-closed; no actual comparability result exists | Medium |
| C · Antigravity | failed reviewer | none | headless command permission and CLI argument compatibility | N/A |

Consensus: repair only the runtime resource-authority component. Both valid reviewers reject tuning, scaling, abandon and any immediate representative/DATA/GPU/S1 work. A future retry PASS would only make a separately reviewed representative-window CPU proposal eligible.

Artifacts: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/accession_roundtrip_failed_run_tri_review/`.
# Tri-review: accession-preserving preflight repair failed run — Job 11528885

Date: 2026-08-12 CEST. Quorum: **2/3 DEGRADED_REVIEW**; confidence capped at Medium. Claude and Codex produced independent full-scope reviews; Antigravity produced no structured review because its headless command permission was denied.

| Reviewer | Judgment | Next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `replace-component` | One read-only probe of the installed FamDB leaf API for the six pinned accessions; then choose leaf adapter vs direct HDF5 | Current aggregation assumes an unavailable `FamDBLeaf.added`; science never ran | High |
| B · Codex | `replace-component` | New exp-scoped leaf-level exact-access contract probe, no RepeatMasker; exact-once metadata/consensus match required | Stop rule forbids a third retry; API/schema version mismatch may extend beyond `.added` | Medium |
| C · Antigravity | failed reviewer | none | Headless tool command permission auto-denied; output is not a review | n/a |

Consensus:

- Job `11528885` is a reproducible engineering failed run, not a biological valid-negative and not evidence against annotation-time accession preservation.
- The resource-guard repair succeeded; the next failed component is the FamDB aggregation/export layer.
- A third submission of the current preflight is forbidden. If work continues, it must use a new exp_id and first run a bounded read-only/API contract probe without RepeatMasker.
- Preferred replacement is leaf-level exact accession access with exact-once partition provenance and frozen accession/name/class/length/consensus SHA checks. Direct HDF5 access or official CLI is only a separately reviewed fallback.
- No representative/full DATA, homology construction, GPU S0 or S1 is authorized.

Disagreement: Reviewer A permits an interactive `srun` probe and suggests 1CPU/4GiB/15m; Reviewer B prefers a new exp-scoped probe capped at 1CPU/4GiB/10m. The binding workflow requires the new exp-scoped, reviewed route; no ad-hoc interactive execution is authorized by this synthesis.

Artifacts: `reports/tefm_new_directions/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/job_11528885_tri_review/`.

# Tri-review: F reviewed-runtime closure failed run — Job 11529694

Date: 2026-08-12 CEST. Quorum: **2/3 DEGRADED_REVIEW**, confidence Medium. Claude and Codex independently returned the same judgment; Antigravity output was an irrelevant CLI-flag clarification and is invalid as a review.

| Reviewer | Judgment | Next action | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | `run-sanity-check-first` | Add shared pre-submit script/hash to reviewed_files, fresh delta review, one same-exp exact-resource retry | Gate installation closure only; science completely untested | High |
| B · Codex | `run-sanity-check-first` | Same narrow gate repair and one retry; no other code/config/data change | Runtime set must be fully covered and job artifacts isolated | High |
| C · Antigravity | invalid reviewer | none | Did not follow prompt or inspect evidence | n/a |

Consensus:

- Allocation-side fail-closed behavior was correct. Job `11529694` is a reproducible engineering failed run, not a method failure or valid negative.
- The scientific method, data contract and DEC-001/002 re-entry shape remain untested and unchanged.
- One same-exp sanity retry is allowed only after the shared `scripts/pre_submit_gate.py` SHA is added to machine reviewed_files, all required runtime paths are shown covered, current post-run experiment documentation is re-hashed, and a fresh independent delta review passes.
- Resource and scope stay exact: 8CPU/32GiB/2h/0GPU, no override; Rice T1 positive-only; no whole-genome metrics, GPU, full F or claim.

Reviewer directions preserved: A noted future richer/global evidence only if the scientific audit later returns information-insufficient; B emphasized no scientific code/config/threshold/evaluator changes in this repair. Neither reviewer supports architecture changes now.

Artifacts: `reports/tefm_new_directions/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/job_11529694_tri_review/`.

# Tri-review: F consensus-collinearity valid negative — Job 11531090

Date: 2026-08-12 CEST. Experiment: `FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1`.

## Review mode

- Mode: independent parallel CLI, one shared self-contained evidence prompt.
- Reviewer A: Claude CLI · success.
- Reviewer B: Codex CLI · success; its read-only shell hit a local namespace-capacity error, but the supplied pack was self-contained and the structured review completed.
- Reviewer C: Antigravity CLI · failed after three bounded retries (full, compact and minimal prompts). Every response misread an internal `--print-timeout` argument or returned only a backend header; none contained the required judgment and none is counted.
- Quorum: **2/3 DEGRADED_REVIEW**. Confidence is capped at Medium by workflow policy.

## Inputs and semantic boundary

- Job `11531090`: `COMPLETED 0:0`, 25 s, exact 8CPU/32GiB/2h/0GPU; all input, command, scheduler, environment and payload hashes verify.
- Rice T1 positive-only audit, 756 groups/2,450 immutable leaves/304 topology groups; no unlabelled-as-negative or whole-genome claim.
- Candidate mapped fraction `0.555102`, exact recovery `0.138889`, pairwise harmonic `0.308188`, topology `0.105263`, false fusion `0.075862`, leaf retention `1.0`.
- GAP100 exact recovery `0.371693`, harmonic `0.669109`, topology `0.473684`; paired candidate-minus-comparator bootstrap intervals are wholly negative. Shuffle separation is positive.
- Terminal is a route-local semantic-successful `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`. The historical ACTIVE_GOAL schema mismatch is retained only as an automation stop.

## Reviewer A · Claude

- Judgment: `abandon-route` for the exact seed-chain consensus-collinearity plus chromosome-wide path-cover route.
- Accepts the run as a high-quality valid negative, not a failed run. Concludes the evidence type is fundamentally insufficient rather than merely under-tuned.
- Attributes failure to low exact-mapping coverage, inability of consensus coordinates to distinguish dispersed copies, and an over-strong biological monotonicity assumption.
- Recommends recording a route-level decision and preserving only the broader fragmentation question. Any re-entry needs new evidence, independent development families and the same safety gates.

## Reviewer B · Codex

- Judgment: `abandon-route` for the exact standalone component; keep broader fragmentation research open.
- Accepts dataset/metric/preprocessing/truth isolation and reproducibility; explicitly rejects threshold tuning because the gaps are large and bootstrap-stable.
- Interprets high purity plus low recall as a conservative but severely under-connecting assembler. Notes T1 limits whole-genome interpretation but cannot explain the large same-input comparator gap.
- Recommends a non-compute closure: register the route as abandoned, with new-information and leakage-safe re-entry criteria.

## Reviewer C · Antigravity

- Failed reviewer after all three allowed attempts. Raw outputs are retained and do not count toward quorum.

## Cross-reviewer agreement

- Both valid reviewers accept the result as a trustworthy valid negative and reject promotion, tuning, scaling, Fly/H0 extension or GPU work.
- Both stop the exact combination of standalone exact consensus mapping, monotonic consensus-coordinate DAG and minimum path cover.
- Both preserve the broader fragmentation objective and permit future work only if it introduces genuinely new global/biological evidence rather than a parameter or species/library change.
- Both require the limitation and re-entry criteria to be written durably before leaving the route.

## Disagreement

- There is no binding decision disagreement. Reviewer A emphasizes the biological invalidity of global consensus-coordinate monotonicity; Reviewer B emphasizes insufficient coverage/discriminability and treats genomic proximity only as evidence that the omitted information matters. This affects future mechanism design, not the stop decision.

## Aggregated recommendation

**Abandon route**: close consensus-collinearity as a standalone parent-copy assembler. Preserve its mapper/evidence only as a non-promoted diagnostic observation that carries signal relative to shuffle. Do not run another F experiment now.

## Required re-entry prerequisites

- A new mechanism must add at least one independently justified source of global copy/boundary evidence; seed/stride/margin/tolerance/path-cover tuning, another species or another consensus library is insufficient.
- Evidence and thresholds must be selected on independent development families; Rice T1 remains untouched final audit evidence.
- The new route must retain immutable leaves and truth isolation, exceed substantially higher pre-registered evidence coverage, and pass the existing recovery/boundary/topology/false-fusion/retention gates without genomic-gap-only shortcutting.
- Whole-genome or publication claims additionally require complete T0-like truth and leakage-safe cross-species evaluation.

Raw review pack: `reports/tefm_new_directions/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/job_11531090_tri_review/`.
# Tri-review: S FamDB leaf exact-access failed run — Job 11533175

Date: 2026-08-12 CEST  
Quorum: `2/3 DEGRADED_REVIEW`（Claude 与 Codex 有效；Antigravity 三次 bounded retry 均返回与 `--print-timeout`/headless 权限有关的无关文本）  
Evidence pack: `reports/tefm_new_directions/SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1/job_11533175_tri_review/`

### 共同事实判断

- 两位有效 reviewer 都接受 `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`：科学 payload 不存在，不能把“probe 在内存返回”推断成 exact-access PASS 或 typed block。
- 两位都认为失败组件是 read-mode lifecycle/result publication，而不是已证实的 accession query 机制失败。
- 当前不得开放 leaf adapter、RepeatMasker、representative/full DATA、homology、GPU direct S0 或 S1。

### 独立意见

- Claude：`run-sanity-check-first`，confidence=Medium。允许最后一次只改 read-mode handle closure 与结果先行 staging 的低成本修复；再次任何 API/lifecycle 失败即永久关闭。
- Codex：`replace-component`，confidence=High。将 lifecycle/publication 视为被替换组件；科学 72-call probe必须逐字保持，fresh review 后仅一次 CPU attempt。
- Antigravity：invalid。初次及三次 retry 均未产生要求的结构化评审，不计入科学 quorum。

### Quorum conclusion

标签不同但行动一致：允许一个**新的、单独审查的 close-only lifecycle repair**，不允许直接重跑旧代码。硬条件为：read mode 不调用 `FamDB.finalize()`；显式关闭 HDF5 handles；观察在 cleanup 前进入不可变 staging；合成测试证明 cleanup failure 不擦除或升级结果；正式科学调用仍恰好一次 6×12=72 calls；旧 gate 不复用；资源仍为 1CPU/4GiB/10m/0GPU。任何再次 API/lifecycle/runtime/integrity failure，或正式 missing/duplicate/drift typed block，都永久关闭 FamDB access/export 路线。

---
