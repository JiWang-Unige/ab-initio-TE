# Lightweight Auto-Research Architecture · v4.1

This package is a portable Claude/Codex/Antigravity auto-research workflow. It uses prompt discipline, reusable skills, lightweight docs, optional subagents for speed, Slurm planning, external CLI tri-review, deterministic context rebuild, and a Chinese-first research-memory layer. It intentionally does **not** include a heavy runtime/state-machine layer; optional git/worktree support is a human-gated isolation layer, not a required state backend. The framework recommends git for framework/lightweight research memory, but never for data, checkpoints, secrets, or full runtime state. Files under `docs/`, `refs/`, `wiki/`, `runs/`, and `reports/` are the source of truth.

## Package layout

```text
CLAUDE.md / AGENTS.md              driver instructions; AGENTS is generated from CLAUDE
.claude/skills/<skill>/SKILL.md    Claude skills
.agents/skills/<skill>/SKILL.md    Codex/Antigravity short-description skills generated from Claude skills
.codex/skills/<skill>/SKILL.md     mirror for Codex loaders that expect this path
scripts/                           reliability helpers, hooks, reusable project scripts
scripts/experiments/<exp_id>/      per-run generated wrappers that affect results
cluster_config.yaml.example        Slurm + CLI reviewer config
docs/                              lightweight research memory
docs/11_master_plan.md             user-facing navigation map
docs/12_publication_strategy.md    paper/venue/contribution strategy
docs/13_pipeline_blueprint.md      raw-data/pipeline DAG + IO contract
docs/14_validation_matrix.md       downstream/generalization/statistics matrix
docs/15_evidence_register.md       smart capture index
docs/16_artifact_registry.md       directory/artifact contract
docs/17_parallel_workspace.md      optional git/worktree parallel-code isolation contract
docs/18_runtime_playbook.md        driver switch, migration, Baobab srun, compact recovery
docs/19_evaluator_contract.md      metric/evaluator/split/claim comparability contract
docs/20_baseline_reproduction.md   baseline/SOTA reproduction central ledger
docs/21_code_review_log.md         pre-submit code-review gate log
docs/22_upgrade_log.md             framework upgrade and compatibility log
docs/23_review_board.md            评审板独立会诊审计日志
docs/24_sprint_pursue_ledger.md    分层推进与证据短跑台账
refs/                              archived papers, repos, supplementary files, dossiers
wiki/                              searchable ideas and notes
configs/ sbatch/ runs/ reports/ outputs/ logs/  experiment bundles
worktrees/                         optional git worktrees for parallel shared-code edits
software_outputs/                  external tool raw outputs with command/version/hash
pipelines/                         pipeline stage scripts/wrappers
data/{raw,interim,processed}/      data layers
```

Use skills as `/skill-name` in Claude and `$skill-name` in Codex.

---

## Three work modes

| Mode | When | Primary skills | Primary docs |
|---|---|---|---|
| Discovery-Iteration | Direction unclear; need to find a SOTA-beating model | `/research-interview → /sota-inventory → /benchmark-roadmap → /pursue` | docs/00-10 |
| Publication-Validation | Strong idea/model already exists; goal is publishable evidence | `/master-plan → /publication-plan → /generalization → /sota-randomized` | docs/11/12/14/15 |
| Pipeline-Execution | Fixed raw-data/bioinformatics analysis pipeline | `/master-plan → /pipeline-blueprint → /artifact-registry` | docs/11/13/16 |

The modes can be mixed. The critical rule is that `docs/11_master_plan.md` states the current mode, the current step, why this step comes before the next, and which user choices are already fixed. Use `/route-reset` when a route needs to restart from Stage A or switch from Discovery to Publication/Pipeline inside the same project without overwriting prior evidence.

---

## Language policy

Research memory and reports default to Simplified Chinese. Deep research prompts are bilingual by design: prose output should be Chinese, while search terms, paper titles, models, datasets, metrics, repository names, commands, and URLs stay in English/original form. This keeps discussion efficient for the user while preserving English academic retrieval quality.

---

## Core flow

