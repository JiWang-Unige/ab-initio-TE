---
name: revise-goal
description: "*· Human-gated revision of the ACTIVE_GOAL.json contract (success_criteria / sota_benchmark / screen_anchor) when new evidence — a newly-found SOTA paper, a verified benchmark, or a shifted scope — makes the current goal stale or wrong. Closes the \"insert literature -> re-analyze -> adjust the goal target\" loop WITHOUT letting the agent silently move the goalposts: it proposes a diff, runs tri-review on comparability, and requires explicit user confirmation before writing ACTIVE_GOAL.json. Use when /note-add or /sota-inventory surfaces a SOTA that beats the current sota_benchmark, when validate_goal emits a stale_benchmark warning, or when the user wants to raise/lower/retarget the goal."
argument-hint: "<what changed: e.g. 'Tiberius verified at 0.91, raise sota_benchmark' / 'add OOD guardrail'>"
---

# Revise-Goal: human-gated goal-contract revision

调整 `ACTIVE_GOAL.json`（目标/成功标准/SOTA 锚点）——闭合"插入文献 → 重新分析 → **调整目标**"这条链，
但**绝不让 agent 偷偷移动球门**：提议 diff → tri-review 复核可比性 → **你确认**才落盘。

> 为什么要人闸：ACTIVE_GOAL 是源头真理（CLAUDE §7.5 advisory 边界）。抬高/降低目标是 major change，
> 必须 `propose → tri-review → 用户确认`。validate_goal 的 `stale_benchmark` 警告 / `/note-add` 的 SOTA 超越标记是触发器，不是授权。

## Step 1 · 读现状 + 触发依据
读 `ACTIVE_GOAL.json` 当前 success_criteria / screen_anchor / sota_benchmark，以及触发证据：
- `$ARGUMENTS` 描述的变更；
- 相关 `refs/dossiers/<slug>.md`（新 SOTA 的 dataset/metric/split——可比性关键）；
- docs/05 Pending integration queue / docs/10 findings 中相关项。

## Step 2 · 可比性复核（不可跳）
新 SOTA 值能否直接用作 `sota_benchmark`？**inline 走可比性 6 维**（dataset version / split / metric 实现 / preprocessing / weights / test-time，即 CLAUDE.md §10 的 comparability 合同），逐维标 ✅/❌ 并给依据。
- 若新 SOTA 用了**不同 split/metric/样本规模**（任一维 ❌）→ **不能**直接抬高 sota_benchmark。两条合规出路：(a) 若能在**我们自己的 split/metric** 上复现该方法、对齐口径后再取值（把对齐结果记进 `refs/dossiers/<slug>.md` 的 metric/split 段），再用对齐后的可比值；(b) 无法对齐 → 标注为 `not-comparable, informational only`，写入 docs/05 与 dossier，**不进** sota_benchmark。
- screen_anchor 的修订要求其在**我们的小样本协议**下取得（同预算），否则拒绝。

## Step 3 · 产出修订提议（diff，不落盘）
inline 输出拟改动：
```
ACTIVE_GOAL.json 修订提议
- sota_benchmark.value: 0.42 → 0.91   (依据: refs/dossiers/tiberius-2025, 同 split? <yes/no>)
- success_criteria[segment_f1].threshold: 0.45 → 0.50
- (screen_anchor 不变 / 调整为 …)
理由: <一段>
影响: validate_goal 之后据新目标判定；可能使此前的 success 重新变为 not_yet/progress。
```

## Step 4 · tri-review（复核这次目标修订是否合理且公平）
`/tri-review` 把"修订提议 + 可比性复核"作为 context 让三方评：新 benchmark 是否可比？阈值是否合理？是否过/欠雄心？

## Step 5 · 用户确认 → 落盘
- tri-review 通过 + **你显式确认** → 才用 Edit 写 `ACTIVE_GOAL.json`（更新对应字段 + `status`），并在 `docs/08_pivot_decisions.md` 记 `## Goal Revision <date>`（依据/diff/tri-review 结论）。
- 未确认 → 不写，留提议在 docs/08 advisory 段。

## 边界
- 不在未经用户确认时写 ACTIVE_GOAL.json。
- 不把"不可比的更高数字"直接抬成 sota_benchmark（先在我们的 split/metric 上对齐口径，无法对齐则标 `informational only` 不入合约）。
- 不动 docs/03 roadmap 主体（那是 /benchmark-roadmap 的事；可建议）。

## Handoff
- **Inputs from**: `/note-add`(SOTA 超越标记)、`validate_goal` stale_benchmark 警告、`/sota-inventory`、用户
- **Uses**: `/tri-review`（可比性复核）；可比性对齐走 inline CLAUDE.md §10 六维，不依赖独立 skill
- **Outputs to**: `ACTIVE_GOAL.json`（经确认）、`docs/08_pivot_decisions.md`
- **Next**: `/pursue`（据新目标继续）
