# SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1

## 唯一问题

本实验只回答一个工程问题：在 4 CPU、16 GiB、20 分钟的固定 allocation 内，Dfam 3.9 partition 3 的 read-only HDF5 metadata traversal 是否能用 deterministic 4-way unit shards 获得可验证的端到端吞吐与至少 25% 预计时间余量。

它不解析 279 targets，不输出 recovered/missing/absence，不修改或运行父 R0，不构建 full catalog、homology graph 或 split，也不运行模型。`PREFLIGHT_FEASIBLE` 只表示工程 preflight 可行；R0/R1/R2/GPU/S1 authorization 在所有状态中都固定为 false。

## 冻结输入与运行时 workload identity

- source 固定为 `dfam39_full.3.h5` partition 3，精确 size 63,939,647,016 bytes，并绑定 Dfam/FamDB metadata、12-partition layout manifest、`rmlib.config`、最新 docs/19、父 R0 config 与已审 R0 telemetry SHA。避免为 64 GB H5 新增全文件哈希负担。
- topology 固定为 `Families/Aux/<bin>` 与 `Families/DR/<prefix1>/<prefix2>` 的 35 个有序 units；ordered-list SHA 为 `bfea5e8d...e94c2`，正式运行必须得到精确 321,856 条、unique、canonical-unit-order 的 dataset paths。
- 登录节点不能真实扫 H5，因此不虚构 8,192-path hash。allocation 内先以四个独立 read-only handles 重建完整 path inventory 两次：第一遍固定 round-robin units，第二遍按第一遍真实 unit counts 做 largest-first balance；parent 按冻结 unit order 聚合。两次 exact count、unique path、unit counts、full ordered inventory SHA 和随后生成的 8,192-path workload SHA 必须完全一致。
- 8,192 paths 按真实 unit counts 做确定性比例分层，每个非空 unit 至少一个样本，unit 内用 midpoint indices 覆盖整个有序范围。`unit_sampling.tsv` 报 population/sample counts、inverse-probability weight、首尾 span、path depth 和四个位置 quartiles；不得用等权 unit prefix 冒充代表性。
- sample shard assignment 固定为 `uint64(sha256(dataset_path)[0:16]) mod 4`。四个 shard 的 union 必须等于同一个 frozen workload，pairwise intersection 为空，每个 path 恰好一次。

## 正式 R0 形状与端到端 ETA

拟评估的正式形状是：35 个 topology units 按真实 dataset counts 分配给四个 workers；每个 worker 用自己的 read-only H5 handle 直接发现并扫描所拥有的 subtree；parent 仅在四个 rc=0 后聚合。preflight 的 known-path serial/parallel probe 只是属性读取成本测量，不替代 path discovery。

保守 ETA 显式相加：第二遍/第一遍较慢者的 full path-discovery wall time + 按正式 balanced-unit 最大 worker population 和 sample batch `max(seconds/dataset)` 外推的 attribute-read time（再乘 4× safety factor）+ measured parent JSON merge、unit assignment、inventory/workload hash 与 shard-build time。最终 ETA 再与已审 R0 telemetry 的 4.41h full-scan baseline 除以最多 4×、由实测支持的 parallel speedup所得 lower bound 取最大值。若 known-path serial 比 R0 observed rate 快超过 4×，将其标为不可比 anomaly 并阻止 feasible。

只有 final conservative ETA ≤900 秒且相对 1,200 秒 allocation 的 headroom ≥25%，才为 `PREFLIGHT_FEASIBLE`；否则为语义成功、rc0 的 `PREFLIGHT_INFEASIBLE`。stage 性能 timeout 同样是预注册 valid negative，不与数据损坏、schema/hash drift、child nonzero 等 integrity/runtime `PREFLIGHT_FAILED` 混淆。

## 预算、并发与终态合同

- 两次 inventory rebuild 各 180 秒，8,192-path serial timeout 540 秒（高于 R0 线性外推约 404 秒），parallel timeout 180 秒，tests/publish reserve 120 秒；硬上限之和恰为 1,200 秒。
- 所有 inventory/sample workers 都是独立子进程、独立 read-only H5 handle、exclusive worker stage。任意 Popen 在部分 children 已启动后异常、child nonzero、timeout、缺失/截断 output、manifest tamper 或 output race 时，parent 都显式 kill+wait 所有已启动进程后才退出。
- `preview/logs/` 必须由静态 preview 在提交前创建并做实际 write probe；其 sentinel 进入 `output_manifest.sha256`。sbatch 不运行 `mkdir` 来补救 Slurm 在脚本启动前已打开 stdout/stderr 的问题。
- runner 先发布 `RUNNING` 再运行 tests/formal。prepare 后 tests failure、Python exception 和 dirty-attempt refusal 均由原子终态覆盖为 `PREFLIGHT_FAILED semantic_success=false`；不得遗留 RUNNING。owner lock 与正整数 `SLURM_JOB_ID` 均为硬 guard。

## 当前状态

当前仅为 `IMPLEMENTED_NOT_RUN` 静态 preview。登录节点仅运行 synthetic tests、代码语法检查与浅层 real-topology/input pin 检查；未枚举任何真实 dataset path，未执行 8,192-path real workload，未提交 Slurm，未写 PASS gate。

## 提交前终止决定

独立 fresh code review 最终为 `BLOCKED`，本实验不会提交。除了发现 child nonzero 可能被另一 child timeout 掩盖、稀有 path-depth stratum 可被当前 sample 漏掉两个代码 blocker 外，资源合同本身已给出确定性否定：父 R0 的审计投影为 15,878 秒，4 workers 的最大允许加速为 4，因此 formal ETA 下界为 3,969.5 秒；20 分钟 allocation 要保留 25% headroom 时上限仅 900 秒。`PREFLIGHT_FEASIBLE` 数学不可达，再提交只会重复一个已知负结论。

机器可读决定为 `outputs/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1/PRE_SUBMIT_DECISION.json`。其明确记录 `throughput_measurement_executed=false`、`slurm_job_submitted=false`，并将 R0/R1/R2/GPU/S1/scientific authorization 全部保持 false。下一步不是修复并提交本实验，而是另建可恢复的 4-way 正式 R0 合同，使用 3 小时 CPU envelope 与 per-unit atomic checkpoints；partial checkpoints 永不构成 identity 结果。
