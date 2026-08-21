---
name: research-interview
description: "A1· Deep interview to clarify a research direction, producing (a) a prompt to send to external deep research tools (ChatGPT / Perplexity / Perplexity / Claude deep research) and (b) an intent memo for the next-stage skill /research-synthesize."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Research Interview

把 `$ARGUMENTS` 拆成清晰的研究方向 + 给外部 deep research 用的 prompt。

## 这是二段式工作流的第 1 段(共 2 段)

```
[本 skill] 项目模式检测 → 访谈 → 产出 deep research prompt + 意图备忘
   │
   ▼
你拿 prompt 去 ChatGPT / Perplexity / Perplexity / Claude deep research
   │
   ▼
报告放进 docs/inputs/deep_research_{claude,chatgpt,perplexity}_<date>.md（三家固化）
   │
   ▼
调用 /research-synthesize(读意图备忘 + 报告 + 和你聊补充)
```

---

## Step 0.2 · Deep Research 语言策略（默认中文报告 + 英文检索）

默认策略不是“全英文”也不是“全中文”：

- **报告输出默认简体中文**：便于用户讨论、归档、复盘；`docs/01_literature_review.md` 与后续 report 默认中文。
- **检索关键词/论文题名/模型名/数据集名保留英文**：学术检索与大模型训练语料中，英文覆盖更好；prompt 必须显式给出 English search keywords / synonyms。
- **引用信息不翻译或中英并列**：paper title、venue、dataset、metric、repo、weights、command 保留原文，避免后续 `/sota-inventory` 追源困难。
- **外部平台报告格式**：正文中文，表格字段可中英混排；所有 URL、metric 名、dataset split、code entry 必须原样保留。
- **用户显式要求英文时才切换全英文**；否则 `zh-CN report + English retrieval terms` 是默认。

写入 `docs/inputs/deep_research_prompt_<date>.md` 时，在 prompt 顶部加一句：

> 请用简体中文撰写报告；但检索时优先使用英文关键词，保留论文/模型/数据集/指标/仓库的英文原名与 URL。


## Step 0 · 项目模式自动检测 (HARD, 不可跳过)

启动时**立刻并行读以下文件**（不存在就标 `(absent)`）并基于内容判断：

| 文件 | 用途 | 模式信号 |
|---|---|---|
| `CLAUDE.md` | 项目级硬约束 / scope / canonical commands | 若 > 50 行且非默认模板 → continuation 倾向 |
| `docs/PROJECT_INDEX.md` | 项目文档导引 | 存在 → continuation 倾向 |
| `docs/00_active_goal.md` | 现有意图备忘 | 已有 "## 当前研究方向" 段 → continuation 倾向 |
| `docs/01_literature_review.md` | 已有文献综述 | 非空 → continuation 倾向 |
| `docs/03_benchmark_roadmap.md` | 已有 roadmap | 非空 → continuation 倾向 |
| `docs/04_experiment_iterations.md` | ITER 历史 | ≥ 1 ITER entry → strong continuation 信号 |
| `docs/06_results_log.md` | 实验结果历史 | ≥ 1 result entry → strong continuation 信号 |
| `docs/05_todo.md` | 当前 TODO | 非空 → continuation 倾向 |
| `docs/08_pivot_decisions.md` / `docs/09_decisions_log.md` | 历史决策 / abandoned routes | 非空 → strong continuation 信号 |
| `findings.md` | 自由形式发现笔记 (RNA 项目特有) | 存在 → continuation 倾向 |
| `refine-logs/EXPERIMENT_TRACKER.md` | 实验追踪 (RNA 项目特有) | 存在 → continuation 倾向 |
| `reports/` 目录 | 已完成实验报告 | 非空 → continuation 倾向 |

**判定规则**：

- **FRESH mode**: 上面没有任何 "strong continuation 信号"，且 docs/00 + docs/01 + docs/03 + docs/06 都 `(absent)` 或为模板默认。
- **CONTINUATION mode**: 任一 strong 信号触发（docs/04 / docs/06 / docs/08 / docs/09 非空），或 ≥ 3 个 continuation 倾向同时存在。
- **歧义时**: inline 输出读到的文件清单 + 推断，问用户一句 "我把这判定为 <mode>，对吗？(可以 fresh / continuation / 显式指定)"，然后按用户答案走。

