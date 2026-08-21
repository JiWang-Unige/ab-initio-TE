---
name: workspace-matrix
description: "*· Optional git/worktree coordinator for parallel experiment directions. Use when up to 3 orthogonal directions need concurrent shared-code edits; otherwise keep the default exp_id directory isolation. Creates a human-gated branch/worktree plan, updates docs/17_parallel_workspace.md, and never commits, merges, or deletes worktrees without explicit user approval."
argument-hint: "<parallel exp_ids / direction cohort / whether shared code will diverge>"
---

# Workspace-Matrix: 可选 git/worktree 并行隔离

默认情况下，本框架靠 `exp_id` 目录隔离并行实验：`configs/<exp_id>.yaml`、`sbatch/<exp_id>.sbatch`、`runs/reports/outputs/logs/<exp_id>`。这已经足够覆盖大多数 Track A screen。git 推荐用于版本化框架代码、skills、docs 模板和轻量研究记录；只有当多个方向**同时修改共享代码**（同一个 `models/`、`training/`、`eval/` 文件）时，才启用 git branch/worktree。

## 何时调用

- `/pivot` 产生 2-3 个 reviewer 建议的正交方向，并且它们需要并行推进。
- `/pursue` 的 portfolio cohort 要同时写共享模型代码。
- 用户想先试传统 DL、预训练模型、结构化 decoder 三条线，且三条线互不应干扰。
- spike 需要改共享代码，但不想污染主线。

**不要调用**：只改超参/config、只跑不同 seed、只跑不同数据比例；那是 exp_id 目录隔离，不需要 worktree。

## Step 0 · 判断是否真的需要 git

先输出：

| exp_id | Orthogonal axis | Will modify shared code? | Default isolation enough? | Worktree needed? |
|---|---|---|---|---|

硬规则：最多 3 个方向；如果全是 lr/batch/dropout/seed 差异，拒绝建 cohort，回到 `/pivot` 重新找结构性方向。

## Step 1 · 状态检查

运行只读检查：

```bash
python3 scripts/workspace_matrix.py status
python3 scripts/workspace_matrix.py plan EXP-A-001 EXP-A-002 EXP-A-003
```

解释结果：是否已有 git、是否有 HEAD commit、现有 worktrees、是否需要用户先做 lightweight initial commit。

## Step 2 · 人闸建 git/worktree（可选）

若需要启用 git 且仓库还没有 git：先展示风险与排除清单（`secrets.env`、data、runs、outputs、logs、checkpoint 不进 git），确认 `.gitignore` / `.git/info/exclude` 后才运行：

```bash
python3 scripts/workspace_matrix.py init --yes
```

如果没有 HEAD commit，不要代替用户提交；提示用户确认 `.gitignore` 和 `.git/info/exclude` 后做一次轻量 commit。只有已有 HEAD commit 才能继续：

```bash
python3 scripts/workspace_matrix.py create EXP-A-001 EXP-A-002 EXP-A-003 --yes
```

## Step 3 · 更新 docs/17

把 cohort 写入 `docs/17_parallel_workspace.md`：

| Cohort | exp_id | Branch/worktree | Orthogonal axis | Shared-code changes? | Owner | Status | Merge / drop decision |
|---|---|---|---|---|---|---|---|

同时在 `docs/11_master_plan.md §6` 写“当前并行 cohort、如何恢复”。

## Step 4 · 每个 worktree 的执行边界

- 每个 subagent / agent 只能在自己的 `worktrees/<exp_id>` 或自己的 exp_id 产物目录里写。
- 训练产物仍按 exp_id 写到主项目约定路径，不能互相覆盖。
- worktree 内也必须遵守 `/smart-sbatch`、`submit_guard`、`result-log → note-gate → exp-log → tri-review → pivot`。
- 不允许 worktree 内 subagent 再 spawn subagent。

## Step 5 · 合并或丢弃

只有当该方向通过 smoke/screen 且 code-plan-reviewer 没有 blocker，才讨论合并。合并前：

1. `python3 scripts/iter_ledger.py` 无严重漂移；
2. `docs/experiments/<exp_id>.md` 已写；
3. `docs/17` 写明 merge/drop rationale；
4. 用户确认。

本 skill 不自动 `git merge`、不删除 worktree、不清理分支；只给计划、命令和文档记录。

### Step 5.1 · merge 冲突解决（HARD，G13）
`git merge` 报冲突时，**绝不**把带 `<<<<<<<`/`=======`/`>>>>>>>` 标记的代码留下就去跑训练（语法错/逻辑混乱、结果作废）。规程：
1. **停下，只读定位**：`git status` + `git diff` 列出冲突文件与冲突块，inline 用通俗话向用户说清"哪两条线改了同一处、各自想干什么"。
2. **提改法让用户拍板**：对每个冲突块给出"保留 A / 保留 B / 合并两者"的建议 + 理由，**人闸确认**后才动手解。
3. **解后必过 `/code-review-gate`**：合并后的共享代码视作"改过的训练/eval 代码"，BLOCKED 未清不得 `/smart-sbatch`。
4. `docs/17` 记录冲突点与解决方式。
解不动 / 风险高 → 宁可放弃该 worktree 的 merge（保留分支待议），不带着冲突跑。

## Handoff

- **Inputs from**: `/pivot` cohort、`/pursue` parallel plan、用户插入的新实验方向。
- **Uses**: `scripts/workspace_matrix.py`。
- **Outputs to**: `docs/17_parallel_workspace.md`、`docs/11_master_plan.md`。
- **Next**: 对每个 exp_id 调 `/implement` 或 scoped implementer，然后 `/smart-sbatch`。