```text
Stage A · before experiments, user-led
[A0 cold import] /ingest-existing   (subagents survey prior code/results/notes/data/refs → digest → co-decide goal/mode → backfill docs)
/research-interview
  → external deep research by user (Chinese report + English retrieval terms)
  → /research-synthesize
  → /sota-inventory
  → /grill                          (two-phase: co-develop idea + adversarially pin specifics)
    → [optional] /council           (foundation-critical/contested direction: Claude/Codex/Antigravity DEBATE across rounds + user arbitrates)
    → [optional] /review-board      (independent tripartite review of design/documents/dilemmas; no exp_id needed)
  → /configure-project              (AI fills CLAUDE/cluster_config/ACTIVE_GOAL + seeds docs/11; human-gated)
  → /benchmark-roadmap
  → /sota-randomized if a fair screen anchor is needed
  → /reproduce-baselines            (verify metric/dataset ground truth; hook gate before /goal)
  → /goal-prompt

Stage B · experiment iteration, /goal-driven
/generated goal, /pursue, /evidence-sprint, or /capability-pursue
  → declare Track A or Track B
  → optional subagent fan-out
  → /implement
  → /code-review-gate
  → comparability + data contract checklist
  → /smart-sbatch
  → train/evaluate or submit-and-handoff
  → /result-log
  → /note-gate
  → /tri-review
  → /pivot
  → maybe /decisions-log
  → maybe /generalization

Stage C · mature idea / publication / pipeline
/master-plan
  ├─ publication branch: /publication-plan → /sota-randomized? → /generalization → /note-gate
  └─ pipeline branch:    /pipeline-blueprint → /artifact-registry → execute stages → /note-gate

Strategic route reset / framework maintenance
/reframe → /route-reset              (rerun Stage A, fork route, or switch A/B→C with carry-forward)
/framework-upgrade                   (v3→v4/v4.x compatibility upgrade, preserving research content)
```

Stage A should not autopilot through major research choices. Stage C is also user-visible and plan-like: it replaces blind exploration with evidence-gap execution.

---

## Track A / Track B / randomized SOTA baselines

### Track A · screen architecture

Track A is fast architecture search under small data/epoch budgets. It asks: **is this architecture family promising enough to scale?** Screen results never claim SOTA.

### Randomized SOTA screen anchor

Published full-data SOTA cannot serve as a small-sample screen anchor. `/sota-randomized` re-trains verified SOTA baselines under the same screen protocol with multiple random seeds and records mean±std in `docs/14_validation_matrix.md`. This closes the fairness gap between “SOTA prediction on small sample” and “SOTA random-init retraining on small sample.”

### Track B · scale promising candidates

Track B receives candidates promoted from Track A and uses larger sample/full data, more epochs, more seeds, and full/scale resource profiles. If Track B does not improve with more data, suspect architecture non-scalability before tuning.

---

## Subagent acceleration policy

Use subagents when the work can be split into independent, bounded, mostly read-only branches. Do **not** use subagents as tri-review reviewers; tri-review uses external CLIs.

| Stage | Subagent use | Owner of final write |
|---|---|---|
| `/research-synthesize` | one subagent per deep research report to extract claims/conflicts | main agent merges docs/01 |
| `/sota-inventory` | one subagent per model/paper or batch to verify paper/GitHub/weights/dataset/metrics; `source-artifact-archivist` can archive one slug into refs/ | main agent writes docs/02 |
| `/benchmark-roadmap` | metric/fairness audit, dataset readiness audit, architecture weakness audit | main agent discusses with user, then writes docs/03 |
| `/ingest-existing` | `project-cartographer` maps old code/results/notes/data/refs/manuscript without editing | main agent proposes import + directory cleanup |
| `/publication-plan` | read-only evidence/venue/figure risk audits | main agent writes docs/12/14 |
| `/pipeline-blueprint` | read-only software/QC/input manifest audits | main agent writes docs/13/16 |
| implementation before sbatch | implementation-plan reviewer, leakage reviewer, sbatch/runtime reviewer through `/code-review-gate` | main agent applies edits; submission blocked on code-review blockers |
| `/generalization` | one subagent per evaluation dimension | main agent composes final completeness plan |

Hard rules: read-only subagents do not edit files; writing subagents must have isolated file scopes; the main agent owns final synthesis, user-facing decisions, and docs writes; `/pivot` is never parallelized.

---

## Enforcement coverage map

