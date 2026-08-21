---
name: pursue
description: "*· Supervised-autonomy driver toward a high-level goal (e.g."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Pursue: supervised-autonomy toward a high-level goal

把"goal = 搭建好 SOTA 模型"这种**终极目标**交给系统自主推进多轮实验，**不用主人手写每个 `/goal`、不用盯每一步**——
但用一道 **agent 跳不过去的确定性失败闸门**杜绝 autoloop 那种"跑失败了却静默续跑"。

> **设计立场（为什么不是 autoloop）**：autoloop 把"成没成/要不要继续"交给 agent 自评 → 漏检失败 → 静默劣化。
> `/pursue` 的"继续/停止"由 `scripts/validate_goal.py`（确定性脚本）裁决；agent **必须运行它并服从其裁决**。

## 边界（HARD）
- 失败检测**不可**由 agent 主观判断；**必须**跑 `scripts/validate_goal.py` 并以其 `status` 为准。
- `failed_run` → **立即停止**，写 intervention 到 docs/08 + inline 通知主人，**绝不续跑下一轮**。
- **幽灵 run 也算 `failed_run`**：`STATUS=RUNNING` 但 `iter_ledger.py` 报 `stale_signal`（无存活进程 / 无 squeue 作业）→ 按 failed_run 处理，不要当作"还在跑"而傻等。
- **首次正式训练前停一次问主人（仅一次，之后全自主）**：见 Step 0.6。这是主人唯一要求的常规介入点；除红线事件外，后续轮不再就"提交训练"打断主人。
- 严格超越 SOTA / 宣布成功前必须过 `/tri-review`（且 `human_gate_before_claim=true` 时需主人确认）。
- 遵守 CLAUDE.md §7.5 advisory boundary：不擅自改 docs/03、不 kill 主人其他 job。

## Step 0 · 读 goal 合约
读 `ACTIVE_GOAL.json`（或 `$ARGUMENTS` 指定的）：`scope`(terminal/milestone)、`primary_metric`、`success_criteria`、`guardrails`、`sota_benchmark`、`max_internal_iterations`、`on_failed_run`、`validate_command`。
inline 回显：goal、成功标准、SOTA 锚点、最大内部迭代数。若 `status != active`（合约状态机：`draft → active → achieved/blocked`；`/configure-project` 填好即 `active`）或字段缺失 → 停下让主人补。

**入口阶段闸（不可跳）**：先跑 `python3 scripts/research_flow_guard.py . --format json`，若 `ok_to_goal=false`（如 evaluator_contract 未固化、baseline 未复现/waive、screen_anchor 缺失）→ **拒绝启动自主循环**，按其 `recommended_next` 先补齐段 A 缺口。这把"阶段闸"从写后 nudge 升级为入口硬前置，防止在模糊上下文上自主开跑。

并读上下文：`docs/03`（paths/gates）、`docs/05` Pending integration queue（/note-add 装填的新文献）、`docs/06`（已有结果趋势）、`docs/09`（abandoned routes，别重试）。

**重启/压缩后接管（防覆盖运行中作业，G6）**：开局先看 `context_pack` 的 tracker_block——**若本 cohort 有 exp 处于 `RUNNING`/`PENDING`**，**强制跳过 Step 1.1-1.3（不再 implement/smart-sbatch 提交），直接进 Step 1.4 作业对账**（job_watch）；对账判终态后再决定续跑。绝不在已有 RUNNING 作业上重提交（会覆盖、跑崩、浪费算力）。

## Step 0.6 · 首次正式训练前的人工确认（仅一次，之后全自主）

主人的自主偏好：**只在第一次正式跑代码前停下来问一次，其余全自主**。机制用 **goal-scoped** sentinel（**不是全局**——换 goal / `/revise-goal` / `/route-reset` / 切段 C 后，goal 签名变、sentinel 名变，新路线会**重新**问一次首训确认，不被旧 sentinel 误跳）：

