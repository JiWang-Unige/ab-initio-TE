---
name: reproduce-baselines
description: "B0· Before writing ANY of our own model code, reproduce 1-2 verified SOTA baselines locally ONCE to nail the technical ground truth you cannot trust from the paper alone: exact metric computation, dataset rawness (pure raw vs FP-pre-filtered / homology-deduped), split scheme, pr…"
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Reproduce-Baselines: run SOTA locally once before building our own

写自己的模型前，**先把 1-2 个 SOTA 在本地真跑一遍**。目的不是刷分，是**确认论文里说不清、信不过的技术事实**——这些一旦搞错，后面所有比较都不可比、白烧 GPU：
- **指标到底怎么算**（F1 的 TP/FP 边界判定？macro/micro？是否含某类的特殊处理？）——以**他们的官方 eval 脚本实际算出来**为准，不是论文文字。
- **数据集是不是纯 raw**，还是其实已经**滤过很多 FP / 去过同源冗余 / 平衡过类别**（这直接决定我们的数据该怎么取才公平）。
- **split 来源**、preprocessing、test-time inference 细节。

**位置**：`/benchmark-roadmap`（已选 paths）之后、`/goal-prompt` 迭代之前。**hook 闸**：未完成至少一个 SOTA 复现（或显式 waive）不准进 `/goal`/`/pursue` 迭代（见 §Gate）。

## Step 1 · 选 1-2 个复现对象
从 `docs/02` 取 `worth ∈ {yes, partial}` 且 repro ∈ {trivial, moderate} 的候选，优先：
- **定义主指标的那个**（它的 eval 脚本就是我们指标实现的 ground truth）；
- **本地单卡可行的**（小模型/可在子集上跑）。
本地无 Slurm → run-and-evaluate 直接 python；太重就在**子集**上复现，或用其**已发布的 predictions** 重算指标。

## Step 2 · 拉齐环境 + 跑他们的 eval
仓库/权重应已由 `/sota-inventory` 归档到 `refs/repos`、`refs/dossiers`；据其 README 建环境（记录到 docs/10 Engineering findings，避免下次重踩）。跑**他们自己的 train（或直接 load 权重）+ 他们自己的 eval 脚本**在**他们自己的数据**上，复现其报告数字（容差内）。

## Step 2.5 · 复现失败的有界处理（防"调别人仓库调到天荒地老"，G7）
复现他人 SOTA 常卡在环境（旧 Python / C++ 编译 / 依赖冲突 / 缺权重）。**禁止无界 debug**——会耗光 token 还推不动主线。规则：
- **最多 3 次有界修复**：每次失败跑 `python3 scripts/repair_advisor.py <log>` 归类（缺依赖/编译/版本/OOM）→ 按其建议改一次再试。记录每次尝试到 `docs/10` Engineering findings。
- **3 次仍失败** → 跑 `python3 scripts/sota_failure_report.py`（或 `lit_search` 查替代实现）出失败诊断，然后用 `AskUserQuestion` 让主人三选一：① 用其**已发布 predictions** 重算指标（仍拿到 metric ground truth）；② **换另一个更易复现的 SOTA**（回 Step 1）；③ **显式 waive**：在 `ACTIVE_GOAL.json` 或 `docs/03` 写 `reproduce_waived: <理由>`，并在 `docs/20` 记 `reproduction: FAILED_BOUNDED` + 风险。
- 不把"复现不出"当卡死，也不伪造成功——降级到可比的替代证据或显式 waive，主线继续。

## Step 3 · 记录 ground-truth 发现（核心产物）
逐条核实并落盘（这是本 skill 的价值所在）：
```markdown
## Baseline Reproduction Report: <model> <date>
- Reported metric: <paper 值> | Reproduced: <我们跑出的值> | Δ: <差异> | 容差内? ✅/❌
- **Metric implementation (VERIFIED)**: <精确算法——从他们 eval 脚本读出的 TP/FP 判定、macro/micro、特殊处理；附脚本路径/行号>
- **Dataset rawness (VERIFIED)**: 纯 raw / 已滤 FP / 已去同源冗余 / 已平衡类别？<证据：从他们数据处理代码读出>
- **Split scheme (VERIFIED)**: <来源 + 是否按染色体/物种/同源切>
- **Preprocessing / test-time**: <关键步骤>
- **Report-vs-reproduce gap**: <若复现不出，说明可能是"论文数字在更优条件下得到"——这是 critical comparability finding>
```
- 把 VERIFIED 的 metric/split/dataset **回填 `refs/dossiers/<slug>.md`**（把原来的 ⏳ 改成已核实），并写 `docs/10_findings.md`。
- 同步写 `docs/20_baseline_reproduction.md` 的中央账本：每个复现对象一行 `Reproduction Runs`，并把 `Metric implementation / Dataset rawness / Split scheme / Preprocessing` 写入 `Verified Facts To Transfer`。
- 同步更新 `docs/19_evaluator_contract.md`：把已核实的 primary metric、official evaluator、dataset/split contract、metrics JSON schema 变成后续 `/code-review-gate` 和 `/result-log` 可检查的合约。
- 复现值与论文显著不符（gap > 容差）→ 这是**最高价值发现**：当前 `sota_benchmark` 可能不可比/在更优条件下取得。**不要静默沿用论文数字**——触发 `/revise-goal` 把 `sota_benchmark` 调到**已复现值**（或明确标注无法复现的风险），并在 dossier 标 `reported_unreproduced: <paper值 vs 复现值>`。否则整个"严格超越"判定建立在一个未证实的数上（reviewer 投稿必质疑）。

## Step 4 · 喂回 benchmark-roadmap + screen_anchor
- 把 VERIFIED 的指标实现/数据集口径写进 `docs/03` 的 comparability contract（覆盖原先靠论文文字的假设）。
- 复现出的 baseline 也是建立 `screen_anchor` 的现成参考架构（可直接在 10% 子集上重跑得 screen_anchor）。

## Gate（hook 强约束）
`docs/03` 存在但 `docs/20_baseline_reproduction.md` 无任何 `Baseline Reproduction Report` / ledger entry 时，`/goal-prompt`/`/pursue` 进入迭代前应被提醒/拦截（除非在 ACTIVE_GOAL 或 docs/03 显式标 `reproduce_waived: <理由>`）。理由：没核实过指标算法/数据集口径就迭代，等于在不可比的地基上盖楼。

## 边界
- **只复现（跑他们的代码/eval）**，不在本 skill 里建我们自己的模型——那是 `/implement` 的事。
- 复现不了就如实记 `report-vs-reproduce gap`，不要伪造"复现成功"。
- 本地跑不动的大模型：子集复现 / 用已发布 predictions 重算指标 / 或显式 waive 并说明。

## Hand-off
- **Inputs from**: `docs/02`(SOTA 表) + `refs/repos`/`refs/dossiers`(已归档代码/权重) + `docs/03`(已选 paths)
- **Outputs to**: `refs/dossiers/*`(VERIFIED 字段) + `docs/20_baseline_reproduction.md` + `docs/19_evaluator_contract.md` + `docs/10_findings.md` + `docs/03` comparability contract + 可选 `/revise-goal`
- **Next**: `/goal-prompt` / `/pursue`（地基核实后才开始写我们自己的模型）
