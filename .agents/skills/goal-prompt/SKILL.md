---
name: goal-prompt
description: "A5· Generate a Claude Code /goal command **+ companion protocol file** for one experiment iteration."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Goal Prompt Generator · Claude Code

把 `$ARGUMENTS` 转成 **2 个 artifact**：
1. 短而精的可粘贴 `/goal` command （≤ 3500 chars）
2. 配套 `goals/<exp_id>_protocol.md` 详细文档（任意长度）

`/goal` evaluator 只看对话内容，不会读 protocol 文件。但 goal 执行中的 Claude **会** read protocol。所以 completion condition 必须 inline 在短 prompt 中要求展示关键 checkpoints；详细执行步骤放 protocol。

---

## Step 0 · Length budget + protocol-file convention (HARD)

### 0.1 为什么有长度限制

Claude Code 终端粘贴有 2 个失败模式：
- markdown 表格被 renderer 转 ASCII boxes → 字符膨胀 ~2×
- 终端粘贴 buffer 在 ~10-15k chars 处截断（OS 相关）
- 嵌入代码块易丢闭合 ``` 导致后续内容渲染错位

### 0.2 长度预算

| 限制 | 建议 | Hard ceiling |
|---|---|---|
| `/goal` 主体（不含 `/goal` 关键字）| ≤ **3500 chars** | **4000 chars** |
| 表格行数（合计 across all tables）| ≤ **6 行** | **10 行** |
| 嵌入代码块 | ≤ **1 段, ≤ 10 行** | 0 段（推荐都放 protocol）|
| H2/H3 章节数 | ≤ **6 个** | 8 个 |

skill 生成完短 prompt 后**必须** `wc -m` 验证 ≤ 4000 **字符**（不是字节！中文 UTF-8 每字 3 字节，用 `wc -c` 会误判）。超了再裁剪 / 推内容到 protocol。

### 0.3 短 prompt 必含 / 必略

**必含**（短 prompt 是 evaluator 唯一可见的契约）：
- 首行 milestone 声明（exp_id + 一行描述 + Mode 含 user-explicit override 标记若有 + protocol reference）
- `## 权限声明` 固定段（见 0.6, 防权限 prompt 浪费 turn）
- `## 运行说明` 固定段（见 0.7, 防过早下线 / 过早信任）
- `## 决策自治` 固定段（见 0.8, 防中途等用户拍板浪费时间）
- `## Mode & Milestone`（mode + claim eligibility + 3-layer gate 数值）
- `## Hard pre-submit gate`（一行陈述 + 失败后果一行）
- `## Required chain`（编号 1-N, 每行 ≤ 1 句陈述句）
- `## Completion (inline ✅ CK1-CK<N>)`
- `## Constraints`（≤ 5 条 bullet）

**必略**（移入 protocol）：
- Slurm polling implementation 详细（background bash 写法、sacct 字段、6 终态分支处理）
- Scout tasks 具体执行命令 + 输出位置表
- Subagent 详细 prompt 模板
- Comparability 6 维 / Data contract 8 项的逐项 checklist 文本
- Skill invocation chain 完整 9 行表
- /pivot baseline-gate / architecture-pivot 选项的详细说明
- 任何超过 3 行的命令示例

### 0.6 固定段 · 权限声明（每次短 prompt 必含, ~380 chars, 全中文）

固定 boilerplate（可附 iteration-specific 覆盖一两行；**不要在固定段里反向放权**）：

```
## 权限声明

本 goal 拥有充分工具权限。若集群命令 / 网络下载 / subagent 调用临时失败, **先尝试 ≥ 1 替代路径**, 仍失败再 inline 报告, 不要停下等用户：
- 内置工具不受限（Bash / Edit / Write / Read / WebFetch / Glob / Grep / TodoWrite / BashOutput / KillShell 等）
- 可并行调用 Claude Code subagents, 但避免写同一文件
- 允许下载任何研究所需数据（公开数据集 / HF weights / 跨物种基因组 / Rfam family 等）；下载后 inline 报告 path / version / hash / 来源
- sbatch 远程提交训练；若已有可复用 sbatch 脚本, **不要重写**, 仅做 read-only review + Phase 1 policy guard
- 必要时可创建新 skill 以稳定流程（创建后 inline 报告路径+用途）
- 关键 source-of-truth 文件（CLAUDE.md / docs/03 / docs/09）只可 draft patch text, 不直接 Edit
- 训练/eval/config/job 脚本改动后，真实训练前必须跑 /code-review-gate 并写 docs/21_code_review_log.md
```

