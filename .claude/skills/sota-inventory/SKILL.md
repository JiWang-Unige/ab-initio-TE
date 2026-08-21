---
name: sota-inventory
description: "A3· Build a verified SOTA model inventory by actually visiting article / GitHub / HuggingFace links using WebFetch. For each candidate from docs/01_literature_review.md, confirm the link exists, extract architecture / metrics / weights / dataset / license info, and classify reproducibility. This skill does NOT trust LLM-generated links — every URL is fetched. Use when the user wants to turn the literature review into a concrete model inventory with article links, GitHub links, weights links, architectures, datasets, and reported metrics organized in a table."
argument-hint: "<optional: focus area or specific model list>"
---

# SOTA Inventory (with link verification)

把 `docs/01_literature_review.md` 里的 SOTA 候选转成**验证过的**清单。**这个 skill 的核心是 WebFetch 实际访问每个链接**,不能只整理 LLM 给的字符串。

## 必填字段(每个模型)

| 字段 | 怎么获取 |
|---|---|
| model name | literature review |
| paper link | WebFetch 验证存在 + 抓 title / authors / year / venue |
| GitHub link | WebFetch 验证存在 + 抓 README 关键信息(license, last commit, stars) |
| pretrained weights link | WebFetch HuggingFace / Zenodo / Google Drive,确认可下载 |
| model architecture | 从 paper abstract + GitHub README 提取一句话 |
| dataset(s) used | paper Methods 段 |
| training setup | GPU 数 / 训练时长 / batch / 特殊技巧(若有) |
| reported metrics + values | paper Table(注意:用我们的 primary metric) |
| inference cost / size | 若可得 |
| reproducibility | 4 档:trivial / moderate / hard / unknown(见下) |
| worth reproducing | yes / partial / no + 理由 |
| **link verification status** | 每个链接独立标 ✅ / ❌ / ⚠️ |

**Reproducibility 4 档**:

- `trivial`: code + weights 都公开 + README 有完整 reproduce 命令 + 最近 1 年有 commit
- `moderate`: code + weights 都有,但要折腾(依赖过时 / 数据要自己处理 / 命令不全)
- `hard`: 只有 code 没 weights,或反之
- `unknown`: paper 给的链接 404,或仓库无 README

## 工作流

### Step 1 · 列候选 + 检索补全

从 `docs/01_literature_review.md` §4 取 SOTA 候选模型表，展开成待处理行。
**不要只信 deep research 给的清单**——它常停在 abstract、且可能漏掉更新的工作。主动补全：
- `python3 scripts/lit_search.py search "<task/方法关键词>" 15` 找相关论文（按 citationCount 排序判影响力）。
- 对已知锚点论文 `python3 scripts/lit_search.py cited-by <ARXIV:id|DOI:..> 15` 顺被引找**更新的 SOTA**（deep research 可能截止在旧时间点）。
- 需要换架构组件时（如 HMM→CRF）`lit_search.py similar <paperId>` 发散替代方案。
- 找论文/榜单/通用网页用 MCP `anysearch`（**academic 垂直**直接搜学术论文、**general** 搜 papers-with-code 榜单/项目主页、**batch** 一次并行多查、**extract** 抓全页转 markdown）或 MCP `exa`（neural 网页搜索）；读懂某仓库实现用 MCP `mcp-deepwiki`。常规 `lit_search` 搜不到时优先用 `anysearch` academic 兜底。
（S2 无 key 走公共池易 429，建议设 `S2_API_KEY`；anysearch 设 `ANYSEARCH_API_KEY` 提配额，匿名亦可用；exa 设 `EXA_API_KEY`。key 走环境变量，不写进 .mcp.json。）

### Step 1.5 · Filter 粗筛（不可跳）—— 治"deep research 给啥都进表"

候选 ≥ ~8 个或来源混杂时**先粗筛再逐个深挖**，避免把无关/不可比/重复的也 WebFetch 一遍浪费上下文。按四闸快速过（只读已有 abstract/元数据，不下载）：

