# Auto-Research Portable v4.0

可迁移的 Claude + Codex + Antigravity 研究推进框架。安装到项目目录后，`docs/`、`refs/`、`wiki/`、`runs/`、`reports/`、`software_outputs/` 与 `ACTIVE_GOAL.json` 是项目真相源；对话窗口只是执行界面。

完整说明、**决策导航（我该用哪个 skill）**、文件夹速查、`docs/wiki/refs` 区别见 `README.auto-research.md` 顶部“导航”节。本文只保留安装、流程和升级要点。

> **三种“记忆”一句话**：`docs/`=结构化流程状态（唯一真相源，每 doc 专属 skill 可写） · `wiki/`=自由可搜的灵感/便签（note-add） · `refs/`=论文 PDF/补充材料/代码/权重链接与 dossier（一手证据）。不知道在哪一步 → 先读 `docs/11_master_plan.md`。

## 安装

```bash
./install.sh --driver both   /path/to/project
./install.sh --driver claude /path/to/project
./install.sh --driver codex  /path/to/project
```

`install.sh` 可重复运行：
- 刷新框架脚本、壳配置、README、ARCHITECTURE。
- 保留研究进度：`docs/`、`goals/`、`refs/`、`wiki/`、`CLAUDE.md`、`ACTIVE_GOAL.json`、`cluster_config.yaml`、`.mcp.json`、`secrets.env`。
- 支持中途补装壳：codex-only 项目可补 Claude，Claude 项目可补 Codex。
- 只刷新已知框架脚本，不会删除你自己放在 `scripts/` 的项目脚本。
- 所有被覆盖的文件会先备份为 `.backup-<timestamp>`。

API key 放在 `secrets.env`。该文件已进入 `.gitignore`，并由安装脚本在已有项目中保留。公开分享/返还包默认不要包含真实 `secrets.env`。

## 三条主流程

```text
段 A: 新方向探索（导入半成品研究则先 /ingest-existing）
[A0 冷导入] /ingest-existing
  → /research-interview
  → external deep research
  → /research-synthesize
  → /sota-inventory              (filter → subagent 归档 PDF/repo/supp → 深读 → 失败源清单)
  → /grill
    → [可选] /council             (重大/有争议方向：多 agent 对抗式辩论 + 你裁判)
    → [可选] /review-board        (对任意争议、方案、文档做三方独立盲审)
  → /configure-project
  → /benchmark-roadmap
  → /sota-randomized 或 /reproduce-baselines 建公平 screen_anchor
  → /goal-prompt

段 B: 实验迭代
/goal, /pursue, /evidence-sprint 或 /capability-pursue
  → /implement
  → /smart-sbatch
  → train/evaluate 或 submit-and-handoff
  → /result-log
  → /note-gate
  → /exp-log
  → /tri-review                  (3/2/1 reviewer 都有降级路径)
  → /pivot                       (先记录所有 reviewer 结论，再按顺序组最多 3 条并行方向)
  → [必要时] /workspace-matrix    (多方向同时改共享代码时启用 git worktree)

段 C: 已有强方案后的投稿验证或流程化 pipeline
/master-plan
  ├─ 投稿验证: /publication-plan → /sota-randomized → /generalization → /note-gate
  └─ 流程执行: /pipeline-blueprint → /artifact-registry → stage execution → /note-gate
```

## v4.0 覆盖的核心问题

| 需求 | 对应设计 |
|---|---|
| Codex skill description 不兼容 / 上下文爆炸 | `build_codex_skills.py` 生成短 YAML-safe frontmatter 到 `.agents/skills` 与 `.codex/skills`；`validate_codex_skills.py` 安装后自检 |
| `/sota-inventory` 后不应直接跳 benchmark | `research_flow_guard.py` + `stage_flow_nudge.sh` 提醒正常顺序：`/sota-inventory → /grill → /configure-project → /benchmark-roadmap` |
| paper/PDF/repo/supp 下载失败要显式汇报 | `sota_failure_report.py` 聚合 `refs/sources.md` 与 dossier 失败项，要求手动补到 `refs/pdfs/`、`refs/supp/` 或 `refs/repos/` |
| 只推进一个方向效率低 | `max_parallel_directions=3`，`/pivot` cohort 化，默认 `exp_id` 隔离；共享代码冲突时 `/workspace-matrix` 启用 git worktree |
| 小样本 vs 大样本 SOTA 不公平 | `screen_anchor` 与 `/sota-randomized`：在同样小样本协议下随机初始化重训 SOTA baseline，screen 阶段只比 screen_anchor，不拿 published full-data SOTA 做 claim |
| 讨论/指标不落盘 | `/note-gate`、`docs/15_evidence_register.md`、`iter_record_nudge`、`precompact_flush` 与 `/exp-log` 分别管讨论、指标、压缩前保存和单实验记录 |
| 中途换 agent / 换机器 / Baobab 提交规则 | `docs/18_runtime_playbook.md`、`/configure-project`、`submit_guard.sh`；Baobab 登录节点重计算默认必须经 `srun`/`sbatch` |
| 半成品研究导入、目录混乱 | `/ingest-existing` + `project-cartographer` subagent + `/artifact-registry` 清理到 `PROJECT_STRUCTURE.md`/`docs/16` 契约 |

