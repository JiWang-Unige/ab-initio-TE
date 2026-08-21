---
name: research-synthesize
description: "A2· Synthesize multiple deep research reports (placed in docs/inputs/) with the user's intent memo into a unified research-status review. This is the second stage after /research-interview — the user has now returned from external deep research platforms with reports, and this skill merges them, resolves conflicts, and re-engages the user with 3-5 focused follow-up questions before producing the final review. Auto-detects FRESH vs CONTINUATION mode by reading docs/00_active_goal.md for `## next_focus_<date>` sections; in CONTINUATION mode, the synthesis is scoped to specific questions, conflicts are weighted by relevance to those questions, and the output appends a `## Follow-up review <date>` section to docs/01 rather than overwriting it. Use after the user has placed deep_research_*.md files in docs/inputs/, or when they say \"I got the deep research reports back, please synthesize\"."
argument-hint: "<optional: research topic or specific focus>"
---

# Research Synthesize

## 语言策略（默认）

`docs/01_literature_review.md` 默认用**简体中文**写，便于用户复盘和讨论；但 paper title、model、dataset、metric、repo、weights、URL、命令、表格列中的技术名词保留英文原文。不要把英文模型/数据集名硬翻译成中文。


合并 `docs/inputs/deep_research_*.md` + 读 `docs/00_active_goal.md` 的意图备忘 + 跟用户再聊几轮 → 研究现状综述。

## 这是二段式工作流的第 2 段

```
/research-interview (已完成) ──► 你拿 prompt 跑外部 deep research ──► [本 skill]
                                                                          │
                                                                          ▼
                                                                /sota-inventory
```

## 工作流

## Step 0 · 模式自动检测（HARD, 不可跳过）

读 `docs/00_active_goal.md` 全文，做如下检测：

| 信号 | 判定 |
|---|---|
| 文件存在 `## next_focus_<YYYY-MM-DD>` 段（最近 30 天内的） | → **CONTINUATION mode** |
| 文件存在 "Handoff to /research-synthesize" 段但无 next_focus | → **FRESH mode**（首次合并） |
| 文件不存在或空 | → 报告"缺少意图备忘"，提示用户先跑 /research-interview |

同时记录最新一条 `next_focus` 的内容（trigger / specific_questions / refined hypothesis / anti-scope / target depth）作为本轮 synthesize 的"靶子"。

CONTINUATION 模式额外读取：
- `docs/01_literature_review.md`（已有综述，作对照基线）
- `docs/02_sota_model_inventory.md`（已有 SOTA 表，标记哪些 claim 已 verified 不必重复）
- `docs/09_decisions_log.md`（abandoned routes，本次 synthesize 触及它们时打 warning）

inline 输出：

```markdown
## Mode detection

- Detected: <FRESH | CONTINUATION>
- next_focus section found: <date or none>
- Existing docs/01 baseline: <present | absent>
- Existing docs/02 SOTA inventory: <present | absent>
- Abandoned routes count (docs/09): <N>
- Specific questions to address this round (CONTINUATION only):
  1. <Q1>
  2. <Q2>
  3. <Q3>
- Anti-scope (CONTINUATION only): <list>
```

---

### Step 1 · Inventory

读取并列出所有 `docs/inputs/deep_research_*.md`,以及 `docs/00_active_goal.md` 里的 "Handoff to /research-synthesize" 段。

如果 `docs/inputs/` 里没找到任何 deep research 报告,停下来报告"没找到输入"并用 `AskUserQuestion` 问用户三选一（G11，治"无外部 deep research 渠道整条段 A 卡死"）:
- ① **等我放报告**：用户去外部平台（ChatGPT/Perplexity/Claude）跑 prompt 后回来粘贴；
- ② **内置降级综述**（无订阅/无外部渠道时）：我用 `scripts/lit_search.py`(Semantic Scholar) + MCP `anysearch`(academic)/`exa`/`deepwiki` 跑多轮内部检索，自动生成 `docs/inputs/deep_research_internal_<date>.md`，**标 `source: internal_degraded`**（覆盖面/可信度低于人工 deep research，下游 claim 据此下调权重）；
- ③ 只用 `00_active_goal.md` 写 minimal 综述（最弱）。
> 选 ② 时：本 skill 接受 `source: internal_degraded` 报告进入合成，但在产出综述里显式标注"基于内部降级检索，需后续 /sota-inventory 实访核实补强"。这样**没有外部 deep research 订阅的用户也能起步**，而不是卡在第一步。

