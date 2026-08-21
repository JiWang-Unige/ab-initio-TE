---
name: note-add
description: "*· Unified durable capture for papers, ideas, notes, metrics, discussion decisions, user preferences, pipeline outputs, and SOTA updates without derailing the running experiment. Paper/idea/note still route to refs/wiki; metric/decision/pipeline evidence routes through docs/15_evidence_register.md and the appropriate formal docs. Usually called by /note-gate after a capture decision."
argument-hint: "<paper url / arXiv id / DOI / repo url> [— why it matters]"
---

# Note-Add: mid-iteration knowledge injection

把 `$ARGUMENTS` 里新发现的论文 / 仓库 / 想法**随时装填**进项目，且**不打断**正在跑的实验。
解决痛点：实验跑到一半发现一篇 nice 的文章、一次随机重训指标、一个用户偏好或一个 pipeline 输出，却无处安放、也无法影响后续迭代。

> 新规则：日常不要只靠人想起 `/note-add`。每个阶段结束先过 `/note-gate`，由它判断是否值得记录，并把 paper/idea/note 类候选交给本 skill。

**advisory 边界（HARD，遵循 CLAUDE.md §7.5）**：本 skill 全程 **advisory + 归档**。**不可**：
overwrite `docs/03_benchmark_roadmap.md`、cancel/modify 任何 running job、override Track B promotion、
直接写 `docs/09`。任何"换路线"动作必须走 `/tri-review → /pivot → 用户确认`。

---

## Step 0 · 解析输入 + 判 kind

从 `$ARGUMENTS` 判断**捕获类型 kind**（统一入口）：
- **paper**：给了论文/arXiv/DOI/GitHub → 走 §Step 1-5（归档到 refs/）。
- **idea**：一个假设/方向（没有具体论文，是"我想到一个思路"）→ 走 §Idea 分支。
- **note**：一个"跑过一次"的快速笔记（看到文章跑了一遍、随手实验）→ 走 §Note 分支。
- **metric / decision / pipeline_output / user_preference**：若不是 paper/idea/note，优先交给 `/note-gate` 路由到 `docs/15`、`docs/11`、`docs/13/14`、`docs/10`；本 skill 可写短 wiki note，但不能替代正式 docs。

抽取：`source`（arXiv id / URL / DOI / GitHub，可多个）、`why`（破折号后"为什么相关"）、
推断 `slug`（`<name>-<year>` 或简短 kebab，如 `tiberius-2025` / `crf-multiscale`）。
只给 GitHub 没给论文（反之）→ 尽量 WebFetch 互补。

### Step 0.5 · Evidence Register 索引（所有 kind）

无论 kind 是 paper/idea/note，都在 `docs/15_evidence_register.md` append 一行索引。
**先取唯一 ID（防 note-add/note-gate 撞号）**：
```bash
EID=$(python3 scripts/next_evidence_id.py)   # 扫 docs/15 现有 E<NNN> → 返回下一个，如 E001
```
```markdown
| Evidence ID | Date | Type | Summary | Source | Routed to | Status | Owner |
|---|---|---|---|---|---|---|---|
| <EID> | <date> | <kind> | <一句话> | <$ARGUMENTS/source> | refs/wiki/docs path | recorded | agent |
```

这样 `/note-gate` 与 `/note-add` 的记录能在同一张 evidence 表中追踪。

### Idea 分支（kind=idea）
```bash
bash wiki/wiki.sh add-idea --slug <slug> --title "<title>" \
  --hypothesis "<假设>" --why "<why>" --next "<下一步>" [--refs "<相关paper slug>"]
```
然后跳到 Step 3（排队，可选）+ Step 4（mini-retrospective）。不归档 refs（无论文）。

### Note 分支（kind=note）
```bash
bash wiki/wiki.sh add-note --slug <slug> --title "<title>" \
  --what "<跑了什么>" --result "<快速结果>" --takeaway "<结论>" --next "<下一步方向>" [--refs "<slug>"]
```
然后跳到 Step 4（mini-retrospective）。

> idea / note 都进 `wiki/`（自动重建 INDEX.md，随时 `wiki.sh search` 可检索）。下面 Step 1-2 仅 kind=paper 执行。

## Step 1 · 归档到 refs/（自动尽力下载）

调用归档脚本（best-effort：失败只记状态，不致命）：

```bash
bash refs/archive_source.sh --slug <slug> \
  [--arxiv <id>] [--pdf-url <url>] [--repo <git-url>] \
  --title "<title>" --type note --why "<why>"
```