### 0.7 固定段 · 运行说明（每次短 prompt 必含, ~370 chars, 全中文）

固定 boilerplate（可附 iteration-specific 覆盖一两行）：

```
## 运行说明

- 所有 sbatch 提交遵循 /smart-sbatch 自动选合适节点 / 分区 / 时长（Phase 1 guard + Phase 2 optimization 两段）
- 若 sbatch 脚本已存在: 对现有脚本跑 /smart-sbatch Phase 1 guard, **跳过** Phase 2 重生成 header
- 预期 ≤ 1 天的运行用 sleep 同步等待, 不中途下线
- **任何长度的运行**: 先等第 1 个 epoch 完成, 确认 loss 在降 / eval 正常 / 后续 epoch 迭代无问题, **之后**才允许降低监控频率
- 本轮预计 <X> 时长, 第 1 epoch 应 ≤ <Y>h 内出, 之后切 30/60/120 min 三档 polling
- 低频监控仍按 protocol Slurm polling cadence 执行, 不可完全放任
```

### 0.8 固定段 · 决策自治 (autonomous decision-making, 每次短 prompt 必含, ~660 chars, 全中文)

固定 boilerplate（不可裁剪；防 goal 中途反复等用户拍板浪费 turn / time）：

```
## 决策自治

goal 执行中遇到**多选项决策点**（如 pivot 7 选 1, 资源分配 A/B/C, anchor 选择 P/Q/R, 重训 vs 接受当前结果等），**默认不暂停等用户**, 而是：

1. inline 列出 N 个选项 + 每选项预期 (a) SOTA gap 收益 (b) 时间成本 (c) 风险
2. 立即并行调 3 CLI reviewer (Claude+Codex+Antigravity, 复用 /tri-review 机制), prompt 含选项 + 项目当前 gap + 时间预算
3. 按 reviewer 共识 + cost-adjusted ROI 自动选 1 个继续 (排序优先级: 严格 SOTA 进展 > 时间成本 > 风险)
4. 决策 + 3 reviewer 简要理由 写 docs/08 (pivot) 或 inline
5. 继续 goal, **不暂停**

**例外** (仍需用户显式确认, 不可自治):
- 强破坏性操作 (scancel 用户其它 running job / rm 数据 / 改 docs/03 roadmap)
- route 级 abandon (写 docs/09)
- 决策影响 > 24h 净新增 compute spend (例: 重训本身的资源决定可自治; 但启动一条新长 sub-iteration 需确认)
- ≥ 2 reviewer 明确反对 default 共识 (tied 3-way 无 leader)
```

### 0.9 字符预算重估（含 0.6 + 0.7 + 0.8 固定段）

固定段合计 ~1410 chars (0.6 ~380 + 0.7 ~370 + 0.8 ~660)。短 prompt 实际可用 iteration-specific 内容 ≈ **2400-2590 chars**（4000 hard ceiling − 1410 fixed）。超了仍要推内容到 protocol。

> **注**: 0.8 决策自治段相对较长 (含 5 步流程 + 4 项例外), 是因为决策行为模糊空间最大、最容易被未来 goal 漂移裁剪——保持详细。如果未来观察到 goal 反复忽略例外条款 (例如自治启动了破坏性操作), 在 0.8 段补一行强化, 不在这里裁剪。

### 0.4 配套 protocol 文件

任何超预算细节写入 `goals/<exp_id>_protocol.md`。短 prompt 在开头一句话 reference：

