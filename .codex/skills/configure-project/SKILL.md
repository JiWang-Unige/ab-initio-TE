---
name: configure-project
description: "A4-pre· After Stage-A research has clarified the project (research-interview → synthesize → sota-inventory → grill), let the AI MATERIALIZE the persistent project contract instead of you hand-filling it at install time: fills CLAUDE.md §0-2 (scope/data/baseline) and §12-15 (comp…"
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Configure-Project: AI-materialize the project contract from clarified research

**反模式**：装完框架就让人手填 CLAUDE.md §0-2/§12-15 + cluster_config——那时诉求没理清、集群没探，填了易返工。**正解**：走完段A（research-interview→synthesize→sota-inventory→**grill**）诉求澄清、SOTA/指标/数据核实后，**让 AI 据澄清上下文 + 实时探测集群/环境来填**，人只确认 diff。

**何时**：grill 之后、benchmark-roadmap 之前调一次（把澄清后的项目定义固化进持久合约）；也可**随时重调**（`/reframe` 换方向后、挪到新集群后）。

> **建议在 plan 模式下跑本 skill**（Claude `plan` / Codex plan）：Step 1-3（读已澄清上下文 + 只读探测 sinfo/sacct/conda + 提议 diff）全是只读，正好是 plan 模式擅长的"勘查+提议+细聊"；**plan 的 `ExitPlanMode` 批准恰好等价于 Step 4 的"确认才写"人闸**，二者合一不冲突——批准后退出 plan 再用 Edit 落盘 + sync AGENTS。

## Step 1 · 收集已澄清上下文（不猜，用已落盘的事实）+ 判定工作流模式
读 `docs/00`(意图 + grill 的 `## direction_clarified_<date>`)、`docs/01`(综述)、`docs/02`(验证过的 SOTA 表)、`refs/dossiers/*`(已核实的指标实现/数据集/split)、当前 `ACTIVE_GOAL.json`/`CLAUDE.md`。**每个拟填字段都要能指到来源**（哪个 doc / 哪条 dossier），不能凭空编。

据澄清诉求**判定工作流模式**（决定走段B还是段C，并初始化导航）：方向模糊/要找超SOTA → `Discovery-Iteration`；已有强候选/超SOTA结果、目标是补证据投稿 → `Publication-Validation`；已有 raw data/固定生信流程 → `Pipeline-Execution`；拿不准就**问主人**。

## Step 2 · 实时探测计算环境（不靠假设）
```bash
# Slurm（有则集群模式，无则本地模式）
command -v sinfo && sinfo -o '%P %l %G %D' 2>/dev/null            # 分区/时限/GRES/节点数
command -v sacct && sacct --version 2>/dev/null
# conda 环境（防 base 污染：探测项目 env）
conda env list 2>/dev/null; echo "active=$CONDA_DEFAULT_ENV"
# 仓库/数据线索
ls environment.yml requirements.txt pyproject.toml 2>/dev/null
```
据返回判定 **submission.mode**（挪机器最该重配的项）：本机有 `sbatch` → `on_cluster`（§12 写真实 partition/限制 + sbatch 模板 + srun 强制）；本机无 Slurm 但能 `ssh <host>` 到有 Slurm 的集群（问主人 host/远程项目路径）→ `remote_ssh`（填 cluster_config `submission` 段的 ssh_host/remote_project_dir/sync/submit/poll）；都没有 → `local_direct`（本地 run-and-evaluate）。conda 有项目 env → 记入 §1/§12；无 → 提议建一个（不默认 base）。

## Step 3 · 生成拟填 diff（不落盘，标来源）
inline 输出每个文件的拟改动，**每项注明来源**：
```markdown
## configure-project 提议 <date>
### CLAUDE.md
- §0 **工作流模式** ← Step1 判定：<Discovery-Iteration / Publication-Validation / Pipeline-Execution>
- §0 scope ← docs/00 direction_clarified：<task / active scope / out-of-scope>
- §1 data  ← docs/02 + dossiers：<dataset/split(按染色体/物种+同源去冗余)/类分布>；conda env=<探测到的>
- §2 baseline ← sota-inventory：published SOTA=<值@出处>（comparability 待 /reproduce-baselines 核实）
- §12 compute ← sinfo 探测：partitions=<…>, 限制=<…>；§13/14 train/eval 入口=<仓库探测>
### cluster_config.yaml ← sinfo/sacct：submission.mode(on_cluster/remote_ssh/local_direct) + partitions/VRAM/time + cli_review 段
### docs/11_master_plan.md §0（初始化导航，让用户开局就能定位）
- Mode=<工作流模式>；为什么是这个模式=<一句>；当前阶段=<A/B/C>；最终产物=<SOTA模型/投稿包/pipeline>；§2 pipeline 地图 now=<第一步>
### ACTIVE_GOAL.json
- goal/primary_metric/success_criteria ← 澄清目标；sota_benchmark=<sota-inventory 值>（screen_anchor 待 benchmark-roadmap M1 建）；status: active
```
拿不准/探测不到的留 `<TODO: 问主人>`，**不编造**。

## Step 4 · 人闸落盘（确认才写）
主人确认/微调后才用 Edit 写 `CLAUDE.md`(含 §0 工作流模式) / `cluster_config.yaml` / `ACTIVE_GOAL.json` / **`docs/11_master_plan.md §0`(初始化导航：模式/阶段/最终产物/now)**；然后 **`bash scripts/sync_agents_md.sh`** 重生成 `AGENTS.md`（零漂移）。未确认 → 不写，留提议。

## 边界
- **人闸**：基础合约（CLAUDE/AGENTS/cluster_config/ACTIVE_GOAL）AI 不擅自覆盖，必须 propose→确认。
- **基于探测/已核实事实**，不猜集群配置、不编 SOTA 值。
- 不填 `screen_anchor`（benchmark-roadmap M1 建）；`sota_benchmark` 的可比性由 `/reproduce-baselines` 最终核实。
- `status` 默认提议 `active`（主人确认后），让 validate_goal 正常判定。

## Hand-off
- **Inputs from**: docs/00(+grill direction)、docs/01、docs/02、refs/dossiers、`sinfo`/`conda` 探测
- **Uses**: `scripts/sync_agents_md.sh`（落盘后重生成 AGENTS.md）
- **Outputs to**: CLAUDE.md §0-2/§12-15(含 §0 工作流模式) + AGENTS.md + cluster_config.yaml + ACTIVE_GOAL.json + **docs/11_master_plan.md §0(导航初始化)**（均经确认）
- **Next**: Discovery → `/benchmark-roadmap`；Publication/Pipeline → `/master-plan` 细化 + `/publication-plan` 或 `/pipeline-blueprint`。挪集群/换方向后可重调本 skill
