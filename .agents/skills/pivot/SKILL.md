---
name: pivot
description: "B5· Make a single final decision (continue / tune / scale / replace component / change backbone / change objective / abandon / return to literature / sanity check first) by CONSUMING the output of /tri-review."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Pivot

基于 `$ARGUMENTS`(应包含 `/tri-review` 输出)做**单一最终决策**。

## 硬约束

- **必须在 `/tri-review` 之后**调用,不可在前
- **先完整记录全部 tri-review 结论,再决策**——做任何决策前,先把 A/B/C 三方各自的 judgment / next-action / 主要 concern / confidence **逐条誊录**到 `docs/08`(见输出格式的 *Tri-review summary* + *Reviewer-proposed directions* 两表),**不得只保留收敛后的结论而丢弃各 reviewer 的原始建议**。这样后续 portfolio / retrospective 能回看每个 reviewer 当初提了什么。
- **单一 primary 决策 + 可选并行 cohort**——本轮收敛出**一个 primary 决策**(不能有两个并列的"最终主方向");但 primary 之外,可把 reviewer 提出的**正交、可并行**方向编成一个 portfolio cohort(≤ `max_parallel_directions`,各自独立 `exp_id`),与 primary **同轮并行推进**。primary 单一是为了避免决策发散;cohort 是 primary 的并行补充,不是并列的另一个最终决策。若 cohort 中 ≥2 条方向需要同时改共享代码，必须交给 `/workspace-matrix` 建可选 git/worktree 隔离；若只改 config/sbatch，则用默认 exp_id 目录隔离。
- **从不并行 `/pivot` 这一步**——本 skill(决策合成)必须由 main agent 直接执行,不可 fan-out 给 subagent。tri-review 的三方已提供多视角,pivot 的工作是把它们收敛 + 编排 cohort,不需要再分裂决策步本身。
- **Host 不当 4th reviewer**——本 skill 是 tri-review 输出的 *消费者* 和 *决策者*,不是再起一个独立评审视角。如果发现 tri-review 输出有遗漏,应当 redo /tri-review,而不是在 pivot 里补一个"主 agent 视角"。
- 用户偏好: 大差距 → 换架构,不调参

## Sanity check 状态(先确认)

| Item | Status |
|---|---|
| At least two independent CLI reviewers succeeded | ✅/❌ |
| Any reviewer raised comparability blocker? | ✅/❌/N/A |
| Any reviewer raised leakage / reproducibility blocker? | ✅/❌/N/A |
| Metric impl matches SOTA | ✅/❌ |
| Loss showed expected pattern | ✅/❌ |
| Seed variance reasonable (if multi-seed) | ✅/❌ |

任一 ❌ → 决策只能是「先解决 sanity」。

## 调参是否合理

**★ 反调参硬闸（确定性，不靠主观）**：若 `validate_goal.py` 输出 `tuning_allowed=false`（即 `gap_to_target ≥ tuning_gap_threshold`，默认 0.05），则决策**禁止**选 "Tune current architecture" / "Continue as-is"——**必须**选一个架构轴（replace component / change backbone / change objective / change decoder / data_view）。这把 CLAUDE §3"架构优先"从约定变成 pivot 的硬约束，根治"沉迷细微调参"。

| 条件（与 validate_goal 一致） | Tuning OK? |
|---|---|
| `tuning_allowed=true`（gap < 0.05）+ 训练不稳定 | ✅ |
| `tuning_allowed=true` + 训练稳定但未超越 | ✅ 同时 scale |
| `tuning_allowed=false`（gap ≥ 0.05） | ❌ **硬禁止调参，必须换架构轴** |
| Sanity 未通过 / validate=failed_run | ❌ 先 debug |

**★ 消费 validate_goal 的两个 advisory 旗标（G8/G9）**：
- `regression=true`（scale 跑得比该候选自己的 screen 还差，架构不可扩展）→ **优先 change-backbone / abandon-route，不要继续 scale 或调参**——这正是 Track A→B 晋升要防的核心失败。
- `suspicious_high=true`（指标超 `sane_upper` 或越 `sane_range`，疑似泄漏/eval bug）→ **claim 前必须先验证**（回 `/code-review-gate` 或 `/reproduce-baselines` 复核 metric/split），**不得**在未排查时把它当 SOTA 候选晋升。

## 输出格式