```
Read and follow `goals/<exp_id>_protocol.md` and `CLAUDE.md`, but judge completion only by the inline checkpoints below.
```

### 0.5 输出 artifact 总数 = 2

| Artifact | 路径 | char limit | 用途 |
|---|---|---|---|
| 短 prompt | `goals/<exp_id>.md` | ≤ 4000 | 用户复制粘贴；或 `/goal @goals/<exp_id>.md` |
| Protocol 详细 | `goals/<exp_id>_protocol.md` | 无上限 | Goal 执行期间 Claude 阅读 |

skill 调用结束时 inline 显示：
1. 短 prompt 完整文本（含字符数 verbatim 验证）
2. Protocol 文件路径 + char count
3. 推荐启动命令

---

## Step 1 · 读项目上下文

**入口阶段闸（不可跳，G4）**：先跑 `python3 scripts/research_flow_guard.py . --format json`——若 `ok_to_goal=false`（evaluator_contract 未固化 / baseline 未复现或 waive / screen_anchor 缺失等），**不要生成 `/goal`**，先按其 `recommended_next` 补齐段 A 缺口（这把阶段闸从写后 nudge 升级为入口硬前置）。并校验 `ACTIVE_GOAL.json status == active`（合约状态机 `draft→active→achieved/blocked`）；若仍 `draft`/缺字段 → 提示先 `/configure-project` 落定再生成 goal。

读取（缺失文件标 `(absent)`，仍生成 artifact，但用 `<FILL: ...>` 占位）:

- `CLAUDE.md`
- `docs/00_active_goal.md`
- `docs/02_sota_model_inventory.md`
- `docs/03_benchmark_roadmap.md`
- `docs/05_todo.md`
- `docs/06_results_log.md`
- `docs/09_decisions_log.md`

从 `docs/03` 抽取：benchmark / SOTA / 三层门 / Path / Track A 默认 sample_fraction/epochs/patience/seeds / Track B 晋升条件 / Dataset readiness / resource profile / expected walltime。

### Step 1.4 · Pending integration queue（必读，来自 /note-add）

读 `docs/05_todo.md` 的 `## Pending integration queue (/note-add)` 段。对每个未勾选项（中途装填的新文献）：
- 评估是否纳入**本轮** goal：作为新候选机制、对照基线、或 comparability 检查项。
- 纳入的：在生成的 `/goal` command 里显式引用（含 `refs/dossiers/<slug>.md` 路径），并在 docs/05 把该项标注 "folded into <exp_id>"。
- 暂不纳入的：留在队列，并一句话说明为何延后。
- 队列为空则跳过。

### Step 1.5 · Retrospective trigger check

读 `docs/04_experiment_iterations.md` + `docs/08_pivot_decisions.md`，判断 4 个触发条件：
- 自上次 retrospective ≥ 5 completed iterations
- 同一路线连续 3 次 gap 未缩小 (Δgap < 0.01)
- Track B scale-up 失败 2 次
- 连续 2 次 /pivot = tune

若任一满足，在短 prompt 顶端追加 1 行 advisory（**不展开**）：

```
⚠️ Retrospective advisory triggered: <condition>. Recommend /retrospective before this; advisory does not cancel this iteration's flow.
```

---

## Step 2 · 判断本轮属于哪一轨

### Track A / screen
小样本（sample_fraction=0.01-0.10）/ 少 epoch（2-5）/ 低 patience（1-2）/ 少 seed（1-2）/ 可并行多候选 / 目标 = 达 `primary_progress_gate` 或暴露 SOTA 弱点上的优势 / **红线：screen 永不 claim SOTA**。

`$ARGUMENTS` 是 batch → 必须生成 parallel batch matrix（在 protocol 中详写）。

### Track B / scale-up
仅接 Track A 晋升候选。说明 promoted_from / 晋升依据 / 样本+epoch+patience 扩大方式 / 不扩则不再是架构问题之判断。
**seed：迭代期（含 scale 比较候选选方向）默认单 seed**——不在这里铺多 seed；多 seed（≥3 + paired 检验）留到方向确定后的 `/generalization`（见 CLAUDE §9 多 seed 时机）。单 seed 的 full/scale 结果可作 claim 候选，最终 robust claim 过 generalization 多 seed 即可。