| 闸 | 留下条件 | 砍掉 |
|---|---|---|
| **相关性** | 同任务/同元件类型/可迁移到本 scope | 任务完全不同、仅 buzzword 命中 |
| **可比性** | 同/可对齐的 dataset+metric（哪怕需对齐） | 自造私有 benchmark 且无公开复现、口径完全不可比 |
| **去重** | 一个方法家族留最强代表 + 最新跟进 | 同一方法的微小变体堆叠 |
| **时效/影响** | 近期 or 高被引 or 公认基线 | 既老又零被引又无开源 |

inline 输出粗筛表：`| candidate | 相关性 | 可比性 | 去重 | 留/砍 | 一句理由 |`，**砍掉的也列出+理由**（透明，便于主人推翻）。只有"留"的进 Step 2 深挖。粗筛是廉价启发式，存疑就留到 Step 2 用真实抓取判定，不要误杀。

### Step 2 · 逐个深挖（**强制 subagent fan-out + 先下载后分析**）

> ⚠️ **防主上下文爆炸（HARD）**：Step 2 是检索/抓取密集步，**必须用 subagent 并行**（read-only 验证用 `.claude/agents/sota-source-verifier`；需要实际写 `refs/` 归档时，每个 slug 可委派 `.claude/agents/source-artifact-archivist`，其写入 scope 仅限 `refs/{pdfs,repos,supp,dossiers,sources.md}`；每个候选或每批一个），**主对话只接收每个候选的结构化摘要行**，绝不把 PDF 全文/README 全文/model card 原文灌进主上下文。codex 驱动时尤其遵守——主上下文只留汇总表。
>
> 每个 subagent 对其负责的候选**先归档下载、再读本地全文**（不是只看 abstract）：
> 1. 先跑 Step 2.5 的 `archive_source.sh`（或委派 `source-artifact-archivist`）把 **PDF + GitHub 仓库 + HF model card + supplementary** 实际拉到 `refs/`（abstract 常丢失指标如何计算/数据集是否预滤过 FP 这类关键结论）。
> 2. 再读**下载下来的全文 + 代码 + 补充材料**，重点抽：**指标的精确计算方式**（如 F1 的 TP/FP 边界判定、是否 macro/micro）、**数据集到底是哪些 + 是否纯 raw 还是已滤过 FP/去冗余**、**split 来源与泄漏**、是否提到我们没覆盖的 module。
> 3. 只把结构化摘要 + dossier 填好的字段返回主对话。

对每个候选,subagent 依次 fetch（**抓取目的是定位+下载，深读用本地文件**）:

```
1. paper link → 提取 title / authors / year / abstract / metric Table 中的数字
2. GitHub link → 抓 README 前 200 行 / license / last commit date / 显著的 setup 命令
3. weights link (HuggingFace model card 优先) → 确认存在 + 抓 model card info
```

**WebFetch 失败的情况**:

- 404 / timeout → 标 ❌,在 notes 写"链接 404,需查 alternative source"
- 需要登录 / paywall → 标 ⚠️,在 notes 写"paywalled,需通过 institutional access"
- redirected → 标 ⚠️,在 notes 写新 URL,继续抓

不要跳过失败的 fetch——这些信号本身就是 reproducibility 的判断依据。

### Step 2.5 · 归档到 refs/（规范化保存，便于后续可比性审查）

对每个 `worth reproducing ∈ {yes, partial}` 的候选，归档其 PDF + 仓库 + 细节档案：

```bash
bash refs/archive_source.sh --slug <slug> \
  [--arxiv <id>] [--pdf-url <paper-pdf-url>] [--repo <github-url>] \
  [--supp-url <supplementary-pdf/zip>]... \
  --title "<title>" --type sota --why "<为何作为 SOTA 锚点/对照>"
```
> **补充材料(`--supp-url`)**：很多关键值（指标精确定义、数据集是否预滤过 FP、额外结果表）只在 supplementary 里。深挖时若在 paper 页/PDF 发现 "Supplementary Material" 链接，**一并传 `--supp-url`**（可多次）下到 `refs/supp/<slug>/`。下载失败 → 记 `failed(url)` → 由 Step 7.5 列给主人手动补（主人放进 `refs/supp/<slug>/` 即可）。

