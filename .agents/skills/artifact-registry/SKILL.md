---
name: artifact-registry
description: "*· Initialize and audit the project artifact/directory contract: where scripts, configs, sbatch files, full training states, metric reports, iteration docs, external software outputs, raw/processed data, and manuscript assets must live."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Artifact-Registry: 目录与产物契约

本 skill 回答“脚本放在哪、完整训练结果放在哪、每次迭代结果放在哪、调用其他软件输出在哪”。它维护 `docs/16_artifact_registry.md` 与 `PROJECT_STRUCTURE.md`，并检查 evaluator/baseline/code-review/upgrade 等中央账本是否存在。

## Step 1 · 初始化目录（用确定性脚本，别手敲）

```bash
python3 scripts/artifact_registry.py --init    # 建齐标准目录(含 scripts/experiments、configs/pipelines、configs/sota_randomized) + 空目录放 .gitkeep
```
脚本的 `DIRS` 是目录契约的**唯一真相源**（scripts、scripts/experiments、pipelines、configs、sbatch、runs、reports、outputs、logs、external_runs、software_outputs、data{raw,interim,processed}、analysis、manuscript、refs、wiki、docs/experiments）。输出 JSON 列出新建目录。

## Step 2 · 目录契约

若 `docs/16_artifact_registry.md` 不存在，用模板创建；若已存在，只 append 新约定，不覆盖历史。

核心约定：
- `scripts/`：通用可复用脚本。
- `scripts/experiments/<exp_id>/`：单次实验专用但会影响结果的训练/eval/数据转换 wrapper；必须被 config/sbatch/docs 引用。
- `pipelines/<pipeline_id>/`：流程 DAG stage 脚本。
- `configs/<exp_id>.yaml`：训练/分析参数。
- `sbatch/<exp_id>.sbatch`：Slurm 提交脚本。
- `runs/<exp_id>/`：完整训练状态/checkpoint。
- `reports/<exp_id>.json`：指标摘要。
- `outputs/<exp_id>/STATUS`：状态与对账。
- `logs/<exp_id>/`：stdout/stderr。
- `software_outputs/<tool>/<run_id>/`：外部软件原始输出。
- `data/raw|interim|processed/`：数据分层。
- `docs/experiments/<exp_id>.md`：单实验结构化记录。
- `docs/19_evaluator_contract.md`：评估器/指标/split/claim 可比性合约。
- `docs/20_baseline_reproduction.md`：SOTA 复现中央账本。
- `docs/21_code_review_log.md`：实现后、提交前代码审查记录。
- `docs/22_upgrade_log.md`：框架升级与兼容修复记录。

## Step 3 · Run bundle 审计（确定性脚本，退出码即门控）

如果 `$ARGUMENTS` 指定 exp_id/run_id：
```bash
python3 scripts/artifact_registry.py --audit-run <exp_id>     # 查 configs/sbatch/STATUS/reports/runs/docs.experiments + docs/06 是否提及
```
脚本对每项输出 `exists: true/false`，**有缺项则退出码非零**（可当门控）。现在 run bundle 还会检查 `docs/21_code_review_log.md` 是否提及 exp_id。把 `exists:false` 的项整理成下表并写入 `docs/05_todo.md`，不要假装完整：
```markdown
| Artifact | Expected path | Exists? | Action |
|---|---|---|---|
```

## Step 4 · External software bundle 审计

```bash
python3 scripts/artifact_registry.py --audit-external <tool> <run_id>   # 查 command/version/stdout/stderr/inputs.sha256/outputs_manifest.tsv 六件套
```
缺项退出码非零。并确认 `docs/13_pipeline_blueprint.md` ledger 有对应行。

## Step 5 · 更新索引

- 如果新增了目录规则，更新 `PROJECT_STRUCTURE.md`。
- 如果发现 misplaced artifacts，把移动建议写入 `docs/05_todo.md`；不要自动移动大文件，除非用户明确要求。
- 重要发现走 `/note-gate` 写 `docs/15`。

## 不要做的事

- 不要把 checkpoint 或大日志塞进 docs。
- 不要自动删除/移动用户文件。
- 不要把 git 当训练状态机；默认仍用 exp_id/run_id 隔离运行产物。git 只用于框架/轻量记录版本化，或由 `/workspace-matrix` 人闸启用 worktree 隔离共享代码修改。

## Handoff

- **Outputs to**: `docs/16_artifact_registry.md`, `PROJECT_STRUCTURE.md`, directories, `docs/05_todo.md`
- **Next**: `/pipeline-blueprint`, `/sota-randomized`, `/implement`, `/note-gate`