```bash
SIG=$(python3 -c "import json,hashlib;g=json.load(open('ACTIVE_GOAL.json'));print(hashlib.sha1(json.dumps([g.get('success_criteria'),g.get('sota_benchmark'),g.get('scope'),g.get('primary_metric')],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12])")
SENTINEL="outputs/.first_run_approved_$SIG"
```
- 在本 goal **第一次**要提交真实训练（Step 1.3 全量/screen `sbatch`，**smoke 不算**）前，若 `$SENTINEL` **不存在**：
  - 用 `AskUserQuestion` 让主人确认三件事：①本轮 cohort 的方向 / exp_id 是否符合预期；②数据 / split / comparability 合同是否正确（inline 给出 §10 checklist 结论）；③资源 profile 是否合适。
  - 主人确认后，写 `$SENTINEL`（记确认时间 + 确认的 cohort + goal 签名），然后提交。
- `$SENTINEL` **已存在**（= 同一 goal 签名已确认过）→ 后续所有轮**不再就"提交训练"打断主人**，由 validate_goal + tri-review + pivot 自主驱动多轮。**goal 签名一变（新路线）→ 新 sentinel 不存在 → 自动重新确认一次**。
- 不受 sentinel 影响、**仍会主动停**的红线事件：`failed_run` / 幽灵 run（HALT + 通知）、`success` 且 `human_gate_before_claim=true`（claim 确认）、阻塞性 intervention（缺数据 / 权限 / comparability blocker）。

## Portfolio 模式（并行多方向，默认开）—— 治"死磕调参一个方向"

读 `ACTIVE_GOAL.max_parallel_directions`（默认 3）。每轮**不是只跑 1 个方向**，而是 fan-out **最多 N 个正交方向并行**：
- N 个候选必须通过 Track A orthogonality（major_axis/mechanism_delta 互不相同；CLAUDE §8）——**被迫并行正交架构，结构上磨不起来单点调参**。
- 并发受 `/smart-sbatch` 分配感知 + `cluster_config.hard_limits.max_concurrent_directions=3` 约束；GPU 不够则排队，不超额。
- 每个方向**独立**走 §Step 1-6（implement→smart-sbatch→job_watch→result-log→validate），互不阻塞。若多个方向需要同时改共享代码，先调用 `/workspace-matrix` 建可选 git/worktree 隔离；只改 config 则保持默认 exp_id 目录隔离。
- 全 cohort 回来后做**一次 cohort 级** `/tri-review` + `/pivot`：留赢家、砍输家、用空出的并发位补下一批正交方向。
- **单方向 `failed_run` 的隔离（不拖停健康方向）**：cohort 中某方向 OOM/崩溃/幽灵 run，只对**该方向**走 `failed_run` 处理（隔离、记 docs/08、按 on_failed_run 修或弃）；**其余健康方向照常完成并照常进 cohort 级 review**。failed 方向不阻断整 cohort，但其结果不计入晋升。

## Step 1 · 内部迭代循环（i = 1..max_internal_iterations，每轮一个 cohort）

每一轮 i：

0. **开局确定性重建上下文（B1，不靠记忆/自我总结）**：先跑
   ```bash
   python3 scripts/context_pack.py --purpose iterate > /tmp/context_pack.md
   ```
   读 `/tmp/context_pack.md` 作为本轮**唯一权威背景**——它已从磁盘 lossless 重建 goal 合约 / 最近结果趋势 / 最新 ITER+pivot / abandoned routes / findings(已否方法+已知坑) / Run tracker / 未消费 ideas（缺块标 `(absent)`，超预算给 `next_files_to_open_if_needed` 指针）。**上下文被压缩、或跨会话续跑时尤其必跑**——这是治"自主多轮丢上下文"的根因步骤，不要跳过靠记忆。需要更多细节再按 next_files 打开原文件。

1. **Plan a cohort（≤ N 个正交方向）**：
   - i=1：建 baseline/anchor + docs/03 §7.2 的前几条 path（凑够正交的 N 个）。
   - i>1：由上一轮 cohort 的 validate + `/pivot` 驱动（赢家扩样本/晋升，输家换 axis）。
   - 纳入 docs/05 Pending integration queue 新机制；规避 docs/10 已知坑。
   - **强制 orthogonality declaration**（≥2 候选时），axis 必须分散。
   - **workspace decision**：逐项声明是否改共享代码；若 cohort 中 ≥2 项会改同一共享模块，先 `/workspace-matrix`，避免 agent 在一个窗口/一份代码里互相覆盖。
   - **反调参硬约束**：若某方向 validate 返回 `tuning_allowed=false`（gap≥阈值），该方向**不许**只调 lr/bs/dropout，必须是架构轴。