```markdown
## Sources

| Source ID | File | Tool | Date | Size (words est.) |
|---|---|---|---|---|
| dr_001 | docs/inputs/deep_research_chatgpt_20260516.md | ChatGPT Deep Research | 2026-05-16 | ~4500 |
| dr_002 | docs/inputs/deep_research_perplexity_20260516.md | Perplexity | 2026-05-16 | ~3800 |
```

### Step 2 · Claim ledger(原子化提取)

从每份报告中拆出原子 claim,每条标:

- `claim_type`: `background` / `method` / `benchmark` / `dataset` / `limitation` / `speculation` / `citation`
- `status`:
  - `verified` — 多份独立报告一致 + 有 primary source URL
  - `partial` — 多份一致但只是间接引用
  - `needs_primary_source` — 涉及具体数字 / DOI / 链接 / 引用,必须由 /sota-inventory 查原文
  - `single_source` — 只有一份报告提到
  - `rejected` — 明显错误(年份不对 / 引用不存在 / 数值与领域共识冲突)

**CONTINUATION 模式额外字段**（FRESH 模式可省）:

- `addresses_next_focus_q`: 该 claim 回答的 specific question 编号 (Q1/Q2/Q3 或 N/A)
- `delta_from_docs01`: 与 docs/01 现有综述对比 — `new` / `refines_existing` / `contradicts_existing` / `confirms_existing` / `unchanged`
- `touches_abandoned_route`: 是否触及 docs/09 中的 abandoned route (yes/route_id 或 no)，是 → 必须在用户回访阶段 inline 警告

```markdown
## Claim ledger (top 20-30)

### FRESH mode format
| claim_id | claim | sources | claim_type | status | conflicts_with |
|---|---|---|---|---|---|
| c001 | Tiberius reports max F1 exon-level of 0.897 | dr_001 | benchmark | needs_primary_source | c002 |
| c002 | Tiberius achieves 0.91 F1 on exon-level | dr_002 | benchmark | needs_primary_source | c001 |

### CONTINUATION mode format
| claim_id | claim | sources | claim_type | status | conflicts_with | addresses_q | delta_from_docs01 | touches_abandoned |
|---|---|---|---|---|---|---|---|---|
| c001 | <new method X for tokenizer-aware ncRNA> | dr_001, dr_002 | method | verified | - | Q2 | new | no |
| c002 | <Tiberius F1=0.91 on new split Y> | dr_002 | benchmark | needs_primary_source | - | Q1 | refines_existing | no |
| c003 | <method Z claims to outperform Tiberius> | dr_003 | method | single_source | - | Q1 | contradicts_existing | route_R7 ⚠️ |
```

CONTINUATION 模式下，特别留意 `addresses_q=N/A` 但被多份报告大量提到的 claim —— 这是 deep research 的"漂移"信号，可能是 anti-scope 写得不准。在 Step 4 用户回访时 inline 提出。

### Step 3 · Conflict matrix(显式列冲突,不要默默选)

```markdown
## Conflict matrix

| Conflict ID | Claim A | Claim B | What conflicts | Resolution route | Blocks_q (CONTINUATION) |
|---|---|---|---|---|---|
| CF-1 | c001: F1=0.897 (dr_001) | c002: F1=0.91 (dr_002) | numeric | check paper Table 3 directly via /sota-inventory WebFetch | Q1 |
```

每条冲突给出**具体解决路径**(哪个 primary source,哪一节,哪一表),不写"需要进一步研究"。