然后**用刚 fetch 到的信息填实 `refs/dossiers/<slug>.md`** 的关键字段（这些正是后续比较最常查的）：
- **Dataset source**：数据集名/版本 + 从哪获取 + license
- **Metric implementation**：指标精确定义（如 segment F1 的边界判定规则）+ 官方实现/脚本
- **Split scheme**：train/val/test split 来源 + 泄漏注意
- **Weights / license**：权重 URL + 版本 + license
- 填不出的留 ⏳ 并记入 docs/02 的 needs_primary_source。

> dossier 与 docs/02 的"SOTA 细节档案"表互为索引；归档一次，后续 /benchmark-roadmap 的 comparability contract、/tri-review 的 Research Pack §5 都直接引用，不必重搜。

### Step 3 · 输出表

```markdown
# SOTA Model Inventory: <topic>

## Summary
- Total candidates: N
- Trivial-to-reproduce: X
- Moderate: Y
- Hard / unknown: Z
- Link verification failures: W

## Candidate models

| Model | Paper | GitHub | Weights | Architecture | Dataset | Metric | Value | Repro | Worth? | Notes |
|---|---|---|---|---|---|---|---:|---|---|---|
| Tiberius | [✅ link](https://...) | [✅ link](https://github.com/...) | [⚠️ HF](https://hf.co/...) | Bi-directional Caduceus + CRF head | CHM13 v2.0 | exon F1 | 0.897 | moderate | yes | weights gated, need request |
| ncRDeep  | [✅ link](https://...) | [❌ link](https://github.com/...) | [—] | CNN+LSTM | RNAcentral subset | macro F1 | 0.78 | hard | no | github repo 404 since 2024 |

字段说明:
- Paper / GitHub / Weights 列里直接写 ✅/❌/⚠️ + markdown link
- Repro: trivial / moderate / hard / unknown
- Worth?: yes / partial / no
```

### Step 4 · 模型家族归纳

```markdown
## Model families (refined from /research-synthesize)

### Family A: <名字>
- Members(已验证): <list>
- Core idea: <一句>
- Strength on this task: ...
- Weakness:
- What we can borrow:
- What we should not borrow:
```

### Step 5 · 复现优先级

```markdown
## Baselines to reproduce first

| Priority | Model | Why this one | Required GPU | Required data | Risk | Expected setup time |
|---:|---|---|---|---|---|---|

## Models to skip

| Model | Reason | Could revisit if |
|---|---|---|
```

### Step 6 · Conflict resolution(联动 /research-synthesize)

如果 `docs/01_literature_review.md` 里列了未解决的 conflict(比如 dr_001 说 F1=0.897 vs dr_002 说 0.91),本 skill 在 fetch paper 时**必须**抓 Table 中的实际数字,resolve 这些 conflict:

```markdown
## Conflict resolution

| Conflict ID | Resolution | Source |
|---|---|---|
| CF-1 | Tiberius exon F1 = 0.897 (per paper Table 3, dr_002 was wrong) | https://...paper.pdf Table 3 |
```

### Step 7.5 · 失败源汇报（不可静默跳过）—— 治"没下下来的也不吭声"

抓取/下载是 best-effort，但**失败必须显式汇总成"请主人手动补"的清单**——绝不静默跳过。
`archive_source.sh` 已把失败状态写进 `refs/sources.md`（`pdf=failed(<url>)` / `repo=link-only`）和各 dossier，
本步把它们 + WebFetch 标 ❌/⚠️ 的链接**聚合**成一个可执行清单。

