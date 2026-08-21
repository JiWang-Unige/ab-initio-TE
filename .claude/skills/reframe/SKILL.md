---
name: reframe
description: "*· Strategic re-direction of the WHOLE research program (not one iteration) when an early assumption turns out wrong, a new path appears that deep-research never explored, or you realize the phases should be re-sequenced mid-stream (e.g. do codingRNA before ncRNA; try traditional DL before pretrained models). Preserves prior findings via a carry-forward ledger (transfer / park / abandon) instead of discarding them, re-sequences the research phases, and is human-gated. Bigger than /revise-goal (which only edits goal targets) and /pivot (one-iteration tactical). Use when the direction itself — not the target — is what changed."
argument-hint: "<what broke / the new direction or re-sequence, e.g. 'do coding RNA first then ncRNA'>"
---

# Reframe: human-gated strategic re-direction with carry-forward

`/pivot` 改**单轮**战术，`/revise-goal` 改**目标值**，`/route-reset` 负责同项目内“重新开线 / Stage A 返工 / A/B→C 切换”的操作化落盘。`/reframe` 管更上层的**战略重定向判断**：早期假设错了、deep-research 没探到的新路径冒出来、或边做边发现**阶段顺序该重排**（先做 codingRNA 再 ncRNA；先堆传统 DL 再上预训练）。它的输出通常交给 `/route-reset` 或 `/master-plan` 落成新的 pipeline。

**何时用**：假设被推翻 / 发现需先做 A 再做 B / pursue 到一半觉得当前大方向不对 / 新文献揭示更优路径。**不是**每轮都用（那是 pivot）。

## Step 0 · 读全局现状
读 `ACTIVE_GOAL.json`、`docs/00-10`、`docs/experiments/ATLAS.md`（全实验分类总览）、`refs/dossiers`、`wiki/`、`docs/09`(已弃路)。`/reframe` 是程序级，必须看**全貌**而非最近几轮。

## Step 1 · Carry-forward 账本（核心——决定什么不丢）
把至今**已验证/已学到**的东西逐条列出并三分类（这是"不想舍弃已有结论"的落地）：

| 项 | 内容 | 处置 | 依据 |
|---|---|---|---|
| 已验证发现/指标口径/数据事实（reproduce-baselines / result-log / findings） | … | **TRANSFER**(迁移到新方向继续用) | docs/10, refs/dossiers |
| 可复用代码/组件（dataloader / eval / 某 head） | … | **TRANSFER** | runs/, configs/ |
| 暂时不适用但将来可能回来的方向/结论 | … | **PARK**(暂存，记 re-entry 条件，不删) | → wiki/ideas + 标记 |
| 已证伪、确定不再走的 | … | **ABANDON** | → `/decisions-log`(cousin+re-entry) |

**PARK ≠ ABANDON**：parked 的进 wiki 可检索 + 记"什么条件下复活"，绝不丢。

## Step 2 · 重述新方向 + 阶段重排序
- **什么假设/前提变了**（一句）+ 证据（哪篇论文/哪个实验结果揭示的）。
- **新的研究阶段序列**（保留旧阶段为 parked，不抹掉）：
  ```
  Reframe <date>: <旧方向> → <新方向/新顺序>
  Phase 1: <如 codingRNA / traditional-DL(CNN,LSTM)>  —— 为什么先做它
  Phase 2: <如 ncRNA / pretrained-LM>                 —— 依赖 Phase 1 的什么 carry-forward
  (parked: <被暂存的原方向 + re-entry 条件>)
  ```

## Step 3 · 轻量 grill 新方向（防换了个方向又是空想）
借 `/grill` 精神快速拷问：新顺序真有依据吗？Phase 1 的结论真能 carry 到 Phase 2 吗？还是只是换个方向逃避当前困难？≥1 个尖锐问题要主人答实。

## Step 4 · 产出重定向提议（diff，不落盘）
inline 输出：carry-forward 账本 + 新阶段序列 + ACTIVE_GOAL scope/sota 的拟改动 + 哪些进 decisions-log / wiki parked。**标明影响**（如换 subject 则 sota_benchmark 要随 `/revise-goal` 改；之前的 success 可能重判）。

## Step 5 · 人闸落盘（确认才写）
主人确认后：
- `docs/03_benchmark_roadmap.md`：**append** `## Reframe <date>` 段（新阶段序列 + carry-forward 映射），**不删**原 roadmap（原阶段标 parked）。
- `ACTIVE_GOAL.json`：经 `/revise-goal` 改 scope/sota（若 subject 变）——仍走 revise-goal 的人闸+可比性复核。
- `docs/00`：写 `## reframe_<date>`（方向变更记录 + carry-forward 账本快照）。
- `docs/09`：truly-abandoned 项（带 cousin + re-entry）。
- `wiki/ideas`：parked 项（带 re-entry 条件，可检索）。
- 下次 `/pursue`/`/goal-prompt` 的 context_pack 会自动带上新方向 + parked 提醒。

## 边界
- 不在未确认前改 ACTIVE_GOAL / 删 roadmap。**parked 绝不静默删**。
- 不替主人决定换不换方向——提议 + 拷问，主人拍板。
- 真要改目标值仍走 `/revise-goal`（可比性人闸）；本 skill 管"方向+阶段+结论保留"。
- 如果需要从 deep research 重新开始、切到 Publication/Pipeline、或重写 docs/11 pipeline 地图，转 `/route-reset` 执行，不在本 skill 内散写多个 docs。

## Hand-off
- **Inputs from**: 主人(新认识)、`/note-add`(新文献/路径)、`docs/experiments/ATLAS.md`、findings
- **Uses**: `/grill`(拷问新方向)、`/route-reset`(重开线/切段C/重写pipeline)、`/revise-goal`(改目标值)、`/decisions-log`(弃路)
- **Outputs to**: strategic proposal；确认后通常由 `/route-reset` 写 docs/11/00/03/12/13/09/wiki
- **Next**: `/route-reset` 或 `/benchmark-roadmap`(若新方向只需重定 paths) 或 `/pursue`(按新阶段序列续)
