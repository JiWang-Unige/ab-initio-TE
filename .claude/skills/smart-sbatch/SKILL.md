---
name: smart-sbatch
description: "B2· Smart sbatch submission planner + Teodoro Slurm router. Synthesizes (a) cluster_config.yaml rules — partition priorities, VRAM filter (default 20GB+ for large-model training), time limits, forbid_claim_from_profiles, (b) live sinfo / squeue / scontrol show reservation output to detect current GPU availability, queue depth, and maintenance windows, (c) static inventory fallback at references/cluster_inventory.md (gpu017-gpu050 nodes, RTX 3080 default-exclude list), and (d) job characteristics (expected wall-clock, GPU count, min/efficient GPUs, min VRAM, checkpointability). Routes CPU-only jobs to private-teodoro-gpu with 0 GPUs (fast path), and for GPU jobs chooses between private-teodoro-gpu (free, 7-day) vs shared-gpu (12-hour limit, sometimes faster start) by estimated completion time, adjusting --time when maintenance reservations cut into the 7-day budget. Use before any sbatch submission, when planning multi-job parallel submission, when reviewing an existing sbatch script, or when private partition is queued and the user wants to know if shared would be faster."
argument-hint: "<job description: expected wall-clock, GPU count, optional constraints, optional 'review existing sbatch <path>'>"
---

# Smart Sbatch  (Teodoro Slurm routing + lwcr integration)

为 `$ARGUMENTS` 推荐 sbatch 头**或**审查现有 sbatch 脚本。**目标**: 既高效用 private 配额, 也综合考虑 shared 何时更快, 同时强制 Phase 1 政策守门 + Track A 正交性 + path 唯一性。

## 提交模式分支（`submission.mode`）—— 在所有 partition 决策之前判定

先读 `cluster_config.yaml` 的 `submission.mode`（由 `/configure-project` 探测设定）——它决定 sbatch **在哪、怎么提交**，必须先分流再进 §0 起的 partition 逻辑：

- **`on_cluster`**（默认，本机即集群）：本机直接 `sinfo/squeue/sbatch`，照常走 §0 起全部步骤。
- **`local_direct`**（本机无 Slurm）：**短路**——不跑 `sinfo/squeue/scontrol/sacct`、不生成 sbatch header、不提交。只输出显存/walltime 的 sanity 检查 + 提示"本地 run-and-evaluate 直接 `python` 跑（CLAUDE §12）；训练脚本结束写 `echo COMPLETED > outputs/<exp>/STATUS`"。`submit_guard` 也会 deny 本机 sbatch。
- **`remote_ssh`**（本地→远程集群）：所有 live 诊断与提交都经 `ssh`，且**用 `cluster_config.yaml submission` 段已写好的命令模板渲染执行，不要即兴拼**（字段 `/configure-project` 填好；缺字段先回 `/configure-project` 补）：
  1. **同步代码**：渲染执行 `sync_cmd`（`rsync … {ssh_host}:{remote_project_dir}/`）。
  2. **live 诊断**：§0「必要的运行时检查命令」整段前缀 `ssh {ssh_host} '…'`（远程跑 sinfo/squeue/scontrol/sacct）。
  3. **提交**：渲染 `submit_cmd`（`ssh {ssh_host} 'cd {remote_project_dir} && sbatch {script}'`），把返回的 Slurm `job_id` 写入 `outputs/<exp>/JOBID`。
  4. **对账**：`scripts/job_watch.sh` 已据 `submission.mode` 自动走 `ssh {ssh_host} sacct/squeue`（无需手改）；`iter_ledger.py` 幽灵 run 检测同理走远程 squeue。
  5. **取回**：训练结束渲染 `fetch_cmd`（`rsync {ssh_host}:…/outputs/ ./outputs/`），并**按需补拉 `reports/`**（`fetch_cmd` 默认只拉 outputs/），再进 `/result-log`。

  Phase 1/2 的 partition 决策逻辑**不变**，只是数据来源与提交通道换成远程。

## 0. CPU-only fast path（partition 决策内最先判定）

如果 `$ARGUMENTS` 是 **CPU-only** 命令（无 GPU 算子, 例如数据预处理 / FASTA 索引 / eval 后处理 / pyplot 报表）, 直接走 fast path:

