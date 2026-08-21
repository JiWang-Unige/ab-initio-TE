# Runtime Playbook / 驱动切换、服务器迁移、Baobab 提交与压缩恢复

> 这是操作层说明。研究真相源仍是 `docs/00-18`、`refs/`、`wiki/`、`ACTIVE_GOAL.json`。

## 1. 中途切换 Claude / Codex / Antigravity

- Claude 与 Codex 共用同一份 `docs/refs/wiki/scripts/ACTIVE_GOAL`。
- Claude 入口：`CLAUDE.md` + `.claude/skills` + `.claude/settings.json`。
- Codex 入口：`AGENTS.md` + `.agents/skills`（并镜像到 `.codex/skills`）+ `.codex/hooks.json`。
- Antigravity/第三 reviewer：优先 `$ANTIGRAVITY_CLI`，其次 `agy -p`（统一三 CLI claude/codex/agy，无 cursor-agent 兜底）；作为 reviewer C 失败不应单独阻断 ordinary iteration（走 2/3 DEGRADED）。

补装另一个壳：

```bash
./install.sh --driver claude /path/to/project   # codex-only 项目补 Claude
./install.sh --driver codex  /path/to/project   # claude-only 项目补 Codex
./install.sh --driver both   /path/to/project   # 双壳刷新
```

## 2. 迁移到另一台服务器

1. 打包项目时排除大数据、checkpoint、secrets 的公开副本；私有迁移可保留 `secrets.env`，但不要进 git。
2. 到新机器后重跑 `install.sh --driver <needed>`，它会刷新框架代码但保留研究 docs。
3. 运行 `/configure-project` 重新探测 conda、Slurm、提交方式、路径约定。
4. 更新 `cluster_config.yaml` 的 `submission_mode`：
   - `on_cluster`：当前就在 Baobab/login 节点，直接 `srun/sbatch`。
   - `remote_ssh`：当前在本地，需要 `ssh baobab` 后再 `srun/sbatch`。
   - `local_direct`：没有 Slurm，只允许 smoke/local 脚本，不跑 full/scale。

## 3. Baobab srun 强制规则

- 在 Baobab / Slurm login 节点上，除下载、轻量文件操作、框架检查脚本外，所有 CPU/GPU 计算命令都必须经 `srun` 或 `sbatch`。
- `scripts/hooks/submit_guard.sh` 会对常见重计算命令给出 ask/deny；`/smart-sbatch` 是长期作业入口。
- 常见轻量例外：`python3 scripts/context_pack.py`、`iter_ledger.py`、`lit_search.py`、`check_data.py` 的小规模检查、`curl/wget/git clone` 下载。

## 4. Compact / resume 后如何恢复

- `PreCompact` hook 会提醒先 `/note-gate` 和 `/master-plan`，因为没写盘的聊天结论会在压缩后丢失。
- `SessionStart(compact/resume)` 与 `SubagentStart` hook 会运行 `research_bootstrap.sh`，从磁盘的 `context_pack.py` 重建上下文。
- Hook 不能替你执行 skill；它只能注入恢复 prompt、提醒、或拦截危险命令。真正的 `/tri-review`、`/pivot`、`/result-log` 仍由 agent 调用。

### 4.1 压缩时「有作业正在运行」怎么办（submit-and-handoff / 长训练）
**关键认知：Slurm 作业独立于对话——压缩、换会话、甚至关掉 Claude 都不会杀掉 sbatch 作业。** 不丢作业的前提是它的"身份"已经在磁盘上：

1. **提交即落盘（最重要）**：`/smart-sbatch` submit-and-handoff 提交后，**立刻**把 `job_id` 写进 `docs/05` tracker 一行（`| <exp_id> | … | RUNNING | <job_id> |`）+ `outputs/<exp_id>/STATUS=RUNNING` + 记 reports 路径与 resume 指令。这样作业身份在压缩**之前**就落盘了。
2. **压缩本身**：PreCompact hook 提醒确认上面已落盘；压缩只压对话历史，**不动磁盘、不碰正在跑的作业**。
3. **压缩后恢复**：`SessionStart(compact)` → `research_bootstrap.sh` 跑 `context_pack.py`，其 tracker_block 会从 `docs/05` + 扫 `outputs/*/STATUS` **重新带出"有哪些 RUNNING 作业"**；再用 `scripts/job_watch.sh --jobid <id> --status-out outputs/<exp>/STATUS` 按 job_id 重新轮询到终态（COMPLETED/FAILED/TIMEOUT/OOM）。
4. **幽灵作业兜底**：若 `STATUS=RUNNING` 但 `squeue/sacct` 查无此作业，`iter_ledger.py` 报 `stale_signal`，按 `failed_run` 处理——不会傻等一个已死的作业。

> 一句话：**只要"提交时把 job_id 落了盘"，压缩/换会话/换机器都不丢作业**；唯一会丢的是"提交了但 job_id 只在对话里没写盘"——所以 submit 后第一件事就是写 tracker + STATUS。运行中作业 ≠ 必须守着会话，这正是 submit-and-handoff 模式的意义。

## 5. API 与检索

- `S2_API_KEY`：`scripts/lit_search.py` 读取 Semantic Scholar API，用于 search / cited-by / similar。
- `ANYSEARCH_API_KEY`：可选 MCP，适合常规搜索不够时做 academic / batch / URL extraction。
- `EXA_API_KEY`：可选 neural web search。
- 缺 key 时必须优雅降级；检索失败要写入 `docs/15` 或 `refs/sources.md` 的失败清单，方便用户手动补。
