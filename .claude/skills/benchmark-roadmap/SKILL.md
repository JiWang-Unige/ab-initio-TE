---
name: benchmark-roadmap
description: "A4· Build the benchmark contract and technical roadmap after /sota-inventory. Defines three-layer gates, comparability contract, dataset readiness plan, SOTA weakness hypotheses, differentiated architecture paths, Track A/Track B promotion rules, milestones, and resource budget. Must draft paths first, ask the user to choose risk preference and technical direction, then finalize docs/03_benchmark_roadmap.md. Use when SOTA candidates are verified and the project needs an engineering roadmap before /goal iterations."
argument-hint: "<optional: focus area, constraints, or preferred risk level>"
---

# Benchmark Roadmap
## Step 0 · Stage-order guard（不可跳）

在写 roadmap 前先运行：

```bash
python3 scripts/research_flow_guard.py --format markdown
```

若它提示还缺 `/grill`、`/configure-project`、SOTA 归档/失败源补全，则**不要**直接写 benchmark-roadmap；先回到对应步骤。正常顺序是：`/sota-inventory → /grill（可选 /council）→ /configure-project → /benchmark-roadmap`。这条闸专门防止 inventory 后直接跳 roadmap，导致方向未被拷问、cluster/goal 未固化。


本 skill 读 `docs/02_sota_model_inventory.md`、`docs/01_literature_review.md`、`docs/00_active_goal.md`，产出 `docs/03_benchmark_roadmap.md`，并初始化/更新 `docs/19_evaluator_contract.md`。

**核心原则**：本 skill 不执行训练、不下载数据、不直接定技术路线。它先提出候选路线，然后和用户讨论，最后才定稿。

> **强烈建议在 plan 模式下跑本 skill**（Claude `plan` / Codex plan）：本 skill"只读勘查→草拟 3-5 路径→和你深聊风险/优先级→才定稿"本来就是 plan 模式形状。在 plan 里只读 docs/01-02+dossiers、把候选路径和权衡聊透，`ExitPlanMode` 批准后再退出落 `docs/03`——天然保证"未讨论批准不落 roadmap"。

---

## Step 1 · Benchmark contract

必须定义：

```markdown
## 1. Target task
- Input:
- Output:
- Evaluation setting:
- Explicitly out of scope:

## 2. Metrics
### Primary metric
- Name:
- Implementation: <library / script / parameters / SOTA repo if applicable>
- Direction: higher_is_better / lower_is_better

### Secondary metrics
- ...

## 3. Three-layer gates
| Gate | Threshold | Trigger |
|---|---|---|
| primary_progress_gate | ... | current-stage progress, not SOTA claim |
| sota_claim_gate | strict `>` or strict `<` | claim candidate only if full/scale + comparable |
| review_decision_gate | ... | force /tri-review + /pivot |
```

严格规则：

- higher-is-better 必须 `observed > SOTA`；等号不算。
- lower-is-better 必须 `observed < SOTA`；等号不算。
- screen / smoke 结果永远不能 claim SOTA。
- primary 达标但未严格超越 → 必须触发 `/tri-review` + `/pivot`。

---

## Step 2 · SOTA reference table + comparability contract

```markdown
## 4. SOTA reference table
| Model | Dataset | Split | Metric | Value | Source | Comparable? | Notes |
|---|---|---|---|---:|---|---|---|

## 5. Comparability contract
| Model | Dataset version | Split scheme | Metric impl | Preprocessing | Weights version | Test-time inference | Verdict |
|---|---|---|---|---|---|---|---|
```

Comparability 6 维：

1. Dataset version
2. Split scheme
3. Metric implementation
4. Preprocessing
5. External weights version
6. Test-time inference

任一 mismatch → 不能 claim SOTA，只能写 exploratory / non-comparable。

### 2.5 Evaluator contract（必须同步 docs/19）

把本节可执行化到 `docs/19_evaluator_contract.md`，至少填：
- primary metric 名称、方向、粒度、positive label、averaging、threshold/mask。
- official SOTA evaluator 路径或待复现对象。
- 我们计划使用的 evaluator script / metrics JSON schema。
- claim eligibility checklist。

