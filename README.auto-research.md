# Auto-Research · Claude + Codex + Antigravity 三壳 v4.1 (中文优先 + 并行workspace + 阶段闸 + 对抗council/冷导入 + 智能归档 + 目录契约)

> Prompt-discipline 研究自动化框架。在双壳与迭代纪律基础上，提供**中文优先 deep research/report 策略**、面向已有强方案的**段C：投稿验证 / 流程化 pipeline 推进**、随机初始化 SOTA 小样本复训、智能归档门控、用户可随时定位的 master plan、统一目录/产物契约；v4.1 在 v4.0 的阶段顺序守卫、SOTA失败源汇报、可选 git/worktree、`.codex/skills` 兼容镜像与运行迁移手册之上，新增**框架升级 skill、同项目 route reset、代码审前闸、evaluator/baseline 中央账本**。
> 双壳/三壳：同一项目同时支持 Claude 驱动 `.claude/`+`CLAUDE.md`、Codex 驱动 `.codex/`+`AGENTS.md`，以及 Antigravity/其它 agent loader 读取 `.agents/skills`；AGENTS.md 由 CLAUDE.md 确定性生成、零漂移；新增 skills 会同步生成 `.agents/skills` 并镜像 `.codex/skills`。默认并行多线靠 `exp_id/run_id/pipeline_id` 目录隔离；只有多方向同时修改共享代码时，才由 `/workspace-matrix` 人闸启用 git worktree（最多 3 条）。
>
> Last updated: 2026-06-13

---

## TL;DR · 三分钟读完

- **deep research / report 默认语言**：中文为默认交付语言；检索式、paper 名、模型名、指标名保留英文，必要时给中英双语关键词。
- **新项目从零开始**？→ `/research-interview` 进 **FRESH mode**，中文访谈 + 全景 deep research prompt。
- **导入"做了一半"的外部研究**（有代码/结果/笔记但没进框架）？→ `/ingest-existing`：subagent 系统梳理 + 目录规整 + 回填 docs，再共定目标。
- **接续已在框架内的项目**？→ `/research-interview` 进 **CONTINUATION mode**，自动读项目快照 + 5 题聚焦 + focused prompt。
- **某个方向很关键/有争议，想辩穿再烧 GPU**？→ `/council`：多 agent 对抗式辩论 + 你裁判（比 `/grill` 重，opt-in）。
- **已经有强候选模型/完整思路，目标是投稿**？→ `/master-plan → /publication-plan → /sota-randomized → /generalization → /note-gate`，先定位期刊/会议、贡献边界、验证矩阵，再推进实验。
- **已经有 raw data / 生信分析流程，目标是构建 pipeline**？→ `/master-plan → /pipeline-blueprint → /artifact-registry → /note-gate`，先钉死 DAG、输入输出、QC、软件产物，再执行。
- **跑探索性实验**？→ `/goal-prompt <EXP-X-NNN>` 生成 `/goal` command，粘贴运行。`/goal` 内自动衔接 smart-sbatch → train → result-log → note-gate → tri-review → pivot。
- **写完训练/评估代码准备提交**？→ `/code-review-gate`：审 label/metric/split/evaluator/output path，BLOCKED 不准训练。
- **当前路线走不通或要 A/B→C 切换**？→ `/route-reset`：同项目内重开线/切 pipeline，保留可迁移证据，不新建项目。
- **框架本身要 v3→v4 或 v4 minor 升级**？→ `/framework-upgrade`：兼容迁移，保留研究内容，写升级日志。
- **怀疑兜圈子**？→ `/retrospective` 跨实验回溯审视。
- **严格超越 SOTA 之后**？→ `/generalization` 八维全面评估；若需要小样本可靠性比较，先用 `/sota-randomized`。

---

## 导航 · 我现在该用哪个？（37 skill 不用记，对号入座）

> 任何时刻只需回答一个问题——"我现在处于什么处境？"——然后查这张表。**不知道自己在哪一步时，永远先读 `docs/11_master_plan.md`**（统领导航图）。

| 你的处境 | 用什么 | 段 |
|---|---|---|
| 全新方向，只有模糊想法 | `/research-interview` → 外部 deep research → `/research-synthesize` | A |
| 手上有"做了一半"的旧项目（代码/结果/笔记），想纳入框架 | `/ingest-existing`（梳理+目录规整+回填） | A0 |
| 综述好了，要把"谁是 SOTA"查实 | `/sota-inventory` | A |
| 方向有了，烧 GPU 前想透/被拷问 | `/grill`（你 vs 单 agent）；重大争议 → `/council`（多 agent 对抗辩论）；设计方案盲审 → `/review-board` | A |
| 诉求清了，要填配置/集群/目标 | `/configure-project`（AI 填，人闸） | A |
| 把方向变成可执行实验路线 | `/benchmark-roadmap` | A |
| 写自己模型前核实指标/数据口径 | `/reproduce-baselines`；要同预算公平参考 → `/sota-randomized` | A→B |
| 开始跑实验 | `/goal-prompt`(手动逐轮)、`/pursue`(监督自主)、`/evidence-sprint`(单点求证) 或 `/capability-pursue`(原创组件有界开发) | B |
| 写完训练/eval/config，提交训练前 | `/code-review-gate` | B |
| 一轮训练跑完 | `/result-log` → `/note-gate` → `/exp-log` → `/tri-review` → `/pivot`（hook 自动提醒） | B |
| 已超 SOTA，要论证可靠性去投稿 | `/master-plan` → `/publication-plan`（期刊/贡献/证据矩阵） | C |
| 有 raw data，要按流程分析 | `/master-plan` → `/pipeline-blueprint` → `/artifact-registry` | C |
| 中途冒出好文章/想法/小结 | `/note-add`（随时，不打断 run） | * |
| 试个直觉又怕污染主线 | `/spike`（隔离 SPIKE-*） | * |
| 感觉兜圈子/在原地调参 | `/retrospective` | * |
| 早期假设错了，想改大方向但保留结论 | `/reframe`（战略重定向 + carry-forward） | * |
| 当前路线要从 Stage A 重来或切到段 C | `/route-reset`（同项目重开线 + 重写 docs/11 pipeline） | * |
| 框架升级/迁移/兼容修复 | `/framework-upgrade` | * |
| 重大讨论/换方向/表态偏好后 | `/note-gate`（把结论/偏好归档，别死在对话里）+ 必要时 `/master-plan` | * |

**三种工作流模式**（`/configure-project` 据诉求设定并写进 `docs/11 §0`，决定走段B还是段C）：
- **Discovery-Iteration**：方向不定，探索迭代找超 SOTA 模型 → 段B。
- **Publication-Validation**：已有强候选，补证据投稿 → 段C 投稿支。
- **Pipeline-Execution**：已有 raw data，按固定流程分析 → 段C pipeline 支。

## docs/ vs wiki/ vs refs/ —— 三种"记忆"别搞混（你问的重点）

| | 是什么 | 存什么 | 谁写 | 何时看 |
|---|---|---|---|---|
| **`docs/`** | **结构化流程状态 = 唯一真相源** | 编号文档 00-24（目标/综述/SOTA表/roadmap/迭代/结果/评审/pivot/导航/投稿/pipeline/证据簿/evaluator/baseline/code-review/upgrade/review-board/ledger） | **每个 doc 只有对应 skill 能写**（写边界见 §6.5） | 会话恢复必读；agent 每轮从这里**确定性重建上下文** |
| **`wiki/`** | **自由形式的可检索知识花园** | `ideas/`(想法/假设) + `notes/`(跑过一次的小结) + 自动 `INDEX.md` | `/note-add`（随手记，不打断 run） | 翻历史灵感/"为什么当时否了某念头"：`wiki/wiki.sh search <kw>` |
| **`refs/`** | **文献归档库（一手证据）** | `pdfs/`+`repos/`+`dossiers/`(每篇数据集源/指标实现/split)+`sources.md` | `/sota-inventory`、`/note-add`、`archive_source.sh` | 查"那篇论文到底怎么算指标/用什么数据" |