`$ARGUMENTS` 可以**显式强制**模式：

- `$ARGUMENTS` 以 `continue:` / `继续:` / `接续:` 开头 → 强制 CONTINUATION。
- `$ARGUMENTS` 以 `fresh:` / `新:` 开头 → 强制 FRESH。
- 其他 → 走自动检测。

判定完成后 inline 输出：

```markdown
## Mode detection

- Detected: <FRESH | CONTINUATION>
- Evidence:
  - <文件 path> → <存在 / 非空 / 已定制 / 模板默认>
  - ...
- $ARGUMENTS prefix override: <none | continue: | fresh:>
- Going with: <FRESH | CONTINUATION>
```

---

## Step 0.5 · CONTINUATION 模式：项目快照 (mode = CONTINUATION 时强制)

读完所有 continuation 信号文件后，inline 输出**项目快照**（fresh 模式跳过本步）：

```markdown
## Project snapshot (auto-summary; please confirm or correct)

### Scope (from CLAUDE.md)
- 项目主题: <e.g. ncRNA gene annotation on eukaryote benchmark>
- 当前 active scope 约束: <e.g. ncRNA-only, exclude protein-coding>
- 资源 partition 偏好: <e.g. private-teodoro-gpu first>
- Canonical training command: <e.g. sbatch scripts/training_rmt/run_ncrna_only_baseline_private.sh>

### Active data
- 当前 train/val 数据: <paths + record counts>
- 数据来源 / provenance reports:

### Historical reference baseline
- 最佳历史结果: <e.g. B010 mixed-data segment F1 = 0.4200>
- 当前 baseline 状态: <established / pending / failed>

### Recent iterations (docs/04, last 5)
| ITER | Track | Path | Architecture change | Result | Pivot |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

### Last result summary (docs/00 # last_result_summary)
- exp_id / track / gap / semantic_success / tri_review_status / pivot_status

### Active blockers / TODOs (docs/05, top 5)
- [ ] ...

### Recent pivot decisions (docs/08, last 3)
- ...

### Abandoned routes (docs/09)
| Route | Reason | Cousins to avoid | Re-entry criteria |
|---|---|---|---|

### Open tri-review disagreements (docs/07)
- ...

### Free-form findings (findings.md / refine-logs/, top signals)
- ...
```

然后问用户一句:

> "这是蕾姆对项目当前状态的理解。哪里不准确，或者有重要的隐含信息蕾姆没读到？(选 ✅ 都对 / ✏️ 我要补充 / ❌ 误读)"

只有用户确认后才进 Step 1。

---

## Step 1 · 访谈

### Step 1 - FRESH mode (访谈 5-10 轮)

不要一次性问完所有问题。每轮聚焦 1-2 个,用户答完再追问。**优先用 `ask_user_input_v0` 工具呈现选项；如果该工具不可用，就直接在聊天中一次提出 1-2 个选择题等待用户回答**(科研方向常常是选择题,而不是开放题)。

需要逐步澄清:

1. **研究问题陈述**: 一句话能说清吗?输入是什么?输出是什么?
2. **任务边界**: 哪些算这个任务?哪些**明确不算**?(后者比前者更重要,防止 deep research 越界)
3. **应用场景**: 学术 benchmark? 工业流水线? 临床? 不同场景对 SOTA 定义不同
4. **数据约束**: 必须用哪个数据集? 物种 / 时间窗口 / 模态限制?
5. **指标偏好**: primary metric 已经定了还是开放?有 secondary 必须报告的吗?
6. **资源约束**: 你的 GPU / 时间预算大致是什么量级?
7. **既有工作**: 你已经知道的 SOTA / baseline 是哪些?(后续 /sota-inventory 验证)
8. **差异化假设**: 你直觉觉得现有 SOTA 哪里有问题?为什么你觉得自己能做更好?
9. **风险偏好**: 想做"稳进 top-3"还是"赌一个全新架构超越"?

### Step 1 - CONTINUATION mode (聚焦访谈 3-5 轮)

项目快照已经覆盖了大部分背景。本访谈**只问当前最关键的方向问题**，不要重复 fresh 模式的全景题。

按顺序问下面 5 题（每轮 1-2 个，等用户答完）：