产出：`refs/pdfs/<slug>.pdf`、`refs/repos/<slug>/`（或 `.link.md`）、`refs/dossiers/<slug>.md`（骨架）、`refs/sources.md` 追加一行。

**填 dossier**：用 WebFetch 读论文/README，把 dossier 的 **dataset source / metric implementation / split scheme / weights&license / repro notes** 字段尽量填实（填不出的留 ⏳ 并记入 needs_primary_source）。引用纪律同 /sota-inventory：不编造数字/链接。

## Step 2 · append 到 docs/01_literature_review.md（不覆盖）

在文件末尾 append（若已有当日段则续写）：

```markdown
## Mid-iteration additions <YYYY-MM-DD>

| claim_id | claim | source(slug) | claim_type | status | addresses_gap / path | delta_from_existing |
|---|---|---|---|---|---|---|
| mNNN | <这篇的核心 claim> | <slug> | method/benchmark/... | needs_primary_source/single_source | docs/03 §7.2 PathN 或 §6 gapX | new / refines / contradicts |

- Why captured (from --why):
- Dossier: refs/dossiers/<slug>.md
```

`status` 用 /research-synthesize 的同套取值。涉及具体数字/链接一律 `needs_primary_source`。

## Step 3 · 排队到 docs/05_todo.md（下次 /goal-prompt 自动读）

在 docs/05 的 `## Pending integration queue (/note-add)` 段 append（没有该段就建）：

```markdown
## Pending integration queue (/note-add)
- [ ] <slug> (<date>): <一句话> — 待 /goal-prompt 评估是否纳入下一轮 [docs/01 mNNN, refs/dossiers/<slug>.md]
```

> `/goal-prompt` 在生成下一个 `/goal` 时**必读**此段，决定是否把该文献的机制/对照纳入下一轮候选或 comparability 检查。

## Step 3.5 · SOTA 超越检测（kind=paper，闭合 goal 漂移）

若这篇论文报告的 primary_metric 值 **超过** `ACTIVE_GOAL.json` 的 `sota_benchmark.value`（按 direction）：
- **醒目标记** `⚠️ NEW SOTA EXCEEDS OUR GOAL`：写明 论文值 vs 当前 sota_benchmark。
- 在 Step 4 mini-retrospective 与 inline 汇总里**强烈建议 `/revise-goal`**（人闸把守地抬高目标），并提示：在 revise 前 `validate_goal.py` 仍用旧 benchmark，可能误判 success——可临时 `--challenger-sota <该值>` 让 validate 输出 stale_benchmark 警告。
- **不要**自行改 ACTIVE_GOAL（那是 /revise-goal + 用户确认的事）。

## Step 4 · mini-retrospective（advisory，inline + 写 docs/08）

简短评估这篇是否**值得改变当前路线**（不是全量 retrospective）：

inline 输出：
```markdown
### Mini-retrospective on <slug>
- Relevance: <directly-attacks-current-gap / adjacent / background>
- Does it change our hypothesis? <no / refines: ... / challenges: ...>
- Conflicts with an abandoned route (docs/09)? <no / route_R# — 可能 re-entry 信号>
- Recommendation: <continue-as-is / fold-into-next-batch / flag-for-/tri-review / trigger-full-/retrospective>
- Urgency: <low — 下一轮再说 / high — 建议本轮结束即评>
```

然后把同样一段 append 到 `docs/08_pivot_decisions.md` 的 `## Mid-iteration note <date>: <slug>`（advisory，**不**是 pivot 决策、**不**改 docs/03）。

若 Recommendation 是 `flag-for-/tri-review` 或 `trigger-full-/retrospective`：只**提示**用户，不自动执行。

## Step 5 · inline 汇总

- 归档状态（pdf/repo/dossier）
- docs/01 新增 claim id
- docs/05 队列新增项
- mini-retrospective 建议 + urgency
- 下一步指引：`正在跑的实验不受影响；下次 /goal-prompt 会读 Pending integration queue`

---

## 不要做的事
- 不要打断 / 修改正在跑的 job。
- 不要直接改 docs/03 roadmap 或 docs/09 decisions-log。
- 不要把 needs_primary_source 的数字当已验证写进结论。
- 不要 spawn subagent 再 spawn。

## Handoff
- **Inputs from**: 用户随时（实验进行中）
- **Outputs to**: `docs/15_evidence_register.md`、`refs/`（pdf/repo/dossier/sources.md）、`docs/01`（Mid-iteration additions）、`docs/05`（Pending integration queue）、`docs/08`（Mid-iteration note，advisory）、`wiki/ideas|notes`
- **Next skill**: 下一次 `/goal-prompt`（读队列）；必要时 `/tri-review` 或 `/retrospective`