```text
partition = private-teodoro-gpu
gpus      = 0   (省略 --gres=gpu / --gpus)
walltime  = min(estimated_runtime, partition_time_limit, time_until_maintenance - safety_buffer, 7d)
```

**理由**: 其他 CPU partition 通常时长受限（≤ 1-12h）, 而 `private-teodoro-gpu` 可跑 7 天且免费, 用 0 GPU 不占其他用户的 GPU 配额。

CPU-only fast path 不进入 Phase 2 "private vs shared 决策树"——直接跳到 §"输出格式" 给出 sbatch header。但 Phase 1 policy guard 仍要全跑（path 唯一性、maintenance 窗口、time 上限）。

模板见 `references/sbatch_templates.md` §1 "CPU-only private job"。

## 两种调用模式

| Mode | 触发 | 行为 |
|---|---|---|
| **Mode A · Generate new** (default) | `$ARGUMENTS` 描述了 job 但没有现成 sbatch | Phase 1 guard + Phase 2 optimization + 输出新 sbatch header |
| **Mode B · Review existing** | `$ARGUMENTS` 含 "review existing sbatch <path>" 或者 `/goal-prompt` 的 `## 运行说明` 段声明 "本轮 sbatch 已存在" | Phase 1 guard only, 检查现有脚本是否过 hard_limits + 现实场景（live sinfo/squeue）下是否仍合理；**不**重生成 header；输出 verdict + 可选改建议 |

Mode B 典型场景：用户已有 `scripts/training_rmt/run_X.sbatch`, 不想重写, 只要确认提交安全且当前集群状态没让默认配置变 suboptimal。

## 两段式执行（HARD 不可跳过）

`/smart-sbatch` 显式分两段, **不允许把 Phase 1 与 Phase 2 混合输出**：

- **Phase 1 · Policy guard**: 输出**硬规则表**, 列出 cluster_config.yaml 的 `hard_limits` 段每条规则的 Pass/Fail + Evidence。任一 ❌ → **不生成 sbatch command** (Mode A) / **标记 BLOCKED** (Mode B), 给出修复建议后停止。
- **Phase 2 · Optimization**: 仅 Mode A 才执行。比较 private vs shared、queue wait、cost、maintenance buffer, 输出最终推荐 + 新 sbatch header。Mode B 跳过 Phase 2; 但**可选**给一段 "现有配置 vs 当前 live 状态下的最优配置 diff"作 advisory（不强制 user 改）。

这一拆分的目的是防止 LLM 把硬约束（GPU 上限、checkpoint 契约、orthogonality）"灵活解释"成"建议"。

## 核心规则(来自用户工作流 + Teodoro 集群特性)

1. **优先 private-teodoro-gpu** — 7 天 + 免费
2. **但检测排队时间** — 若 private 排队 > 任务时长,且任务能放进 12h,改用 shared
3. **GPU 数量充足度** — 区分 `min_gpus`（能跑） vs `efficient_min_gpus`（跑得有意义）
   - 若 private 当前只剩 1-2 GPU 但任务需要 `efficient_min_gpus ≥ 4`, 用 shared 12h × 多次 resubmit(只对短任务/可 checkpoint)
   - 若 private GPUs ≥ `efficient_min_gpus` 且队列短, 仍走 private
4. **长任务例外** — 真要 3-4 天的任务,等 private 是合理的(shared 怎么 resubmit 也撑不下)。non-checkpointable multi-day 必走 private。
5. **维护窗口** — 若 private 有维护 reservation 在 X 天后,而你默认 `--time=7-00:00:00` 会被拒。检测并降到 `min(7d, reservation_start - now - buffer)`
6. **VRAM 过滤** — 大模型训练 GPU 必须 ≥20GB(default,可在 cluster_config.yaml 改);**默认排除 RTX 3080**: `gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043` (来自真实 inventory, 见 `references/cluster_inventory.md`)。
7. **不要硬编码 7 天** — 即使 partition 允许 7 天, `--time` 也必须 `= min(estimated_needed_time, partition_time_limit, time_until_maintenance - safety_buffer)`。
8. **CPU-only 命令走 §0 fast path**, 不进入 1-7 的 GPU 决策。