若 evaluator 仍未知，把 `docs/19` 标 `Status: draft` 并在 `docs/05_todo.md` 加 TODO：`/reproduce-baselines` 核实 official evaluator。没有可用 `docs/19` 时不得进入 `/implement` 写训练/eval 代码。

### 两层锚点（消除"小样本 vs 大样本 SOTA"的伪不公平）—— 必填

published SOTA 常用**大样本/多物种联合训练**；前期我们为快速筛架构只能**小样本**。直接对比不公平。
因此定义**两个锚点**（写进 `ACTIVE_GOAL.json` 的 `screen_anchor` + `sota_benchmark`，供 validate_goal `--profile` 区分）：

| 锚点 | 怎么得到 | 用途 |
|---|---|---|
| **`screen_anchor`（同预算公平参考）** | 把**参考架构/baseline 在我们自己的小样本协议**（同 sample_fraction/epochs/split）下跑出来 | Track A screen **只比这个**——苹果比苹果，公平筛架构 |
| **`sota_benchmark`（已发表大样本）** | /sota-inventory 核实的 published 值 + comparability 合同 | **仅 full/scale** 阶段判 SOTA claim |

规则（validate_goal 已强制）：**screen/smoke 永远不对 published SOTA 判 success**，只对 screen_anchor 判进展；架构优势是否随规模保持，留给 Track B full/scale 大样本验证后再对 published SOTA。
→ **必须先跑一个 screen_anchor**（参考架构在小样本协议下的值），否则 Track A 无公平对照。把它列为 M1 milestone。

---

## Step 3 · Dataset readiness plan（只计划，不下载）

不要在本 skill 下载数据。这里只判断数据何时需要准备。

```markdown
## 6. Dataset readiness plan

| Dataset | Purpose | Required by | Timing | URL | Size | Split source | Hash needed? | Notes |
|---|---|---|---|---|---:|---|---|---|
| Main benchmark | baseline + SOTA claim | M1-M4 | now | ... | ... | official | yes | must fix split |
| Dataset for Path 2 | architecture-specific feature | M2 | on-demand | ... | ... | generated / official | yes | only if Path 2 selected |
| Mouse / rat data | generalization | M5 | later | ... | ... | official | yes | Phase 8 |
```

Timing 规则：

- `now`: baseline / M1 / 公平比较必须准备。
- `on-demand`: 某条 Path 被本轮 `/goal` 选择时才下载。
- `later`: Phase 8 泛化 / OOD / robustness / secondary benchmark 再下载。

本 skill 输出后，`/goal-prompt` 会要求具体 goal 如需下载数据，必须报告 path / version / hash / split source。

---

## Step 4 · Draft SOTA weaknesses and differentiated paths

先草拟，不要定稿。

### 4.1 SOTA weaknesses

必须具体到机制，不能写空话。

```markdown
## 7.1 SOTA weaknesses (mechanism-level)

| SOTA model | Weakness | Mechanism | Evidence | Exploitable? |
|---|---|---|---|---|
| ... | poor cross-domain generalization | trained on narrow distribution; representation overfits domain-specific priors | paper Table X / docs/01 claim | yes / no |
```

### 4.2 Differentiated paths

至少 3 条路径。至少 1 条必须涉及替换 backbone / head / decoder / objective / data view。纯调参不算 path。

```markdown
## 7.2 Differentiated paths (draft)

### Path 1: <name>
- **Hypothesis**:
- **Architecture change**: <specific layer / module / head / decoder / backbone / objective / data view>
- **Why this attacks SOTA weakness**:
- **Track A screen design**: sample_fraction=, epochs=, patience=, seeds=, expected walltime=
- **Track B scale-up rule**: if Track A ..., expand to ...
- **Required data**: now / on-demand / later
- **Expected gain**:
- **Risk**:
- **Failure detection**:

### Path 2: ...
### Path 3: ...
```

---

## Step 5 · User discussion before finalizing（必须做）

在写入最终 roadmap 前，必须向用户提出 3-5 个问题。优先一次给出选择题，而不是开放式长问答。

建议问题：

1. **你更想优先攻击 SOTA 的哪个弱点？**
   - A. 泛化性 / cross-domain / cross-species
   - B. 长序列 / long context
   - C. decoder / structured prediction
   - D. 数据效率 / low-resource
   - E. inference cost / deployment