1. **触发本轮 deep research 的外部信号**: 是什么让你觉得"现在需要做一次新的文献调研"？候选场景:
   - (a) 最近 N 次实验 gap 卡住 / pivot tune 连续两次 → 怀疑 architecture hit ceiling
   - (b) 新论文 / 新 SOTA 发布 → 想看是否值得对标
   - (c) reviewer / 同行评价 → 指出某方面 weakness
   - (d) Phase 8 generalization 需求 → 跨物种 / OOD / robustness 文献调研
   - (e) abandoned route 想重新看 → 有新证据
   - (f) 其他: ___

2. **本轮 deep research 想回答的 specific 问题** (1-3 个，要 narrow，不是全景):
   - 例: "近 12 个月有没有用 latent diffusion 做 RNA 二级结构的工作？"
   - 例: "Tiberius 在跨物种 generalization 上的失败模式被哪些 paper 显式讨论过？"
   - 例: "ncRNA-only training 在 evolution-aware 表示上有哪些 emerging 方法？"

3. **本轮新的差异化假设** (在已有差异化假设之上的细化或新增):
   - 例: "我猜 ncRNA 标注的瓶颈不在 head_arch，而在 tokenizer 对二级结构 motif 的表达"
   - 例: "B010 在 mixed-data 上达到 F1=0.42 是被 protein-coding 信号'蹭'高的，纯 ncRNA 会显著掉"

4. **本轮不希望 deep research 跑偏到的方向** (anti-scope, 防止 LLM 发散):
   - 例: "不要扩展到 RNA folding / RNA 3D structure prediction"
   - 例: "不要列 protein-coding gene annotation 方法"
   - 例: "不要再列 LSTM 时代的 baseline"

5. **本轮报告深度**（平台已固化为 Claude + Perplexity + ChatGPT 三家，不要再问平台数量）:
   - 1500 字 focused / 3000 字 standard / 6000 字 deep

CONTINUATION 模式**不要**重新问"研究问题陈述 / 应用场景 / 数据约束 / 既有 SOTA / 资源约束"——这些已经在 CLAUDE.md / docs/00 / docs/02 / docs/03 里固定下来了，重问只会打扰用户。

如果用户在快照确认环节有补充，把补充内容内化进后续 prompt，但**不重新走 fresh 模式 9 问**。

---

## Step 2 · 写意图备忘

### Step 2 - FRESH mode: 覆写 `docs/00_active_goal.md`

格式(必须包含 "Handoff to /research-synthesize" 段):

```markdown
# Active Goal

## 当前研究方向
<一句话>

## 任务边界
- 输入:
- 输出:
- 算这个任务:
- 不算这个任务:
- 应用场景:

## 候选数据集
- ...

## 评估指标
- Primary 候选:
- Secondary 候选:

## 既有 SOTA(用户感知,待 /sota-inventory 验证)
- ...

## 差异化假设
- 用户觉得现有 SOTA 的薄弱点: ...
- 我们打算如何不同:

## 资源约束
- GPU 量级:
- 时间预算:
- 风险偏好:

## Handoff to /research-synthesize

(这一段是给下一个 skill 读的——本次访谈中用户表达的核心 motivation、未明说的假设、期望 deep research 回答什么问题)

- 用户的核心 motivation: ...
- 隐含假设(用户没明说但贯穿对话的): ...
- 期望 deep research 回答的问题:
  1. ...
  2. ...
  3. ...
- 用户**不**关心的方向(防止 synthesize 跑偏): ...
```

### Step 2 - CONTINUATION mode: 追加 `## next_focus_<YYYY-MM-DD>` 段到 `docs/00_active_goal.md`

**不要覆盖**已有 active goal。在文件末尾追加一个时间戳块：

```markdown
---

## next_focus_<YYYY-MM-DD>

### Trigger
<external signal — Step 1 第 1 题答案>

### Specific questions for this deep research round
1. ...
2. ...
3. ...

### Refined differential hypothesis (delta on existing 差异化假设)
- Existing: <docs/00 原有差异化假设>
- This round's refinement: ...
- New hypothesis (if any): ...

### Anti-scope (do NOT let deep research drift into)
- ...
- ...

### Platforms + depth
- Number of platforms: <1/2-3/4+>
- Target depth: <focused 1500w / standard 3000w / deep 6000w>

### Handoff to /research-synthesize

- 本轮核心 motivation (与已有 active goal 的关系): ...
- 期望 deep research 回答的 specific 问题 (复述 Step 1.2):
  1. ...
- 不希望 synthesize 扩散到的方向 (复述 Step 1.4):
  ...
- 本轮 synthesize 是否需要更新 docs/00 原有 active goal?
  - <no, only append next_focus and updates>
  - <yes, in which section>
- 本轮 synthesize 是否会 trigger /retrospective?
  - <e.g. yes — Trigger 1.a "gap stuck" 是 retrospective 的 3-no-progress 信号>
```