> 一句话：**docs = 我们决定了什么、做到哪（结构化·受控·权威）；wiki = 路上的灵感与零碎尝试（自由·可搜）；refs = 别人的论文与代码（一手）。** docs 进上下文重建、wiki 靠搜索召回、refs 是查证来源。

## 文件夹速查 · 什么放哪

| 目录 | 放什么 | 谁产生 |
|---|---|---|
| `docs/` | 流程文档 00-24 + `experiments/`(单实验档案+ATLAS) + `inputs/`(deep research 报告 drop 区) | 各 skill |
| `scripts/` | 框架可靠性脚本 + `hooks/`；可复用项目脚本 | 框架 |
| `scripts/experiments/<exp_id>/` | 单次实验专用但会影响结果的训练/eval/数据转换 wrapper | `/implement` |
| `configs/` | 每 exp 超参 `<exp_id>.yaml`；`pipelines/`、`sota_randomized/` 子目录 | implement / sota-randomized |
| `runs/` | **完整训练状态/checkpoint**，按 `<exp_id>` 隔离 | 训练 run |
| `reports/` | 每 run 指标摘要 `<exp_id>.json`（**hook 监听它触发自动归档提醒**） | 训练/eval |
| `outputs/` | 每 run 的 `STATUS` + 产物（对账用） | 训练 run |
| `logs/` `sbatch/` | stdout/stderr；Slurm 提交脚本 `<exp_id>.sbatch` | run / smart-sbatch |
| `pipelines/` | pipeline 的 stage 脚本（`<pipeline_id>/`） | pipeline-blueprint |
| `software_outputs/` | 外部软件（bedtools/blast…）原始输出 `<tool>/<run_id>/`（含 6 件套） | pipeline stage |
| `data/raw\|interim\|processed/` | 数据分层，**raw 只读绝不改** | 你/下载 |
| `manuscript/` `external_runs/` `analysis/` | 投稿材料；外部/手工运行记录；探索 notebook | 你 / publication-plan |
| `goals/` | `/goal` command 模板 | 框架 |
| `.git/`（可选） | 框架代码/轻量文档版本控制；不放 data/runs/secrets/checkpoints | `/workspace-matrix` 人闸初始化 |

> 完整契约（含"绝不放这里"+保留期）见 `docs/16_artifact_registry.md`、`docs/17_parallel_workspace.md`、`docs/18_runtime_playbook.md` 与 `PROJECT_STRUCTURE.md`；`/artifact-registry --init` 自动建齐、`--audit-run` 查错放。

---

## 0. Install（单仓双壳：Claude / Codex / both）

```bash
# 双壳（默认，推荐）：同时装 Claude 壳(.claude/+CLAUDE.md) 与 Codex 壳(.codex/+AGENTS.md)
./install.sh --driver both   /path/to/your/project
# 只装一个壳：
./install.sh --driver claude /path/to/your/project
./install.sh --driver codex  /path/to/your/project
```

**install 是幂等的、可安全重跑**（三种意图一个命令，全程备份 `.backup-<timestamp>`、不碰 git）：
- **首次安装**：seed 模板 + 所请求的壳。
- **中途补壳**：在只装了 codex 的项目上重跑 `--driver claude` 会**补上 claude 壳、保留 docs 研究进度 + 已有 codex 壳**（反之亦然）——这正是"中途换驱动接力"的基础。
- **升级/挪机器**：刷新框架代码（scripts/壳/ARCHITECTURE/README），**保留**研究内容（docs/goals/refs/wiki/CLAUDE.md/ACTIVE_GOAL/cluster_config/secrets/.mcp.json）。最新 CLAUDE 模板落为 `CLAUDE.md.example` 供 diff。

> 分类：**研究内容 seed-if-absent（绝不覆盖进度）**；**框架代码刷新**；**只装请求的壳**。`.agents/skills` 是由 `scripts/build_codex_skills.py` 从 `.claude/skills` 生成的**真实短描述目录**（**不是** symlink——早期 symlink 会撑爆 codex ~8000 字符 skill-list 预算，已弃用）；`AGENTS.md` 由 `scripts/sync_agents_md.sh` 从 `CLAUDE.md` **确定性生成**，改 CLAUDE.md 后重跑同步。

**安装后怎么起步**（推荐：不开局手填，诉求澄清后交给 AI）：

