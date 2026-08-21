# Parallel Workspace Matrix / 并行方向与可选 git worktree 契约

> 由 `/workspace-matrix` 与 `scripts/workspace_matrix.py` 维护。默认安全模式仍是 `exp_id` 目录隔离；当 2-3 条方向需要同时修改共享代码时，才启用 git branch/worktree 隔离。

## 0. Current Workspace Status

| Date | Git initialized? | HEAD commit? | Active branch | Worktrees | Notes |
|---|---:|---:|---|---|---|
| 2026-06-13 | yes | no | master | none | Git was initialized for framework/docs/scripts versioning only. Make a lightweight initial commit after reviewing `.gitignore` before creating worktrees. |

## 1. 何时需要 worktree

| 场景 | 默认 exp_id 目录隔离够吗？ | 建议 |
|---|---:|---|
| 只改 config / sbatch / notes | 够 | 不开 worktree，写 `configs/<exp_id>.yaml` + `outputs/<exp_id>/notes.md` |
| 三个方向都要改同一训练脚本/模型代码 | 不够 | 用 `/workspace-matrix` 建 `worktrees/<exp_id>`，每方向一个 branch |
| spike 小实验，不想污染主线 | 视情况 | 轻量 spike 用 exp_id；改共享代码的 spike 用 worktree |
| 投稿阶段补证据/跑 ablation | 多数够 | 只在 ablation 会冲突时用 worktree |

## 2. 并行上限

- `ACTIVE_GOAL.json.max_parallel_directions` 与 `cluster_config.yaml.max_concurrent_directions` 默认最多 **3**。
- 三条线必须是**机制正交**：例如 head_arch / backbone / objective / data_view 不能只是 lr/dropout/seed 差异。
- `/pivot` 先记录全部 tri-review 结论，再按 reviewer 给出的方向顺序组 cohort；每个 cohort 最多 3 个 exp_id。

## 3. Git/worktree 安全规则

- 框架运行**不强制使用 git**，但本项目规模已经建议启用 git 来版本化框架代码、skills、docs 模板和轻量研究记忆；git 不是训练状态机，也不保存大数据/权重。
- 不把 `secrets.env`、raw data、runs、outputs、logs、checkpoint、大文件纳入 git。
- worktree 只隔离“会互相冲突的代码修改”；训练产物仍写回该 exp_id 自己的 `runs/reports/outputs/logs`。
- worktree 内的 agent 只能写自己的 branch 和自己的 exp_id 产物；不能合并到 main，也不能提交 claim。
- 合并前必须经过 `code-plan-reviewer` / 测试 / smoke / `iter_ledger.py`。

## 4. 命令模板（人闸）

只查看：

```bash
python3 scripts/workspace_matrix.py status
python3 scripts/workspace_matrix.py plan EXP-A-001 EXP-A-002 EXP-A-003
```

首次启用 git（会创建 `.git/`，但不会自动提交大文件）：

```bash
python3 scripts/workspace_matrix.py init --yes
# 然后做一次轻量 initial commit；确认 .gitignore 和 .git/info/exclude 已排除 data/runs/outputs/logs/secrets/checkpoints。
```

建议纳入 git 的内容：`CLAUDE.md`、`AGENTS.md`、`.claude/.codex/.agents`、`scripts/`、`docs/*.md` 模板与轻量记录、`refs/dossiers/`、`wiki/`、`configs/*.yaml`。不纳入：`data/`、`runs/`、`outputs/`、`logs/`、`software_outputs/`、`external_runs/`、`secrets.env`、模型权重。

创建最多 3 个并行 worktree：

```bash
python3 scripts/workspace_matrix.py create EXP-A-001 EXP-A-002 EXP-A-003 --yes
```

## 5. Matrix

| Cohort | exp_id | Branch/worktree | Orthogonal axis | Shared-code changes? | Owner | Status | Merge / drop decision |
|---|---|---|---|---|---|---|---|
| C001 |  |  |  |  |  | TODO |  |

## 6. 合并/丢弃记录

| Date | exp_id | Decision | Evidence | Files merged or parked | Notes |
|---|---|---|---|---|---|
