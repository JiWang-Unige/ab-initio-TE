# Decisions Log (read before each new iteration)

每次 /goal-prompt 生成新迭代前,Claude 必须先读完整个本文件,确认新方向与任何 abandoned route 都没有 unexplained overlap。

如果新方向落在某个 cousin 列表里,必须在 /goal command 的「差异化说明」段明确写"这次为什么不同",或考虑放弃。

**注意:单次实验失败不进本文件**,进 docs/06_results_log.md 就够。只有 /tri-review + /pivot 决定 abandon 整条 route 才进这里。

每个 entry 用 ## DEC-<NNN>: <route name> 开头。模板见 /decisions-log SKILL.md。

---

## DEC-001: structured decoder fragmentation objectives for TE interval cleanup

- **Date** (UTC): 2026-06-30
- **Abandoned by**: pivot decision `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-pursue-retconstr-20260630`
- **Evidence base**: result-log entries `PIPE-TEFM-STRUCTDEC-20260630`, `PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630`, `PIPE-TEFM-PURSUE-MINHASH-INTERVALSURV-20260630`, and `PIPE-TEFM-PURSUE-RETCONSTR-20260630`; tri-review `docs/07_tri_review.md#tri-review-pipe-tefm-pursue-retconstr-20260630`
- **Resource profile of evidence**: bounded screen, single seed `42`

### What was tried

The route tested trainable structured decoder objectives attached to GENERanno token logits, including joint HMM/CRF-style losses, semi-Markov proxy, boundary auxiliary loss, interval-survival objective, segment-aware rescue decoding, and a final retention-constrained interval loss with raw-evidence veto. These were intended to reduce fragmented TE interval predictions while preserving true TE segments under strict segment-F1@IoU0.8 and boundary-F1@5bp metrics.

### Why it failed

The family showed a consistent structural tradeoff rather than a simple optimization issue. Interval/survival-style objectives improved segment and boundary metrics only by deleting many true-backed fragments (`deleted_true_backed_fraction` up to `0.4592`). The final retention-constrained objective reduced missed_true_rate and lowered true-backed deletion, but strict segment-F1 and boundary-F1 fell below the CE baseline and deletion still exceeded the hard `0.15` guardrail.

### What we now believe

Current Markov/survival/retention structured decoder objectives are useful diagnostics for the fragmentation tradeoff, but they are not a deployable fragmentation solution for this milestone. The defensible reporting path is CE baseline plus existing overlap/smoothing for annotation support, with structured interval-aware decoding framed as future work.

### Cousin list (also avoid)

| Cousin | How similar | Re-allowed if |
|---|---|---|
| More threshold/gap/post-hoc HMM/CRF penalty tuning | Same failure mode: suppresses fragments without proving true-backed retention | A new evaluator or theory shows a fixed post-hoc rule can distinguish false fragments from true-backed fragments under `deleted_true_backed_fraction <= 0.15` |
| Another semi-Markov / duration-prior / survival-loss tweak | Shares the duration/survival prior that pruned true short fragments | A new objective directly models true-backed fragment survival and passes a fresh smoke on the same strict CE-relative gates |
| Frozen-logit interval refiner with only local probability/gap features | Already failed to beat existing smoothing and lacks sequence/interval evidence | It adds genuinely new interval evidence such as supervised proposal labels, sequence embedding, strand agreement, or family consistency and passes a small leak-checked smoke |
| Center-offset/boundary head that still deletes low-confidence candidate intervals | Same deletion-risk mechanism if no true-retention guardrail is built in | It optimizes deletion guardrail as a primary constraint and demonstrates segment/boundary gains plus `deleted_true_backed_fraction <= 0.15` before any scale-up |

### Re-entry criteria

This route may be reopened only if all apply:

- [ ] A substantially different mechanism is proposed, not another Markov/survival/retention penalty tweak.
- [ ] The training objective directly optimizes or constrains true-backed fragment retention.
- [ ] The first smoke keeps CE baseline in the same job and requires segment-F1 delta > 0, boundary-F1 delta > 0, missed_true_rate delta <= 0.03, and deleted_true_backed_fraction <= 0.15.
- [ ] The experiment is explicitly scoped as non-claim until it passes the strict guardrails.

### Links

- Related result log: `docs/06_results_log.md#result-pipe-tefm-pursue-retconstr-20260630`
- Related tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-pursue-retconstr-20260630`
- Related pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-pursue-retconstr-20260630`

---

## DEC-002: frozen/post-hoc interval reconstruction modules for TE fragmentation

- **Date** (UTC): 2026-07-01
- **Abandoned by**: pivot decision `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-cap-fraggraph-20260701`
- **Evidence base**: result-log entries `PIPE-TEFM-CAP-FRAGARCH-20260701` and `PIPE-TEFM-CAP-FRAGGRAPH-20260701`; tri-reviews `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fragarch-20260701` and `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fraggraph-20260701`
- **Resource profile of evidence**: bounded capability-pursue screen, single seed `42`, small human/mouse panel