1. 直接开跑段A（`CLAUDE.md §0-2` 已预设通用方向，足够起步）→ 走到 `/grill` 澄清后 → **`/configure-project`**：AI 据澄清上下文 + 探测集群(`sinfo`)/conda/**提交模式** 自动填 `CLAUDE.md §0-2/§12-15` + `cluster_config.yaml`(含 `submission.mode`) + `ACTIVE_GOAL.json`（提议 diff→你确认才写），并重生成 `AGENTS.md`。挪集群/换方向随时可重调。
2. API key 填进 `secrets.env`（随框架走、填一次，详见 README.md 的安装说明与 `secrets.env.example`）。
3. 外部 CLI（Codex / Antigravity `agy`，首次 `agy -p "hi"` 完成 Google 登录）在 PATH。统一三 CLI：claude / codex / agy，无 cursor-agent 兜底（agy 不可用 → reviewer C 失败走 2/3 DEGRADED）。
4. （可选·手填）也可自己填 `CLAUDE.md §0-2/§12-15` + `cp cluster_config.yaml.example cluster_config.yaml` + 改 `ACTIVE_GOAL.json` status→active；改完 CLAUDE 跑 `bash scripts/sync_agents_md.sh`。

### 0.1 在新项目里开启对话（部署关键）

> `native-templates/{claude-native,codex-native}` 是**原始架构备份**，**不要**在里面跑实验。先用 `install.sh` 装到一个独立的新项目目录，再在那里开对话。**一个研究课题 = 一个项目目录**；同课题内的多个实验用 `exp_id`（`runs/<exp_id>` / `outputs/<exp_id>`）区分，不是每个实验开新项目。

**Claude 驱动**（零额外配置）：

```bash
cd /path/to/your/project   # install 出来的目录
claude                     # 在项目根开 Claude Code
```

Claude Code 自动读项目根的 `.claude/settings.json`（hooks，含 `CLAUDE_PROJECT_DIR` 自动注入 + `CLAUDE_CODE_FORK_SUBAGENT=1`）与 `CLAUDE.md`。**首次会提示"信任本文件夹的 hooks"，确认一次**——之后 SessionStart 自动跑 `session_status` + `research_bootstrap`（开局/compact/resume 从磁盘重建上下文）。然后段A `/research-interview`→`/research-synthesize`→`/sota-inventory`→`/grill`→`/configure-project`→`/benchmark-roadmap`→`/reproduce-baselines`→`/goal-prompt`；段B `/pursue`(自主) 或 `/goal-prompt`(逐轮)。

**Codex 驱动**：

```bash
cd /path/to/your/project
codex                      # codex 自动读 AGENTS.md + .codex/config.toml 的 hooks
```

Codex 以项目根 `AGENTS.md` 为权威指令；hooks 在 `.codex/hooks.json`。**开局把 `RUN_PROMPT.codex.md` 整段粘进首条消息**（含开局复述、硬约束、hook 兜底）。skill 用 `$skill-name`（`.agents/skills/`）。

> 两壳可在**同一项目**共存：例如 Claude 跑迭代、Codex/agy 作为 tri-review 的独立 reviewer（B/C 路），互不冲突——这正是 tri-review 三方并行的来源。

---

## 1. 安装后的项目结构

```text
<project_root>/
├── CLAUDE.md                         ← Claude 壳指令 + lwcr 工作流（§0-2 + §12-15 需要您填）
├── AGENTS.md                         ← Codex 壳指令（由 scripts/sync_agents_md.sh 从 CLAUDE.md 生成）
├── RUN_PROMPT.codex.md               ← Codex 开局粘贴 prompt
├── agents/openai.yaml                ← Codex 包元数据（instruction_file / skills_dir / subagents_dir）
├── README.auto-research.md  ← 本文档副本
├── ARCHITECTURE.md                   ← lwcr 框架架构说明 + enforcement coverage map
├── cluster_config.yaml.example       ← Slurm 配置模板（hard_limits + preferences 拆段）
├── cluster_config.yaml               ← 您从 example 复制并填的实际配置（首次安装时不存在）
├── goals/iteration-goal-template.md  ← /goal command 模板
├── docs/
│   ├── 00_active_goal.md             ← 意图备忘 + ## last_result_summary + ## next_focus_<date>
│   ├── 01_literature_review.md       ← 综述（FRESH 覆写 / CONTINUATION append Follow-up review）
│   ├── 02_sota_model_inventory.md    ← 验证过的 SOTA 表
│   ├── 03_benchmark_roadmap.md       ← benchmark contract + paths
│   ├── 04_experiment_iterations.md   ← ITER 历史
│   ├── 05_todo.md                    ← TODO
│   ├── 06_results_log.md             ← 实验结果
│   ├── 07_tri_review.md              ← 三方评审记录
│   ├── 08_pivot_decisions.md         ← pivot 决策 + retrospective 记录
│   ├── 09_decisions_log.md           ← abandoned routes + cousin lists
│   ├── 10_findings.md                ← Research/Engineering 发现（会话恢复必读）
│   ├── 11_master_plan.md             ← 用户导航总图：当前模式/阶段/为何先做/已接受与待讨论
│   ├── 12_publication_strategy.md    ← 投稿/会议/期刊定位、核心贡献、claim 边界
│   ├── 13_pipeline_blueprint.md      ← 流程化 pipeline DAG、IO、QC、失败恢复
│   ├── 14_validation_matrix.md       ← 下游任务、泛化、随机化 SOTA 验证矩阵
│   ├── 15_evidence_register.md       ← 智能归档：指标/讨论/决策/外部输出证据簿
│   ├── 16_artifact_registry.md       ← 脚本/训练结果/软件输出/外部工具产物 registry
│   ├── 17_parallel_workspace.md      ← 并行方向 / optional git worktree matrix
│   ├── 18_runtime_playbook.md        ← 换驱动、迁移、Baobab srun、compact恢复
│   ├── 19_evaluator_contract.md      ← 评估器/指标/split/claim 可比性合约
│   ├── 20_baseline_reproduction.md   ← SOTA/基线复现中央账本
│   ├── 21_code_review_log.md         ← 真实训练前代码审查记录
│   ├── 22_upgrade_log.md             ← 框架升级与兼容修复记录
│   ├── 23_review_board.md            ← 评审板独立会诊审计日志
│   ├── 24_sprint_pursue_ledger.md    ← 分层推进与证据短跑台账
│   └── inputs/                       ← 外部 deep research 报告 drop 区
├── ACTIVE_GOAL.json                  ← 监督式自主 goal 合约（/pursue 用；填后 status:draft→active）
├── scripts/                          ← 可靠性脚本 + hooks（见 §6.5）
│   ├── validate_goal.py / check_data.py / repair_advisor.py / iter_ledger.py / job_watch.sh
│   └── hooks/  session_status / research_bootstrap / wiki_reindex / guard_paths / submit_guard / iter_record_nudge / stage_flow_nudge / loop_ledger
├── refs/                             ← 文献归档 pdfs/repos/supp/dossiers + archive_source.sh
├── wiki/                             ← 可检索 wiki ideas/notes/INDEX + wiki.sh
├── pipelines/                        ← pipeline 定义与执行入口（pipeline_id 命名空间）
├── data/raw|interim|processed/        ← 数据层级，默认不覆盖 raw
├── runs/                             ← 训练/评估 run 包，按 exp_id/run_id 隔离
├── software_outputs/                  ← 其他软件/外部工具输出，按 tool/task/run_id 隔离
├── external_runs/                     ← 外部平台或手工运行记录
├── manuscript/ reports/ logs/         ← 投稿材料、报告、日志
├── worktrees/                         ← optional git worktree 并行代码隔离区（/workspace-matrix）
├── PROJECT_STRUCTURE.md               ← 当前目录契约摘要
├── .claude/                          ← Claude 壳
│   ├── skills/      (37 个 skills，见 §3)
│   ├── agents/      (6 个 agents，见 §4)
│   └── settings.json (hooks: SessionStart[startup|resume|clear|compact]+SubagentStart+Pre/PostToolUse+Stop+PreCompact, env fork)
├── .codex/                           ← Codex 壳
│   ├── config.toml  (multi_agent / max_threads / max_depth)
│   ├── hooks.json   (镜像 .claude/settings.json 的 hooks)
│   ├── skills/      (37 个 codex skill mirror，兼容不同 loader)
│   └── agents/      (4 个 codex 原生 subagent shell)
├── .agents/                          ← Codex skills/agents 入口（真实目录，非 symlink）
│   ├── skills/     (37 个短描述 codex/cross-agent skills，由 build_codex_skills.py 从 .claude/skills 生成，零漂移)
│   └── agents/     (codex 用 subagents)
├── CLAUDE.md.example                  ← 每次 install 落下的最新 CLAUDE 模板（供 diff，不覆盖你的 CLAUDE.md）
├── secrets.env                        ← 检索 API key（chmod600+gitignore，随框架走；见 README.md 与 secrets.env.example）
└── outputs/ sbatch/ ...             ← legacy 输出目录；新结果优先按 docs/16 进入 runs/ 或 software_outputs/
```

---

## 2. 三条主流程

### 段 A · 实验前，人类掌舵（不 autopilot）

```text
/research-interview ──► 外部 deep research ──► /research-synthesize
                                                       │
                                                       ▼
                                              /sota-inventory   (filter粗筛→subagent下载深读→失败源汇报)
                                                       │
                                                       ▼
                                              /grill            (读完论文/代码后两段式深聊：Phase1 共创思路 + Phase2 对抗钉死)
                                                       │
                                                       ▼
                                              /configure-project (AI 据澄清+探测集群/conda/提交模式 填配置，人闸)
                                                       │
                                                       ▼
                                              /benchmark-roadmap (先草拟3-5 paths→与你定稿)
                                                       │
                                                       ▼
                                              /reproduce-baselines (写代码前本地复现SOTA核实地基；hook闸：未复现不进/goal)
                                                       │
                                                       ▼
                                              /goal-prompt EXP-X-NNN: ...
```

每一步看输出后再决定下一步（研究讨论步建议在 plan 模式下跑）。`/grill` 既共创深挖思路又对抗钉死技术细节；`/benchmark-roadmap` 必须先草拟 3-5 条 paths，再与您讨论风险偏好后定稿；`/reproduce-baselines` 是进 /goal 迭代前的 hook 闸（未复现或未显式 waive 不放行）。

### 段 B · `/goal` 内自动衔接

```text
[advisory] /retrospective (若 trigger)
      ▼
读 docs/05+06+09
      ▼
Subagent fan-out → Orthogonality declaration (Track A batch)
      ▼
/implement → /code-review-gate (BLOCKED 不提交)
      ▼
/smart-sbatch (Phase 1 policy guard → Phase 2 optimization)
      ▼
sbatch submit
      ├─ run-and-evaluate ──► /result-log → /note-gate → /tri-review → /pivot
      └─ submit-and-handoff  ──► While-waiting Scout plan (advisory)
                                       ▼
                              (job 完成后另开 goal)
                                       ▼
                              /result-log → /note-gate → /tri-review → /pivot
                                                              ▼
                                              若 pivot=abandon → /decisions-log
                                                              ▼
                                              严格超越 SOTA → /generalization
```

---

### 段 C · 已有强方案/完整思路后的投稿与流程化推进

```text
/master-plan
      ├─ 投稿验证线：/publication-plan → /sota-randomized → /generalization → /note-gate
      └─ 流程执行线：/pipeline-blueprint → /artifact-registry → /note-gate
```

段 C 不以“随机探索一个更好模型”为默认，而是围绕既定思路做**贡献拆解、验证矩阵、pipeline DAG、产物管理与投稿证据闭环**。适合两类场景：一是已经有超越 SOTA 的候选模型，需要定位目标期刊/会议、定义核心贡献、补齐 downstream/reliability/ablation；二是已有 raw data 或生信/计算流程，需要把分析步骤、输入输出、QC 与外部软件产物流程化。

---

## 3. 37 个 Skills 速查（完整设计见各 skill 的 SKILL.md）

> 每个 skill 的 `description` 开头带**阶段序号标签**（A0/A1…A5 / B0…B6 / C0…C4 / Ph8 / `*`=任意时刻），输入 `/` 时菜单一眼看出阶段与顺序。下表「Tag」列即该标签。

| Tag | Skill | 用途 | 关键输出 |
|---|---|---|---|
| **A0** | `/ingest-existing` | **冷导入**外部半成品研究：subagent 系统梳理 code/结果/笔记/数据/refs/手稿 → 汇报 → 共定目标+模式 → **目录规整 + 回填 docs**（人闸） | docs/00-11 + refs/ + 目录契约 |
| **A1** | `/research-interview` | 访谈 → deep research prompt（**FRESH/CONTINUATION 自动识别**） | docs/inputs/ + docs/00 |
| **A2** | `/research-synthesize` | 合并 deep research 报告（FRESH 覆写 / CONTINUATION append） | docs/01 |
| **A3** | `/sota-inventory` | filter 粗筛 → subagent 先下载后深读全文 → 验证 paper/GitHub/weights/datasets（lit_search 扩候选） | docs/02 + refs/ |
| **A3.5** | `/grill` | 读完论文/代码后**两段式深聊**：Phase1 共创深挖思路本身（steelman+假设空间）+ Phase2 对抗拷问钉死细节（grill-me+devils_advocate+反谄媚） | docs/00 |
| **A3.5+** | `/council` | **对抗式多 agent 辩论**（重大/有争议方向）：三方 CLI 逐轮交叉反驳(Proponent/Opponent/Referee)+你裁判，烧 GPU 前辩穿（opt-in；复用 tri-review CLI 管线，区别于其实验后独立发散审） | docs/00 ## council |
| **A3.6** | `/review-board` | **独立评审会诊**（对任意争议、方案、文档）：三方 CLI 独立盲审，不依赖 exp_id，也不直接触发 pivot，评审结果写入 docs/23 | docs/23 |
| **A3.7** | `/configure-project` | 人闸·AI 据澄清上下文 + 探测集群/conda/**提交模式** 填 CLAUDE §0-2/§12-15 + cluster_config + ACTIVE_GOAL（diff→确认才写），重生成 AGENTS；挪集群/换方向可重调 | CLAUDE/AGENTS/cluster_config/ACTIVE_GOAL |
| **A4** | `/benchmark-roadmap` | benchmark contract + 3-5 paths + Track A/B 晋升规则 + evaluator contract | docs/03 + docs/19 |
| **B0** | `/reproduce-baselines` | 写代码前本地复现 SOTA，核实指标算法/数据集是否纯 raw（hook 闸：未复现不进 /goal） | refs/dossiers + docs/20 + docs/19 + docs/10 |
| **A5** | `/goal-prompt` | 生成可粘贴 `/goal` command（retrospective trigger / orthogonality / scout / chain） | inline `/goal` |
| **B1.2** | `/evidence-sprint` | **单点证据短跑**：1-2步快速收集单点证据或诊断问题，不走 validate_goal.py 校验，直接对账登记并写入台账 | docs/24 + docs/10/15 |
| **B1.3** | `/capability-pursue` | **原创能力组件有界推进**：2-5轮原创组件有界开发，目标是交付 prototype/limitation，可提议 promote_to_claim 并经人闸升级为 `/pursue` | docs/24 + docs/15 |
| **B1** | `/implement` | path→可跑训练/评估代码 + 自审 + code-review-gate + check_data 数据闸 + sanity smoke | configs/ scripts/experiments/ docs/21 |
| **B1.5** | `/code-review-gate` | 实现后、真实训练前 read-only 审 label/metric/split/evaluator/output/runtime；BLOCKED 不提交 | docs/21 + docs/19 |
| **B2** | `/smart-sbatch` | Phase 1 policy guard（orthogonality 二校）+ Phase 2 优化（本地模式只做显存sanity） | sbatch / 决策理由 |
| **B3** | `/result-log` | semantic success + metrics + **multi-doc 联动 docs/06+04+05+00** | docs/06 + 联动 |
| **B3.5** | `/exp-log` | 每实验写 docs/experiments/<id>.md + build_atlas 生成按方法族分类的 ATLAS 总览 | docs/experiments/ |
| **B4** | `/tri-review` | Claude/Codex/Antigravity 三外部 CLI 并行评审（quorum 3/2-DEGRADED/<2-inconclusive） | docs/07 |
| **B5** | `/pivot` | 消费 tri-review → 单一决策 | docs/08 |
| **B6** | `/decisions-log` | abandon route 时记录 cousin list + re-entry criteria | docs/09 |
| **Ph8** | `/generalization` | 严格超越 SOTA 后八维评估 | docs/06 + report |
| **C0** | `/master-plan` | 建立/更新用户可读总图：当前模式、阶段、为什么先做、已接受/待讨论/下一步 | docs/11 |
| **C1** | `/publication-plan` | 已有强方案后的投稿定位、贡献拆解、claim 边界、验证矩阵 | docs/12 + docs/14 |
| **C2** | `/pipeline-blueprint` | 已有 raw data / 生信或软件分析流程的 DAG、IO、QC、失败恢复 | docs/13 + pipelines/ |
| **C3** | `/sota-randomized` | 对 SOTA 做随机初始化/小样本重训/多 seed 公平比较 | configs/sota_randomized + docs/14 |
| **C4** | `/artifact-registry` | 规范脚本、训练结果、外部软件输出、run bundle 与目录契约 | docs/16 + PROJECT_STRUCTURE |
| **`*`** | `/workspace-matrix` | 多方向同时改共享代码时，创建/维护 optional git branch/worktree matrix；人闸，最多3线，不自动 merge/commit | docs/17 + worktrees/ |
| **`*`** | `/pursue` | 监督式自主驱动：读 ACTIVE_GOAL.json 多轮迭代，续/停由 validate_goal.py 裁决（非自评） | 串起 B1–B5 |
| **`*`** | `/note-add` | 任意时刻捕获 paper/idea/note/metric/decision；通常由 note-gate 路由决定后调用（Evidence ID 由 `scripts/next_evidence_id.py` 统一分配防撞号） | refs/ wiki/ docs/05+15 |
| **`*`** | `/note-gate` | 智能归档门控：判断指标、讨论结论、用户偏好、失败原因、外部输出是否必须落盘 | docs/15 + docs/11/docs/05/06/10 |
| **`*`** | `/revise-goal` | 人闸修订 ACTIVE_GOAL.json：提议 diff→tri-review 复核可比性→你确认才落盘 | ACTIVE_GOAL.json |
| **`*`** | `/reframe` | 战略重定向（假设错/新路径/阶段重排序）；carry-forward 保留结论，重排阶段，人闸 | docs/03+00+09 + wiki |
| **`*`** | `/route-reset` | 同项目内重新开线、重跑 Stage A、或 A/B→C；重写 docs/11 pipeline map，carry-forward/park/abandon | docs/11 + docs/00/03/12/13/09 |
| **`*`** | `/framework-upgrade` | v3→v4 或 v4 minor 兼容升级；保留研究内容，更新 skills/docs/hooks/scripts | docs/22 |
| **`*`** | `/spike` | 插隔离 side 实验（SPIKE-*）：记录但不进主线晋升/不污染轨迹/永不 claim；好了 promote | docs/experiments/SPIKE-* |
| **`*`** | `/retrospective` | 周期 advisory 审视，找 marginal tuning / skipped signal / 可复活 route | docs/08 ## Retrospective |

---


## 4. 6 个 Subagents

`.claude/agents/`：

- `literature-claim-extractor` —— 并行抽取多份 deep research 报告 claim
- `sota-source-verifier` —— 并行验证 paper / GitHub / weights 链接
- `code-plan-reviewer` —— read-only sbatch 前代码 / config / metric / split 审阅
- `experiment-implementer` —— scoped write，每个 subagent 只写自己 exp_id 的 config/sbatch/notes
- `project-cartographer` —— read-only 冷导入/目录清理侦察，梳理 code/results/notes/data/refs/manuscript，不泄漏 secrets，不直接改文件
- `source-artifact-archivist` —— scoped write，仅写 `refs/` 下某一个 paper/model slug，归档 PDF/repo/supp/dossier 并返回失败 manifest

**硬规则**：read-only subagent 不得 Edit/Write；写入型 subagent 必须有独立 file scope；主 agent 负责 merge；不要让 subagent 再 spawn subagent。

`/goal-prompt` 会把 subagent fan-out plan 写进生成的 `/goal` command。

---

## 4.5 自动化 hooks + 可靠性脚本

**可靠性脚本（`scripts/`，agent 无关，可手动跑）**：
- `context_pack.py` — **确定性上下文重建（B1）**：`--purpose iterate|tri-review|pivot|plan`，从磁盘 lossless 重建"续跑简报"（goal/结果趋势/最新 ITER+pivot/abandoned/findings/tracker/ideas，按字符预算+缺块标记+next_files 指针）。`/pursue` 每轮开局、压缩/续跑后**先跑它**当唯一权威背景——治"自主迭代丢上下文"病根。
- `validate_goal.py` — 确定性 goal 闸门（success/progress/not_yet/failed_run + 反调参硬闸 + 两层锚点）。`/pursue` 每轮不可跳。
- `check_data.py` — 训练前数据泄漏硬闸（split ID 重叠 / 时间穿越 / schema / target，exit3 阻断）。
- `job_watch.sh` — Slurm 作业对账（不假设成功）；本地模式用 STATUS sentinel 代替。
- `repair_advisor.py` — 失败日志分类 → 有界修复计划。
- `iter_ledger.py` — 迭代对账：扫 reports/runs vs docs/04+05+06+STATUS + 链路闭合（最近 result 是否 tri-review/pivot）+ **幽灵 run 检测**（STATUS=RUNNING 但无存活进程/squeue 作业 → stale_signal，按 failed_run 处理）。手动 `python3 scripts/iter_ledger.py` 自查。
- `sota_seed_matrix.py` — 生成随机初始化 SOTA 小样本复训矩阵（sample fraction × seed × metric × dataset），供 `/sota-randomized` 使用。
- `note_gate.py` — 对一段讨论/结果做可复现归档分类建议，帮助 `/note-gate` 决定写入 docs/15、docs/11、docs/05/06/10。
- `artifact_registry.py` — 初始化/审计标准目录、创建 run bundle/external tool bundle，维护 docs/16 与 `PROJECT_STRUCTURE.md`。
- `research_flow_guard.py` — 阶段顺序守卫：防止 `/sota-inventory` 后跳过 `/grill`/`/configure-project` 直奔 roadmap/goal。
- `sota_failure_report.py` — 聚合 PDF/repo/weights/supp 下载/验证失败，形成“请主人手动补全”清单。
- `workspace_matrix.py` — optional git/worktree 并行隔离助手（人闸、最多 3 条，不自动提交/合并）。
- `context_pack.py` — 确定性上下文重建：按 exp_id 语义排序取最新结果/迭代/pivot + 磁盘 STATUS 对账。被 research_bootstrap.sh / /pursue 调用。
- `sync_agents_md.sh` — 从 CLAUDE.md 确定性生成 AGENTS.md（双壳零漂移）。

**Hooks（Claude 壳 `.claude/settings.json` / Codex 壳 `.codex/hooks.json` 镜像同一批脚本；python3 解析 stdin 不依赖 jq）**：
| 事件 | 脚本 | 作用 |
|---|---|---|
| SessionStart[startup\|resume\|compact] | `session_status.sh` | 打印项目快照（ACTIVE_GOAL/开放 runs/findings/待整合队列） |
| SessionStart[startup\|resume\|compact] | `research_bootstrap.sh` | 从磁盘重注入 context_pack + 操作纪律（治 compact/resume 丢上下文、目标漂移） |
| SubagentStart | `research_bootstrap.sh` | 每个 subagent 启动注入同样上下文 + 纪律（配合 `CLAUDE_CODE_FORK_SUBAGENT=1`） |
| PostToolUse(Write\|Edit) | `wiki_reindex.sh` | 写 wiki/ideas\|notes 时刷新 INDEX |
| PostToolUse(Write\|Edit) | `iter_record_nudge.sh` | 写 reports/<id>.json 时催 /result-log+note-gate+exp-log；**写 ACTIVE_GOAL.json 时提醒"移动球门应走 /revise-goal"** |
| PostToolUse(Write\|Edit) | `stage_flow_nudge.sh` | 写 docs/02/03/ACTIVE_GOAL 后给出阶段顺序提醒；写 docs/02 后附 SOTA source failure report |
| Stop | `loop_ledger.sh` | 每轮结束跑 iter_ledger，记录对账 + 链路闭合 + 幽灵 run advisory；**+ master-plan 过期提醒**（非阻断） |
| **PreCompact[manual\|auto]** | `precompact_flush.sh` | **压缩前**提醒：讨论结论/偏好/进度先 /note-gate 落盘（聊天压缩后丢，docs 才留得住） |
| PreToolUse(Bash) | `guard_paths.sh` | 拦截破坏性 rm（含长选项）/ 覆盖 ACTIVE_GOAL.json |
| PreToolUse(Bash) | `submit_guard.sh` | 无 Slurm 时 deny sbatch/srun（自动适配集群）；重跑已 COMPLETED run 时 ask；**baobab 登录节点未经 srun 跑重计算时 ask** |

> 两层保障：**驱动层**=skill 编排 + validate_goal 确定性闸（正常路径强制顺序）；**兜底层**=hooks（漏了就提醒/拦截）。**hook 只能提醒/拦截，不能执行 skill**。全景见 `ARCHITECTURE.md` 的 *Enforcement coverage map*。

---

## 5. 启动姿势

### 5.0 冷导入半成品研究（IMPORT 模式）
```text
/ingest-existing /path/to/old_project
# Step0 浅扫旧材料分6区(code/结果/笔记/数据/refs/手稿)
# Step1 subagent 并行系统梳理 → 每个只回结构化摘要(做了什么/结论/为什么/缺口)
# Step2 合成"前序工作摘要"汇报你(架构×结果矩阵 + 失败教训 + 缺口风险)
# Step3 与你共定研究目标 + 工作流模式(Discovery/Publication/Pipeline) + carry-forward
# Step4 人闸回填 docs/00-11 + refs + ACTIVE_GOAL(draft)；Step4.5 目录规整(对齐契约,大文件不搬)
# 旧主张默认未核实 → 交接 /grill 或 /council 辩穿 → /sota-inventory+/reproduce-baselines 重核
```

### 5.1 新项目（FRESH 模式）

```text
/research-interview
# 9 题访谈，产出 deep research prompt（全景 7 节）
# 您去 ChatGPT/Perplexity/Perplexity Deep Research 跑 2-3 个 platform
# 报告放 docs/inputs/deep_research_*_<YYYYMMDD>.md

/research-synthesize
# 合并报告，写 docs/01_literature_review.md

/sota-inventory
# WebFetch 严格验证 + filter 粗筛 + subagent 下载深读 + 失败源汇报，写 docs/02 + refs/

/grill
# 读完论文/代码后两段式深聊：Phase1 共创深挖思路 + Phase2 对抗钉死技术细节（写 docs/00 澄清合约）

# [可选] /council   ← 该方向基础关键/有争议时：三方 CLI 逐轮交叉反驳 + 你裁判，辩穿再烧 GPU

/configure-project
# AI 据澄清上下文 + 探测集群/conda/提交模式，填 CLAUDE §0-2/§12-15 + cluster_config + ACTIVE_GOAL（diff→确认才写），重生成 AGENTS

/benchmark-roadmap
# 草 3-5 paths，与您对齐风险偏好，写 docs/03

/reproduce-baselines
# 写代码前本地复现 1-2 个 SOTA，核实指标算法/数据集是否纯 raw（hook 闸：未复现不进 /goal）

/goal-prompt EXP-A-001: Track A screen Path 1 CRF head, sample_fraction=0.05
# 复制生成的 /goal command 运行
```

### 5.2 接续已有项目（CONTINUATION 模式）

```text
/research-interview
# 自动检测：CLAUDE.md 已定制 + docs/06 非空 + findings.md 存在
#         → 自动进 CONTINUATION mode
# Step 0.5 inline 输出项目快照（scope/active data/最近 5 ITER/TODO/pivot/abandoned routes）让您确认
# Step 1 聚焦 5 题（触发信号 / specific Qs / 新假设 / anti-scope / depth）
# Step 2 不覆盖 docs/00，只 append `## next_focus_<date>` 段
# Step 3 生成 FOCUSED deep research prompt（~200字context + 1-3 specific Qs）
```

或显式强制聚焦方向：

```text
/research-interview continue: <focus area>
```

回来跑 deep research 后：

```text
/research-synthesize
# 自动检测 docs/00 next_focus 段 → CONTINUATION mode
# claim ledger 额外标 addresses_q / delta_from_docs01 / touches_abandoned
# conflict matrix 额外标 Blocks_q (vs aux)
# 综述 append `## Follow-up review <date>` 到 docs/01（不覆盖原综述）
```

### 5.3 跑实验循环（B 段）

```text
/goal-prompt EXP-B-007: Track B scale-up CRF head with full data, expected 36h
# 生成包含以下要素的 /goal command：
# - Retrospective trigger check
# - Orthogonality declaration（若是 Track A batch）
# - /smart-sbatch Phase 1 policy guard + Phase 2 optimization
# - run-and-evaluate 或 submit-and-handoff 模式
# - While-waiting Scout plan（若 submit-and-handoff）
# - /result-log multi-doc 联动 → /tri-review → /pivot
# - Skill invocation chain 表（显式 8 步顺序）

# 然后粘贴 /goal command 运行
```

### 5.4 周期性回溯

满足任一触发条件就跑：

- 自上次 retrospective ≥ 5 completed iterations
- 同一路线连续 3 次 gap 缩减 < 0.01
- Track B scale-up 失败 2 次
- 连续 2 次 /pivot = tune
- 您自己怀疑兜圈子

```text
/retrospective
# 读 docs/03~09 全量，inline 输出：
# - Are we doing marginal tuning? yes/no/partially + 证据
# - Gap trajectory + 缩减半衰期估计
# - Repeated failure pattern
# - Early signal we skipped
# - Abandoned route worth reconsidering?
# - Recommendation（continue/pivot/revisit/literature/ablation/escalate）
# 写入 docs/08 ## Retrospective <date> 段（不动 docs/03/06/09）
```

或聚焦：

```text
/retrospective check whether Path 2 is marginal
```

### 5.5 Phase 8 泛化（严格超越 SOTA 后）

```text
/generalization
# 八维评估：cross-distribution（species/domain/time）/ OOD / robustness（noise/adv/corruption）
#         / secondary metrics / cost / ablation / failure analysis / multi-seed paired t-test
```

---

## 6. 关键约束（HARD）

### 6.1 架构优先于调参

- gap ≥ 0.05 时**不接受**"只是参数没调好"。优先怀疑架构假设。
- gap < 0.02 才把系统化调参视为合理。
- 严格超越：higher-is-better 必须 `observed > SOTA`，等号不算。

### 6.2 Track A orthogonality 两层校验

每个 Track A batch 候选必须声明 `major_axis` + `mechanism_delta`：

**Hard fail**（阻止 sbatch）：

- 所有候选只改 `lr / batch_size / dropout / seed / scheduler / warmup`。
- ≥ 2 候选的 mechanism_delta 实质相同。
- 候选无法解释 why structural。

**Soft warn**（允许，但顶部标 `⚠️ FOCUSED ARCH BATCH on <axis>`）：

- ≥ 2 候选共享同一 major_axis，但 mechanism_delta 不同（如 CRF/HMM/Transformer decoder 都是 head_arch 但 mechanism 不同）。

校验两道闸：`/goal-prompt` 生成阶段 + `/smart-sbatch` Phase 1。

### 6.3 Scout / Retrospective advisory boundary

Scout 和 Retrospective 的所有输出都是 **advisory only**。**不可**：

- overwrite `docs/03_benchmark_roadmap.md`
- cancel / kill / modify any running sbatch job
- override 进行中的 Track B promotion
- replace user-approved technical path
- 直接 write `docs/09_decisions_log.md`（只有 /pivot abandon route 才写）

任何 major change 必须走 `/tri-review → /pivot → 用户可见确认`。

### 6.4 Claim policy

| Profile | 用途 | 能 claim SOTA? |
|---|---|---|
| smoke | pipeline 验证 | **永远不能** |
| screen | Track A 架构筛查 | **永远不能** |
| full | 主 benchmark 训练 | 可作为 claim 候选 |
| scale | 大资源 / ablation / pretraining | 可作为强证据 |

Claim 前必须 inline 走完 Comparability 6 维 + Data contract 8 项。任一 ❌ → 阻止 claim。

### 6.5 写文档边界

| 文件 | 谁可以写 | 谁不能写 |
|---|---|---|
| `docs/00_active_goal.md` | /research-interview, /result-log (last_result_summary 块) | 其他 skill |
| `docs/01_literature_review.md` | /research-synthesize | 其他 skill |
| `docs/02_sota_model_inventory.md` | /sota-inventory | 其他 skill |
| `docs/03_benchmark_roadmap.md` | /benchmark-roadmap | **/retrospective 绝不写** |
| `docs/04_experiment_iterations.md` | /result-log, /goal-prompt | 其他 skill |
| `docs/05_todo.md` | /result-log, /goal-prompt | 其他 skill |
| `docs/06_results_log.md` | /result-log | 其他 skill |
| `docs/07_tri_review.md` | /tri-review | 其他 skill |
| `docs/08_pivot_decisions.md` | /pivot, /retrospective | 其他 skill |
| `docs/09_decisions_log.md` | **仅 /decisions-log（由 /pivot abandon route 触发）** | 所有其他 skill 包括 /result-log |