```markdown
# Pivot Decision: <exp_id>

## Inputs consumed
- /tri-review: <ref>
- /result-log: <ref>
- Resource profile: <screen / full / scale>

## Current evidence summary

## SOTA gap
| Metric | Current | SOTA | Gap (abs) | Gap (rel %) | Severity |
|---|---:|---:|---:|---:|---|

## Sanity check
- [ ] ...

## Tri-review summary (record ALL reviewer conclusions — drop none)
| Reviewer | Judgment | Next action proposed | Main concern | Confidence |
|---|---|---|---|---|
| A · Claude | | | | |
| B · Codex | | | | |
| C · Antigravity | | | | |

Consensus:
Disagreement:
Quorum / degraded review status: <3/3 | 2/3 DEGRADED_REVIEW | 1/3 SINGLE_REVIEW_CONTINUATION>

## Reviewer-proposed directions (ordered A→B→C, verbatim before convergence)
逐个誊录每个 reviewer 建议的候选方向,保留原始建议供 portfolio 选材(不要在这里就筛掉):
| # | From reviewer | Direction | major_axis | mechanism_delta | Orthogonal to others? | Into this round's cohort? |
|---:|---|---|---|---|---|---|
|  | A · Claude | | | | | |
|  | B · Codex | | | | | |
|  | C · Antigravity | | | | | |

## Is tuning justified?
- One of ✅ / ❌ / 🟡 / Premature (sanity 没过)

## Architecture hypothesis status
supported / weakened / falsified / unknown

## DECISION (choose exactly one)

- [ ] Continue current architecture as-is (more seeds / more data)
- [ ] Tune current architecture (justify above)
- [ ] Scale data / training (Track B with current architecture)
- [ ] Replace component: <which layer / module / head / decoder>
- [ ] Change backbone: <from X to Y>
- [ ] Change objective / loss: <from X to Y>
- [ ] Comparability audit first (inline)
- [ ] Sanity check first → inline data contract checklist or reproduce baseline
- [ ] Abandon this route → /decisions-log
- [ ] Return to literature → /research-synthesize

## Why this decision (not another)
<明确解释为什么不是别的选项,尤其是为什么不是「调参」>

## Best next architecture moves (if applicable)
| Priority | Move | Expected mechanism | Goes to which EXP / Track |
|---:|---|---|---|

## Parallel cohort this round (primary + orthogonal directions)
- **Primary direction (single)**: 对应上面唯一的 DECISION。
- **Parallel cohort (可选, ≤ `max_parallel_directions`)**: 从 *Reviewer-proposed directions* 里挑**正交、可并行**的方向,各起独立 `exp_id` 同轮跑,交给 `/pursue` portfolio fan-out。

| Slot | EXP ID (new) | Direction | major_axis | mechanism_delta | Track | Resource profile |
|---|---|---|---|---|---|---|
| primary | | | | | | |
| parallel-1 | | | | | | |
| parallel-2 | | | | | | |

Shared-code conflict? <yes/no>；若 yes → 下一步先 `/workspace-matrix`，再 `/implement`。

## If abandoning, log to /decisions-log:
- Path tried:
- Evidence why failed:
- What we now believe:
- Cousins to also avoid:

## TODO update
- [ ] update docs/05_todo.md
- [ ] update docs/08_pivot_decisions.md
- [ ] run /note-gate to persist reviewer-proposed directions and decision rationale
- [ ] update /master-plan if the next pipeline step or user-visible state changed
- [ ] if cohort needs shared-code isolation, run /workspace-matrix and update docs/17_parallel_workspace.md
```

## 默认倾向(与用户偏好一致)

- 大差距 + sanity 通过 → **换结构**
- 接近 SOTA + 不稳定 → 可调参
- 小样本接近 SOTA → 扩大数据 scaling
- scale 后效果掉 → 架构不可扩展,换路线
- 泛化失败 → 优先研究泛化结构,不只调 dropout
- 同一架构家族 ≥ 3 次失败 → return to literature 或 abandon

## Don'ts

- 不要有两个并列的 **primary** 决策(primary 必须单一);但 reviewer 提出的正交方向可编成并行 cohort,这不算并列决策
- 不要在记录决策时丢弃任何 reviewer 的原始建议(两张 tri-review 表必须填全)
- 若 tri-review 0 方成功,不要给 pivot 决策;1 方成功只能走 `SINGLE_REVIEW_CONTINUATION`(可逆非 claim 迭代,不能 claim/abandon/改 goal)
- Sanity 没过时不要 claim SOTA；但可以讨论用于下一轮的 architecture debug
- /tri-review 缺失时不要调用本 skill
- "Continue" 不能模糊—必须有具体行动(多 seed / 多数据 / 新 ablation)

## Hand-off

- **Inputs from**: `docs/07_tri_review.md` 中本 exp 的 entry + `docs/06_results_log.md`
- **Outputs to**: `docs/08_pivot_decisions.md` (append), `docs/15_evidence_register.md` via `/note-gate`, `docs/11_master_plan.md` when navigation changes, 触发 `docs/04_experiment_iterations.md` 的下一轮
- **Next skill**(if abandon): `/decisions-log`; if shared-code parallel cohort: `/workspace-matrix`; otherwise directly next `/goal-prompt` or `/pursue` cohort
