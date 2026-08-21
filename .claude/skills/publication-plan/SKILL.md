---
name: publication-plan
description: "C1· Publication-oriented planning for mature ideas or already-strong results. Positions the target venue/journal tier, defines the publishable core contribution, converts claims into an evidence/figure/table/downstream-task matrix, and writes docs/12_publication_strategy.md plus docs/14_validation_matrix.md. Use when the goal is no longer blind model search but making a known idea/result robust enough to submit."
argument-hint: "<candidate model/result/idea and target venue preference if any>"
---

# Publication-Plan: 投稿推进 / 证据包规划

本 skill 对应用户提出的第二类研究：**我们已经有较完整的思路、甚至已有超越 SOTA 的模型；现在要决定 publish 什么、投哪里、补哪些下游任务与证据**。这不是抛弃迭代，而是把迭代变成“证据缺口驱动”的流程。

## 使用场景

- 已经有一个候选模型在主 benchmark 上超过 SOTA，需要论证可靠性。
- 已经有完整方法想法，需要细化成可投稿故事。
- 需要先定位期刊/会议层级，再倒推 validation burden。
- 需要把“核心贡献”从一堆实验中筛出来。
- reviewer 或导师要求补下游任务、ablation、泛化、统计检验。

## Step 0 · 切换模式声明

先输出：

```markdown
## Mode switch proposal
- From: <Discovery-Iteration / Mixed / ...>
- To: Publication-Validation
- Reason: <已有候选/思路完整/需要投稿证据>
- What remains iterative: <只围绕证据缺口迭代，不再盲目找模型>
- What is frozen unless evidence breaks it: <主模型/核心假设/目标任务>
```

并更新或提示调用 `/master-plan`，让 `docs/11` 成为用户导航。

## Step 1 · 读证据与约束

读取：
- `docs/11_master_plan.md`
- `docs/00_active_goal.md`
- `docs/02_sota_model_inventory.md`
- `docs/03_benchmark_roadmap.md`
- `docs/06_results_log.md`
- `docs/07_tri_review.md`
- `docs/08_pivot_decisions.md`
- `docs/09_decisions_log.md`（已弃路线 + cousin list —— 定核心贡献时别把已否决的路线当卖点，也别漏了"为何不选 X"的论证素材）
- `docs/10_findings.md`
- `docs/14_validation_matrix.md`（若已有）
- `docs/experiments/ATLAS.md`（若已有）
- `$ARGUMENTS` 指定的候选模型/目标期刊

## Step 2 · 期刊/会议定位

不要凭空说“投一区”。必须把定位拆成约束：

| 层级 | 适合什么故事 | 需要的证据 | 风险 |
|---|---|---|---|
| 顶会/一区综合 | 方法新颖 + 多数据集/多任务强证据 | 主 benchmark、外部数据、ablation、OOD、成本、统计 | 证据负担重 |
| 领域强刊/强会 | 清楚解决领域痛点 | 领域主 benchmark + 下游任务 + 可解释/案例 | novelty 要聚焦 |
| 应用/资源期刊 | pipeline/数据/工具价值 | 完整流程、复现、案例、可用性 | 方法 novelty 可弱 |

输出 2-3 个候选定位，不要定稿前写死。若用户已指定目标，按该目标倒推。

## Step 3 · 核心贡献菜单

把潜在贡献拆成 claim，并逐个问：是否值得保留？证据是否够？

```markdown
| Contribution ID | Claim | Novelty type | Evidence needed | Current evidence | Risk | Recommendation |
|---|---|---|---|---|---|---|
| C1 | 新模型在 X 上严格超越 SOTA | performance | comparable full + multi-seed | EXP-B-... | metric mismatch | keep, but validate |
| C2 | 方法在下游任务 Y 有生物学价值 | application | downstream task | missing | high | plan |
```

贡献类型：`performance / method mechanism / robustness / data resource / pipeline usability / biological insight / efficiency`。

## Step 4 · Validation matrix

更新 `docs/14_validation_matrix.md`：
- Main result。
- Downstream / external validation tasks。
- Robustness / OOD / sensitivity。
- Ablations。
- Randomized SOTA small-sample retraining（如果还没做，列为证据缺口）。
- Statistical tests。

每个验证任务必须有：目的、数据、metric、baseline、seed 数、输出路径、完成证据。

## Step 5 · Figure/table 计划

更新 `docs/12_publication_strategy.md` 的 Figure/Table plan：
- Fig.1 不一定是 architecture；也可能是 workflow/pipeline。
- 每张图必须连接一个 claim。
- 每张图必须有所需实验 run ID 或待跑任务。

示例：

```markdown
| Fig/Table | Message | Required experiments / analyses | Owner docs | Status |
|---|---|---|---|---|
| Fig.2 | 主模型在 3 个下游任务上保持优势 | D1-D3 in docs/14 | reports/EXP-* | TODO |
```

## Step 6 · Evidence-gap backlog

把所有待补证据写入 `docs/05_todo.md`，不是写在对话里结束。

格式：

```markdown
## Publication evidence backlog
- [ ] PUB-D1: run downstream task <task> for claim C2 → docs/14 D1
- [ ] PUB-A1: ablation <module> for claim C1 → docs/14 A1
- [ ] PUB-S1: multi-seed paired test for EXP-B-... → docs/14 S1
```

## Step 7 · 输出投稿推进摘要

最后输出：

```markdown
### 投稿推进结论
- 推荐定位：<target tier + backup>
- 主故事：<one sentence>
- 保留贡献：C1, C2, ...
- 最关键证据缺口：<top 3>
- 下一步：<具体 skill/run/pipeline>
```

## 不要做的事

- 不要把“已经超 SOTA”直接等同于“可投稿”；必须看 comparability、variance、downstream、ablation。
- 不要让下游任务无限膨胀；每个任务必须服务一个 claim。
- 不要只给写作建议；本 skill 重点是把投稿需求转成可执行实验/分析矩阵。
- 不要自动承诺目标期刊；输出定位建议和证据负担。

## 完整性自检（确定性，宣布“可投稿”前必跑）
```bash
python3 scripts/validate_stage_c.py --mode publication        # advisory：列出无证据的 claim / 未完成下游 / 未勾选 readiness
python3 scripts/validate_stage_c.py --mode publication --strict   # 宣布 submission-ready 前当硬门（有缺口 exit 2）
```
它**只查完整性不评质量**（每个 claim 是否有 run/evidence、下游任务是否完成、readiness checklist 是否勾完）——是段 C 对应段 B `validate_goal` 的角色。有缺口先补 docs/14/12，不要凭感觉宣布可投。

## Handoff

- **Outputs to**: `docs/12_publication_strategy.md`, `docs/14_validation_matrix.md`, `docs/05_todo.md`, `docs/11_master_plan.md`（通过 `/master-plan` 或直接同步导航）
- **Uses**: `scripts/validate_stage_c.py --mode publication`（完整性闸）
- **Next**: `/generalization`, `/sota-randomized`, `/pipeline-blueprint`, `/implement` 具体下游任务