---

## 7. cluster_config.yaml 怎么填

复制 `cluster_config.yaml.example` 到 `cluster_config.yaml`，按两段填：

```yaml
# 1. HARD LIMITS — /smart-sbatch Phase 1 强制
hard_limits:
  max_concurrent_jobs: 8
  max_array_size: 16
  min_vram_gb_default: 20
  require_checkpoint_for_shared_over_12h: true
  require_unique_output_dir: true
  require_track_a_orthogonality: true
  orthogonality_policy:
    hard_fail_when: [...]
    soft_warn_when: [...]
    allowed_major_axis: [head_arch, backbone, objective, ...]
  forbid_claim_from_profiles: [smoke, screen]

# 2. PREFERENCES — /smart-sbatch Phase 2 优化（违反不会阻止）
preferences:
  prefer_private: true
  shared_when_private_wait_gt_job_time: true
  maintenance_buffer_seconds: 3600
```

Phase 1 检查 hard_limits（任一 ❌ 阻止 sbatch），Phase 2 才用 preferences 决定 private vs shared。

`partitions:` 段填您 cluster 的实际 partition / GPU 节点清单。

---

## 8. Tri-review CLI policy

`/tri-review` **不使用 subagent** 作为 reviewer。直接并行调用外部 CLI：

| Reviewer | Source | stdin | 备注 |
|---|---|---|---|
| A | Claude CLI | true | `cat prompt | claude -p ...` |
| B | Codex CLI | true | `codex exec --sandbox read-only --skip-git-repo-check - < prompt`（codex≥0.135 已无 `--ask-for-approval`） |
| C | **Antigravity CLI**（替代 Perplexity） | true | `bash .claude/skills/tri-review/scripts/reviewer_c_antigravity.sh prompt`（设 `ANTIGRAVITY_CLI` 用真 CLI，否则用官方 `agy -p`；无 cursor-agent 兜底） |