## 必要的运行时检查命令

按顺序运行（详尽版本见 `references/diagnostics_commands.md`）:

```bash
# 1. 当前可分配 GPU —— 看 Slurm 分配(gres vs gresused)，不是物理占用！(见 decision_policy §0)
#    free_gpus = gres - gresused。alloc 节点即便 nvidia-smi 空闲也=0 可用。
sinfo -p private-teodoro-gpu,shared-gpu -N -O "nodehost,statecompact,gres:30,gresused:30"

# 2. 当前队列(预估等待) + 扣除排在你前面的 pending 作业
squeue -h -p private-teodoro-gpu -o "%i|%T|%L|%S|%j|%N|%b"
squeue -h -p shared-gpu -o "%i|%T|%L|%S|%j|%N|%b" | head -50
squeue -t PD -p private-teodoro-gpu,shared-gpu -o "%.10i %.8u %.4C %b %r" --sort=i 2>/dev/null  # pending ahead
squeue --start -p private-teodoro-gpu,shared-gpu 2>/dev/null   # 最佳：调度器自己的启动时间预估

# 3. 维护 reservation
scontrol show reservation 2>&1 | grep -iE "Nodes=.*gpu03[45]|partition=private-teodoro|state=ACTIVE|InActive" \
  || echo "(no active reservation on private)"

# 4. 最近 24h 你的 partition 的 throughput(粗略估等待)
sacct -X -u $USER --format=Partition,State,Submit,Start,Elapsed,NodeList -S now-24hours | head
```

如果存在 `cluster_config.yaml` 在项目根目录,优先读它。否则用 `references/cluster_inventory.md` 静态清单 + 嵌入的默认规则。

`cluster_config.yaml` 4 段：
- `hard_limits`（Phase 1 强制）
- `preferences`（Phase 2 优化）
- `partitions`（节点 + GPU type + VRAM inventory；用于 Phase 1 VRAM filter + Phase 2 routing）
- `path_conventions`（项目级输出路径; 替代 lwcr 默认的 `outputs/<exp_id>/`; 新项目从 lwcr 模板迁移时 customize 这段）

详细 schema 见 `references/cluster_config_schema.md`。

Phase 1 看 `hard_limits` + `partitions.vram_gb` + `path_conventions`；Phase 2 看 `preferences` + `partitions` 全部 + live cluster state。

---

## Phase 1 · Policy guard（hard pass/fail）

**必须先输出一张表**，按 cluster_config.yaml `hard_limits` 段逐条 check：

```markdown
## Phase 1 · Policy guard

| Rule | Pass? | Evidence | Action if fail |
|---|---|---|---|
| GPU count <= max_concurrent_jobs | ✅/❌ | <current running + queued = N, limit = M> | 减少 batch / 等待已有 job 结束 |
| Array size <= max_array_size | ✅/❌ | <requested array_size = K, limit = L> | 拆批提交 |
| GPU VRAM >= min_vram_gb_default (or job-specific override) | ✅/❌ | <picked GPU vram = X GB, requirement = Y GB> | 改 partition / 加 --constraint |
| Walltime <= partition time_limit_hours | ✅/❌ | <expected = H h, partition limit = P h> | 拆任务 / 改 partition / 启用 checkpoint |
| If shared && walltime > 12h: checkpoint+resubmit declared? | ✅/❌/N/A | <script supports USR1@600 + load_from_checkpoint = yes/no> | 加 checkpoint 逻辑或换 partition |
| output_dir unique across concurrent jobs | ✅/❌ | <`<output_root>/<exp_id>/` exists empty? clash check; output_root from cluster_config.yaml.path_conventions, fallback `outputs/`>| 改 exp_id / 清空 |
| checkpoint path unique | ✅/❌ | <path under `<output_root>/<exp_id>/`> | 改 exp_id |
| Disk/quota preflight | ✅/❌ | <`df -h .` 与（集群）`du`/quota：runs/outputs/logs 剩余空间 vs 预估 checkpoint 体积×save_top_k> | 清旧 run / 降 save_top_k / 设 checkpoint 保留策略 / 换盘；不足则**不提交** |
| sbatch --output / --error path unique | ✅/❌ | <`<log_root>/<job_name>_%j.{out,err}` from path_conventions> | exp-scoped |
| Maintenance reservation does not cut uncheckpointable job | ✅/❌ | <T_maint - now = X h, expected = Y h> | 缩 --time / 等维护后 / 改 shared+checkpoint |
| Excluded nodes (default 3080) honored in --exclude / --constraint | ✅/❌ | <--exclude has gpu023..gpu043 or constraint blocks them?> | 加 --exclude= / typed --gres= |
| Track A batch orthogonality (if applicable) | ✅/❌/N/A | <见下方 Orthogonality check 表> | 修改候选 / 拆 batch / 改 axis |
| Profile not in forbid_claim_from_profiles when claim intended | ✅/❌/N/A | <profile = smoke/screen, claim flag = ?> | 升 profile / 取消 claim flag |
```

