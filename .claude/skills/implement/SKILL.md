---
name: implement
description: "B1· Turn an experiment plan / roadmap path into runnable training+eval code BEFORE submitting a full run, then de-risk it with mandatory self-review, /code-review-gate, deterministic data-leakage check, and a small sanity smoke run with bounded auto-debug. Fills the gap where goal-prompt/smart-sbatch assume the training script already exists. Prevents \"trained 8h then found the code was wrong\". Use after benchmark-roadmap/goal-prompt have a concrete path and before /smart-sbatch submits the real run; also used inside /pursue as the code-realization step."
argument-hint: "<exp_id + which docs/03 path / what model to build>"
---

# Implement: plan → runnable code → de-risked before full run

补上 lwcr 留白的一步：**把"实验计划/path"变成能跑的训练代码**，并在投全量前用
**自审 + 独立代码审前闸 + 数据闸门 + sanity smoke + 有界自动 debug** 把代码 bug 挡在 8h 训练之前。

> 借自 ARIS experiment-bridge，去掉对 Codex MCP 的依赖（用 Claude 自审）。

## Step 1 · 读输入，定 exp 契约
读 `docs/03`（目标 path 的 architecture change / mechanism_delta / Track / resource profile）、`docs/00`、
`CLAUDE.md §14-15`（canonical training/eval 模板）、`docs/05` Pending integration queue（相关新机制）、
`refs/dossiers/`（要对标的 SOTA 实现细节）。
inline 输出本次要实现什么：模型/ head、数据接口、loss、metric、产物路径 `outputs/<exp_id>/`。

**重跑前清旧产物（防"崩溃却读到上次旧结果判 success"，G5）**：若本 `exp_id` 是**重跑**（已存在 `reports/<exp_id>.json` 或 `outputs/<exp_id>/STATUS`），在写新代码/提交前**先清除或归档这两个旧文件**（`mv reports/<exp_id>.json reports/<exp_id>.json.bak-<n>`、清 `outputs/<exp_id>/STATUS`）。否则本次若在早期就崩，`validate_goal.py` 会读到**上一次的旧 metrics** 误判 success/progress，把错代码晋升为 SOTA 候选。（若是首次跑则跳过。）确认无 RUNNING 作业占用该 exp_id 再清。

## Step 2 · 生成代码（基于现有模板，不重造轮子）
> **非平凡架构改动建议先进 plan 模式**（Claude `plan` / Codex plan）：只读勘查 `refs/repos/` 的 baseline 实现、§14-15 脚手架、数据接口，产出实现计划→主人批准→退出 plan 模式再落码。挡"写错代码"于动笔前，与下面 Step 3-5 的写后自审/数据闸/smoke 叠成两道闸。简单改动（换 loss/调 config）可跳过。
- 优先**复用** CLAUDE.md §13-15 的 canonical 脚本，只写**差异部分**（新 head/loss/config）。生成的 sbatch/训练脚本**必须照 §13 模板**：`set -e` + 写 `outputs/<exp>/env.txt` 环境快照 + 先 `RUNNING`、指标 `.tmp→rename` 原子写、**最后**才 `COMPLETED`（防半写结果/崩溃误判 success）。
- 写 `configs/<exp_id>.yaml` + 必要的训练/eval 代码改动，**scope 限定在本 exp_id**（不动公共文件，除非必要且声明）。
- 单次实验专用、但会影响结果的生成脚本/wrapper 放 `scripts/experiments/<exp_id>/`，并从 `configs/<exp_id>.yaml`、`sbatch/<exp_id>.sbatch` 或 `docs/experiments/<exp_id>.md` 引用；可复用组件才放 `scripts/` 或项目代码；Slurm 提交脚本只放 `sbatch/<exp_id>.sbatch`。
- 产出 metrics 时**必须**写成 validate_goal.py 能读的 JSON（含 `primary_metric` 键）。

## Step 3 · 代码自审（不可跳）
让 Claude 以审稿人视角扫一遍刚写的训练/eval 代码，对照计划逐条核对，重点抓**会让结果失真或崩溃**的错误：
- ground-truth / label 是否用错（最常见的致命 bug）
- loss 与目标是否一致；metric 实现是否与 SOTA 可比（对 refs/dossiers 的 metric impl）
- split 是否按 docs/03 契约；有无 target 泄漏 / 未来信息
- 设备/精度（bf16 vs fp16）、checkpoint 逻辑
inline 输出 self-review 表（issue | 严重度 | 是否已修）。CRITICAL 未修 → 不进 Step 3.5。