三方收到**相同** full-scope prompt，都必须审阅：fairness/comparability / semantic success / leakage/reproducibility / architecture / Track A/B decision / next SOTA step。

失败策略：

- 任一 reviewer 失败重试 1 次。
- 2/3 成功 → `DEGRADED_REVIEW`，confidence 上限 Medium。
- < 2 成功 → review inconclusive，**不可**进入 /pivot 视为审阅完成。
- Host（在 Claude Code 跑 skill 的 Claude）是 aggregator，**不**作为第 4 个 reviewer。

---

## 9. 常见问题（FAQ）

### Q1: 我是新项目，但 `/research-interview` 进了 CONTINUATION 模式？

原因：项目根有 `findings.md` / `docs/00_active_goal.md` 已被改 / `docs/06` 非空之一。

解决：用 `$ARGUMENTS` 强制：

```text
/research-interview fresh: <您的方向>
```

### Q2: 我接续项目时不想自动读所有 docs，太慢？

接续模式 Step 0 读 11 个文件并不慢（每个 < 5KB）。如果您希望跳过项目快照，直接说"跳过快照"即可，但**不推荐**——快照确认是 anti-drift 关键。

### Q3: `/smart-sbatch` 一直 Phase 1 FAIL 怎么办？

读 Phase 1 表格的 `Action if fail` 列，按提示修：