### baseline
非 Track A 也非 Track B。专门建立 anchor 数字给后续 ablation 用。永不 claim。

### 并行
Track A 可继续筛新架构 / Track B 可同时 scale 已晋升候选 / 不等所有 Track A 结束再启 Track B。

---

## Step 3 · 选择 execution mode

CLAUDE.md §11 定义 **3 种 mode**：

| Mode | 用途 | 长度建议 | walltime > 12h |
|---|---|---|---|
| `run-and-evaluate` | ≤ 12h smoke/screen | 短 prompt | ❌ |
| `submit-and-handoff`（原 submit-and-stop）| 长任务，希望本 goal 立即下线 | 短 prompt | ✅ 默认 |
| `run-wait-review-pivot` | 长任务但**单 goal 全程跑完** | **必须有 protocol**（含 Slurm polling）| 仅当 user 明确请求 |

默认：
- Track A screen ≤ 12h → `run-and-evaluate`
- Track B/full/scale/multi-seed → `submit-and-handoff`
- 用户在 `$ARGUMENTS` 写 "single long-lived" / "run-wait-review-pivot" → 覆盖 default

---

## Step 3.5 · Track A orthogonality

Track A parallel batch（≥ 2 候选）必须 inline 输出 orthogonality 表 + verdict (`PASS` / `HARD_FAIL` / `SOFT_WARN — focused arch batch on <axis>`)。

两层结构：
- `major_axis`: head_arch / backbone / objective / data_view / tokenizer / decoder / training_signal / loss_design / regularization_design / augmentation_design
- `mechanism_delta`: 真正结构性差异点（"CRF transition" / "HMM latent smoothing" / "autoregressive decoder" / "contrastive aux loss" / "multi-species pretrain" / "kmer tokenizer with overlap"）

**Hard fail**: 全候选只改 lr/batch/dropout/seed/scheduler/warmup；≥ 2 候选 mechanism_delta 实质相同；任一候选写不出 why structural（新增张量 / forward 改 / loss term）。

**Soft warn**: ≥ 2 共享 major_axis 但 mechanism_delta 不同 → focused arch batch，必须在短 prompt 顶部标 `⚠️ FOCUSED ARCH BATCH on <axis>`，不可伪装 diverse batch。

短 prompt 中只写 verdict + 1 行 declaration；详细 axis/mechanism/why-structural 表移入 protocol。

---

## Step 4 · 显式 subagent fan-out

涉及大量检索 / 多候选 / 代码检查 / 并行实验矩阵 → 短 prompt 一句话声明哪些 subagent + 文件 scope；详细 prompt 模板移入 protocol。

注意 tri-review 不走 subagent（CLI reviewer）。

推荐场景：
- 多份 deep research → `literature-claim-extractor`
- 多 SOTA/GitHub/weights 链接 → `sota-source-verifier`
- 训练前代码/metric/split 检查 → `code-plan-reviewer`
- Track A 多候选 config 草案 → `experiment-implementer`（每 subagent 仅写自己的 exp_id scope）

硬规则：subagent 不能写同一文件 / read-only 不得 Edit/Write / 主 agent 负责 merge / full+scale+claim-candidate pre-submit 至少 1 次 read-only review subagent。

### Step 4.5 · Code review gate（真实训练前硬闸）

若本轮新增或修改训练/eval/data/config/job 脚本，短 prompt 和 protocol 都必须要求：
- `/implement` 后立即跑 `/code-review-gate`。
- `docs/21_code_review_log.md` 有 `PASS` / `PASS_WITH_WARNINGS` 才能进入 `/smart-sbatch`。
- `BLOCKED` 未修不得提交；用户强行豁免须写 `WAIVED_BY_USER`。
- 涉及 metric/evaluator 时同步 `docs/19_evaluator_contract.md`。

---

## Step 5 · 数据下载规则

