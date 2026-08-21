---
name: evidence-sprint
description: "B1.2· Answer one narrow evidence, diagnostic, comparator, audit, or publication-support question in 1-2 bounded actions when the goal is question answered rather than SOTA claim."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Evidence Sprint: 单点研究证据/诊断短跑

`$evidence-sprint`（或 `/evidence-sprint`）用于**单点、短期（通常1-2个动作）**的求证任务。它回答“这个问题是否被可靠回答”，不是追求 SOTA，也不是多轮组件开发。

区别于全面的 SOTA 追求（`$pursue`），它的目标极其专注，例如：“测试 CRF head 是否比 softmax 更容易过拟合（单次运行对照）”、“定位评估器在处理极端不平衡数据时的精度除零 bug”、“针对特定审稿意见补做一组 baseline comparator 实验”。

## 使用规范

- **目标边界**：每次启动必须有具体、可回答的问题或诊断命题（例如：“SOTA 在 AUPRC 指标上是否有 2% 的波动性？”）。
- **执行步数**：通常限制在 1 到 2 轮操作（例如：修改配置 -> 提交小样本训练 -> 分析结果）。
- **非目标**：不 claim SOTA，不修改 `ACTIVE_GOAL.json`，不把单点问题自动延长成多轮组件开发。
- **训练闸门**：凡涉及训练/eval 代码或真实训练提交，仍必须走 `/implement`、`/code-review-gate` 和 `/smart-sbatch`；本 skill 只是不使用 `validate_goal.py` 判定 SOTA success。
- **结果归档**：
  - 过程中的 metrics 和结论需要记录在 `docs/24_sprint_pursue_ledger.md`（加 `[Evidence-Sprint]` 前缀）。
  - 有价值的学术/工程发现，应该通过 `/note-gate` 路由或手动 append 进 `docs/10_findings.md`（加 `[Evidence-Sprint: <问题描述>]`）。
  - 对外部产生的文件（比如 logs 或 plots），记录在 `docs/15_evidence_register.md` 中。

## 与 $pursue 和 $spike 的区别

| 特性 | `$spike` | `$evidence-sprint` | `$pursue` |
| --- | --- | --- | --- |
| **层级** | 极小隔离，侧面实验 | **中等，单点求证/诊断** | 全局，SOTA 闭环追求 |
| **主要目标** | 纯粹的防污染尝试，不 claim | **解答一个具体的证据/诊断问题** | 验证整体架构是否超越 published SOTA |
| **执行周期** | 1 轮动作 | **1-2 轮动作** | 多轮迭代（直到达成或 failed_run） |
| **对账与校验**| 零对账，不进晋升主线 | **对账登记，重要结论入 findings/evidence** | `validate_goal.py` 强制反调参、双层锚点校验 |
| **升级通道** | 无 | **无直接 claim**；若需要多轮组件开发，先归档本 sprint，再由用户确认另开 `$capability-pursue` | 终极 claim 通道 |

## 步骤流程

1. **澄清问题**：明确要回答的问题是什么。
2. **写 evidence card**：记录 question / hypothesis / evidence_needed / budget / non_goals / acceptance_criteria。
3. **执行求证**：无训练任务可直接做 source audit / table / analysis；涉及训练或评估代码时，按 `/implement` → `/code-review-gate` → `/smart-sbatch` → `/result-log` 执行。
4. **分析结论**：只允许选择一个状态：`answered_yes` / `answered_no` / `answered_mixed` / `inconclusive` / `needs_capability_pursue` / `needs_full_pursue` / `feed_publication`。
5. **升级边界**：`needs_capability_pursue` 只建议另开 `$capability-pursue`；`needs_full_pursue` 必须经用户确认并通过 `/revise-goal` 或新 goal 进入 `$pursue`。
6. **归档落盘**：
   - 登记至 `docs/24_sprint_pursue_ledger.md`；
   - 发现写入 `docs/10_findings.md`；
   - 证据索引写入 `docs/15_evidence_register.md`；
   - 用 3-6 句通俗话告诉用户：做了什么、问题是否回答、下一步是停止/转 capability/转 pursue/进 publication。