### Orthogonality check（Track A batch 专用）

如果 `$ARGUMENTS` 是 Track A parallel batch（≥ 2 个候选），必须输出下表：

```markdown
| exp_id | major_axis | mechanism_delta | why structural | not merely hyperparam? |
|---|---|---|---|---|
| EXP-A-001 | head_arch | CRF transition modeling | 在 logits 上加 transition matrix，结构性改 decoding | yes — 加了新参数张量 + 改 forward |
| EXP-A-002 | head_arch | HMM latent-state smoothing | 显式 latent state 后验 + Baum-Welch 风格 smoothing | yes — 新增 latent layer |
| EXP-A-003 | objective | contrastive auxiliary loss | 加 contrastive head + InfoNCE loss | yes — 新增 head + loss term |
```

**Hard fail** 触发条件（任一中即整批阻止，**不**生成 sbatch command）：

- 所有候选只改变 `lr / batch_size / dropout / seed / scheduler / warmup`（即 batch 实质是 hyperparameter sweep 而非架构筛查）。
- ≥ 2 候选的 `mechanism_delta` 实质相同（例如两个都是"CRF transition"只是 transition rank 不同）。
- 任一候选无法在 `why structural` 列给出"为什么是结构性变化"的解释（即写不出 mechanism_delta 的本质内容）。

**Soft warn**（允许继续，但 Phase 2 输出顶端用 `⚠️ FOCUSED ARCH BATCH` 标记）：

- ≥ 2 候选共享同一个 `major_axis`（如三个都是 head_arch: CRF / HMM / Transformer decoder），但 mechanism_delta 不同。此时允许，因为这是有价值的 *focused architecture batch*，必须在 Phase 2 输出顶部声明"这是 focused arch batch on `<axis>`，不是 hyperparameter sweep"。

判定完成后明确输出：

```markdown
**Orthogonality verdict**: PASS / HARD_FAIL / SOFT_WARN (focused arch batch on <axis>)
```

### Phase 1 失败处理

若任一 Hard rule ❌：

```markdown
## Phase 1 result: BLOCKED

- Failed rules: <list>
- Repair suggestions: <one per rule>
- DO NOT submit. Re-run /smart-sbatch after fixing.
```

**不要继续 Phase 2**。不要输出 sbatch header。不要给"sbatch command 草稿"。整段终止。

---

## Phase 2 · Optimization（只有 Phase 1 全 ✅ 才进入）

下面的"决策树 / 输出格式 / Parallel batch matrix"全部归属 Phase 2。Phase 2 的输出顶端必须明示：

```markdown
## Phase 2 · Optimization (Phase 1 passed; orthogonality verdict: <PASS|SOFT_WARN focused arch batch>)
```

### 决策树（GPU 任务用；CPU-only 已在 §0 决定）

