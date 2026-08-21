---
name: route-reset
description: "*· Restart, fork, or switch the research route inside the same project without creating a new project."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Route-Reset: 同项目内重新开线 / 切换主流程

`/reframe` 处理战略重定向；`/route-reset` 更操作化：当一条路线走不通、要从 Stage A 重新做 deep research，或 Stage A/B 完成后要切到 Stage C，不新建项目，而是在同一项目中重排 pipeline、保留证据、重建下一轮入口。

## Step 0 · 先说明给用户听

在任何人闸前先用通俗语言输出 5 行以内：

```markdown
我们现在不是“调一个实验参数”，而是在决定是否换主线。
已完成的是：...
卡住/要切换的原因是：...
如果继续旧线，代价是：...
如果重启/切段 C，保留哪些成果：...
```

这个摘要解决“用户长时间没看，回来不知道发生了什么”的问题；没有这段，不进入后续人闸。

## Step 1 · 读取全局状态

读：
- `docs/11_master_plan.md`
- `docs/00_active_goal.md`
- `docs/01_literature_review.md`
- `docs/02_sota_model_inventory.md`
- `docs/03_benchmark_roadmap.md`
- `docs/04_experiment_iterations.md`
- `docs/06_results_log.md`
- `docs/07_tri_review.md`
- `docs/08_pivot_decisions.md`
- `docs/09_decisions_log.md`
- `docs/10_findings.md`
- `docs/12_publication_strategy.md`、`docs/13_pipeline_blueprint.md`、`docs/14_validation_matrix.md`
- `docs/19_evaluator_contract.md`、`docs/20_baseline_reproduction.md`
- `docs/experiments/ATLAS.md`、`refs/dossiers/`、`wiki/`

## Step 2 · 选择 reset 类型

| Reset type | 何时使用 | 下一步入口 |
|---|---|---|
| `rerun-stage-a` | 当前大方向不成立，需要重新 deep research | `/research-interview continue:` 或 fresh-like focused prompt |
| `route-fork` | 保留旧线 parked，新线并行探索 | `/reframe` → `/benchmark-roadmap` |
| `stage-c-transition` | 已有强候选/完整思路，停止盲目探索，补投稿/流程证据 | `/master-plan` → `/publication-plan` 或 `/pipeline-blueprint` |
| `pipeline-rewrite` | docs/11 的流程图、阶段顺序、完成证据不再对 | `/master-plan` 重写 + 相关 docs append |

## Step 3 · Carry-forward / Park / Abandon 账本

必须列出：

| Item | Evidence | Decision | Destination |
|---|---|---|---|
| 已核实 evaluator / metric / split | docs/19, refs/dossiers | TRANSFER | 新路线继续用 |
| 已复现 baseline 事实 | docs/20 | TRANSFER/PARK | 新路线或 wiki |
| 已跑实验结果 | docs/06, docs/experiments | TRANSFER/PARK/ABANDON | docs/11/09/wiki |
| 工程代码/组件 | scripts/configs/runs | TRANSFER/PARK | docs/16/docs/21 |
| 被证伪路线 | docs/07/08/10 | ABANDON | `/decisions-log` |

定义：
- `TRANSFER`：迁移到新主线，继续作为事实。
- `PARK`：暂存，不作为主线，但保留 re-entry 条件。
- `ABANDON`：route-level 放弃，必须走 `/decisions-log`。

## Step 4 · 设计新 pipeline map

给出不超过 8 步的新地图，包含“为什么先做这一步”：

```text
<Step 1> → <Step 2> → <Step 3> → <Step 4>
             ↑ now
```

并明确：
- 新 Mode：`Discovery-Iteration` / `Publication-Validation` / `Pipeline-Execution` / `Mixed`
- 当前阶段：A / B / C / Ph8
- 哪些旧 docs 继续权威，哪些只作历史参考。
- 是否需要重跑 deep research、SOTA inventory、baseline reproduction、evaluator contract。

## Step 5 · 人闸提议

未确认前只输出 proposed diff，不直接改：

```markdown
## Route reset proposal <date>
- Type:
- Why reset:
- User-facing plain summary:
- Carry-forward:
- Parked:
- Abandoned:
- New pipeline map:
- Docs to update:
- Skills to run next:
- Risks if wrong:
```

用户确认后再落盘。

## Step 6 · 落盘动作

确认后：
- `docs/11_master_plan.md`：更新 Mode、pipeline 地图、已确定选择、开放问题、恢复指令。
- `docs/00_active_goal.md`：append `## route_reset_<date>`，记录原因与 carry-forward。
- `docs/03_benchmark_roadmap.md`：如果仍走 Discovery，append reset 后的 roadmap 入口，不删除旧路线。
- `docs/12_publication_strategy.md` / `docs/13_pipeline_blueprint.md`：如果切段 C，初始化或更新主线。
- `docs/09_decisions_log.md`：只有 ABANDON 的路线才写。
- `wiki/ideas`：PARK 项写 re-entry 条件。
- `docs/15_evidence_register.md`：用 `/note-gate` 索引 reset 决策。

如果目标值、scope、SOTA benchmark 变了，转 `/revise-goal`；`/route-reset` 不直接移动球门。

## 边界

- 不新建项目；除非用户明确要求。
- 不删除旧 docs/runs/refs/wiki。
- 不把单次失败升级成 route reset；单次失败走 `/result-log` + `/pivot`。
- 切 Stage C 不等于取消实验，只是把实验从“找方向”改成“补证据缺口”。

## Handoff

- **Inputs from**: `/pivot`、`/tri-review`、`/retrospective`、用户新决定、Stage C 转换需求。
- **Uses**: `/master-plan`、`/reframe`、`/research-interview`、`/publication-plan`、`/pipeline-blueprint`、`/note-gate`、`/decisions-log`。
- **Outputs to**: `docs/11`、`docs/00`、`docs/03/12/13`、`docs/09`、`wiki/ideas`、`docs/15`。
- **Next**: 新路线从 `docs/11 §6` 指定的 skill 继续。
