# Framework Upgrade Log / 框架升级记录

> 由 `/framework-upgrade` 维护。记录 auto-research 框架自身的版本迁移、兼容修复、新 skill/doc/hook 引入，以及哪些研究内容被保留。

## Upgrade Entries

### Upgrade 2026-06-13 — v4.0 → v4.1
- Reason: 补齐框架升级、同项目重开线、代码审前闸、evaluator/baseline 中央留档，以及人闸前通俗摘要规则。
- Files changed: `CLAUDE.md`, `README.auto-research.md`, `ARCHITECTURE.md`, `.claude/skills/*`, `scripts/*`, `docs/15-22`, install/sync scripts, hooks.
- Skills added/updated: added `/framework-upgrade`, `/route-reset`, `/code-review-gate`; updated `/implement`, `/pursue`, `/goal-prompt`, `/reproduce-baselines`, `/benchmark-roadmap`, `/artifact-registry`, `/master-plan`, `/council`, `/reframe`, `/workspace-matrix`, `/note-gate`.
- Docs added/updated: added `docs/19_evaluator_contract.md`, `docs/20_baseline_reproduction.md`, `docs/21_code_review_log.md`, `docs/22_upgrade_log.md`; updated `docs/15/16/17`.
- Scripts/hooks changed: `context_pack.py`, `research_flow_guard.py`, `iter_ledger.py`, `artifact_registry.py`, `note_gate.py`, `guard_paths.sh`, `submit_guard.sh`, `iter_record_nudge.sh`, `research_bootstrap.sh`, `install.sh`, `sync_agents_md.sh`.
- Research content preserved: no research result, refs, wiki, runs, outputs, data, secrets, ACTIVE_GOAL, or cluster_config was overwritten.
- Compatibility checks: `build_codex_skills.py`, `validate_codex_skills.py`, `sync_agents_md.sh`, `context_pack.py --purpose iterate`, `research_flow_guard.py`, `iter_ledger.py`, and new skill quick validators completed; false-positive stage guards were fixed.
- Required follow-up: review `git status`, then make one lightweight initial commit if the tracked file set looks right. No automatic commit was made.
- Rollback note: revert this upgrade by restoring the touched framework files from git/backup once git is initialized or from external backup; do not delete docs/19-22 if they already contain later project evidence.

### Upgrade <date> — <from> → <to>
- Reason:
- Files changed:
- Skills added/updated:
- Docs added/updated:
- Scripts/hooks changed:
- Research content preserved:
- Compatibility checks:
- Required follow-up:
- Rollback note:

### Upgrade 2026-06-30 — v4.1 → v4.2 lane-split
- Reason: User requested framework refresh from `/home/users/j/jwang/auto-research-portable-v4.2-lane-split-20260630.tar.gz` to introduce the lane-split middle layer: `$evidence-sprint`, `$capability-pursue`, `$review-board`, `docs/23_review_board.md`, and `docs/24_sprint_pursue_ledger.md`.
- Files changed: refreshed framework entry files `CLAUDE.md`, `AGENTS.md`, `README.auto-research.md`, `README.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, driver shell config/templates under `.claude/`, `.codex/`, `.agents/`, `agents/openai.yaml`, `cluster_config.yaml.example`, `secrets.env.example`, `.mcp.json.example`, `.gitignore`, and framework scripts/hooks.
- Skills added/updated: added `$evidence-sprint`, `$capability-pursue`, and `$review-board`; regenerated `.agents/skills` and `.codex/skills` from canonical `.claude/skills`.
- Docs added/updated: seed-if-absent created `docs/23_review_board.md` and `docs/24_sprint_pursue_ledger.md`; `docs/00-22*.md` were preserved except for this upgrade-log append and the evidence-register row documenting the upgrade.
- Scripts/hooks changed: refreshed v4.2 framework scripts from the release tarball, including `context_pack.py`; preserved project-specific `scripts/experiments/` code.
- Research content preserved: `docs/00-22`, existing project-specific docs such as `docs/23_te_refinement_publication_route.md`, `refs/`, `wiki/`, `runs/`, `outputs/`, `reports/`, `pipelines/`, `configs/`, `ACTIVE_GOAL.json`, `secrets.env`, and any existing cluster runtime configuration were not overwritten. `cluster_config.yaml` was absent at upgrade time; only `cluster_config.yaml.example` was refreshed.
- Compatibility checks: upgrade audit completed before copying; `python3 scripts/build_codex_skills.py .` completed with total cross-agent description budget 6157 chars; `python3 scripts/validate_codex_skills.py .` passed for `.agents/skills` and `.codex/skills`; `bash scripts/sync_agents_md.sh` regenerated `AGENTS.md`; `python3 scripts/context_pack.py --purpose iterate` completed and includes docs/23/24. `python3 scripts/research_flow_guard.py . --format markdown` returned the pre-existing Stage-A warning that `docs/02` has no usable candidate model inventory and recommends `$sota-inventory`; this is a research-stage guard, not an upgrade validation failure.
- Required follow-up: if using git later, initialize or attach a repo before expecting `git status`; current workspace is not a git repository. Use `$evidence-sprint` for one-question evidence checks, `$capability-pursue` for bounded 2-5 round component work, `$review-board` for non-result independent review, and keep `$pursue` for claim/SOTA-goal loops.
- Rollback note: restore the refreshed framework files from the v4.1 backup/source if needed, but do not delete `docs/23_review_board.md` or `docs/24_sprint_pursue_ledger.md` once they contain project evidence.

## Compatibility Decisions
| Date | Decision | Reason | Affected files | Revisit condition |
|---|---|---|---|---|
| 2026-06-13 | Initialize git, but do not commit automatically | Framework/docs/scripts are now complex enough to need version history; heavy artifacts, secrets, cloned repos, PDFs, and runtime outputs remain ignored. | `.git/`, `.gitignore`, `.git/info/exclude`, `docs/17_parallel_workspace.md` | Revisit before first worktree cohort or if `.gitignore` would include sensitive/heavy files. |
| 2026-06-13 | Put per-run generated scripts under `scripts/experiments/<exp_id>/` | The existing contract separated reusable scripts and sbatch/results, but did not name a home for one-off wrappers that affect a run. | `docs/16_artifact_registry.md`, `PROJECT_STRUCTURE.md`, `scripts/artifact_registry.py`, `/artifact-registry`, `/implement`, `CLAUDE.md`, `AGENTS.md`, `README.auto-research.md`, `ARCHITECTURE.md` | Revisit if pipeline stages need a different namespace; pipeline DAG code still belongs under `pipelines/<pipeline_id>/`. |