```text
Inputs:
  expected_walltime_hours: 用户给 / 询问
  min_gpus: 用户给 / 询问 (任务能跑的下限)
  efficient_min_gpus: 用户给 / 询问 (跑得有意义的下限, 默认 1)
  min_vram_gb: 用户给 / 询问 (默认 20)
  job_can_checkpoint_resubmit: 用户给(默认 false 但问)

Step 1 — Filter
  Candidate GPUs = all GPUs with vram ≥ min_vram_gb
  默认排除: gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043 (RTX 3080)
  Ambiguous: gpu050 (RTX 5000 待确认 32GB Ada vs 16GB) — 先 sinfo 查证再决定纳入

Step 2 — Check private maintenance
  Run scontrol show reservation, parse for nodes gpu034 / gpu035
  If maintenance starts in T_maint hours:
    private_max_time_hours = max(0, T_maint - buffer/3600)
  Else:
    private_max_time_hours = 168 (7 days)

Step 3 — Check private availability (ALLOCATION-aware, see decision_policy §0)
  Run sinfo -O gres,gresused for private partition
  Available_now_private = Σ over gpu034-035 of (gres - gresused) on nodes with ≥min_vram_gb
                          AND state ∈ {idle, mix}  (skip alloc/drain/down/maint/resv)
                          # NOT nvidia-smi physical idle — a Slurm-allocated GPU is unusable.
  Queue_ahead_private = pending jobs (squeue -t PD) ahead of you that will claim GPUs first
  # Effective availability = Available_now_private - GPUs claimed by Queue_ahead_private
  # (or just trust `squeue --start` when available)

  Estimate wait_private_hours (heuristic):
    If Available_now_private >= efficient_min_gpus: wait = 0
    Else if Available_now_private >= min_gpus: 
      wait = 0 但 runtime *= (efficient_min_gpus / Available_now_private)   # scaled runtime
    Else: wait = approx remaining time of (min_gpus - Available_now_private) jobs ahead
    (rough — squeue's expected START_TIME / squeue --start is most reliable when present)

Step 4 — Branch by job length

  Case A: expected_walltime_hours <= 12 (短任务,shared 能直接放)

    A1. If Available_now_private >= efficient_min_gpus AND private_max_time_hours >= expected:
        → Recommend: private, --time = expected + buffer
        Reason: free + immediate, save shared quota

    A2. Else if wait_private_hours > expected_walltime_hours:
        → Recommend: shared
        Reason: waiting longer than running

    A3. Else (private available soon enough):
        → Recommend: private with wait
        Reason: free, wait acceptable

  Case B: 12 < expected_walltime_hours <= private_max_time_hours

    B1. If job_can_checkpoint_resubmit AND wait_private_hours > expected_walltime_hours:
        → Recommend: shared with checkpoint+resubmit chain (--time=11:50:00, --signal=B:USR1@600)
        Inline warn: "需要训练脚本支持 checkpoint resume,否则 12h 后丢进度"

    B2. Else if wait_private_hours < expected_walltime_hours / 4:
        → Recommend: private, --time = min(expected + buffer, private_max_time_hours)
        Reason: wait << job length, makes sense

    B3. Else:
        → Recommend: private, but warn long wait
        Reason: shared 不能整段跑这种长度,只能等 private

  Case C: expected_walltime_hours > private_max_time_hours

    C1. If maintenance is imminent (private_max_time < expected) AND job is non-checkpointable:
        → Block: "私有分区将在 T_maint 小时后维护,不够跑完 expected_walltime,且任务不能 checkpoint."
        Suggest: 拆分任务 / 等维护后 / 改任务支持 checkpoint 再走 shared

    C2. If maintenance is imminent AND job is checkpointable:
        → Recommend: shared with checkpoint+resubmit chain
        Reason: 私有窗口不够整段跑, shared 12h × N 段可拼接

Step 5 — Maintenance window adjustment

  Always set --time = min(requested_time, private_max_time_hours) when using private
  Always set --time ≤ 12h (推荐 11:50:00 留 checkpoint trap 时间) when using shared
  Include comment in sbatch reason
```

可选 helper（确定性 Python 评分）：

```bash
python .claude/skills/smart-sbatch/scripts/choose_partition.py \
  --task gpu \
  --expected-hours 30 \
  --checkpointable yes \
  --min-gpus 2 --efficient-min-gpus 4 \
  --required-vram-gb 40 \
  --private-available-gpus 2 \
  --shared-available-gpus 4 \
  --private-queue-hours 8 \
  --shared-queue-hours 1
```

输出 JSON 含两个 candidate 的 estimated completion 时间, 用于辅助 LLM 给出建议（**不**替代决策树本身）。

### 输出格式

