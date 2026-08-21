# BENCH-HITE-ISOLATED-20260811-R1

状态：`COMPLETED`；Job `11524485`；isolated engineering smoke PASS，claim-ineligible。

## Result

- Slurm `COMPLETED 0:0` in 23m04s，4 CPU/48 GiB/0 GPU。
- HiTE 3.3.3 help identity rc0；minimum rc0、未超时，命令 wall time 21m58.53s，peak RSS 2,111,456 KiB。
- `HiTE.gff` 1,203,491 bytes；canonical adapter 14,315 rows。
- artifact manifest 12/12、published canonical payloads 5/5、runtime environment hashes全部通过。
- `hite_engineering_pass=1`、`semantic_success=true`、`two_cell_evidence_ready=true`。
- 父 `BENCH-RM-HITE-VALIDITY-20260811-R1` 仍为 `FAILED`；仅复用其逐字节核验的 RM cell。`single_successful_run=false`、`claim_eligible=false`，不得表述为五工具闭合或生物学结果。
- route-level GOAL_B 因缺少完整五 cell `terminal_cell_count` 返回 `failed_run`，因此进一步 B compute 停止，等待 tri-review/pivot。
- 3/3 result tri-review 接受 isolated HiTE pass 与 parent RM hash-reuse 的 two-job/two-cell reconciliation；父 aggregate 仍 FAILED，不是一次成功 denominator run。
- 原始 `further_retry_allowed=true` 保留不改；`reconciliation_review.json` 将实际操作权限固定为 false，因为唯一一次 isolated authorization 已用完。
- Pivot=`continue` by archive only；不得自动运行剩余工具。

## 研究问题与边界

父实验 `BENCH-RM-HITE-VALIDITY-20260811-R1` 的 Slurm job `11523819` 聚合状态为 `FAILED`：RepeatModeler2/RepeatMasker cell 已通过，HiTE cell 在 600 秒处超时。三方结果复审一致选择最窄的 Option A：只重跑 HiTE，避免重复消耗已经闭合的 RM cell。

本实验只执行 hash-pinned HiTE 3.3.3 的 help identity 和 minimum-input 命令。它不会生成或执行 RepeatModeler/RepeatMasker、Earl Grey、EDTA、TEtrimmer 或 Pfam 命令。父作业的 RM cell 仅作为逐字节核验的跨 run 证据引用，父作业与父实验文件绝不改写。

## 严格合同

- HiTE SIF、manifest、help、inspect、fixture、准备脚本、准备环境、adapter 均由配置给出 SHA-256；manifest 内 reference、source commit、准备 job 与准备 config hash 同时核验。
- 容器以 `--cleanenv`、断网代理和 direct argv 运行；help 必须 rc=0、未超时且出现锚定整行 `HiTE, version 3.3.3`。
- minimum argv 固定为 `python /HiTE/main.py --genome /work/input/hite.fa --thread 2 --annotate 1 --out_dir /work/hite`。
- minimum timeout 为 1800 秒，GNU timeout `--kill-after=10`；资源是 4 CPU、48 GiB、1 小时、0 GPU。预算记账为 1860 秒命令上限、20 秒 kill-after、300 秒预检 hash 与 900 秒收尾余量，共 3080 秒，尚余 520 秒；明确满足至少 600 秒的 post-command cleanup/adapter/hash/publish 余量。
- runner 在读取 config/资产或构造容器命令前强制要求正整数 `SLURM_JOB_ID`；本地或不可解析 job id 立即拒绝，绝不启动容器。每次 sbatch 环境快照先写临时文件再 rename，runner 的 input manifest 记录其路径与 SHA-256。
- 只有 help identity、minimum rc=0、精确最终文件 `HiTE.gff` 非空且可解析、canonical adapter 至少一条合法记录、资产/父证据/产物 manifest 全闭合时，才写 `ENGINEERING_PASS`、`semantic_success=true`、进程 rc=0。
- timeout、非零退出、缺失/空/畸形 GFF、adapter 或 manifest 失败均为 `INVALID_RUN`、`semantic_success=false`、进程 rc=2；不存在把执行后失败降格为 typed block 的路径。
- metrics 同时记录 `primary_metric="hite_engineering_pass"` 与数值键 `hite_engineering_pass`。metrics、semantic、command、reconciliation、latest（失败时再含 failure）先写 attempt staging，再由 canonical manifest 对 staging/canonical 路径及 runtime environment hash 闭包，最后才原子发布终态。

## 父 RM 证据 reconciliation

配置 byte-pin 父 job 11523819 的 `STATUS`、metrics、RM cell result、HiTE cell result、artifact manifest、command manifest、input manifest、父 config 与父 runner。runner 不仅验证 RM result 与 command manifest、adapter source/output 与 artifact manifest、父 config 与 input manifest 的逐项映射，也要求父 HiTE result 的真实 SHA-256 为 `c5cc670021ffc9fdea5a0df6231aeade990575fac9ddb789470c3ef290b1ae4f`，其第二条命令精确为 `hite_min`、configured/effective timeout 均为 600 秒、rc=124、`timed_out=true`，且 result/command/artifact 三方映射一致。

父 600 秒 timeout 只授权本隔离实验一次 1800 秒有界 retry。如果这一次也 timeout，runner 会立即原子写 `STOP.json`，其中 `stop_rule_triggered=true`、`further_retry_allowed=false`，并同时保存父 timeout 与本次 timeout 的证据。所有未来尝试在资产 hash 或容器动作之前读取该 sentinel；存在、损坏或状态异常都 fail-closed，不再执行 HiTE。

即使隔离 HiTE 通过，结论也只能是“父 RM pass（跨 run、hash 核验）+ 本实验 HiTE pass 的 two-cell evidence ready”。原父 R1 的 aggregate 始终是 `FAILED`；`single_successful_run=false`、`accuracy_claim=false`、`claim_eligible=false`。这不是一次成功聚合 run，也不产生 accuracy 或论文 claim。

## 产物与所有权

独立输出根为 `outputs/BENCH-HITE-ISOLATED-20260811-R1/`。取得 ownership 后、任何实验命令前先原子把状态切到 `RUNNING`，并归档旧终态与旧 canonical bundle。每次尝试写入独立 attempt、input/result/runtime/artifact/canonical manifests；所有可捕获异常和 SIGTERM/SIGINT 都转成 `FAILED`、`failure.json` 与 rc=2。独立 lock 只接受正整数 owner、有限且不在未来的 created；`squeue` 必须 rc=0、stderr 精确为空、stdout 精确为空或该 owner，其他一律 fail-closed。只有明确 inactive 且超过 stale threshold 才回收，release 仍只删除自己的 token。

当前 preview 只含 `IMPLEMENTED_NOT_RUN`、`BLOCKED` gate 和待运行 reconciliation；不存在 metrics 或伪造结果。正式提交前必须由独立 reviewer 写真实 code-review gate PASS，随后才能通过 `pre_submit_gate.py`。