2. **本轮风险偏好是什么？**
   - A. 稳健 baseline improvement
   - B. 中风险结构替换
   - C. 高风险新架构

3. **哪些方向明确不想做？**
   - 纯调参
   - 纯 ensemble
   - 只靠数据增强
   - 不可解释大模型堆叠
   - 其他：...

4. **第一轮 Track A 并行筛几个架构？**
   - 3 / 5 / 8 / 由集群资源决定

5. **一旦 screen 接近 SOTA，Track B 如何启动？**
   - top-1 马上扩数据
   - top-2 扩数据
   - 达到 primary_progress_gate 才扩
   - gap ≤ 指定阈值才扩

如果用户不想逐题回答，也要让用户至少确认：优先 path、风险偏好、Track A batch size、Track B 晋升规则。

---

## Step 6 · Final roadmap

用户确认后，写最终 `docs/03_benchmark_roadmap.md`。

```markdown
## 7.3 Track A / Track B strategy

### Track A: small-sample parallel architecture screening
- Default sample_fraction:
- Default epochs:
- Default patience:
- Default seeds:
- Parallel candidates per batch:
- Claim policy: never claim SOTA from Track A / screen

### Track B: scale-up promising candidates
- Promotion criteria from Track A:
- Data expansion rule:
- Epoch / patience expansion:
- Seed expansion:
- Failure interpretation:

### Parallel progression rule
Track A continues exploring new architectures while Track B scales candidates that passed promotion criteria.
```

```markdown
## 7.4 Milestones
| ID | Milestone | Threshold | Track | Expected runs | Completion evidence |
|---|---|---|---|---|---|
| M1 | Baseline reproduces published SOTA within tolerance | ... | baseline/full | 1 | comparable result-log |
| M2 | One path hits primary_progress_gate on screen | ... | Track A | 3-8 screen runs | screen result-log + tri-review |
| M3 | Best M2 candidate holds on larger sample / full | ... | Track B | 1-3 full runs | full result-log |
| M4 | First strict exceed on full/scale | ... | Track B | 1-3 full/scale | comparability all ✅ |
| M5 | Phase 8 comprehensive superiority | all dimensions verified | generalization | varies | /generalization |
```

```markdown
## 7.5 Resource budget
| Stage | Resource profile | Compute estimate | Wall-clock estimate | Notes |
|---|---|---|---|---|
| M1 | full or baseline | ... | ... | ... |
| M2 Track A batch | screen | ... | ... | parallel matrix |
| M3 Track B scale-up | full | ... | ... | submit-and-handoff likely |
| M4 final | scale | ... | ... | multi-seed |
```

---

## Final output to user

在最后一轮 inline 展示：

1. Three-layer gates 数值。
2. SOTA reference table。
3. Dataset readiness plan，并明确没有下载数据。
4. 用户确认后的 differentiated paths。
5. Track A / Track B 策略。
6. Milestones + resource budget。
7. 写入路径：`docs/03_benchmark_roadmap.md`。
8. 下一步：让用户挑一个具体 milestone/path → 先 `/reproduce-baselines`（写代码前本地复现 1-2 个 SOTA、核实指标算法/数据集口径；**hook 闸：未复现或未显式 waive 不进 /goal 迭代**）→ 再 `/goal-prompt <iteration description>`。

## Don'ts

- 不要在没有用户确认的情况下定稿技术路线。
- 不要真的下载数据；只做 readiness plan。
- 不要把 screen 数字写进 `sota_claim_gate`。
- 不要把 path 写成“探索 A 和 B 结合”这种空话，必须到层级。
- 不要省略 Track A / Track B 晋升规则。

## Hand-off

- **Inputs from**: `docs/02_sota_model_inventory.md`, `docs/01_literature_review.md`, `docs/00_active_goal.md`
- **Outputs to**: `docs/03_benchmark_roadmap.md`, `docs/05_todo.md`
- **Next skill**: `/reproduce-baselines`（复现地基、核实指标/数据集，hook 闸不可跳）→ `/goal-prompt <milestone/path iteration description>`