### What was tried

The capability branch tested new interval-level components intended to turn strong bp-level TE signal into complete TE segments under strict metrics. Round 1 tested two lightweight interval-aware heads on frozen GENERanno 4096 embeddings/logits: `boundary_proposal` and `anchor_free_interval`. Round 2 replaced those heads with a fragment graph linker that converts CE raw fragments into graph nodes and learns adjacent fragment links, with a preservation-first `fragment_graph_keepall` decoder and a diagnostic learned keep/drop decoder.

### Why it failed

The failures split into two modes. Preservation-first decoders avoided deleting true-backed fragments but failed to improve interval quality: `fragment_graph_keepall` was identical to CE raw on both human and mouse. Components that improved strict interval metrics did so by deleting true-backed fragments: `anchor_free_interval` had high deleted true-backed fractions in Round 1, and `fragment_graph_keepdrop` improved human segment-F1/boundary-F1 to `0.4964`/`0.2458` only with `deleted_true_backed_fraction=0.8632`, while failing the mouse smoothing comparator.

### What we now believe

Frozen or post-hoc interval reconstruction modules built on CE fragments, local probability tracks, or frozen embeddings are not a publishable TE fragmentation solution in this project. They remain useful diagnostics for the tradeoff between interval cleanup and true-fragment deletion, but not a reusable interval-level annotation module. Existing overlap/smoothing can remain as fixed comparators or practical heuristics, not as a solved biological segment decoder.

### Cousin list (also avoid)

| Cousin | How similar | Re-allowed if |
|---|---|---|
| Another frozen boundary/proposal/center-length head on the same CE/frozen embeddings | Same Round-1 failure mode: shallow interval heads suppress or reshape fragments without proving true-backed retention | It introduces end-to-end training or global matching and passes the strict CE-relative gates on at least two chromosomes/species |
| Another fragment graph linker with only local probability/gap/embedding similarity features | Same Round-2 failure mode: safe keep-all does nothing; keep/drop deletion appears as false progress | It learns links without any deletion path and demonstrates nontrivial interval gains with `deleted_true_backed_fraction <= 0.15` |
| Boundary-conditioned span refiner that starts from CE fragments and can drop/trim weak fragments | Likely overlaps the same post-hoc reconstruction/deletion tradeoff | It is constrained as no-delete or true-retention-primary, improves segment-F1 and boundary-F1 over CE and smoothing, and passes mouse plus human screens |
| Rebranding threshold/gap/HMM/CRF/survival-retention tweaks as interval modules | Already covered by DEC-001 and this DEC; they do not add a new mechanism | A new biological/evaluator audit shows the rule specifically preserves true-backed fragments while deleting false fragments |

### Re-entry criteria

This route may be reopened only if all apply:

- [ ] The mechanism is not a frozen/post-hoc repair module over CE fragments or local probability tracks.
- [ ] The objective performs global interval/set prediction or uses substantially richer biological evidence, not only local fragment/gap features.
- [ ] The first bounded smoke keeps CE raw and smoothing comparators in the same job.
- [ ] It passes segment-F1@IoU0.8 and boundary-F1@5bp against both CE and smoothing, with missed_true_rate <= CE+0.03 and deleted_true_backed_fraction <= 0.15.
- [ ] The gain holds on at least two chromosomes or species-level screens before any publication wording beyond future work.

### Links

- Round 1 result log: `docs/06_results_log.md#result-pipe-tefm-cap-fragarch-20260701`
- Round 1 tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fragarch-20260701`
- Round 1 pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-cap-fragarch-20260701`
- Round 2 result log: `docs/06_results_log.md#result-pipe-tefm-cap-fraggraph-20260701`
- Round 2 tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-cap-fraggraph-20260701`
- Round 2 pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-cap-fraggraph-20260701`
## DEC-003: Dfam 3.9 post-hoc exact identity recovery for the current RepeatMasker annotation snapshot

- **Date**: 2026-08-12
- **Decision**: abandon/close this route after final grammar-repair Job `11528267` and 3/3 tri-review.
- **What was tried**: indexed FamDB lookup, partition-3 index-independent full scan, Dfam 3.9 curated EMBL exact NM/PI/SN/DR/AC/ID crosswalk, full DF+DR EMBL target-only scan, and official PI/DR grammar repair.
- **Final evidence**: 50/279 identifiers resolve uniquely, 2 remain ambiguous and 227 remain missing; 73.229% occurrence mass lacks authoritative identity. Full raw DR adds zero exact support after grammar-complete scanning.
- **Cousins prohibited**: prefix/case-fold/substring/suffix guessing; current API backfill; RMRBMeta chaining without a version-matched authoritative bridge; copy-derived/genome-copy consensus; taxonomy inference; dropping unresolved identifiers; choosing one fragment for L1HS/L1PREC2; repeating/scaling the same Dfam 3.9 source scan.
- **Re-entry criteria**: a new official, versioned, hash-pinned explicit identifier-to-accession/consensus source for the frozen denominator, or explicit user approval of a new annotation-time accession-preserving benchmark/data contract. Either path requires fresh comparability review and CPU data gates before GPU.