`/benchmark-roadmap` 不下载。`/goal` 若需下载：只下 `docs/03` 标 `now`/`on-demand` 的数据 / 下后 inline 报告 path/version/hash/split source / 不临时换 split / 失败 → 停止报 blocker。

短 prompt 一句话陈述本轮是否需下载；详细 hash 验证流程入 protocol。

---

## Step 6 · 生成短 prompt（≤ 3500 chars 推荐 / 4000 hard ceiling）

### 6.1 短 prompt 模板（**用户复制粘贴的 artifact**, 包含 0.6+0.7+0.8 固定段）

```text
Complete <EXP_ID> · <one-line milestone description> as <mode>. Read and follow `goals/<exp_id>_protocol.md` and `CLAUDE.md`, but judge completion only by the inline checkpoints below.

## 权限声明
[逐字插入 0.6 固定段, 替换 <yes 路径/no 已就位> + <脚本路径>]

## 运行说明
[逐字插入 0.7 固定段; 若本轮 walltime > 24h 可补一行 "本轮预计 <X> 天, 第 1 epoch 应在 <Y>h 内出, 之后切 30/60/120 min 三档"]

## 决策自治
[逐字插入 0.8 固定段; 可附 iteration-specific 一行覆盖, 如 "本轮 anchor 阈值选择 (M0 ≥ 0.35 vs ≥ 0.20) 适用决策自治"]

## Mode & Milestone

Mode: <run-and-evaluate | submit-and-handoff | run-wait-review-pivot>[, user-explicit override if applicable]. <One-line: where this goal ends>.

Milestone: <M0/M1/.../track type>, <claim eligibility>, resource profile = <screen/full/scale>.

3-layer gate: primary_progress_gate=<v>; sota_claim_gate=<strict rule>; review_decision_gate=<v range>.

## Hard pre-submit gate

<one-line condition>. If fails, do not submit sbatch; final pivot must be `fix_eval` (or analog).

## Required chain

1. <verb phrase>
2. <verb phrase>
...
N. <verb phrase>

## Completion (inline ✅ CK1-CK<N>)

CK1 <summary>; CK2 <summary>; ... CK<N> <summary>.

## Constraints

- <≤ 5 critical bullets, 一行一条>
```

### 6.2 短 prompt 不应包含

- 详细 Slurm polling bash 实现
- 完整 sacct 6 终态决策矩阵
- 完整 skill invocation chain 表
- Scout task 4 条的逐条命令 + 输出位置
- Comparability 6 维 / data contract 8 项 逐项 checklist
- /pivot 选项每条的解释段落
- 详细 subagent prompt 模板
- 长 advisory boundary 列表（一行 reference protocol 即可）

### 6.3 生成后验证

```bash
wc -m goals/<exp_id>.md   # 字符数, 不是字节数（中文 UTF-8 每字 3 字节）
```

> 4000 字符 → 必须裁剪 → 移更多到 protocol。

---

## Step 6.5 · 生成 protocol 文件（`goals/<exp_id>_protocol.md`）

protocol 文件是 goal 执行期间 Claude 的「操作手册」。**没有长度限制**。建议结构：

```markdown
# <EXP_ID> · Protocol

## Permissions
<full tool list + file scope restrictions, including "CLAUDE.md only draft patch text, no direct Edit" if applicable>

## Final goal
<full milestone description + 3-layer gates + reference benchmark with verbatim numbers>

## Track + resource
<full Track A/B params, parallel batch matrix if applicable, resource profile, partition>

## Execution mode details
<for run-wait-review-pivot: full Slurm polling protocol (Option A background monitor bash + Option B foreground fallback cadence + state transition table + sacct terminal state decisions)>
<for submit-and-handoff: scout-deferral marker convention>
<for run-and-evaluate: short eval timing>

## Pre-submit gate
<full steps 1-N for verifying the gate>

## Safe Scout tasks
<full table: # | task | exec method | output location | defer policy>
<Scout advisory boundary HARD rules>

## Orthogonality declaration
<for Track A batch: full axis/mechanism/why-structural table>
<otherwise: N/A>

## Subagent fan-out
<full subagent prompts + file scope>

## Slurm polling protocol
<for run-wait-review-pivot only: full Option A/B bash + state matrix>

## Pivot decision menu
<full list of allowed pivot outcomes for this milestone type (baseline-gate / track-A-screen / track-B-promote / claim-decision) with description per option>

## Skill invocation chain
<full table with all skipped rows marked>

## Constraints (full)
<full list, including ones too long for short prompt>
```

