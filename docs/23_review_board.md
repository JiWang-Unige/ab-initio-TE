# Review Board Audit Trail / 评审板审计日志

> 本文档由 `/review-board` 维护，记录对设计方案、争议文档、架构决策的背对背独立会诊记录。

## Audit Entries

### Review Board 2026-07-01 — postprocess threshold and length-adaptive fragmentation diagnostic
- **Reviewer Quorum**: 3/3 effective quorum (Claude, Codex, Antigravity).
- **Reviewed Docs/Context**: `docs/09_decisions_log.md` (`DEC-001`, `DEC-002`), `reports/tefm_capability/PIPE-TEFM-CAP-POSTPROC-20260701/POSTPROCESS_THRESHOLD_REPORT.md`, `postprocess_threshold_metrics.tsv`, `postprocess_true_length_bins.tsv`.
- **Audit Summary**:
  - **Consensus**: multi-threshold/postprocess results are useful as a sensitivity and tradeoff audit, not as a promoted TE interval module.
  - **Consensus**: report per-panel Pareto curves and guardrails; do not pool human/mouse into one winner and do not pick an "optimal threshold" from this already-viewed screen.
  - **Consensus**: HMM/gap/length-adaptive rows that improve segment-F1 must be vetoed when they delete too many true-backed fragments.
  - **Risk**: true short fragments, nested TE, and annotation fragmentation mean that reducing fragment counts alone can be biologically wrong.
- **Recommended Action**: include the postprocess table/curve as supporting evidence for why strict interval reconstruction remains hard; do not reopen DEC-001/DEC-002 as a method route.
- **User Decision**: answered within the current capability diagnostic; no new training route launched.

### Review Board 2026-06-30 — lane/docs architecture update
- **Reviewer Quorum**: Council 2/3 DEGRADED (Claude auth failed; Codex + Antigravity succeeded); independent architecture review 2/3 DEGRADED after retry (Claude auth failed; Codex + Antigravity succeeded).
- **Reviewed Docs/Context**: `CLAUDE.md`, `AGENTS.md`, `README.auto-research.md`, `README.md`, `ARCHITECTURE.md`, `.claude/skills/*`, `docs/23_review_board.md`, `docs/24_sprint_pursue_ledger.md`.
- **Audit Summary**:
  - **Consensus**: do not renumber `docs/00-22`; keep them as the stable compatibility contract and append `docs/23` / `docs/24`.
  - **Consensus**: add distinct middle-lane skills for single evidence questions and multi-round capability programs; keep `$pursue` narrowed to claim/SOTA.
  - **Consensus**: add `$review-board` rather than overloading `$tri-review`; keep `$tri-review` for post-result pivot decisions and `$council` for adversarial route debates.
  - **Required fixes applied**: tightened no-claim and user-gated promotion boundaries, added review-board negative boundaries/quorum rule, replaced absolute `file://` example link, and synchronized `.agents/.codex` plus `AGENTS.md`.
- **Recommended Action**: use `$evidence-sprint` for 1-2 action evidence questions, `$capability-pursue` for 2-5 round original capability components, `$review-board` for non-result independent review, and `$pursue` only for claim/SOTA autonomous loops.
- **User Decision**: user requested at least `$evidence-sprint` + `$capability-pursue`; implementation includes those plus `$review-board`.

### Example Entry: Review Board <YYYY-MM-DD> — [议题名称]
- **Reviewer Quorum**: 3/3 (A=Claude, B=Codex, C=Antigravity)
- **Reviewed Docs/Context**: `docs/03_benchmark_roadmap.md`
- **Audit Summary**:
  - **Consensus**: 三方均同意新设计中引入 CRF head 对小样本可能过拟合，需增加 validation screen 比例。
  - **Disagreements / Blindspots**: Codex 认为应完全舍弃 GNN backbone，而 Claude 认为保留 GNN backbone 作为对比基线对审稿有利。
- **Recommended Action**: 保留 GNN backbone 作为 contrast comparator，但优先配置 CRF head 的 screen 资源。
- **User Decision**: 已采纳建议，修改 docs/03 路径，由 `/benchmark-roadmap` 完成。
