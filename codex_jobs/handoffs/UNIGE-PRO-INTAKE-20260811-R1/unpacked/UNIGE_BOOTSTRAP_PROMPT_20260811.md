在 `/home/users/j/jwang/ab-initio-TE` 完成 `UNIGE-PRO-INTAKE-20260811-R1`：先对齐研究状态、核查 Pro 新交付的可执行资格，并只在门禁通过后准备第一批 smoke；不要直接启动完整科学实验。完整上下文见 `codex_jobs/handoffs/UNIGE-PRO-INTAKE-20260811-R1/UNIGE_BOOTSTRAP_PROTOCOL_20260811.md`。

## 权限与边界

- 可以只读检查仓库、Slurm、软件和既有证据；可以在本实验唯一目录写入清单、报告和经门禁批准的 smoke 结果。
- 不得覆盖远端现有 `docs/`、`software_outputs/`、`runs/` 或失败证据；不得删除、迁移数据库、部署、提交或推送 Git。
- ChatGPT Pro 交付只是候选，不等于 Codex 已验收。未收到对应 ZIP、SHA-256、闭合 manifest、前序 delta、独立 code-review PASS 和外部 trust pins 时，不得运行该包。
- 不得在登录节点运行科学计算。所有会执行研究代码、扫描大量文件、调用生信工具、训练、推理、统计或绘图的命令都必须遵循 `.agents/skills/smart-sbatch/SKILL.md`。

## 必读与当前事实

1. 读取 `AGENTS.md`、`CLAUDE.md`、`README.md`、`cluster_config.yaml`、`.agents/skills/smart-sbatch/SKILL.md` 和本轮 protocol。
2. 运行 `python3 scripts/research_flow_guard.py . --format json`；当前已知基线是 `ok_to_goal=false`，原因是远端 Stage-A/benchmark 合同尚未闭合。不得伪造 PASS。
3. 只读核查 `squeue -u jwang`、近期 `sacct`、磁盘/配额、maintenance reservation 和本轮输出路径唯一性。
4. 已验收的远端结果仅包括资产/代码/候选普查；四项新科学主张目前均为 0 个 claim-admitted result。

## 执行链

1. 核对 handoff 文件 SHA-256 和远端现有证据目录，生成 `REMOTE_STATE_DIFF.md`，不得改写旧文档。
2. 为 fragmentation、superfamily、generalization、embedding、five-tool benchmark 建立状态矩阵：`accepted_remote / candidate_local_only / missing / blocked / next_gate`。
3. 确认 Pro 新包当前是否实际存在于本轮 intake 目录；不存在则标记 `PACKAGE_NOT_STAGED`，不得自行从聊天结论重建代码。
4. 对已存在的 sbatch 使用 smart-sbatch Mode B；只有 Phase 1 全部 PASS 才可建议提交。新任务使用 Mode A，先给 Phase 1 表，再给 Phase 2。
5. 第一执行优先级固定为：five-tool exact version/dependency/offline smoke → fragmentation code/runtime gate → superfamily S0 输入执行门禁。G/E 只做后续 kill-gated smoke。
6. 本轮若没有任何已独立验收且完整 staged 的新包，以 `READY_FOR_PACKAGE_INTAKE` 正常结束，不提交科学作业。

## 完成条件

- 展示研究状态矩阵、远端已有上传物清单、缺失上传物清单、research-flow-guard 原始 verdict、Slurm live snapshot、下一条唯一安全动作。
- 所有新文件写入 `codex_jobs/handoffs/UNIGE-PRO-INTAKE-20260811-R1/`；不得把 smoke/screen 描述为论文结果。
- 如确有可提交 smoke，先展示 smart-sbatch Phase 1 PASS 证据、脚本路径、输出唯一目录和预计资源；否则明确 `NO_JOB_SUBMITTED`。