2. **`/implement` + `/code-review-gate`**（代码就绪 + 去风险，不可跳）：把本轮 path 变成可跑代码 → 自审 → 独立代码审前闸（写 `docs/21_code_review_log.md`）→ `check_data.py` 数据闸门 → **sanity smoke + 有界自动 debug**。code-review-gate 或 smoke 不过不进全量。（首轮或代码已存在且未变时可快速确认跳过，但必须说明已有 `docs/21` PASS 记录。）

3. **`/smart-sbatch`**（Phase 1 policy guard + Phase 2 分配感知）。提交前读 `docs/05` Run tracker **跳过已 DONE 的 run**；提交后写一行到 Run tracker（status=RUNNING, 记 job_id）。
   - 按 `cluster_config.submission.mode`：`on_cluster` 本机直接 sbatch；`remote_ssh` 走 `/smart-sbatch` 的 remote 分支（rsync→`ssh sbatch`→记 `outputs/<exp>/JOBID`→`ssh sacct` 对账）submit-and-handoff；`local_direct` 本机直接 `python` run-and-evaluate，训练脚本自己写 `outputs/<exp>/STATUS`（见 §本机说明）。

4. **作业对账（不可跳）**——别假设跑完了：
   ```bash
   bash scripts/job_watch.sh --jobid <job_id> --status-out outputs/<exp>/STATUS --log <err.log> [--poll 60 --max-wait <sec>]
   ```
   产出 STATUS（COMPLETED/FAILED/TIMEOUT/OOM/STALE/UNKNOWN）。更新 Run tracker 状态。**幽灵 run 防线**：若 `STATUS=RUNNING` 但 `python3 scripts/iter_ledger.py` 报该 exp 的 `stale_signal`（无存活进程 / 无 squeue 作业），按 `failed_run` 处理（HALT + 通知），不要当作还在跑而续等——这正是 GB EXP-B-011 那种"启动即夭折却挂着 RUNNING"的漏洞。

5. **`/result-log`**（semantic success 8 项 + metrics + multi-doc 联动 + 提炼 `docs/10` findings）。产出 metrics JSON 路径。

6. **★ 确定性闸门（不可跳）**——按本方向 resource profile 传 `--profile`：
   ```bash
   python3 scripts/validate_goal.py --goal ACTIVE_GOAL.json \
     --metrics <本轮 metrics.json> --run-status outputs/<exp>/STATUS \
     --profile <screen|full|scale> [--challenger-sota <若有更高已验证SOTA>] \
     [--prior-screen <该候选自己的 Track-A screen 值，full/scale 时传>]
   ```
   - **两层锚点**：screen → 只比 screen_anchor、**上限 progress 永不 claim**；full/scale → 比 sota_benchmark 才可能 success。
   - **反调参**：读 `tuning_allowed`；为 `false`（gap≥阈值）则下一步**禁止 tune**，pivot 必须选架构轴。
   - **回退/可疑高（G8/G9）**：full/scale 传 `--prior-screen`，若输出 `regression=true`（scale 比自己 screen 还差）→ pivot 优先 backbone/abandon 不 scale；`suspicious_high=true`（超 sane_upper/越 sane_range，疑泄漏）→ claim 前先 `/code-review-gate` 或 `/reproduce-baselines` 复核。
   - 见 `stale_benchmark` 警告 → 提示 `/revise-goal`（人闸抬目标），不自行改 ACTIVE_GOAL。

   读 `status`：

   | status | 动作 |
   |---|---|
   | `failed_run` | **先试有界修复一次**：`python3 scripts/repair_advisor.py --log <err.log>`。`bounded=true`(oom/timeout/missing_dep/nan) → 按 patch_hint 改一处 → 回 Step 3 重提**一次**（同类失败第 2 次则升级）。`bounded=false`(cuda_device/disk/data_error/unknown) → **立即 STOP + 写 docs/08 HALT + 通知主人**，不瞎试。 |
   | `not_yet` / `progress` | 收齐 cohort 后**一次** `/tri-review`（带 Standard Research Pack）→ `/pivot`（受 tuning_allowed 约束）→ 规划下一 cohort，i++。 |
   | `success` | （仅 full/scale）进 Step 2 宣布前复核。 |

