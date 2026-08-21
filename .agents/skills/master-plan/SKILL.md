---
name: master-plan
description: "C0· Maintain docs/11_master_plan.md as the user-facing navigation map for the whole research pipeline: current mode, current step, why this step comes first, user-approved choices, unresolved branches, recent decisions, and resume instructions."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Master-Plan: 用户导航图 / 统领性推进文件

本 skill 解决“讨论 A/B/C/D 后只继续聊 B/C，过 20 分钟用户忘了 A/D 已经确认”的问题。它维护 `docs/11_master_plan.md`，作为项目级导航图。

## 触发时机

必须触发：
- 每次用户明确支持/反对某个选项后。
- `/pivot` 后、`/reframe` 后、`/publication-plan` 后、`/pipeline-blueprint` 后。
- 长作业 `submit-and-handoff` 前。
- 从探索迭代切到投稿推进 / pipeline 执行时。
- 用户说“现在到哪了”“为什么先做这个”“之前我们定了什么”。

建议触发：
- 一段复杂讨论结束但还没产生实验结果。
- 多个分支同时存在，用户可能丢失上下文。

## Step 1 · 读已有事实，不靠对话记忆

读取：
- `docs/11_master_plan.md`（若无则用模板创建）
- `docs/00_active_goal.md`
- `docs/03_benchmark_roadmap.md`
- `docs/04_experiment_iterations.md`
- `docs/05_todo.md`
- `docs/06_results_log.md`
- `docs/08_pivot_decisions.md`
- `docs/10_findings.md`
- `docs/12_publication_strategy.md`（若存在）
- `docs/13_pipeline_blueprint.md`（若存在）
- `$ARGUMENTS` 中的新事件/新决策

若当前对话里刚发生了用户选择，也要写入“已确定选择”，但必须明确标注来源为 `conversation <date>`，不要假装来自已有文件。

## Step 2 · 判定当前模式

四类模式：

| Mode | 何时使用 | 典型下一步 |
|---|---|---|
| `Discovery-Iteration` | 尚在找模型方案 / 超 SOTA 路线 | `/benchmark-roadmap → /pursue` |
| `Publication-Validation` | 已有强候选或完整思路，需要做证据包 | `/publication-plan → /generalization / downstream tasks` |
| `Pipeline-Execution` | 已有 raw data / 生信分析流程 / 固定 pipeline | `/pipeline-blueprint → stage execution → validation` |
| `Mixed` | 一边保留少量探索，一边推进投稿/流程证据 | 主线由 `docs/11` 指定 |

如果模式切换，必须写明：
- 为什么切换。
- 哪些旧结论 carry forward。
- 哪些迭代逻辑暂时降级为 advisory，而不是删除。

## Step 3 · 更新 pipeline 地图

在 `docs/11` 的 pipeline 地图里写清：
- 全部关键步骤，不超过 8 步。
- `now` 在哪里。
- 每一步为什么要先于后一步。
- 每一步完成证据是什么。

示例：

```text
定位投稿层级 → 定义核心贡献 → 设计验证矩阵 → 跑下游任务 → 统计检验 → 组织 figure/table
                       ↑ now
```

或：

```text
raw data manifest → QC → preprocessing → model/stat analysis → validation → figures
         ↑ now
```

## Step 4 · 写“已确定选择”与“开放问题”

### 已确定选择
只写用户已经明确支持的项，格式：

```markdown
| ID | Date | 选择 | 理由 | 影响哪些后续步骤 | 可重开条件 |
|---|---|---|---|---|---|
| D-001 | 2026-06-10 | 采用 Publication-Validation 作为主线 | 已有超 SOTA 候选，下一步是论证可靠性 | docs/12/14, downstream task matrix | 若主候选在 full validation 失败 |
```

### 开放问题
把未定的 B/C 分支留在表里，不要让它们消失：

```markdown
| ID | 问题 | 当前候选 | 证据缺口 | 下一步如何关闭 | Owner |
|---|---|---|---|---|---|
| Q-002 | 目标期刊选一区还是专业二区？ | A/B | 缺 validation burden 评估 | /publication-plan 做定位 | agent+user |
```

## Step 5 · 更新“现在该做什么”

必须用用户能一眼懂的语言写：
- 当前动作。
- 为什么不是别的动作。
- 下一步触发条件。
- 如果换会话/换 driver，恢复指令。

### 5.5 人闸摘要（必须通俗）

如果下一步需要用户决定，先写一段 3-6 句的“非专业摘要”，禁止只给术语表：

```markdown
我们刚做了什么：
现在遇到的问题：
为什么这会影响后续结果：
可选方向 A/B/C 分别意味着什么：
我的建议和风险：
```

这段要让长时间没看项目的人也能做决定；专业细节可以放在后面的表格或引用里。

## Step 6 · 输出对话内摘要

最后输出 5 行以内：

```markdown
### 当前导航
- Mode: ...
- Now: ...
- 已固定: A, D
- 未闭合: B, C
- 下一步: ...
```

## 不要做的事

- 不要把 `docs/11` 写成论文综述；它是导航图。
- 不要只记录最终结论而不记录为什么先做这一步。
- 不要覆盖历史推进记录；append 或更新表格均可，但要保留日期。
- 不要替代 `/pivot`、`/publication-plan`、`/pipeline-blueprint` 的专业判断；它只做统领和定位。

## Handoff

- **Inputs from**: 任意讨论、`/pivot`、`/publication-plan`、`/pipeline-blueprint`、`/note-gate`
- **Outputs to**: `docs/11_master_plan.md`
- **Next**: 由 `docs/11` 的 “现在该做什么” 指定
