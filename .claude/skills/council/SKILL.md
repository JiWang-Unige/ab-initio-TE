---
name: council
description: "A3.5+· Adversarial multi-agent COUNCIL for Stage A. Runs a multi-round DEBATE among the Claude / Codex / Antigravity CLIs over one research direction / hypothesis / plan — they SEE and REBUT each other across rounds (unlike /tri-review's independent, no-cross-talk divergent review), under assigned adversarial stances (Proponent / Opponent / Referee), while the USER arbitrates. Goal: stress-test the weakest assumptions and solidify the foundation BEFORE any GPU is spent. Use during or after /grill on a foundation-critical or contested direction. Opt-in (multi-round CLI — costlier than /grill); not for every discussion."
argument-hint: "<the proposition to debate, e.g. 'CRF head beats softmax for exon boundaries'>"
---

# Council: 对抗式多 agent 辩论（烧 GPU 前夯实段 A 基础）

`/grill` 是**你 vs 单个 agent** 的苏格拉底拷问；`/council` 是**多个外部 CLI agent 互相辩论 + 你当裁判**——强调**对抗性**（彼此看见、逐轮反驳），用于把一个重要/有争议的方向在烧 GPU 前**辩穿、夯实基础**。它也可用于 `/pursue` 首轮前或重大资源投入前的方向争议，但不替代实验后的 `/tri-review`。

**与 /tri-review 的区别（关键，别混）**：

| | `/tri-review` (B4) | `/council` (A3.5+) |
|---|---|---|
| 时机 | 实验**之后** | 段A 烧 GPU **之前** |
| reviewer 关系 | **独立**，互不可见 | **互相看见、逐轮反驳** |
| 思维取向 | 发散（各自全功能审） | **对抗**（指派立场，攻防） |
| 产出 | pivot 决策 | 方向基础合约（钉死/存疑/否决） |

**使用边界**：
- 没有实验结果、争议是“该不该走这条路/该先做哪条路线” → `/council`。
- 已有具体 run 结果、要决定继续/scale/pivot/abandon → `/tri-review`。
- `/pursue` 前如果存在 ≥2 条基础路线互斥、会消耗大量 GPU 或影响 `ACTIVE_GOAL`，可以先 `/council`；普通 cohort 内的小选择仍走 `/tri-review`/`/pivot`。

**复用** `/tri-review` 的 CLI 管线：`cluster_config.yaml` 的 `cli_review.reviewers`（A=claude/B=codex/C=antigravity，Reviewer C 经 `.claude/skills/tri-review/scripts/reviewer_c_antigravity.sh`）+ **stdin 喂 prompt 防 ARG_MAX**。

> **长讨论的落盘（你自控压缩）**：council 多轮很占 context。三方原文本就建议存 `/tmp/council_<slug>/round*.md`；收敛后写完整"方向基础合约"。**若你准备 `/compact`，先把已辩出的结论 flush 进 docs/00/11 §4 再压**——不必每轮强制 append docs（你自控时机即可），撞上 auto-compact 才丢最近一轮。

## Step 0 · 定辩题 + 共享上下文
- 与用户确认**辩题**：一句**可证伪**的命题（如"在外显子边界标注上 CRF head 显著优于 softmax head"）。模糊就先收敛成可辩的命题。
- 构建**自足的轻量共享上下文**写入 `/tmp/council_<slug>/context.md`（reviewer 看这一份就够，不依赖它访问不到的文件）：研究目标/scope（docs/00）、相关 SOTA + dossier 摘要（docs/02 + refs/dossiers，各一句指标实现/数据集/split）、`/grill` 已钉死/存疑点（docs/00 `direction_clarified`）、本方向的核心不确定性。

## Step 1 · Round 1 · 指派立场陈述（三方互不可见）
三方各领一个**对抗立场**（每次轮换分配，避免固定角色偏置）：
- **Proponent**：把辩题 steelman 到最强——最强机制论证 + 最有力支持证据（带出处）。
- **Opponent**：red-team——最弱假设、最可能 fail 的机制原因、矛盾证据、更简单的替代解释。
- **Referee**：列出"判定这场辩论必须回答的关键问题"，并标注哪些可**检索/复现**验证、哪些纯属猜测。

每方输出固定结构：`立场 | 1-3 个最强论点(各带依据) | 对自己立场最大的威胁 | 需要的判定证据`。用 stdin 并行调用，prompt 三方相同只换 identity+stance。

## Step 2 · Round 2 · 交叉反驳（三方互相可见）
把 Round 1 三方**原文互相喂给对方**，每方必须：
- **反驳对方最强论点**（攻要害，不空辩、不复述）；
- **诚实承认对方哪些点站得住**（不为赢而嘴硬）；
- **更新自己立场**（若被说服，明说改了什么；没被说服，说明为何）。

反谄媚纪律：压力≠证据；反复坚持同一空答不加分；只攻论点不攻人。

## Step 3 · 收敛 · host 综合 + 用户裁决
host（主 Claude）**只做聚合**，不当第四个 reviewer：
- **已夯实（共识 + 依据）**：三方一致且有据。
- **仍争议（未决）**：分歧点 + 为何重要 + 如何判定 → `/reproduce-baselines` 或 `lit_search`/exa。
- **被否决/降级的假设**：被有力反驳、应放弃或留 PARK。
- **最强反方论证**（保留警惕，写进合约）。

把**争议点交用户裁决**（你支持哪边 / 要不要先验证 / 直接否决）——用户拍板才算数。

## Step 4 · 产出"方向基础合约"
inline + append 到 `docs/00` 的 `## council_<date>`（或 `docs/11` §4 待议分支）：
```markdown
## Council <date> — 辩题: <可证伪命题>
- 立场分配: Proponent=<A/B/C> Opponent=<…> Referee=<…> · Quorum: <3/3 | 2/3 DEGRADED | 1/3>
- 已夯实(共识+依据): <bullets>
- 仍争议 → 验证: <bullet → /reproduce-baselines | lit_search>
- 否决/降级假设 + 理由: <bullets>
- 用户裁决: <你的决定>
- 最强反方论证(保留警惕): <2-3 句>
```

## 降级 / 边界
- 复用 tri-review 的失败重试 + quorum 降级：**3 方**=完整对抗；**2 方**=`DEGRADED`（缺一方对抗性，confidence ≤ Medium）；**1 方**=退化为单 agent，提示"改用 `/grill` 即可，无需 council"。
- **opt-in**：多轮 CLI 比 `/grill` 贵——用于**基础关键 / 有争议**的方向，不是每次讨论都开。日常拷问用 `/grill`。
- 不 kill running job、不写 `docs/03` 主体、不替用户做方向决策。
- 不把 `exit 0` 当成功；每方输出须非空且含要求的结构字段，否则按失败重试。

## Hand-off
- **Inputs from**: `/grill`（有争议的方向）、`docs/00`/`docs/02`、`refs/dossiers`
- **Uses**: `cluster_config.yaml cli_review`、`.claude/skills/tri-review/scripts/reviewer_c_antigravity.sh`、`scripts/lit_search.py`、MCP exa/anysearch
- **Outputs to**: `docs/00 ## council_<date>`（基础合约）；争议点 → `/reproduce-baselines` / `lit_search`
- **Next**: 基础夯实后 → `/configure-project` 或 `/benchmark-roadmap`；仍有空答的技术点 → `/grill` 补钉