```markdown
# Smart Sbatch Recommendation

## Job spec
- Task type: CPU-only / GPU
- Expected wall-clock: <h>
- min_gpus / efficient_min_gpus: <n> / <n>
- Min VRAM: <GB>
- Can checkpoint+resubmit: yes / no
- Job description: <$ARGUMENTS>

## Cluster snapshot (live)
- private-teodoro-gpu: <X> GPUs idle now, queue has <N> jobs ahead, est wait <h>
- shared-gpu (≥<VRAM>GB filter): <Y> GPUs idle now, est wait <h>
- Maintenance: <none / starts in <h>, ends <when>>

## Filter applied
- Excluded: <list of GPU types below VRAM threshold>
- Eligible nodes: <list>

## Recommendation

**Partition**: `<private-teodoro-gpu | shared-gpu>`
**--time**: `<HH:MM:SS or D-HH:MM:SS>`
**--gres**: `gpu:<n>` or `gpu:<type>:<n>`  (or omit for CPU-only)
**--constraint**: <if needed for specific GPU type>
**--exclude**: <if default 3080 exclude list applies>
**--mem**: `<GB>`
**--cpus-per-task**: `<n>`

### Sbatch header (paste into your script)

```bash
#!/usr/bin/env bash
#SBATCH --job-name=<job_name>
#SBATCH --partition=<chosen>
#SBATCH --time=<chosen>
#SBATCH --gres=gpu:<n>                                # omit for CPU-only
#SBATCH --constraint=<if-any>
#SBATCH --exclude=<if-applicable>
#SBATCH --cpus-per-task=<n>
#SBATCH --mem=<GB>G
#SBATCH --output=<log_root>/<job_name>_%j.out
#SBATCH --error=<log_root>/<job_name>_%j.err
#SBATCH --signal=B:USR1@600        # only if checkpoint+resubmit needed (shared > 12h chain)
```

(更多模板见 `references/sbatch_templates.md`: CPU-only / private long / shared checkpointable / typed GRES / exclude list)

## Reasoning

- Why <chosen partition>: <one paragraph applying the decision tree>
- Why this --time: <if reduced due to maintenance, explain>
- Why filtered out <GPU type>: <VRAM>
- Alternative not chosen: <other partition + why rejected>

## Risks / caveats

- <if shared chosen for >12h: warn about checkpoint behavior and trap setup>
- <if wait estimate is uncertain>
- <if maintenance reservation might extend>
- <if ambiguous node like gpu050 was in candidate set>

## After submission

1. `sbatch <your_script>.sbatch` to submit
2. `squeue -u $USER` to monitor
3. Once job completes, /result-log with output dir
```

### 询问用户的事(若 `$ARGUMENTS` 缺信息)

```markdown
为了推荐准确的 sbatch 配置,需要:

1. Expected wall-clock(完整训练大约多久?)
2. min_gpus(任务能跑的最少卡数?) 和 efficient_min_gpus(跑得有意义的卡数?)
3. Min VRAM(默认 20GB 排除 3080;若大模型要 ≥40GB 或 ≥80GB 请说明)
4. 训练脚本是否支持 checkpoint resume?(影响是否能用 shared 12h × 多次)
5. 是否 CPU-only(无 GPU 算子)?
```

优先用 `ask_user_input_v0` 工具收集；如果该工具不可用，就直接在聊天中提出这些问题，等待用户回答。

### 不要做的事

- 不要在没看 sinfo / squeue 的情况下推荐 partition(必须有 live 数据)
- 不要把 3080 算进候选(VRAM 不够;`gpu023,gpu024,gpu036-043` 默认排除)
- 不要忽略维护 reservation(会直接 reject)
- 不要让 --time 超过该 partition 的 TimeLimit
- 不要在 12h shared 上跑 24h 任务而不开 checkpoint
- 不要在 private 已经空闲且无维护时强推 shared "怕排队"——直接 private
- 不要硬编码 `--time=7-00:00:00` 仅因为 partition 允许 7 天 —— 必须 `min(needed, partition_limit, maintenance_buffer)`
- 不要把 CPU-only 任务路由到其他 CPU partition —— 走 §0 fast path: private + 0 GPU
- 不要在 `private_available_gpus < efficient_min_gpus` 时盲推 private "因为免费" —— 跑得慢比排队更浪费