- VRAM 不足 → 改 `--constraint` 加 GPU 类型筛选 或 改 partition
- output_dir 冲突 → 改 exp_id
- Track A orthogonality HARD_FAIL → 重设计候选，要么改 mechanism_delta 要么改 major_axis
- walltime 超 partition limit → 改 partition 或加 checkpoint 逻辑

### Q4: `/retrospective` 输出建议 pivot，但我不同意？

Retrospective 是 advisory only。您可以：

- 在 docs/08 该 Retrospective 段下加一句"User override: <理由>" 并继续原路径
- 或主动跑 `/tri-review` 让三方就 retrospective 给的 advisory 评一次
- 或显式说"defer retrospective"，但记得记入 docs/05_todo.md 防止遗忘

### Q5: deep research 跑回来的报告写在哪？

```text
docs/inputs/deep_research_chatgpt_<YYYYMMDD>.md
docs/inputs/deep_research_perplexity_<YYYYMMDD>.md
docs/inputs/deep_research_claude_<YYYYMMDD>.md
```

文件名含 platform 标签，方便 synthesize 区分。同一天可以加后缀 `_a`/`_b`。

### Q6: 我能不能不跑 `/goal-prompt` 直接写 /goal command？

技术上可以，但**不推荐**。`/goal-prompt` 会自动注入：