---

## DEC-004: standalone consensus-collinearity parent-copy assembly

- **Date** (UTC): 2026-08-12
- **Abandoned by**: `docs/08_pivot_decisions.md#pivot-decision-abandon-standalone-consensus-collinearity-parent-assembly-after-job-11531090`
- **Evidence base**: Job `11531090` result log and `docs/07_tri_review.md#tri-review-f-consensus-collinearity-valid-negative--job-11531090`
- **Resource profile of evidence**: bounded Rice T1 positive-only CPU information-sufficiency screen, 8 CPU/32 GiB/2h/0GPU; 1,000 chromosome-block bootstrap replicates

### What was tried

Immutable Rice T1 positive fragments were mapped by frozen exact seed-chain evidence to consensus identity, strand and coordinates. A chromosome-wide DAG and deterministic minimum path cover then grouped leaves using same-consensus, same-strand monotonic consensus coordinates, without truth IDs, genomic-gap joins or leaf deletion.

### Why it failed

The evidence carried real signal relative to a shuffled null, but it was not sufficient to discriminate dispersed biological copies. Only `55.51%` of leaves mapped; exact recovery was `13.89%` versus GAP100's `37.17%`; pairwise harmonic was `30.82%` versus `66.91%`; topology preservation was `10.53%` versus `47.37%`; and cross-RM-ID false fusion `7.59%` exceeded the `5%` ceiling. Candidate-minus-comparator bootstrap intervals were wholly below zero. The failure is mechanistic—coverage and copy discriminability—not a near-threshold optimization issue.

### What we now believe

Consensus identity/strand/coordinate evidence is useful as an auxiliary channel but is not a standalone parent-copy assembler. TE copies sharing a consensus are dispersed genomic insertions; consensus-coordinate monotonicity alone does not identify which fragments belong to one copy. A successful global method must incorporate substantially richer copy/boundary evidence while preserving immutable leaves and leakage-safe truth isolation.

### Cousin list (also avoid)

| Cousin | How similar | Re-allowed if |
|---|---|---|
| Retuning k-mer size, stride, posting cutoff, diagonal tolerance, coverage margin or winner margin on Rice T1 | Same evidence bottleneck and test-family tuning risk | Thresholds are selected on disjoint development families and a new evidence source removes the coverage/discriminability failure before Rice evaluation |
| Replacing minimum path cover with another deterministic partition over only consensus identity/strand/coordinates | Same standalone evidence and biological monotonicity assumption | The partition adds independently justified global copy/boundary evidence and passes the same frozen gates |
| Repeating the same mechanism on FlyBase, H0, another Rice subset or another consensus library | Species/library change cannot repair the missing information demonstrated on the frozen same-input comparison | A pre-registered new mechanism first passes an independent development audit; no result-driven species hopping |
| Adding only a genomic-gap threshold to the current join | Collapses back toward DEC-001/002 diagnostic/local postprocessing cousins | Gap is not the sole decision rule and a genuinely richer global model passes immutable-leaf, false-fusion and topology gates |
| Treating consensus collinearity as a promoted module because it beats shuffle | Confuses “contains signal” with “information sufficient” | It is only one auxiliary feature inside a separately reviewed architecture that beats registered comparators |

### Re-entry criteria

This route may be reopened only if all apply:

- [ ] A new, independently motivated global copy/boundary evidence source is added; parameter, species, library and partition-rule changes alone do not qualify.
- [ ] Evidence construction and thresholds are frozen on family/homology-isolated development data; Rice T1 is not used for model or threshold selection.
- [ ] Immutable leaves, evaluator-only truth and positive-only metric boundaries remain intact.
- [ ] A bounded CPU falsification first demonstrates materially higher usable evidence coverage and passes the existing recovery, boundary, topology, false-fusion and retention gates against registered comparators.
- [ ] Any whole-genome/publication claim adds complete biological truth beyond T1 and leakage-safe cross-species evaluation.

### Links

- Related result log: `docs/06_results_log.md#result-frag-consensus-collinearity-audit-20260812-r1--final-retry-job-11531090`
- Related tri-review: `docs/07_tri_review.md#tri-review-f-consensus-collinearity-valid-negative--job-11531090`
- Related pivot: `docs/08_pivot_decisions.md#pivot-decision-abandon-standalone-consensus-collinearity-parent-assembly-after-job-11531090`
