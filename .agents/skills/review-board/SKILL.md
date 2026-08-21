---
name: review-board
description: "A3.6· Tripartite independent blind review of non-result proposals, documents, architecture changes, or strategic questions when no exp_id/result-log exists and a non-adversarial review is needed."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Review Board: 三方独立审阅会诊

`$review-board`（或 `/review-board`）用于**尚无实验结果的学术设计、方案、文档、架构改动或战略问题**的外部独立会诊。

与 `/tri-review`（实验后绑定 `result-log`/`exp_id` 并触发 `pivot`）以及 `/council`（对抗攻防辩论，消耗大量 GPU 前辩穿基础）不同，`$review-board` 不要求有实验结果，不自动触发 pivot，也不指派 Proponent/Opponent 攻防角色。它提供的是**三方独立（背对背，互不可见）的建设性评估与缺陷审计**。

## 负面边界

- 已有实验结果并要决定 continue / scale / pivot / abandon：用 `/tri-review` → `/pivot`。
- 需要 Proponent / Opponent / Referee 逐轮攻防、用户裁判基础路线：用 `/council`。
- 真实训练前代码审查：用 `/code-review-gate`。
- 文献读完后和用户深聊方向：用 `/grill`。

## 使用场景

- 对新设计的 `docs/03_benchmark_roadmap.md` 进行合理性审计。
- 对即将实施的复杂 Pipeline 架构（`docs/13_pipeline_blueprint.md`）进行 QC 和逻辑审计。
- 讨论一个非实验的战略两难问题（如：“Baobab 集群存储配额告急，应该如何优化数据清理方案？”）。
- 对撰写好的一项 literature review（`docs/01_literature_review.md`）或 baseline reproduction 结论进行盲审。

## 使用规范

- **独立性（背对背）**：调用 Claude、Codex 和 Antigravity 三方 CLI reviewer。三方无法彼此看到对方的评审文本，仅基于 host 提供的共享上下文和评审提纲独立作答。
- **配置复用**：执行时，三方 CLI 的具体执行命令（如 claude, codex exec, agy 等）与模板参数应严格复用 `cluster_config.yaml` 中的 `cli_review.reviewers` 配置，以防多端命令不一致导致环境漂移。
- **无需 exp_id**：可以在没有运行任何实验、没有 status 和 results_log 的情况下运行。
- **Quorum与降级机制**：最理想为 3/3 评审通过。若个别 CLI 执行失败（如 agy 未配置 OAuth），允许降级至 2/3（DEGRADED_REVIEW）输出审计日志。若成功评审方 < 2，则该评审失效。
- **Host 边界**：host 只聚合，不充当第四 reviewer；若只有 1/3 成功，只能把原文交给用户，不写成有效 review-board 结论。
- **审计记录**：评审结果将被合并并追加写入专属审计日志 `docs/23_review_board.md`。

## 与 council 和 tri-review 的区别

| 特性 | `/tri-review` | `/council` | `/review-board` |
| --- | --- | --- | --- |
| **应用时机** | 实验跑完后 | 烧 GPU 大争议前 | **任意时刻，无实验限制** |
| **Reviewer 关系**| 独立且互不可见 | 逐轮交叉反驳（对抗） | **独立且互不可见** |
| **主要定位** | 发散、各自全功能审阅 | 指派立场攻防，辩穿基础 | **背对背方案会诊，设计缺陷审计** |
| **结果去向** | `docs/07` & `docs/08` (触发 pivot) | `docs/00` (方向基础合约) | **`docs/23_review_board.md` (会诊日志)** |

## 步骤流程

1. **确定会诊目标与共享上下文**：
   - 与用户确定本次 review Board 的核心议题（e.g., “评估 docs/03 中提出的 Head 替换方案是否完备”）。
   - 将要评审的文档内容、当前 active scope（`docs/11_master_plan.md §0`）等整理为输入。
2. **三方背对背评审**：
   - 并行调用三方 CLI，输入评审 prompt。
   - 每方需要输出：`1. 方案可行性评估 | 2. 潜在逻辑/实验漏洞 | 3. 改进与替代建议`。
3. **Host 综述与归档**：
   - Host 汇总三方意见，整理出“高度共识项”、“主要分歧/潜在盲点”与“推荐行动项”。
   - 将以上内容以 Markdown 格式追加写入 `docs/23_review_board.md`：
     ```markdown
     ### Review Board - [会诊时间] - [评审议题]
     - Reviewer Quorum: [3/3 | 2/3 DEGRADED]
     - 共享上下文/评估文档: [如 docs/03_benchmark_roadmap.md]
     - 三方意见摘要 (Claude / Codex / Antigravity):
       - [摘要]
     - 审计结论 (共识与缺陷):
       - [共识/缺陷 bullets]
     - 推荐行动方案:
       - [行动项 bullets]
     ```
4. **提示用户决策**：展示给用户看，并推荐下一步行动（如：进行修改，或是按原计划推进）。