CONTINUATION 模式必须标 `Blocks_q` 列：该 conflict 阻碍了哪个 specific question 的回答。 conflict 与 specific questions 无关 → 标 `aux`（auxiliary，可以延到未来轮次）。优先级：blocks specific question 的 conflict > aux conflict。

### Step 4 · 跟用户再聊 3-5 轮(关键,不能跳过)

本 skill 的关键区别是**必须**在产出综述前再访谈用户,而不是直接 merge 后定稿。

这是本 skill 区别于纯 merge 工具的关键步骤——**必须**在产出综述前再访谈用户。

优先用 `ask_user_input_v0` 工具呈现 3-5 个**针对性问题**；如果该工具不可用,就直接在聊天中分批提出选择题。基于上一步的 claim ledger 和意图备忘:

### FRESH mode 用户回访题（3-5 题）

1. "deep research 报告里提到 X 方法和 Y 方法,你的偏好/直觉觉得哪个更值得我们对标?(选项 / 都对 / 都不,有第三个)"
2. "对于这个 conflict CF-N,你想现在解决还是延到 /sota-inventory 阶段去查 primary source?"
3. "deep research 没有提到 Z(你在意图备忘里关心的方向),你希望我:(a)在综述里补一段 ad hoc 讨论 (b)记入 needs_primary_source 队列 (c)忽略"
4. "你看了报告之后,有没有新的差异化假设想加进 00_active_goal.md?"

### CONTINUATION mode 用户回访题（3-5 题，与 next_focus 对照）

不再问 fresh 的全景偏好题。聚焦于 next_focus 缺口：

1. **specific question 覆盖度**: "本次 deep research 对您 next_focus 的 Q1/Q2/Q3 回答情况是：Q1 已被 N 条 claim 回答（强度 strong/weak），Q2 几乎无答案，Q3 部分回答。是否：(a) 接受当前覆盖度往下走 (b) 重发一份针对 Q2 的更窄 prompt (c) 把 Q2 改写得更具体"
2. **anti-scope 漂移检查**: "本次报告里有 N 条 claim 与您 next_focus 的 specific questions 无关（addresses_q=N/A），主要扎堆在 <topic>。是 anti-scope 写得不够准，还是 deep research 自然发散？要不要在 docs/00 下次更新 anti-scope 时把这块加进去？"
3. **abandoned route 触及**: "本次报告中有 claim 触及您 docs/09 abandoned route R<id>（原因：<reason>）。新报告提到的 <new evidence> 是否构成 re-entry criteria 满足条件？(a) 不复活 (b) 标 'reconsider in next /retrospective' (c) 立即触发 /retrospective"
4. **conflict 优先级**: "blocks-question 的冲突 CF-N1, CF-N2 必须现在解决（影响您主线 specific question）；aux 冲突 CF-N3 可以延到 /sota-inventory。是否同意按此优先级处理？"
5. **next_focus 是否需要更新**: "看完报告，您 next_focus 的 refined hypothesis 是否需要进一步收窄？或者发现了应该在下一轮 next_focus 加入的新问题？"

不要超过 5 轮——目的是修正方向,不是再做一次访谈。

### Step 5 · 综述 prose(只写 paper-safe + 用户确认过的部分)

**FRESH mode**: 覆写 `docs/01_literature_review.md`（首次综述）。
**CONTINUATION mode**: **不覆盖** `docs/01_literature_review.md`，在文件末尾 append 一个 `## Follow-up review <YYYY-MM-DD>` section。

### Step 5 - FRESH mode: 覆写 `docs/01_literature_review.md`