### Parallel batch matrix（Track A 必须输出）

如果 `$ARGUMENTS` 是 Track A screen batch，不能只给一个通用 sbatch header，必须输出并行实验矩阵：

```markdown
## Parallel batch matrix

| exp_id | Track | Path | Architecture change | sample_fraction | epochs | patience | seed | config | output_dir | sbatch script |
|---|---|---|---|---:|---:|---:|---:|---|---|---|
| EXP-A-001 | A-screen | Path 1 | CRF head | 0.05 | 5 | 2 | 42 | configs/EXP-A-001.yaml | outputs/EXP-A-001 | sbatch/EXP-A-001.sbatch |
| EXP-A-002 | A-screen | Path 2 | HMM head | 0.05 | 5 | 2 | 42 | configs/EXP-A-002.yaml | outputs/EXP-A-002 | sbatch/EXP-A-002.sbatch |
```

并说明使用哪种提交方式：

#### Option A · sbatch array

适合多个配置只差 index：

```bash
sbatch --array=1-N sbatch/screen_batch.sbatch
```

#### Option B · multiple sbatch commands

适合脚本/资源不同：

```bash
sbatch sbatch/EXP-A-001.sbatch
sbatch sbatch/EXP-A-002.sbatch
sbatch sbatch/EXP-A-003.sbatch
```

硬性要求：

- 每个 exp_id 必须有独立 `output_dir`、log、checkpoint、metrics path。
- 不同候选不能写同一个 checkpoint 或 metrics 文件。
- 一次提交的 job 数不能超过集群并发限制；若不确定，保守分批提交。
- screen batch 结果只能用于晋升 Track B，不能 claim SOTA。

## Sbatch 提交协议

- 多个并行实验: 每个独立 `experiment_id`,独立 `outputs/<exp_id>/`,不共享 log / checkpoint 路径
- Job array(若多个配置仅 index 不同): `sbatch --array=1-N`
- 一次提交的 job 数 ≤ 集群并发配额,留 buffer

## Hand-off

- **Inputs from**: `$ARGUMENTS` + `cluster_config.yaml` (`hard_limits` + `preferences` + `partitions` + `path_conventions`) + live cluster state + `references/cluster_inventory.md` (静态 fallback)
- **Outputs to**:
  1. Phase 1 policy guard table (always)
  2. Orthogonality check table (if Track A batch)
  3. Phase 2 recommendation + sbatch header (only if Phase 1 ✅, Mode A)
  4. Mode B advisory diff (optional, Mode B only)
- **Refuse to output sbatch command when**: any Phase 1 rule ❌, or orthogonality HARD_FAIL.
- **Next step**: 用户 `sbatch <script>.sbatch`, 然后 `/result-log` 在训练完成后；若是 submit-and-handoff 模式，还需启动 *While-waiting Scout plan*（见 `/goal-prompt`）。

## Appendices · 子目录索引

- `references/cluster_inventory.md` — 真实节点清单 gpu017-gpu050（GPU type, count, VRAM, 默认排除列表）。`cluster_config.yaml.partitions` 缺失时的 fallback。
- `references/decision_policy.md` — Decision policy 详尽版（CPU fast path / private-vs-shared / maintenance / low private availability / checkpointing requirements）。决策树的人类可读补充。
- `references/diagnostics_commands.md` — sinfo / squeue / scontrol / sacct 命令模板与解释规则。
- `references/sbatch_templates.md` — CPU-only / private long / shared checkpointable / GPU filter / resume-friendly 5 类模板。
- `references/cluster_config_schema.md` — `cluster_config.yaml` 4 段字段说明 + 最小示例。
- `scripts/choose_partition.py` — 确定性 Python 评分器（给定 queue/window/GPU facts → JSON 推荐）。
- `examples/scenarios.md` — 6 个 worked scenarios（CPU 3 天 / GPU 3h 但 private 排队 12h / 长 checkpointable / 长 non-checkpointable / maintenance / 模糊 GPU）。
- `evals/test_cases.md` — Skill 行为校验用例（should trigger / should not trigger / expected behavior）。