## 34 个 Skills

段 A：`ingest-existing`、`research-interview`、`research-synthesize`、`sota-inventory`、`grill`、`council`、`review-board`、`configure-project`、`benchmark-roadmap`、`reproduce-baselines`、`goal-prompt`

段 B：`implement`、`smart-sbatch`、`evidence-sprint`、`capability-pursue`、`result-log`、`exp-log`、`tri-review`、`pivot`、`decisions-log`、`retrospective`、`generalization`

段 C：`master-plan`、`publication-plan`、`pipeline-blueprint`、`sota-randomized`、`artifact-registry`

随时可用：`pursue`、`note-gate`、`note-add` Fair screen、`revise-goal`、`reframe`、`spike`、`workspace-matrix`

Claude 用 `/skill-name`；Codex 用 `$skill-name`。Antigravity/其它 loader 优先读 `.agents/skills`，Codex 兼容镜像在 `.codex/skills`。

## 关键目录

```text
docs/11_master_plan.md          用户导航总图
docs/12_publication_strategy.md 投稿定位和核心贡献
docs/13_pipeline_blueprint.md   pipeline DAG、IO、QC
docs/14_validation_matrix.md    下游任务、随机化 SOTA、统计检验
docs/15_evidence_register.md    指标、讨论、偏好、外部输出归档索引
docs/16_artifact_registry.md    目录与产物契约
docs/17_parallel_workspace.md   并行方向 / optional git worktree matrix
docs/18_runtime_playbook.md     换驱动、迁移、Baobab srun、compact 恢复
docs/19_evaluator_contract.md   评估器/指标/split/claim 可比性合约
docs/20_baseline_reproduction.md   baseline/SOTA reproduction central ledger
docs/21_code_review_log.md      pre-submit code-review gate log
docs/22_upgrade_log.md          framework upgrade log
docs/23_review_board.md         评审板独立会诊审计日志
docs/24_sprint_pursue_ledger.md 分层推进与证据短跑台账
refs/pdfs|repos|supp|dossiers/  paper、repo、补充材料、指标/数据 dossier
PROJECT_STRUCTURE.md            根目录速查
pipelines/                      pipeline stage 脚本
configs/                        run/pipeline 配置
runs/                           完整训练状态
reports/                        指标摘要 JSON
outputs/<id>/STATUS             run 状态
software_outputs/<tool>/<id>/   外部软件原始输出和 provenance
worktrees/                      optional git worktree 并行代码隔离区
data/raw|interim|processed/     数据分层
```

## Hooks

- SessionStart/SubagentStart：打印项目快照，并从磁盘重建 context pack。
- PreToolUse(Bash)：拦截破坏性删除、未分配资源的 Baobab 重计算、重复覆盖 completed run。
- PostToolUse(Write/Edit/apply_patch)：写 `reports/*.json` 后提醒 `/result-log → /note-gate → /exp-log`；写 `docs/02/03` 或 `ACTIVE_GOAL.json` 后提醒阶段顺序和 SOTA 失败源。
- PreCompact：提醒把讨论结论先 `/note-gate`/`/master-plan` 落盘。
- Stop：运行 ledger 对账，提醒漏记 result、tri-review、pivot。

## 使用入口

Claude：

```bash
cd /path/to/project
claude
```

Codex：

```bash
cd /path/to/project
codex
```

Codex 开局把 `RUN_PROMPT.codex.md` 粘进首条消息；项目权威规则来自 `AGENTS.md`，由 `CLAUDE.md` 生成。