---

## Step 3 · 写 deep research prompt 到 `docs/inputs/deep_research_prompt_<YYYY-MM-DD>.md`

这是要发给**外部** AI 的 prompt (不是给 Claude Code 自己)。**FRESH 与 CONTINUATION 模板不同**。

### Step 3 - FRESH mode

全景调研报告 prompt:

```markdown
# Deep Research Prompt: <topic> (FRESH)

把下面这段复制到 ChatGPT(Deep Research mode)/ Perplexity(Deep Research)/ Perplexity / Claude(deep research)。建议同一份 prompt 跑 2-3 个 platform,以便后续 /research-synthesize 处理冲突。

---

(prompt 主体,平铺直叙,不要嵌套代码块)

请用**简体中文**撰写报告；检索、论文追踪与关键词扩展请优先使用英文。论文题名、模型名、数据集名、metric 名、GitHub/HuggingFace/DOI/arXiv URL 必须保留英文原文。

English search keywords / synonyms to try:
- <keyword 1>
- <keyword 2>
- <keyword 3>

I am working on the following research problem: <一句话研究问题>.

Task scope:
- Input: ...
- Output: ...
- Application setting: ...
- Explicitly NOT in scope: ...

Please write a research-status report in Simplified Chinese covering:

1. **Method families**: Identify 4-6 method families that have been used for this problem. For each family give: core idea, representative works (paper title + year + venue + first author), strength, weakness, and typical performance level.

2. **Current SOTA candidates**: List the top 3-7 SOTA models as of <year>. For each: paper link (full URL), official GitHub URL, pretrained weights URL (HuggingFace if available), reported primary metric value and the dataset/split it was reported on.

3. **Datasets and benchmarks**: List the main datasets used in this area. For each: name, version/release, size, splits commonly used, where to download, known issues (label noise, splits inconsistency, leakage history).

4. **Evaluation metrics**: What metrics are standard? Are there community disagreements on metric implementation (e.g. F1 macro vs micro, IoU thresholds)? What secondary metrics are usually reported?

5. **Known limitations of current SOTA**: Specifically — where does current SOTA fail? Cross-species generalization? Long sequences? Specific subdomains? Adversarial robustness? Inference cost?

6. **Open research opportunities**: What gaps in the literature have been explicitly called out as needing work?

7. **Reproducibility status**: Which SOTA models have working code + weights? Which only have paper but no code? Which have code but broken / undocumented?

Constraints on your answer:
- Main prose language: Simplified Chinese. Keep technical names, paper titles, dataset names, metric names, code commands, and URLs in English/original form.
- Cite specific papers with full URLs. Do not say "studies have shown" without a citation.
- If you are uncertain about a number (e.g. a metric value), say so — do not fabricate.
- If you encounter conflicting numbers in different sources, list both and flag the conflict.
- Use plain markdown. Do not use HTML.

Length: aim for 3000-6000 words.

---

(prompt 主体结束)

## 怎么用这份 prompt

1. **三家固化** —— 把上面三横线之间的内容**整段复制**到以下三个 deep research 平台：
   - **Claude** (Deep Research)
   - **Perplexity** (Deep Research)
   - **ChatGPT** (Deep Research mode)
2. 报告回来后**直接粘贴**进已经预生成好的占位文件（见 Step 3.5），文件名固化为：
   - docs/inputs/deep_research_claude_YYYYMMDD.md
   - docs/inputs/deep_research_perplexity_YYYYMMDD.md
   - docs/inputs/deep_research_chatgpt_YYYYMMDD.md
3. 三份报告全部粘贴完毕后调用 /research-synthesize
```

### Step 3 - CONTINUATION mode

聚焦调研 prompt (不要全景！):

