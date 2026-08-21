---
name: note-gate
description: "*· Smart capture gate that decides whether new metrics, discussion conclusions, user preferences, failed attempts, SOTA updates, or external-software outputs should be persisted, then routes them to /note-add, /result-log, /exp-log, docs/10_findings.md, docs/11_master_plan.md, d…"
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Note-Gate: 智能归档门控

`/note-add` 原本太依赖人主动调用，容易漏掉指标、用户选择和讨论结论。本 skill 是一个**轻量门控层**：每完成一小段工作，就判断哪些信息必须持久化，并把它们路由到正确文件。

## 核心思想：弱门控 + 强归档

- **弱门控**：用一个低成本、保守的判断器（可以是小模型/低上下文 pass，也可以是下面的 deterministic checklist）只回答“是否值得记录”和“记录到哪里”。弱门控宁可多报，不负责写最终文本。
- **强归档**：主 agent 根据弱门控 verdict，把信息写入 `docs/15_evidence_register.md`，并调用或执行 `/note-add`、`/result-log`、`/exp-log`、`/master-plan` 等对应归档。

这样避免每段讨论都由强模型完整重写文档，也避免重要信息留在对话上下文。

## 触发时机（默认每个阶段结束检查一次）

必须触发：
- 写入 `reports/<exp_id>.json` 后。
- `/result-log` 后。
- `/pivot` 后。
- `/publication-plan` 或 `/pipeline-blueprint` 后。
- `/sota-randomized` 每个 seed batch 结束后。
- 讨论中用户明确支持/反对 A/B/C/D 某些选项后。
- 外部软件 run 产生 `software_outputs/<tool>/<run_id>/` 后。

建议触发：
- 长作业提交前/完成后。
- 发现 bug、环境坑、数据问题、指标异常。
- 有“这个之后可能有用”的想法。

## Step 1 · 收集候选 evidence

从 `$ARGUMENTS`、最近文件、报告路径中抽取候选：

| Type | 例子 | 默认路由 |
|---|---|---|
| metric | seed=3 F1=0.812, mean±std | `/result-log`, `docs/14`, `docs/15` |
| discussion_decision | 用户支持 A/D，B/C 继续讨论 | `/master-plan`, `docs/15` |
| user_preference | 风险偏好、目标期刊、反对某方向 | `docs/11`, `docs/12`, `docs/15` |
| failure_reason | OOM、metric bug、数据泄漏 | `docs/10`, `docs/06`, `docs/15` |
| insight | 机制层发现 | `docs/10`, `wiki/notes`, `docs/15` |
| idea | 新假设 | `/note-add kind=idea`, `wiki/ideas` |
| paper/repo | 新 SOTA/新文献 | `/note-add kind=paper`, `refs/`, `docs/05` |
| pipeline_output | 外部软件输出/QC | `docs/13`, `software_outputs`, `docs/15` |
| artifact_path | 新脚本/配置/输出目录 | `docs/16`, `docs/15` |
| evaluator_contract | metric/evaluator/split/schema 变化 | `docs/19`, `docs/15` |
| baseline_reproduction | SOTA/基线复现事实或 waive | `docs/20`, `refs/dossiers`, `docs/15` |
| code_review | `/code-review-gate` PASS/BLOCKED/WAIVED | `docs/21`, `docs/15` |
| framework_upgrade | 框架升级/兼容修复 | `docs/22`, `docs/15` |

## Step 2 · 门控判定

对每个 candidate 打分：

| 问题 | yes 则 +1 |
|---|---:|
| 是否包含数值指标、seed、路径、版本、hash？ | +1 |
| 是否改变下一步动作或优先级？ | +1 |
| 是否是用户明确偏好/选择？ | +1 |
| 是否能避免未来重复踩坑？ | +1 |
| 是否支撑投稿 claim / figure / table？ | +1 |
| 是否涉及 SOTA/benchmark/数据 split/metric 可比性？ | +1 |
| 是否来自外部来源，需要 provenance？ | +1 |

判定：
- `score >= 2`：必须记录。
- `score = 1`：写入 Gate decisions，若一句话能讲清则记录短索引。
- `score = 0`：可不记录，但在 `Gate decisions` 留一行，说明为什么跳过。

## Step 3 · 路由动作

按类型执行：

```markdown
| Candidate | Score | Verdict | Route | Action |
|---|---:|---|---|---|
| EXP-B-003 mean±std | 5 | record | docs/06 + docs/14 + docs/15 | run /result-log, append validation matrix |
```

常见路由：
- 实验结果 → `/result-log` → `/exp-log` → `docs/14`（如投稿相关）→ `docs/15`。
- 用户选择/流程定位 → `/master-plan` → `docs/15`。
- 新想法 → `/note-add kind=idea`。
- 新论文/新 repo → `/note-add kind=paper`。
- 环境/bug 经验 → `docs/10_findings.md` Engineering Findings + `docs/15`。
- 流程 stage 输出 → `docs/13_pipeline_blueprint.md` ledger + `software_outputs/.../manifest` + `docs/15`。
- evaluator / baseline / code-review / upgrade → 分别写 `docs/19/20/21/22`，再在 `docs/15` 登记索引。

## Step 4 · 写 Evidence Register

**先取唯一 ID（防 note-add/note-gate 撞号）**：`EID=$(python3 scripts/next_evidence_id.py)`。
多类型一条证据多路由时（primary_type + also），**同一 EID 写一行、Routed to 列出全部目标**，不要每路由发一个新 ID。
在 `docs/15_evidence_register.md` append：

```markdown
| Evidence ID | Date | Type | Summary | Source | Routed to | Status | Owner |
|---|---|---|---|---|---|---|---|
| <EID> | <date> | metric | SOTA-randomized mean F1=... ± ... | reports/SOTA-... | docs/14 §5; docs/06 | recorded | agent |
```

若不记录，append 到 Gate decisions：

```markdown
| Date | Candidate evidence | Gate verdict | Reason | Revisit condition |
|---|---|---|---|---|
| 2026-06-10 | quick thought about X | skip | no action/claim impact | revisit if appears in tri-review |
```

## Step 5 · 对话内简报

输出：

```markdown
### 归档门控结果
- 必须记录：N 条，已路由到 ...
- 仅登记跳过：M 条
- 更新了：docs/15, docs/11/10/14/... 
- 下一步：...
```

## 不要做的事

- 不要把所有聊天逐字存档；只存 durable evidence。
- 不要把未经验证的指标写成结论；标 `unverified`。
- 不要替代 `/result-log` 和 `/exp-log`；结果仍要走正式结果链。
- 不要在 running job 期间改其 config/output。

## Handoff

- **Outputs to**: `docs/15_evidence_register.md`，并按路由更新 `docs/10/11/12/13/14/16`、`wiki/`、`refs/`
- **Next**: `/master-plan`（若影响路线），`/publication-plan`（若影响投稿证据），`/pipeline-blueprint`（若影响流程）
