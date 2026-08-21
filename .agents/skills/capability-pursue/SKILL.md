---
name: capability-pursue
description: "B1.3· Bounded 2-5 round pursuit of an original capability component when the goal is usable prototype, conservative limitation, future work, or user-gated promotion to claim rather than immediate SOTA."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Capability Pursue: 原创能力组件的有界多轮推进

`$capability-pursue`（或 `/capability-pursue`）用于**多轮、有界（通常2-5轮）**的原创能力组件开发与验证任务。它不是小号 `$pursue`：不直接 claim SOTA，不用 `validate_goal.py` 判 success，不自动 pivot 到主线。

当我们的目标不是去碰 published SOTA 终极指标，而是要“实现并调通一个新的原创特征/网络组件，确保其可运行（usable prototype）”、“摸清该组件保守的性能限制（conservative limitation）”、“为后续工作（future work）奠定基准”时使用。

## 使用规范

- **目标边界**：每次启动需要指明目标能力组件（如：“实现并测试 Transformer 感受野的 linear attention 扩展”）。
- **执行轮数**：通常限制在 2 到 5 轮迭代。
- **能力合约**：先写 `capability_id`、`capability_type`、`success_policy`、核心指标、minimum_gate、max_rounds、if_fail 行为。
- **停止状态**：只允许 `usable_prototype` / `conservative_limitation` / `future_work` / `blocked` / `promote_to_claim_proposed` / `abandon_component`。
- **结果归档**：
  - 迭代进展、实验指标以及代码改动写入 `docs/24_sprint_pursue_ledger.md`（加 `[Cap-Pursue]` 前缀）。
  - 对外部产生的文件（比如新代码库分支、训练模型权重），登记到 `docs/15_evidence_register.md`。
- **晋升机制（Promote to Claim）**：
  - 如果该组件表现极佳，AI 只能提议 `promote_to_claim_proposed`，不能直接 claim、不能直接改 `ACTIVE_GOAL.json`。
  - 得到用户拍板后，通过 `/revise-goal` 将目标写入 `ACTIVE_GOAL.json`，或由 `/route-reset` 重排主线，然后才切换到全局的 `$pursue` 流程以挑战 SOTA。

## 与 $pursue 和 $spike 的区别

| 特性 | `$spike` | `$capability-pursue` | `$pursue` |
| --- | --- | --- | --- |
| **层级** | 极小隔离，侧面实验 | **中等偏上，原创组件多轮有界推进** | 全局，SOTA 闭环追求 |
| **主要目标** | 纯粹的防污染尝试，不 claim | **产出可用原型，摸清性能底细** | 验证整体架构是否超越 published SOTA |
| **执行周期** | 1 轮动作 | **2-5 轮多轮动作** | 多轮迭代（直到达成或 failed_run） |
| **对账与校验**| 零对账，不进晋升主线 | **对账登记，有 usable prototype / limitation 归档** | `validate_goal.py` 强制反调参、双层锚点校验 |
| **升级通道** | 无 | **只可用户确认后 promote_to_claim**；经 `/revise-goal` 或 `/route-reset` 后进入 `$pursue` | 终极 claim 通道 |

## 步骤流程

1. **设定能力边界**：与用户共同确定本次 capability pursue 的核心组件及 2-5 轮的目标。
2. **多轮有界推进**：
   - 每轮开局使用 `context_pack.py` 恢复状态，并读取 `docs/24_sprint_pursue_ledger.md` 的本 capability 记录。
   - 借用 `/implement`、`/code-review-gate`、`/smart-sbatch`、`/result-log` 的工程闭环。
   - 不调用 `validate_goal.py` 判 SOTA success，不 claim，不自动进入 `/pivot`；必要的评审用 `/review-board` 或轻量 `/tri-review` context，但结论仍由本 capability 合约裁决。
3. **完成判定**：在 2-5 轮内取得可用原型，摸清性能边界，或达到 round budget 后写 limitation/future work。
4. **归档落盘与决策**：
   - 登记至 `docs/24_sprint_pursue_ledger.md`。
   - 发现写入 `docs/10_findings.md`，证据索引写入 `docs/15_evidence_register.md`。
   - 若可以 **Promote to Claim**，先用 3-6 句通俗话说明理由、风险和需要改变的 goal，再等待用户确认；若否，保留为 limitation/future work 并退出。