```markdown
# Deep Research Prompt: <topic> · CONTINUATION · <YYYY-MM-DD>

请用**简体中文**撰写报告；检索时优先使用英文关键词，保留论文/模型/数据集/指标/仓库的英文原名与 URL。

English search keywords / synonyms to try:
- <keyword 1>
- <keyword 2>
- <keyword 3>

This is a FOLLOW-UP deep research for an ongoing project. The team already has:
- existing literature review on the topic
- a working baseline and recent experimental results
- specific failure modes / open questions

Therefore: do NOT produce a full landscape report. Produce a FOCUSED follow-up
research report in Simplified Chinese answering ONLY the specific questions listed below, plus a
"what's new" section.

---

## Project context (compressed, ~200 words)

<one paragraph: 项目主题 + scope + active baseline + 当前 gap>

例:
We are working on ncRNA gene annotation on a eukaryote benchmark. Our active
scope is ncRNA-only (protein-coding excluded). Our best historical result is
F1_segment=0.42 on mixed-data; we just established the ncRNA-only baseline at
F1_segment=<value>. The current SOTA we track is Tiberius (~F1=0.89 exon-level
under different evaluation regime). Our latest pivot decision concluded that
gap may be tokenizer-limited rather than head-architecture-limited.

## Specific questions to answer

Answer ONLY these (do not expand to neighboring topics):

1. <Step 1.2 第 1 题>
2. <Step 1.2 第 2 题>
3. <Step 1.2 第 3 题>

For each question:
- Cite specific papers with full URLs (paper + GitHub + weights if applicable).
- Include publication date so we can filter to last 12-18 months.
- If a paper claims to outperform a method we use, state the exact metric, dataset, and split — not just "outperforms".
- If you cannot find a strong answer, say so — do not pad.

## What's new since <last review date or N months ago>

Briefly (≤ 500 words) list:
- new SOTA candidates published in the last 12 months for this exact problem
- new datasets / benchmarks released
- new evaluation methodology papers that change how we should measure

For each: title + year + venue + URL + 1-line relevance to our specific questions.

## Anti-scope (do NOT drift into)

- <Step 1.4 第 1 项>
- <Step 1.4 第 2 项>

## Format constraints

- Main prose language: Simplified Chinese. Keep technical names, paper titles, dataset names, metric names, code commands, and URLs in English/original form.
- Plain markdown, no HTML.
- All claims with paper URL. No "studies have shown" without citation.
- If a number conflicts across sources, list both with sources.
- Length: aim for <Step 1.5 chosen depth: 1500w focused / 3000w standard / 6000w deep>.

---

## 怎么用这份 prompt

1. **三家固化** —— 把上面三横线之间的内容**整段复制**到以下三个 deep research 平台：
   - **Claude** (Deep Research)
   - **Perplexity** (Deep Research)
   - **ChatGPT** (Deep Research mode)
2. 报告回来后**直接粘贴**进已经预生成好的占位文件（见 Step 3.5）：
   - docs/inputs/deep_research_claude_YYYYMMDD.md
   - docs/inputs/deep_research_perplexity_YYYYMMDD.md
   - docs/inputs/deep_research_chatgpt_YYYYMMDD.md
3. 三份报告全部粘贴完毕后调用 /research-synthesize（synthesize 会读 next_focus 段并对照 specific questions 做 claim ledger，比 FRESH 模式的 conflict matrix 更精细）
```

---

## Step 3.5 · 默认生成三个空报告占位文件（HARD，不可跳过）

写完 prompt 文件后，**必须**额外创建三个空占位文件，让用户回来后直接粘贴即可（不用先 mkdir / touch / 手动起名）。**三家固化**：Claude / Perplexity / ChatGPT。

对每个 `<source>` ∈ `{claude, chatgpt, perplexity}`，写入 `docs/inputs/deep_research_<source>_<YYYYMMDD>.md`，内容模板如下（注意 source/date 替换）：

```markdown
# Deep Research Report — <source> · <YYYY-MM-DD>

> 占位文件，由 /research-interview 在 <YYYY-MM-DD> 自动生成。
>
> **使用方式**: 把外部平台（<source>）跑出来的完整 deep research 报告**整段粘贴**到下面
> "## Report body" 之下。可以保留这段说明也可以删除，由 /research-synthesize 自动跳过。
>
> 对应的 prompt: `docs/inputs/deep_research_prompt_<YYYY-MM-DD>.md`

---

## Source platform
- Platform: <source>
- Mode: Deep Research
- Run date:
- Number of retries / refinements:
- Subjective quality (filled later): low / medium / high

## Report body

<在此处粘贴报告全文>
```