确定性聚合（扫 sources.md + 各 dossier 的失败记录，再补 WebFetch 失败）：
```bash
python3 scripts/sota_failure_report.py --format markdown
# 或最小兜底：grep -nE 'failed\(|link-only|missing|gated' refs/sources.md refs/dossiers/*.md 2>/dev/null || echo "(无失败记录)"
```
（PDF / repo / **补充材料(supp)** 的下载失败都写成 `failed(<url>)`，supp 在 dossier 的 `- Supplementary:` 行——这条 grep 一并捕获。）

在 `docs/02` **末尾**输出（也 inline 给主人）：
```markdown
## ⚠️ 需主人手动补全的源（自动获取失败，逐条列出，不省略）

| slug | 失败项 | 失败的 URL/原因 | 建议手动操作（补到哪） |
|---|---|---|---|
| tiberius | weights | HF gated（需申请） | 申请后 PDF/权重放 `refs/pdfs/`、`refs/repos/`，回填 dossier `## Weights` |
| ncRDeep | paper PDF | failed(https://…/paper.pdf) 403 | 用机构 access 下载 → 存 `refs/pdfs/ncRDeep.pdf` → 重读全文回填 dossier |
| xModel | github repo | link-only（private/过大） | `git clone <url> refs/repos/xModel/` 后重读 README |
| segNet | **补充材料(supp)** | failed(https://…/supplementary.pdf) | 手动下载 supp → 存 `refs/supp/segNet/` → 重读（**关键指标定义/数据集是否预滤过 FP 常在 supp**）→ 回填 dossier metric/dataset |

- **影响评估**：标注每条失败是否阻塞复现/可比性判定（阻塞 → 该候选 `worth?` 暂记 `partial`，待补全再定）。
- 主人补全后：把文件放到对应 `refs/` 路径 → 让浮浮酱重读本地全文回填 dossier 与 docs/02 → 必要时刷新 `worth?`/`repro` 档位。
- **若无失败**：明确写 "本轮所有源均成功获取（PDF/repo/weights 全 ✅）"，不要省略这句（让主人确信没有被悄悄跳过的）。
```

### Step 8 · 最终输出

写 `docs/02_sota_model_inventory.md`,inline 展示:

- Summary(候选数 + 分类计数 + 链接失效数)
- 完整 candidate models 表
- Baselines to reproduce first 表
- Conflict resolution(若有)
- **失败源汇报（Step 7.5 的"需手动补全"清单 / 或"全部成功"声明）**
- 写入路径
- 下一步: `/grill`（读完论文/代码后二次拷问、钉死方向，再 `/configure-project`→`/benchmark-roadmap`）

## WebFetch 调用模式

```
对每个 URL:
  WebFetch(url, "Extract: title, authors, year, abstract or README summary, license, last commit date if GitHub, model size if HuggingFace, key reported metrics with exact values.")
```

如果一次 fetch 漏抓了重要信息,可以二次 fetch 用更精确 prompt:

```
对 paper URL 二次抓:
  WebFetch(url, "Find the main results table and list every metric with its exact numeric value and the dataset/split it was computed on. Also extract the training setup section verbatim.")
```

## 不要做的事

- 不要相信 LLM 给的字符串,所有链接都要 fetch
- 不要发明 GitHub URL / HuggingFace repo 名(LLM 经常 hallucinate)
- 不要在缺信息时写"likely"——写 unknown
- 不要把 4 档 reproducibility 模糊化——必须给具体判定
- 链接失效时不要静默忽略——必须标 ❌ 并在 notes 写原因

## 引用纪律

- 所有数字必须来自 fetched primary source,不能从 deep research 报告搬运
- paper Table 和 README 不一致时,**以 paper Table 为准**,在 notes 标注
- 论文版本号 / checkpoint hash 都要尽量记录

## Hand-off

- **Inputs from**: `docs/01_literature_review.md` §4 (SOTA candidates) + §8 (unresolved conflicts)
- **Outputs to**: `docs/02_sota_model_inventory.md`（含失败源汇报） + `refs/`（pdfs/repos/dossiers/sources.md，经 archive_source.sh）
- **Next skill**: `/grill`（二次拷问钉死方向）→ `/configure-project`（AI 填配置，人闸）→ `/benchmark-roadmap`
