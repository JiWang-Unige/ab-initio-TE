---
name: retrospective
description: "*· Periodic retrospective audit that breaks out of forward-only iteration to detect marginal-tuning drift, repeated failure patterns, skipped early signals, and abandoned routes worth reconsidering."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Retrospective Review

对项目历史做**周期性回溯审查**。lwcr 默认 forward-only：result → tri-review → pivot → next。本 skill 是唯一会**主动回头看**的环节。

`$ARGUMENTS` 可以为空（做全量回溯）或聚焦某条 path / 时间窗口。

---

## 触发条件（任一满足即应运行）

1. **每 5 个 completed iterations** —— 由 `/goal-prompt` 在 Step 1 检查 `docs/04` 中 completed 计数，若自上次 retrospective 后 ≥ 5，主 agent 应提示用户运行 `/retrospective`。
2. **同一路线连续 3 次未显著缩小 gap**（gap 缩减 < 0.01 or 反而扩大）。
3. **Track B scale-up 失败 2 次**（Track A 晋升候选放大到 full 后未达 SOTA）。
4. **用户手动怀疑兜圈子** —— 出现"我们是不是在调参"、"是不是绕了一圈"、"为什么 gap 不动" 时主动建议运行。
5. **/pivot 连续 2 次输出 `tune` 决策** —— 强烈怀疑 marginal tuning，强制 retrospective。

---

## 输入（必读）

| 文件 | 用途 |
|---|---|
| `docs/03_benchmark_roadmap.md` | 当初定的 paths、milestones、SOTA weakness hypotheses |
| `docs/04_experiment_iterations.md` | 全量 ITER 表格，看每轮 Track / hypothesis / result / pivot |
| `docs/05_todo.md` | 当前 TODO 状态，看是否有长期 waiting / blocked 项 |
| `docs/06_results_log.md` | 全量 result entry，看 gap 趋势 |
| `docs/07_tri_review.md` | 历次三方评审 consensus + disagreements |
| `docs/08_pivot_decisions.md` | 历次 pivot 决策 |
| `docs/09_decisions_log.md` | abandoned routes + cousin lists + re-entry criteria |

读完后**inline 摘要每个文件的关键时间序列**，让回溯有据可查。

---

## 输出格式

```markdown
# Retrospective Review · <YYYY-MM-DD>

## Scope
- Iterations covered: ITER-<a> .. ITER-<b>
- Trigger: <every-5 / 3-no-progress / Track-B-fail-2 / user-suspicion / pivot-tune-2 / manual>
- Focus: <empty or $ARGUMENTS>

## Are we doing marginal tuning?

| Verdict | Evidence |
|---|---|
| yes / no / partially | <ITER ids + what changed across them> |

判定规则:
- yes: 最近 ≥ 3 个 iteration 的 architecture change 字段实质相同（同一 head / 同一 backbone / 同一 objective），只是 lr / bs / dropout / seed / scheduler 变化。
- partially: 部分 iteration 有结构性改动，但夹杂调参轮。
- no: 每一轮 architecture change 都有 mechanism_delta 区别。

## Gap trajectory

| ITER | Track | Path | Primary metric | SOTA | Gap | Δ vs prev |
|---|---|---|---:|---:|---:|---:|

- 拟合趋势 (one line): <improving / flat / oscillating / regressing>
- gap 缩减半衰期估计 (粗): <N iterations to halve> 或 "indeterminate"

## Repeated failure pattern

| Pattern | Affected ITERs | Evidence | Possible root cause |
|---|---|---|---|

例: "head_arch 换 3 次都在 Track A 卡住 primary_progress_gate" → 可能是 backbone 表达力上限，而不是 head。

## Early signal we skipped

| Signal | Where it first appeared | Why it might matter now | Suggested re-examination |
|---|---|---|---|

例: "ITER-3 的 tri-review 提到 tokenizer 可能限制感受野，被 pivot 判 defer，最近 4 轮 gap 都卡在同一水位" → 重新考虑 tokenizer axis。

## Abandoned route worth reconsidering?

| Route (from docs/09) | Original abandon reason | New evidence | Reconsider? | Re-entry criteria check |
|---|---|---|---|---|

re-entry 必须明确 docs/09 当初定的 re-entry criteria 是否已满足。如果没有满足而强行重启，必须 inline 说明为什么覆盖原 criteria。

## Subagent / scout fan-out gaps

- 是否有应该并行做的 read-only 检查被跳过 (例: SOTA 链接验证、新论文扫描、cousin 冲突检查)?
- 是否有 Scout 任务在 submit-and-handoff 等待期没启动?

## Recommendation (advisory only)

Pick **one** primary recommendation; may add secondary suggestions:

- [ ] continue current path (no change needed)
- [ ] pivot to different architecture axis (specify: <axis + mechanism_delta>)
- [ ] revisit abandoned route (specify: <route id + new evidence>)
- [ ] return to literature / SOTA inventory (specify what to re-verify)
- [ ] run focused ablation to isolate root cause (specify variable)
- [ ] escalate to user decision (when retrospective itself cannot decide)

## Advisory boundary (HARD)

This retrospective is **advisory only**. It MUST NOT:

- overwrite `docs/03_benchmark_roadmap.md`
- cancel or modify any currently running sbatch job
- override an active Track B promotion in progress
- replace a user-approved technical path
- write to `docs/09_decisions_log.md` (only /pivot abandon-route triggers that)

Any **major change** (pivot to new axis, revive abandoned route, kill running job, change Track B promotion rule) MUST go through:

```text
/tri-review (let three reviewers weigh the retrospective evidence)
  → /pivot (single decision)
  → user-visible confirmation
```

## Write-back

Append this entry to `docs/08_pivot_decisions.md` under a new `## Retrospective <date>` section (so the audit trail lives next to pivots).
不要写 docs/03/04/06/09。
```

---

## Subagent fan-out (optional)

若历史超过 30 个 iteration 或 4 条 path，可并行：

- `literature-claim-extractor`：扫 docs/01 + 新近 deep research 报告，看是否有新 claim 颠覆原 hypothesis
- `sota-source-verifier`：抽样重新验证 3-5 个 SOTA 链接，看 leaderboard 是否更新（新 SOTA 出现会让本项目 gap 重新评估）
- 主 agent 负责合并 + 写 docs/08

硬规则同 lwcr 全局：read-only fan-out，不写 docs/03/04/06/09。

---

## 与 /pivot 的关系

- `/pivot` 是**单实验**决策（看本轮 tri-review + result）。
- `/retrospective` 是**跨实验**审视（看整段历史）。
- 两者**不抢决策权**：retrospective 给 advisory，pivot 给 binding。
- 如果 retrospective 发现需要大改方向，必须 trigger 下一次 /tri-review 把这个 advisory 作为输入之一。

---

## Don'ts

- 不要在 retrospective 里直接修改 active TODO（让 pivot 来动）。
- 不要把 retrospective 输出当作"已决定的事"——它只是证据汇总和建议。
- 不要忽略 docs/09 的 cousin 列表：复活 abandoned route 时必须解释 cousin 关系。
- 不要让 retrospective 跑成"安慰型回顾"——必须 inline gap 数字、ITER ids、tri-review 原句作为证据。

---

## Hand-off

- **Inputs from**: `docs/03` ~ `docs/09` 全量 + optional `$ARGUMENTS`
- **Outputs to**: `docs/08_pivot_decisions.md` 新增 `## Retrospective <date>` section
- **Next skill**: 若 recommendation 非 "continue"，调 `/tri-review` 把 retrospective entry 作为额外 context，然后 `/pivot`