- Retrospective trigger check
- Orthogonality declaration（若是 Track A batch）
- Comparability + data contract 8 项 checklist
- /smart-sbatch Phase 1/2 调用
- /result-log multi-doc 联动要求
- /note-gate + /tri-review + /pivot 顺序
- Skill invocation chain 表
- Advisory boundary

手写 /goal 很容易漏其中某项，最常见的漏点是 multi-doc 联动 → 实验完成后 docs/04/05/00 没更新 → 下次会话 Claude 不知道上次结果。

### Q7: 我项目已经在用其他 framework（如 labloop），能共存吗？

可以。lwcr skill 名（`research-interview` / `goal-prompt` / `smart-sbatch` / `tri-review` / `pivot` / ...）与 labloop 系列（`labloop-*` + `/goal*` commands）**命名零冲突**。共存方式：

- lwcr 装到 `.claude/skills/` 主目录
- labloop 留在原位（或从备份恢复）

两套并存不会互相干扰，您可以同时使用两边的 slash command。

---

## 10. 项目特定填充（关键，安装后必做）

打开 `CLAUDE.md` 找到下列段填您项目的内容：

| 段 | 填什么 |
|---|---|
| §0 项目特定 Scope | task / active scope / out-of-scope / 必读文档清单 |
| §1 Active Data | 训练/验证数据集名称 + 路径 + 大小 + provenance |
| §2 Historical Reference / Baseline | 历史最佳指标 + reports 路径 + baseline 状态 |
| §13 项目特定 Compute Rules | partition 偏好 + 日志/checkpoint/reports 目录约定 |
| §14 项目特定 Canonical Training Template | sbatch 主入口 + underlying trainer 命令 |
| §15 项目特定 Canonical Evaluation Template | eval 主入口 + 配套 by-type / by-length 命令 |

参考填充示例：`examples/CLAUDE.md.rna-example`（RNA Benchmark 项目 ncRNA-only scope）。

---

## 11. 反馈与扩展

发现 skill prompt 有遗漏 / hard rule 不够严 / 触发条件不够灵敏？两种处理：

- **现场调整**：直接 Edit `.claude/skills/<name>/SKILL.md`，下次会话生效。
- **结构性改动**：写 issue 笔记到 `docs/05_todo.md` 顶部"framework hardening"段，下次 retrospective 时一起评估。

新增 skill 的建议路径：

1. 先在 `docs/05_todo.md` 记动机 + 输入输出 + 触发条件
2. 跑一次 `/retrospective` 看是否已有 skill 能覆盖
3. 若确实缺，先用 prompt-only 方式（即不创建 skill 文件，每次手动 prompt Claude）跑 2-3 次验证价值
4. 验证有用后再正式建 `.claude/skills/<name>/SKILL.md`

---

## Changelog

### v4.1 · 2026-06-13 · 升级/重开线/代码审前闸 + evaluator/baseline 账本

- **框架升级 skill**：新增 `/framework-upgrade`，用于 v3→v4 或 v4 minor 兼容迁移，保留 docs/refs/wiki/ACTIVE_GOAL/cluster_config/secrets，写 `docs/22_upgrade_log.md`。
- **同项目重开线**：新增 `/route-reset`，用于当前路线不可行、需要重跑 Stage A、或 A/B→C 切换；重写 `docs/11` pipeline，carry-forward/park/abandon 不丢证据。
- **代码审前闸**：新增 `/code-review-gate` + `docs/21_code_review_log.md`，训练/eval/config/job 改动后、真实训练前必须审 label/metric/split/evaluator/output/runtime，BLOCKED 不提交。
- **评估与复现中央账本**：新增 `docs/19_evaluator_contract.md` 与 `docs/20_baseline_reproduction.md`，`/benchmark-roadmap`、`/reproduce-baselines`、`/result-log`、`/code-review-gate` 共同维护。
- **git 定位升级**：运行不强制 git，但建议版本化框架/轻量记录；data/runs/outputs/logs/software_outputs/secrets/checkpoints 永不入库。

### v4.0 · 2026-06-11 · 阶段闸 + SOTA失败源 + workspace矩阵 + Codex兼容