```markdown
# Literature Review: <topic>

## 1. Research question
<一段,来自 00_active_goal.md>

## 2. Scope and task formulation
<边界,来自 00_active_goal.md>

## 3. Method families

| Family | Core idea | Representative works | Strength | Weakness | Opportunity for us |
|---|---|---|---|---|---|
<只列 status=verified 或用户在 Step 4 确认过的>

## 4. Representative papers (SOTA candidates, to be verified by /sota-inventory)

| Paper | Year | Method | Dataset | Reported metric | Source claim status |
|---|---:|---|---|---|---|

## 5. Datasets and metrics

### Datasets
<列出 + 来源 + 已知问题>

### Metrics
<列出 + 实现细节是否标准>

## 6. Research gaps (from reports + user input)
- <gap 1, 来源标注>
- <gap 2, 来源标注>

## 7. Architecture opportunities (针对我们的具体方向)
1. <来自意图备忘的差异化假设 + deep research 启发的具体形式>
2. ...
3. ...

## 8. Unresolved
### Conflicts to resolve in /sota-inventory
<列 CF-N 一览>

### Needs primary source
| Priority | Claim | Where to look |
|---|---|---|

### Single-source / suspicious
- ...

## 9. Next action
→ /sota-inventory using SOTA candidates listed in §4
```

### Step 5 - CONTINUATION mode: append `## Follow-up review <YYYY-MM-DD>` 到 docs/01

**不**覆盖现有 `docs/01_literature_review.md`。在文件末尾 append:

```markdown
---

## Follow-up review <YYYY-MM-DD>

### Source
- next_focus referenced: `## next_focus_<date>` in docs/00
- Specific questions addressed this round:
  1. <Q1 verbatim>
  2. <Q2 verbatim>
  3. <Q3 verbatim>
- Deep research reports:
  | Source ID | File | Tool | Date |
  |---|---|---|---|

### Answers to specific questions

#### Q1: <verbatim>

- Direct answer (synthesized from claims): <2-4 sentences>
- Supporting claims: c001, c004, c007
- Confidence: <strong / moderate / weak>
- Open conflicts blocking full answer: <CF-N if any>
- Delta from docs/01 original review: <new finding / refines §X / contradicts §Y / unchanged>

#### Q2: <verbatim>
... (same structure)

#### Q3: <verbatim>
... (same structure)

### What's new since last review

| Item | Year | Type | URL | Relevance to which Q |
|---|---:|---|---|---|
| <new method> | 2026 | method | <url> | Q2 |
| <new dataset> | 2025 | dataset | <url> | Q1 |
| <new benchmark methodology> | 2026 | eval | <url> | Q1+Q3 |

### Cross-reference with existing literature review (docs/01 §1-9)

| Original section | This round's update |
|---|---|
| §3 Method families | <new family found / family X updated / no change> |
| §4 SOTA candidates | <new candidate <name> / <existing> revised metric / no change> |
| §5 Datasets | <new dataset / no change> |
| §6 Research gaps | <gap closed by new method / gap confirmed / new gap> |
| §7 Architecture opportunities for us | <refined / new opportunity / no change> |

### Abandoned routes touched (from docs/09)

| Route ID | Original abandon reason | New evidence in this round | Recommendation |
|---|---|---|---|

Recommendation 必须是: `keep abandoned` / `flag for /retrospective` / `escalate immediately`. 永远不直接复活 abandoned route——必须走 /retrospective 或 /tri-review → /pivot。

### Conflicts to resolve in /sota-inventory (this round)

| CF-id | What | Resolution route | Priority (blocks_q vs aux) |
|---|---|---|---|

### Needs primary source (this round, priority-sorted by next_focus relevance)

| Priority | Claim | Where to look | Blocks_q |
|---|---|---|---|

### Recommendation for next_focus update

- Should we tighten anti-scope? <yes / no / suggest:>
- Should we add a new specific question to next_focus? <yes / no / suggest:>
- Should we trigger /retrospective? <yes — which trigger condition / no>
- Should we re-run a narrower deep research for unresolved Q? <yes / no>

### Next action

→ /sota-inventory using SOTA candidates listed above (priority by blocks_q)
→ optional: /retrospective if abandoned-route or skipped-signal triggers fired
```

**重要**：CONTINUATION mode 也要 inline 写一条**短摘要**到 `docs/00_active_goal.md` 中那个 `## next_focus_<date>` 段的末尾（不是覆盖，是补一句 "Follow-up review completed on <date>, see docs/01 §Follow-up review <date>"）。

