---
name: pipeline-blueprint
description: "C2· Convert a mature fixed research idea, raw-data analysis plan, or bioinformatics workflow into an executable DAG with IO contracts, stage scripts, external software calls, QC gates, output locations, and validation checks."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Pipeline-Blueprint: 流程化研究 / 生信分析推进

本 skill 用于用户说的“有 raw data，需要按流程分析处理”或“已有完整思路，需要构建 pipeline 推进”。它把研究从“找模型”切换成 **DAG + IO contract + QC gates + validation**。

## Step 0 · 判定是不是 pipeline 模式

如果满足任一条，进入 `Pipeline-Execution`：
- 主要输入是 raw data / count matrix / FASTQ / BAM / VCF / 表型表 / 图像等。
- 已经知道大体分析步骤，只是不确定实现细节、参数、输出管理。
- 需要调用外部软件（如 STAR, Salmon, CellRanger, DESeq2, GATK, MMseqs2, CD-HIT, BLAST, AlphaFold 等）。
- 目标是形成可复现流程、图表、补充材料，而不是继续盲目搜架构。

输出 mode switch，并调用或更新 `/master-plan`。

## Step 1 · 盘点 raw inputs

建立 raw data manifest：

```markdown
| Raw ID | Source | Path/URL | Format | Size | Samples | Checksum | Access/licence | Notes |
|---|---|---|---|---:|---:|---|---|---|
```

raw 数据进入 `data/raw/` 或以 `.link.md` 记录外部路径；不直接覆盖。

## Step 2 · 构建 DAG

在 `docs/13_pipeline_blueprint.md` 写：

```text
raw_data → QC → preprocessing → feature/model/statistical analysis → validation → figures/tables
```

每个 stage 必须定义：
- 输入路径 pattern。
- 输出路径 pattern。
- 软件/脚本。
- config 参数位置。
- QC gate。
- 失败处理。

## Step 3 · IO contracts

用 `docs/16_artifact_registry.md` 的目录契约落位：

| 类型 | 推荐路径 |
|---|---|
| pipeline stage 脚本 | `pipelines/<pipeline_id>/<stage_id>_<name>.sh` 或 `.py` |
| config | `configs/pipelines/<pipeline_id>.yaml` |
| 外部软件原始输出 | `software_outputs/<tool>/<run_id>/` |
| 中间数据 | `data/interim/<pipeline_id>/<stage_id>/` |
| 最终可分析数据 | `data/processed/<pipeline_id>/` |
| 日志 | `logs/<run_id>/` |
| 指标/QC summary | `reports/<run_id>.json` |

## Step 4 · 外部软件调用规范

每个外部软件 run 都要保存：

```text
software_outputs/<tool>/<run_id>/command.txt
software_outputs/<tool>/<run_id>/version.txt
software_outputs/<tool>/<run_id>/stdout.log
software_outputs/<tool>/<run_id>/stderr.log
software_outputs/<tool>/<run_id>/inputs.sha256
software_outputs/<tool>/<run_id>/outputs_manifest.tsv
```

如果是 Slurm 上跑，仍走 `/smart-sbatch`，并用 `PIPE-<pipeline_slug>-NNN` 作为 run_id。

## Step 5 · QC gates

每个 stage 至少一个 gate。例：

| Stage | Gate examples |
|---|---|
| FASTQ QC | read quality, adapter contamination, duplication rate |
| Alignment | mapping rate, multimapping, rRNA contamination |
| Quantification | library size, detected features, sample correlation |
| Differential analysis | batch check, dispersion fit, FDR control |
| Model inference | input schema, missingness, confidence distribution |

QC gate 失败时不能悄悄继续；写入 `docs/13` ledger + `docs/05` blocked。

## Step 6 · Execution plan

输出可以直接执行的 stage 顺序：

```markdown
### Pipeline execution plan
1. PIPE-xxx-001: raw manifest + checksum
2. PIPE-xxx-002: QC stage
3. PIPE-xxx-003: preprocessing
...
```

每一步给出：命令模板、资源需求、输出路径、完成证据。

## Step 7 · 与投稿/模型迭代衔接

- 如果 pipeline 输出用于 paper：同步 `docs/12_publication_strategy.md` 和 `docs/14_validation_matrix.md`。
- 如果 pipeline 中包含模型训练：模型 run 仍用 `EXP-*`；pipeline wrapper 用 `PIPE-*` 调度，不混淆。
- 如果 pipeline 发现新研究问题：写 `/note-gate` 或 `/note-add`，不要直接改变主线。

## 不要做的事

- 不要把所有步骤写成一个巨大 shell 脚本；必须 stage 化，可单独重跑。
- 不要把 raw data 放进 `runs/`。
- 不要把外部软件输出散落在当前目录。
- 不要让 QC 失败后自动进入 downstream 分析。

## 完整性自检（确定性，进下游 stage 前跑）
```bash
python3 scripts/validate_stage_c.py --mode pipeline           # advisory：列出缺 status/QC 的 stage
python3 scripts/artifact_registry.py --audit-external <tool> <run_id>   # 外部软件 6 件套(command/version/std*/sha256/manifest)齐全？
```
QC 失败/上游未完成不进下游（与 SKILL 约束一致）；缺口先补 docs/13 ledger。

## Handoff

- **Outputs to**: `docs/13_pipeline_blueprint.md`, `docs/16_artifact_registry.md`, `configs/pipelines/`, `pipelines/`, `software_outputs/`, `docs/05_todo.md`
- **Uses**: `scripts/validate_stage_c.py --mode pipeline`、`scripts/artifact_registry.py --audit-external`
- **Next**: `/artifact-registry` 初始化目录 → `/smart-sbatch` 或具体 stage 执行 → `/note-gate` 归档结果