7. 每轮留 durable trace（docs/04 ITER + docs/06 + docs/10 findings + Run tracker + validate 输出存档）。**并强制 `/note-gate`** 对本轮指标、赢家假设、被否方向、pivot 给出的并行 cohort 候选、用户可见下一步做归档判定：
   - 必记内容写 `docs/15_evidence_register.md`；
   - 思路类 route 到 `/note-add` → `wiki/ideas|notes`；
   - 改变用户导航时同步 `/master-plan` → `docs/11_master_plan.md`。
   这一步治"wiki 全空 / 指标没入档 / 用户等长作业后丢失思路"。

## Step 2 · 成功复核（仅当 validate=success）
1. `/tri-review`：让三方确认不是 leakage / comparability 假象（success 闸门已查 degenerate，但 tri-review 复核 fairness）。
2. tri-review 通过 + `human_gate_before_claim=true` → inline 向主人报告"goal 达成 + 证据"，**等主人确认**后才标 ACTIVE_GOAL `status=achieved`。
3. `scope=terminal` 且严格超 SOTA → 提示可进 `/generalization`（Phase 8）。
4. `scope=milestone` → 提示更新 ACTIVE_GOAL 到下一里程碑或终极目标。

## Step 3 · 循环终止条件
- `failed_run`（任意轮）→ HALT + 通知（最高优先）。
- `success` + 复核通过 → 达成。
- 达到 `max_internal_iterations` 仍未 success → 停，inline 总结进展轨迹 + 建议（continue with more budget / `/retrospective` / 换 path），等主人决定。
- 阻塞性 intervention（缺数据/缺权限/comparability blocker）→ 停 + 写 docs/08 + 通知。

## 本机无 Slurm 的两种子模式（按 `cluster_config.submission.mode` 区分，别混）
本机无 Slurm 不等于一定 handoff 到远程——有两种合法模式：
- **`remote_ssh`（本地→远程集群）**：本机只跑 prompt 层（plan/validate/tri-review/pivot 决策逻辑），真实训练 **submit-and-handoff 到远程**：`/smart-sbatch` remote 分支 rsync 代码 → `ssh {ssh_host} sbatch` → 记 `outputs/<exp>/JOBID` → `job_watch.sh`/`iter_ledger.py` 自动走 `ssh sacct/squeue` 对账 → `fetch_cmd` 取回 outputs/reports → 从 Step 1.4 续。
- **`local_direct`（无远程，纯本地直跑）**：训练就在本机 `python` **run-and-evaluate**（小数据/调试），**训练脚本结束必须 `echo COMPLETED > outputs/<exp>/STATUS`**（canonical template 已含）；`job_watch.sh` 无 Slurm 时会**尊重该 sentinel / `reports/<exp>.json`** 判 COMPLETED，不会误写 UNKNOWN。

**两种模式下闸门和续跑判定逻辑与有 Slurm 时完全一致**（validate_goal 只认 STATUS + metrics，不关心作业在哪跑）。

## inline 汇总（每轮 + 终止时）
- 本轮 exp_id / 计划 / validate status / 关键 metric vs 目标 vs SOTA
- 下一步（由 validate+pivot 决定）或终止原因
- 当前距 goal 的差距轨迹

## 不要做的事
- 不要把 `exit code 0` 或 agent 主观判断当成功——**只认 validate_goal.py 的 status**。
- 不要在 `failed_run` 后续跑。
- 不要静默吞掉失败——必须 inline 通知 + 写 docs/08。
- 不要擅改 docs/03 / docs/09 / kill 主人其他 job。

## Handoff
- **Inputs**: `ACTIVE_GOAL.json`、`docs/03`、`docs/05`(pending queue)、`docs/06`、`docs/09`
- **Uses skills**: `/implement` `/code-review-gate` `/smart-sbatch` `/result-log` `/note-gate` `/master-plan` `/tri-review` `/pivot`（必要时 `/decisions-log` `/retrospective` `/generalization`）
- **Gate**: `scripts/validate_goal.py`（确定性，不可跳）
- **Outputs**: docs/04/05/06/07/08 全程更新 + ACTIVE_GOAL.json status