写入完毕后，inline 输出实际写入的三个路径，让用户能立即打开复制。

**为什么三家固化为 Claude + Perplexity + ChatGPT**：用户偏好稳定的三源对比（同一 prompt × 3 平台），方便 /research-synthesize 做 conflict matrix。如果未来用户明确要求换成别的三家，再调 skill；本 skill 默认不再问平台数量也不再用 Perplexity。

---

## Step 4 · 最终对话内输出(给用户确认)

在最后一轮里 inline 展示:

### FRESH mode

- 意图备忘的关键字段(研究问题 / 边界 / 差异化假设 / handoff section)
- deep research prompt 完整内容（默认中文报告 + 英文检索关键词，让用户能直接复制）
- **5 个写入路径**（docs/00_active_goal.md + prompt + 三个空占位 deep_research_{claude,chatgpt,perplexity}_<date>.md）
- 下一步指引: "在 Claude / Perplexity / ChatGPT 三家分别跑 prompt，回来直接粘贴进三个占位文件，然后 /research-synthesize"

### CONTINUATION mode

- 项目快照（用户确认版）的关键字段摘要
- next_focus 段的关键字段(trigger / specific questions / refined hypothesis / anti-scope)
- deep research prompt 完整内容（focused 版本，默认中文报告 + 英文检索关键词）
- **5 个写入路径**（docs/00 append 位置 + prompt + 三个空占位 deep_research_{claude,chatgpt,perplexity}_<date>.md）
- 下一步指引: "在 Claude / Perplexity / ChatGPT 三家分别跑 focused prompt，回来粘贴进三个占位文件，然后 /research-synthesize"
- **若无外部 deep research 渠道（无订阅/网络限制，G11）**: 告诉用户可直接 `/research-synthesize` 并选"内置降级综述"——用 `lit_search.py` + MCP(anysearch/exa/deepwiki) 跑内部检索生成 `source: internal_degraded` 报告起步（可信度低于人工 deep research，后续 `/sota-inventory` 实访核实补强），**不必卡在"必须有外部报告"**。
- 提醒: "/research-synthesize 会自动读你的 next_focus 段，知道这是 continuation 而非 fresh，conflict matrix 会聚焦于 specific questions"

---

## 不要做的事

- 不要替用户做学术判断("X 方向更有前途")
- 不要在访谈期间发起 web search 或 deep research(那是外部 platform 的事)
- 不要写综述 prose(那是 /research-synthesize 的事)
- 不要把模糊的方向直接当确定方向往下推——必须问清边界
- 不要省略 "Handoff to /research-synthesize" 段(意图备忘的关键)
- **CONTINUATION mode 特有禁忌**:
  - 不要覆盖现有 docs/00 active goal——只能 append next_focus
  - 不要在快照确认前开始访谈
  - 不要重复 fresh 9 问——continuation 只问 5 个聚焦题
  - 不要忽略 docs/09 已 abandoned routes——deep research 触及它们时必须 inline 警告 user

---

## Hand-off

- **Inputs from**:
  - 用户口头 / 文字描述的研究方向 (FRESH)
  - 现有项目文档 (CONTINUATION: CLAUDE.md, docs/00-09, findings.md, refine-logs/, reports/)
  - `$ARGUMENTS` 可选前缀 `continue:` / `fresh:` 强制模式
- **Outputs to**:
  - `docs/inputs/deep_research_prompt_<YYYY-MM-DD>.md` (focused for CONTINUATION, full landscape for FRESH)
  - `docs/inputs/deep_research_claude_<YYYYMMDD>.md` (空占位，等用户粘贴)
  - `docs/inputs/deep_research_perplexity_<YYYYMMDD>.md` (空占位，等用户粘贴)
  - `docs/inputs/deep_research_chatgpt_<YYYYMMDD>.md` (空占位，等用户粘贴)
  - FRESH: `docs/00_active_goal.md` (覆写)
  - CONTINUATION: `docs/00_active_goal.md` (append `## next_focus_<date>` section, never overwrite)
- **Next skill**: `/research-synthesize`（在用户从外部 platform 拿回报告后调用；synthesize 会自动识别是 CONTINUATION 模式产出的 focused 报告，对比 next_focus 中的 specific questions）