---

## Step 7 · Skill 检查表（生成前自检）

短 prompt 生成完毕后，skill 必须 inline 自检：

| Check | 通过条件 |
|---|---|
| char count | `wc -m goals/<exp_id>.md` ≤ 4000（字符数，**不是**字节数）|
| 表格行数 | ≤ 10 行（合计）|
| 嵌入代码块 | ≤ 1 段 ≤ 10 行 |
| protocol reference | 短 prompt 首段必含 `Read and follow goals/<exp_id>_protocol.md` |
| **0.6 权限声明 段在场** | `## 权限声明` 存在且 5+ bullets 完整 |
| **0.7 运行说明 段在场** | `## 运行说明` 存在且 5 bullets 完整, 含 "第 1 epoch 完成才降频" 规则 |
| **0.8 决策自治 段在场** | `## 决策自治` 存在, 含 5 步流程 (列选项 → tri-review → 共识选 → 写 docs/08 → 不暂停) 与 4 项例外 (破坏性/abandon/>24h/tied 共识) |
| completion checkpoints | CK1-CKN 全在短 prompt 内 |
| protocol 文件存在 | `goals/<exp_id>_protocol.md` 已 write |
| Step 1.5 retrospective verdict | inline 一行陈述（triggered 或 not triggered + 理由）|
| Track A batch orthogonality | verdict 一行；详细表在 protocol |

任一失败 → 不输出, 修正后重检。

---

## Step 8 · Final output

skill 调用结束时按此顺序 inline 给用户：

1. **短 prompt 完整文本**（含 `wc -m` 验证字符数，**不是 `wc -c`**：中文 UTF-8 每字 3 字节会误判）
2. **Protocol 文件路径** + char count
3. **推荐启动命令**: 任选一
   - `/goal $(cat goals/<exp_id>.md)` （bash substitution）
   - `/goal @goals/<exp_id>.md` （Claude Code @-file 引用）
   - 直接复制短 prompt 文本粘到 `/goal `
4. **Skill invocation chain 摘要**（≤ 4 行；详细在 protocol）
5. **Track / Mode / Retrospective 决策一句话理由**
6. 列出 `<FILL: ...>` 若有

---

## Don'ts (skill-level)

- **不要**生成只有 1 个 artifact（短 prompt 必须有配套 protocol，即使 protocol 较短）
- **不要**让短 prompt 超过 4000 chars
- **不要**在短 prompt 嵌入 > 1 段代码块或 > 10 行总表格
- **不要**把 Slurm polling 实现、sacct 终态矩阵、scout task 执行命令、subagent prompt 模板放进短 prompt
- **不要**默默用旧 `submit-and-stop` 名字（CLAUDE.md §11 已重命名为 `submit-and-handoff`）
- **不要**在没有用户明确请求时把 mode 设为 `run-wait-review-pivot`
- **不要**让 protocol 文件覆盖 docs/03/09（protocol 是 execution-time reference，不是 source of truth）
- **不要**省略 Step 7 自检
- **不要**省略 0.6 权限声明 / 0.7 运行说明 / 0.8 决策自治 固定段（即使 mode 是 run-and-evaluate；三段分别防权限/监控/决策行为漂移）
- **不要**在固定段里添加"允许覆盖 docs/03/09" 或 "允许直接 Edit CLAUDE.md" 之类放权——固定段是 floor 不是 ceiling
- **不要**在 0.8 决策自治段里删除"4 项例外"——破坏性/abandon/>24h-spend/tied-consensus 必须仍 pause; 自治是默认行为不是无脑放权