### Step 6 · 最终对话内输出

#### FRESH mode

inline 展示:
- Mode detection 段
- Source inventory 表
- Conflict matrix(必须 inline)
- 用户在 Step 4 给的关键判断
- 综述各节标题 + §7 architecture opportunities 完整内容
- needs_primary_source 队列前 5 条
- 写入路径 (`docs/01_literature_review.md` 覆写)
- 下一步: `/sota-inventory`

#### CONTINUATION mode

inline 展示:
- Mode detection 段（含 next_focus 引用）
- Source inventory 表
- Claim ledger 至少包含 addresses_q + delta_from_docs01 + touches_abandoned 列
- Conflict matrix 含 Blocks_q 列
- 用户在 Step 4 给的关键判断 (5 题)
- "Answers to specific questions" Q1/Q2/Q3 的 direct answer 文本
- "What's new since last review" 前 5 条
- Abandoned routes touched 表（若有）
- Recommendation for next_focus update
- 写入路径: `docs/01_literature_review.md` **append**, `docs/00_active_goal.md` 末尾 next_focus 段补一句 follow-up 完成
- 下一步: `/sota-inventory` (priority by blocks_q) + optional `/retrospective`

## 引用纪律

- 不要发明论文标题 / 作者 / 年份 / DOI / benchmark 数字
- LLM deep research 给的链接经常 hallucinate——本 skill **不**做链接验证(那是 /sota-inventory 的事),但要把可疑链接标 `needs_primary_source`
- 3 份报告都说同一个数字不代表对(可能共享同一份过期 training data)
- LLM 推测语("likely"、"possibly"、"some studies suggest")当 speculation 标记,不当事实

## 不要做的事

- 不要跳过 Step 4 的用户回访(这是本 skill 和纯 merge 工具的区别)
- 不要默默 resolve conflict
- 不要把 single_source 当 verified 写进综述
- 不要写最终论文 prose——这是给 /sota-inventory 和 /benchmark-roadmap 用的工程级综述
- **CONTINUATION mode 特有禁忌**:
  - 不要覆盖 `docs/01_literature_review.md` — 只能在末尾 append `## Follow-up review <date>` section
  - 不要忽略 next_focus 的 anti-scope —— 漂移 claim 必须在 Step 4 inline 让用户决定
  - 不要"默默复活"abandoned route — 触及 docs/09 的 route 时必须 inline 警告 + 给 keep/flag/escalate 三选项
  - 不要直接修改 docs/00 的 next_focus 段主体内容；只能在该段末尾补一句 follow-up 完成
  - 不要把 CONTINUATION 当 FRESH 处理 — Step 0 检测出 next_focus 后必须切到 CONTINUATION 分支

## Hand-off

- **Inputs from**:
  - `docs/inputs/deep_research_*.md` (由你从外部 platform 跑回来)
  - `docs/00_active_goal.md`:
    - FRESH: "Handoff to /research-synthesize" 段
    - CONTINUATION: 最新一条 `## next_focus_<date>` 段 + handoff 子段
  - CONTINUATION 额外: `docs/01_literature_review.md` (作对照基线), `docs/02_sota_model_inventory.md` (已 verified claim), `docs/09_decisions_log.md` (abandoned routes)
- **Outputs to**:
  - FRESH: `docs/01_literature_review.md` (overwrite)
  - CONTINUATION: `docs/01_literature_review.md` (append `## Follow-up review <date>` section); `docs/00_active_goal.md` next_focus 段末尾补一句 follow-up 完成
- **Next skill**:
  - FRESH: `/sota-inventory`
  - CONTINUATION: `/sota-inventory` (按 blocks_q 优先级排序，可能只跑增量 verify) + optional `/retrospective` (若触及 abandoned route 或 skipped signal)