| Discipline | Mechanism | Layer |
|---|---|---|
| Session/compaction recovery | `context_pack.py` includes master plan, active goal, recent results, findings, publication/pipeline docs, evidence register | script |
| User navigation | `/master-plan` updates `docs/11_master_plan.md`; `session_status.sh` prints mode/current action | skill + hook |
| Run completion recording | `iter_record_nudge.sh` nudges `/result-log → /note-gate → /exp-log`; `iter_ledger.py` audits docs/04/05/06 and STATUS | hook + script |
| Discussion not lost at compaction | `precompact_flush.sh` (PreCompact) reminds to `/note-gate` + `/master-plan` before the transcript is compressed (chat-only info dies; only on-disk survives) | hook |
| Goalpost-move guard | `iter_record_nudge.sh` flags direct ACTIVE_GOAL.json edits → should go through `/revise-goal` (human gate + tri-review comparability) | hook |
| Stage-C completeness | `validate_stage_c.py` (publication: claim↔run↔figure + readiness; pipeline: stage/QC) — advisory, `--strict` gates | script |
| Evidence ID allocation | `next_evidence_id.py` hands note-add/note-gate a collision-free `E<NNN>` | script |
| Smart capture | `/note-gate` + `scripts/note_gate.py` routes metrics, decisions, preferences, failures, papers, pipeline outputs to durable docs | skill + script |
| Evaluator contract | `docs/19_evaluator_contract.md` maintained by `/benchmark-roadmap`, `/reproduce-baselines`, `/code-review-gate`, `/result-log` | docs + skill |
| Baseline reproduction ledger | `/reproduce-baselines` writes `docs/20_baseline_reproduction.md` plus refs/dossiers | skill + docs |
| Code-review gate | `/code-review-gate` writes `docs/21_code_review_log.md`; `iter_record_nudge.sh` reminds after config/job edits | skill + hook |
| Route reset | `/route-reset` rewrites `docs/11` pipeline map with carry-forward/park/abandon ledger | skill + human |
| Framework upgrade | `/framework-upgrade` writes `docs/22_upgrade_log.md`; build/sync scripts keep shell layers compatible | skill + scripts |
| Fair screen anchor | `/sota-randomized` + `scripts/sota_seed_matrix.py` creates deterministic seed/sample manifests | skill + script |
| Pipeline artifact placement | `/artifact-registry` + `docs/16_artifact_registry.md` + `scripts/artifact_registry.py` | skill + script |
| Stage order guard | `research_flow_guard.py` + `stage_flow_nudge.sh` warns if `/grill`, `/configure-project`, screen-anchor, or baseline reproduction are skipped | hook + script |
| SOTA source failure reporting | `sota_failure_report.py` aggregates failed PDF/repo/weights/supp links for manual user help | script + hook |
| Parallel shared-code isolation | `/workspace-matrix` + `docs/17_parallel_workspace.md` + `scripts/workspace_matrix.py` creates optional git worktrees, max 3, no auto merge/commit | skill + script + human |
| Data leakage checks | `check_data.py` inside `/implement`; `/code-review-gate` reviews leakage assumptions before submission | script + skill |
| Slurm/resource policy | `/smart-sbatch` + `submit_guard.sh` | skill + hook |
| Continue/stop decision | `validate_goal.py` four-state gate | script |
| Ghost run detection | `iter_ledger.py` stale signal for RUNNING with no live process/job | script |
| Claim before success | full/scale only, comparability/data contract, tri-review quorum, human gate | skill + human |
| Dual-shell zero drift | `sync_agents_md.sh` and `build_codex_skills.py` | script |

Hooks remind or block; they do not execute skills. The agent still calls `/result-log`, `/note-gate`, `/tri-review`, `/pivot`, etc.

---

## Directory and artifact contract

The framework separates reusable code, per-run config, full training state, metric summaries, and external tool outputs:

```text
scripts/                       reusable helpers
scripts/experiments/<exp_id>/   per-run generated wrappers that affect results
pipelines/<pipeline_id>/        pipeline stage wrappers
configs/<exp_id>.yaml           run config
sbatch/<exp_id>.sbatch          Slurm submission
runs/<exp_id>/                  checkpoint/full training state
reports/<exp_id>.json           metric summary
outputs/<exp_id>/STATUS         run status
logs/<exp_id>/                  stdout/stderr
docs/19_evaluator_contract.md   metric/evaluator/split contract
docs/20_baseline_reproduction.md baseline reproduction ledger
docs/21_code_review_log.md      pre-submit code-review log
docs/22_upgrade_log.md          framework upgrade log
docs/23_review_board.md         tripartite independent review board log
docs/24_sprint_pursue_ledger.md sprint and capability-pursue ledger
software_outputs/<tool>/<run_id>/ command/version/hash/raw output
refs/pdfs|repos|supp|dossiers/      paper/repo/supplementary/provenance archive
worktrees/<exp_id>/                  optional branch worktree for parallel shared-code edits
data/raw|interim|processed/     data layers
docs/experiments/<exp_id>.md    structured per-experiment note
```

`docs/16_artifact_registry.md` is the authoritative detailed contract.

---

## Claim policy

A result can be discussed as SOTA only if:

1. it is full/scale, not smoke/screen;
2. it strictly exceeds SOTA, not equal;
3. comparability checks pass;
4. data contract checks pass;
5. semantic success passes;
6. evaluator contract and baseline reproduction evidence are recorded in docs/19-20;
7. changed training/evaluator code passed `/code-review-gate` in docs/21;
8. tri-review does not block it;
9. evidence is registered through `/note-gate` and the relevant result/validation docs.