## Step 3.5 · `/code-review-gate` 独立审查（不可跳）

写完训练/eval/config/job 脚本后、任何真实训练提交前，调用 `/code-review-gate`：
- 优先用 read-only `code-plan-reviewer`；Codex-only 时用 host read-only checklist。
- 审查 label/ground truth、metric/evaluator、split/leakage、output path、metrics JSON schema、runtime sanity。
- 结果写 `docs/21_code_review_log.md`；涉及 evaluator 时同步 `docs/19_evaluator_contract.md`。
- `Verdict: BLOCKED` 或 CRITICAL 未修 → 不进数据闸、smoke 或 `/smart-sbatch`。

## Step 4 · 数据泄漏闸门（确定性，不可跳）
```bash
python3 scripts/check_data.py --train <train> --val <val> --id-col <id> [--time-col <t>] [--target-col <y>]
```
`status=leakage`（exit 3）→ **停**，修数据/ split 再来。`pass` 才继续。

## Step 5 · Sanity smoke（小规模真跑）+ 有界自动 debug

**Step 5.0 · 环境纪律（装任何依赖前必做，HARD）**：先**探测并激活本项目 conda 环境，绝不在 `base` 装**：
```bash
conda env list; echo "active=$CONDA_DEFAULT_ENV"      # 确认当前/可用 env（项目 env 名见 CLAUDE.md §1/§12）
conda activate <your-env>                              # 无明确 env → 看 environment.yml/README 或问主人，别默认 base
```
- 缺依赖：`conda activate <env>` 后装进**该 env**（`conda install -n <env> …` 或 pip），**装前 inline 说明装什么/装进哪个 env**。
- `repair_advisor` 报 `missing_dep` 时，patch 也装进项目 env，**不是 base**。
- 当前在 `base` 且要装东西 → **停下提醒主人**先选/建 env。sbatch 脚本里显式 `conda activate <env>`（计算节点不继承激活态）。

跑一个**极小**配置（如 sample_fraction 极小 / 1-2 步 / 1 epoch）验证"代码能从头跑到产出 metrics"。
- 本机（无 Slurm）可直接小跑；**在 baobab 等集群上，即便是 smoke 也不能在登录节点直接 `python` 跑**——用 `srun -p <partition> --time=<hh:mm> python …` 拿节点跑，或用 `/smart-sbatch` 提交 smoke profile（screen 之下）。登录节点只许下载/文件操作/轻量脚本（CLAUDE.md §12 srun 强制；hook 会 ask 提醒）。
- smoke 失败 → 用 repair_advisor 分类并**有界修复，最多 3 次**：
  ```bash
  python3 scripts/repair_advisor.py --log <smoke_err.log>
  ```
  - `bounded=true`（oom/timeout/missing_dep/nan）→ 按 patch_hint 改一处 → 重跑。
  - `bounded=false`（cuda_device/disk/data_error/unknown）→ **停并通知主人**，不要瞎试。
- 3 次仍失败 → 停，写 docs/10_findings.md（Engineering Finding）+ 通知。

## Step 6 · 交接
smoke 通过 → 代码已就绪，可由 `/smart-sbatch` 提交**全量** run（screen/full/scale）。
- inline 汇总：实现了什么、self-review 结论、code-review-gate 结论、check_data 结论、smoke 结论、产物路径、下一步 `/smart-sbatch`。
- 把 smoke 中获得的 engineering 经验（如"加 grad checkpoint 避免 OOM"）写入 `docs/10_findings.md`。

## 边界
- scope 限本 exp_id；改公共文件必须声明。
- 不在 self-review/code-review-gate/check_data/smoke 任一未过时进全量。
- `bounded=false` 失败不自动重试。
- 不 spawn subagent 再 spawn。

## Handoff
- **Inputs from**: `docs/03`(path), `goal-prompt`/`pursue`, `CLAUDE.md §14-15`, `refs/dossiers`
- **Uses**: `/code-review-gate`, `scripts/check_data.py`, `scripts/repair_advisor.py`, `/smart-sbatch`(smoke)
- **Outputs to**: `configs/<exp_id>.yaml` + reusable code or `scripts/experiments/<exp_id>/` + `docs/21_code_review_log.md` + `outputs/<exp_id>/` + `docs/10_findings.md`(engineering)
- **Next**: `/smart-sbatch`（全量）→ `/result-log` → validate → `/tri-review` → `/pivot`