- **Codex skill 兼容**：`build_codex_skills.py` 生成短 YAML-safe description 到 `.agents/skills` 与 `.codex/skills`，安装后 `validate_codex_skills.py` 自检。
- **阶段顺序守卫**：新增 `research_flow_guard.py` + `stage_flow_nudge.sh`，防止 `/sota-inventory` 后跳过 `/grill`、`/configure-project`、baseline reproduction。
- **失败源闭环**：新增 `sota_failure_report.py`，自动汇报 PDF/repo/weights/supp 下载失败，让用户手动补到 `refs/` 后重读。
- **并行 workspace**：新增 `/workspace-matrix`、`docs/17_parallel_workspace.md`、`scripts/workspace_matrix.py`，默认 exp_id 隔离；共享代码冲突时可选 git worktree，最多 3 条，人闸且不自动 commit/merge。
- **运行迁移手册**：新增 `docs/18_runtime_playbook.md`，说明中途换 Claude/Codex、补装壳、迁移服务器、Baobab srun 规则与 compact 恢复。
- **新增 subagents**：`project-cartographer` 与 `source-artifact-archivist`，分别用于半成品目录侦察与 `refs/` 源材料归档，减少主上下文消耗。

### v3.8 · 2026-06-11 · 对抗 council + 冷导入 ingest + 文档/导航大修
- **对抗式多 agent 辩论**：新增 `/council`（A3.5+）——三方 CLI 逐轮交叉反驳（Proponent/Opponent/Referee 立场）+ 用户裁判，在烧 GPU 前辩穿基础。复用 tri-review 的 CLI 管线，但与其"实验后独立发散审"互补对立（段A 对抗 vs 段B 发散）。
- **冷导入半成品研究**：新增 `/ingest-existing`（A0）——subagent 并行系统梳理外部旧 code/结果/笔记/数据/refs/手稿 → 汇报 → 共定目标+工作流模式 → **目录规整（对齐契约，大文件不搬）+ 回填 docs**（人闸）。区别于 research-interview CONTINUATION。
- **文档/导航大修**：README.auto 顶部新增"导航·我该用哪个(对号入座表)" + "docs/wiki/refs 三种记忆区别" + "文件夹速查"；CLAUDE §0 加工作流模式字段、configure-project 初始化 docs/11、CLAUDE §3 加归档纪律；exp-log 增"为什么做(motivated_by + Why/Motivation)"。
- 当时 **30 skills**（双壳 30/30，codex desc 预算 5258<8000）。

### v3.7 · 2026-06-10 · 中文优先 + 段C投稿/pipeline + 智能归档 + 目录契约

- **语言策略**：deep research prompt/report 默认中文；检索关键词、模型名、paper 名、指标名保留英文，降低中文讨论成本，同时不牺牲英文语料检索质量。
- **段 C 工作流**：为“已经有强候选/完整思路”的研究新增投稿验证线与流程化 pipeline 线，不再强迫所有项目都走开放式架构搜索。
- **随机化 SOTA 小样本验证**：新增 `/sota-randomized` 和 `scripts/sota_seed_matrix.py`，把“只拿 SOTA 现成预测结果比较”升级为“重新随机初始化、小样本训练、多 seed 预测”的公平比较。
- **智能归档**：新增 `/note-gate`、`docs/15_evidence_register.md` 与 `scripts/note_gate.py`，让指标、讨论结论、用户选择、失败原因和外部软件输出都能进入持久文档。
- **用户导航总图**：新增 `/master-plan` 与 `docs/11_master_plan.md`，用于记录当前处于哪条线、为什么先做这一步、已接受 A/D 还是继续讨论 B/C。
- **目录契约**：新增 `/artifact-registry`、`docs/16_artifact_registry.md`、`PROJECT_STRUCTURE.md` 与标准目录 `pipelines/ data/ runs/ software_outputs/ external_runs/ manuscript/ reports/ logs/`。


### v3.5 · 2026-06-03 · 监督式自主 + 可靠性闭环 + 迭代纪律 hooks

- **B1 上下文重建（治"自主迭代丢上下文"病根）**：`scripts/context_pack.py --purpose iterate|tri-review|pivot|plan` 从磁盘确定性重建续跑简报；`/pursue` 每轮开局先跑当唯一权威背景，`/tri-review` Step1 用它生成 Standard Research Pack 基底。
- **段B 自主**：新增 `/pursue`（读 ACTIVE_GOAL.json 自主多轮，续/停由 `validate_goal.py` 确定性裁决，非 agent 自评；failed_run 必停）、`/implement`（path→可跑代码+自审+check_data+sanity smoke）、`/note-add`（任意时刻捕获 paper/idea/note）、`/revise-goal`（人闸改目标）。skills 12→**16**。
- **确定性闸 + 4 纪律**：`validate_goal.py` 反调参硬闸（gap≥0.05 禁调参换架构轴）+ 两层锚点（screen 比 screen_anchor 永不 claim / full 比 sota_benchmark）+ portfolio 并行 ≤max_parallel_directions + goal 防漂移（revise-goal）。
- **可靠性脚本**：`check_data.py`（泄漏硬闸）/ `job_watch.sh`（作业对账）/ `repair_advisor.py`（有界修复）/ `iter_ledger.py`（迭代对账+链路闭合）。
- **归档/记忆**：`refs/`（pdfs/repos/dossiers + archive_source.sh）+ `wiki/`（ideas/notes/INDEX + wiki.sh）+ `docs/10_findings.md`。
- **6 个 Claude Code hooks**：SessionStart 快照 / PostToolUse wiki 索引 + reports 记录催促 / Stop 迭代对账 / PreToolUse 路径守卫 + 提交规则守卫（无 Slurm deny sbatch、并行防覆盖）。见 §4.5 + ARCHITECTURE *Enforcement coverage map*。
- **tri-review reviewer C**：Perplexity → Antigravity（`agy`，四级后端解析，需 Google OAuth）。codex 0.135 命令修正。
- **skill 阶段标签**：当时 skill 的 description 加 `A1…/B1…/Ph8/*` 序号，`/` 菜单一眼定位；v3.7 已扩展到 28 个 skill，并加入 C0–C4。
- **bug 修复（审计）**：validate_goal 缺锚点不再误判 success、screen 不回退比 SOTA、反调参 gap 始终对 SOTA；guard_paths 补长选项；docs 模板补 hook 依赖结构；清残留论文机制 + 悬空 `/compare`；submit-and-stop→submit-and-handoff 统一。

### v3.4.1+ · 2026-05-16 · RNA-enhanced

吸收 labloop 设计亮点 + 用户反馈精修：

- 新增 `/retrospective` skill（5 触发条件、cross-iteration advisory、绝不写 docs/03/09）
- `/research-interview` + `/research-synthesize` 加 FRESH/CONTINUATION 双模式
- `/smart-sbatch` 拆 Phase 1 policy guard / Phase 2 optimization
- Track A orthogonality 改为 major_axis + mechanism_delta 两层规则（hard fail / soft warn）
- `/goal-prompt` 注入 Scout plan + Advisory boundary + Skill invocation chain 表
- `/result-log` 强制 multi-doc 联动（06+04+05+00），明确不写 09
- `cluster_config.yaml.example` 拆 `hard_limits` / `preferences` / `orthogonality_policy`

### v3.4.1（上游）

- `install.sh`: backup then replace package-owned paths
- Claude reviewer template use piped stdin context with `claude -p`
- Codex read-only reviewer template add `--ask-for-approval never`
- `/pivot` 显式声明 "never parallelized" 和 "host is aggregator, not a 4th reviewer"
- `/goal-prompt` 显式负责追加 `docs/04_experiment_iterations.md` 的 ITER entry
- `cluster_config.yaml.example`: Reviewer A=Claude 改用 stdin（避免 ARG_MAX）
- `/tri-review` 加 ARG_MAX 鲁棒性说明
- `.claude/agents/` 四个 agent 定义扩到具体 checklist

---
