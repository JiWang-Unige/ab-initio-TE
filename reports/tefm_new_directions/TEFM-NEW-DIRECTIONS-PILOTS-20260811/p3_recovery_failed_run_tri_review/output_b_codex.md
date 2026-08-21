2026-08-11T23:31:09.804494Z ERROR codex_core::shell_snapshot: Shell snapshot validation failed: Snapshot command exited with status exit status: 2: /home/users/j/jwang/.codex/shell_snapshots/019ff32a-6164-7982-a213-f6cbac746f5b.tmp-1786491068807451944: line 636: syntax error near unexpected token `('

OpenAI Codex v0.147.0
--------
workdir: /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 019ff32a-6164-7982-a213-f6cbac746f5b
--------
user
# Independent Full-Scope Research Review

You are an independent external reviewer. Do not assume a specialized role and do not rely on other reviewers. Review the full scope below and answer in professional Simplified Chinese. The host will aggregate independently; do not ask questions.

## 1. Research question and north star

The project must first establish a leakage-safe direct-superfamily S0 baseline before any hierarchical/open-set S1 work. Frozen human decision: RepeatMasker direct `BG/SINE/LINE/LTR/DNA/Unknown` annotations are prediction truth; sequence homology defines split components only and never relabels; 10 label-contract-excluded identifiers remain U/ignore; `X13_LINE` is audit-only. Before homology clustering, R0 must determine whether 279 exact-name misses are recoverable from Dfam 3.9 partition 3, whose canonical H5 legitimately lacks `Lookup/ByName`.

This experiment is a claim-ineligible CPU asset audit, not a model benchmark. No R1 full catalog, R2 homology graph/split, GPU S0, S1, or claim is permitted unless this gate completes and later gates independently pass.

## 2. Method under test

`SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1` freezes 279 missing identifiers from Job 11524255 (occurrence mass 6,432,583) and scans all canonical `Families/...` datasets in `dfam39_full.3.h5` by exact, case-sensitive dataset `name` attr. It requires full counts: 321,856 datasets, 321,856 consensus attrs, 321,818 model attrs. Recovery requires a unique versioned accession plus consensus SHA. Prefix/casefold/substring/genome-copy fallback, sampling, clustering, split and model execution are forbidden. Progress is emitted every 10,000 datasets.

Terminal semantics: complete unique recovery permits only a separately reviewed full-catalog stage; complete unresolved results are a valid-negative typed block; input/count/read/conservation failure is failed-run. Partial scan is never a valid negative.

## 3. Result and trend

Job 11525316 ran on `private-teodoro-gpu`, 4 CPU, 48 GiB, 2h limit, 0 GPU. Independent code review was PASS with 0 blockers; 13/13 allocation-side tests passed. The real scan was healthy and I/O-bound: checkpoints at 10k, 20k, 30k; no traceback; RSS about 121 MiB; CPU cumulative about 8 seconds; disk reads continuously increased. The 30k checkpoint occurred after about 1,480 seconds. Linear exhaustive projection: 15,878 seconds (4.41h), beyond the reviewed 2h walltime. The controller cancelled the exact job early at 01:25:01 CEST instead of consuming the entire allocation for a certain TIMEOUT.

Audited terminal: `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`, semantic_success=false, validate_goal=failed_run rc3. Raw runner STATUS remains RUNNING because external SIGTERM interrupted it; a separate audited status/metrics/audit plus 18-entry hash manifest closes this without rewriting raw state. `sacct` is unavailable because slurmdbd refused connection; Slurm stderr records exact cancellation and squeue became empty.

The first 30,000 datasets had 0 exact candidates, but coverage is only 9.321096%. Contract says this is diagnostic telemetry only and cannot support biological or identity claims.

Prior trend: Job 11524255 completed exact-index provenance across 35.6M annotations and resolved 6,447/6,727 identifiers, leaving these 279 missing plus audit-only X13. Earlier Job 11523938 failed because a resolver assumed every H5 partition had `Lookup/ByName`; this R0 intentionally removed that index dependency and did make correct progress.

## 4. Known weaknesses and conflicts

- The H5 is 63,939,647,016 bytes. Contract intentionally does not hash all 64 GB; it pins layout, size, Dfam/FamDB metadata and exact terminal counts.
- Serial h5py small-attribute access is extremely I/O-bound and currently uses little of the 4-CPU allocation.
- A naive walltime extension to 5-6h would likely complete but costs more and preserves inefficient serial access.
- Deterministic disjoint sharding across accession-prefix bins/processes may use available CPU and fit a short allocation, but must avoid concurrent HDF5 corruption, duplicate/omitted datasets, nondeterministic aggregation, and output races. Source is read-only.
- Restart/checkpoint reuse could reduce repeated work, but the current attempt is partial and must not be promoted; any reuse semantics require new implementation/review.
- Active project `ACTIVE_GOAL.json` is an old selector/decoder goal and is not metric-compatible with this route. validate_goal therefore only provides the failed-run stop signal; no SOTA gap/tuning decision is meaningful.

## 5. Comparability contract

This is asset identity, not SOTA comparison. Required fairness dimensions are exact frozen source/layout, exhaustive dataset denominator, exact-case name semantics, input and occurrence conservation, no test-derived genome copy substitutions, no partial-result promotion, and claim-ineligible 0-GPU execution. The latest evaluator contract is SHA `fe0d63e9b525a0bac5ee03b3b88b83385fc4582f8a1b3f9802d171c72594ade2`.

## 6. Abandoned cousins

Do not propose prefix/case/suffix guessing, random/chromosome split, dropping unresolved identifiers, genome-copy-derived representative sequences, or combining resolver repair with homology clustering. Do not restart abandoned local threshold/gap/HMM/CRF fragmentation routes. This review only decides the next R0 validity action.

## 7. This round versus last round

Unlike Job 11523938, this implementation does not call the missing ByName index and successfully traverses `Families` attrs. Unlike Job 11524255, it targets only the 279 unresolved identifiers in partition 3. The new failure is resource sizing/serial traversal shape, not identity semantics, data corruption, or model quality.

## Artifacts

- Result log: `docs/06_results_log.md` section `SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1`
- Audited outputs: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`
- Raw progress: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/preview/attempts/slurm-11525316.tmp/scan_progress.jsonl`
- Config: `configs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.yaml`
- Code: `scripts/experiments/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/recover_p3_identities.py`
- Sbatch: `sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch`

## Required output

### 1. Overall judgment
Choose exactly one: continue-current-route; scale-to-track-b; tune-only-if-near-sota; replace-component; change-backbone; change-objective-or-loss; run-sanity-check-first; comparability-blocker; abandon-route; return-to-literature.

### 2. SOTA gap interpretation
State N/A where appropriate and say whether tuning is meaningful.

### 3. Comparability and benchmark fairness audit
Table: dataset/source version, denominator/exhaustiveness, identity semantics, preprocessing, external assets, resource profile/claim.

### 4. Semantic success and reproducibility audit
Table: metrics/audit parseability, finite values, execution health, partial-result guard, logs/config/manifests, Slurm accounting limitation.

### 5. Architecture/implementation assessment
What does the result imply? Compare at least these repair options: (A) deterministic 4-way read-only disjoint scan with strict union/count/conservation, (B) 5-6h serial rerun, (C) resumable checkpointed serial scan. Name concrete failure guards and whether a small preflight throughput benchmark should precede formal resubmission.

### 6. Track recommendation
State exactly what may run next and what remains forbidden.

### 7. Risks and blockers
List concrete risks, including billing waste.

### 8. Next action
Give one concrete bounded repair experiment, its resource envelope, required code-review tests, and stop rules. Do not authorize R1/R2/GPU/S1.

### 9. Confidence
High/Medium/Low with reason.

2026-08-11T23:31:10.947306Z ERROR codex_memories_write::phase2: failed preparing memory workspace: write blob /home/users/j/jwang/.codex/memories/extensions/ad_hoc/instructions.md
hook: SessionStart
hook: SessionStart
hook: SessionStart Completed
hook: SessionStart Completed
codex
我会按 `$tri-review` 的独立审阅规范执行，但只形成我这一份判断，不调用或依赖其他 reviewer。先核对该 skill 的约束及关键产物，再给出严格按 9 项要求组织的结论。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/bash -lc "sed -n '1,240p' .agents/skills/tri-review/SKILL.md" in /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
 exited 1 in 0ms:
bwrap: Creating new namespace failed: No space left on device

codex
本地命令沙箱因节点 namespace 资源耗尽而未能启动（与实验产物无关）。我会再用最小只读调用核对 skill；若环境仍拒绝，则明确按用户给出的完整审计事实独立评审，不把工具故障混入研究判断。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/bash -c "/usr/bin/sed -n '1,260p' /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/.agents/skills/tri-review/SKILL.md" in /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
 exited 1 in 0ms:
bwrap: Creating new namespace failed: No space left on device

codex
说明：本地命令沙箱因 namespace 资源耗尽，无法读取 `$tri-review` 文件及直接复核产物；以下严格依据题面提供的冻结合同、结果与审计事实独立完成，不依赖其他 reviewer。

## 1. Overall judgment

**replace-component**

应替换的是低吞吐的串行 HDF5 attribute traversal 组件，而不是 direct-superfamily 路线、身份语义或数据源。当前失败属于明确的资源—实现不匹配；9.32% 的部分扫描既不能证明 279 个标识不可恢复，也不能支持任何生物学结论。

## 2. SOTA gap interpretation

**N/A。**

这是 claim-ineligible 的资产身份审计，不存在 SOTA、模型性能差距或可解释的 `gap_to_target`。模型超参数 tuning 完全无意义；当前只适合做有界的工程吞吐与确定性验证。

旧 `ACTIVE_GOAL.json` 与本路线指标不兼容，因此 `validate_goal=failed_run` 只应解释为强制停止信号，不能用于路线优劣、调参许可或晋级判断。

## 3. Comparability and benchmark fairness audit

| 维度 | 审计判断 | 依据与限制 |
|---|---|---|
| dataset/source version | 合同充分，实际结果未完成 | 冻结 Dfam 3.9 partition 3、64 GB H5、布局/大小/FamDB 元数据和终端计数。未做整文件 SHA 留有较小的位级漂移风险，但不构成本次取消原因。 |
| denominator/exhaustiveness | **未满足** | 合法终点必须覆盖 321,856 datasets、321,856 consensus attrs、321,818 model attrs。当前仅 30,000 datasets，即 9.321096%，不能作为 valid negative。 |
| identity semantics | 设计正确 | exact、case-sensitive `name` attr；仅“唯一 versioned accession + consensus SHA”可恢复。禁止 prefix、casefold、substring 和 genome-copy fallback。 |
| preprocessing | 无引入偏差 | 当前仅做 canonical `Families/...` 全量 attr traversal，没有 clustering、split、标签重写或模型执行。 |
| external assets | 基本充分 | 冻结 279 identifiers、6,432,583 occurrence mass、Dfam/FamDB 元数据和精确终端计数。正式重跑仍须重新核验这些输入守恒量。 |
| resource profile/claim | 语义公平，资源规划失败 | 0 GPU、CPU-only、claim-ineligible 符合合同；但串行扫描预计 4.41h，与 2h walltime 明显不匹配。资源失败不能转化为身份证据。 |

## 4. Semantic success and reproducibility audit

| 项目 | 判断 |
|---|---|
| metrics/audit parseability | 审计状态、metrics、manifest 可解析，并明确记录 `semantic_success=false` 和 `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`。 |
| finite values | 进度、覆盖率、时间、RSS、CPU 和读盘量均为有限且合理值；不存在完整 recovery 指标。 |
| execution health | 扫描在取消前健康推进，无 traceback，内存稳定。失败原因是确定的 walltime/吞吐不匹配，而非输入损坏或 identity 逻辑异常。 |
| partial-result guard | **通过**。30,000 条中的 0 candidates 仅作 telemetry，没有被提升为 valid negative。 |
| logs/config/manifests | 配置、原始进度、Slurm stderr、审计覆盖层和 18-entry hash manifest 足以复现“为何停止”。原始 `STATUS=RUNNING` 必须继续保持不可变，并由审计状态覆盖解释。 |
| Slurm accounting limitation | `sacct` 不可用削弱了完整资源核算，但 exact cancellation stderr 加上 `squeue` 清空足以确认作业已终止；不影响 failed-run 判定。 |

因此，本轮是工程执行意义上的可解释失败，不是语义成功，也不是 valid negative。

## 5. Architecture/implementation assessment

结果证明无索引 traversal 路径可以正确进入并读取 `Families` attrs；它没有证明任何目标标识存在或不存在。主要缺陷是逐 dataset 的小 attribute 访问使任务受存储延迟支配，4 CPU 基本闲置。

| 修复方案 | 优点 | 主要风险 | 建议 |
|---|---|---|---|
| A. 确定性四路只读分片 | 最可能在短 walltime 内完成；利用已申请 CPU；保持 exhaustive 语义 | 共享存储并行读可能不加速甚至抖动；分片遗漏/重叠；输出竞争；一个 shard 失败后错误聚合 | **首选，但必须先做小型吞吐与正确性 preflight** |
| B. 5–6h 串行重跑 | 代码变化最少，确定性最容易维持 | 计费浪费明显；4 CPU 中大部分闲置；重复读取已知慢路径；仍可能受文件系统波动超时 | 仅当并行 preflight 证明无收益后，另行评审 |
| C. 可恢复串行 checkpoint | 中断后可续跑，降低重复工作 | 不改善首次完整扫描的总成本；需严格绑定源指纹、游标、计数和输出哈希；错误 checkpoint 会漏扫/重复 | 可作为后续可靠性增强，不应是首个修复 |

四路实现至少需要以下 fail-closed guards：

- 每个 dataset path 精确归属一个冻结 shard；最终 union 无遗漏、pairwise intersection 为空。
- 各 shard 独立只读打开 H5，独立输出到隔离目录；父进程仅在全部成功后原子聚合。
- 任一 shard 异常、被取消或计数不完整，整体必须失败且禁止生成 recovery 结论。
- 聚合后严格满足三个终端计数以及 279 identifiers、6,432,583 occurrence mass 守恒。
- exact-case 匹配和唯一 accession/consensus SHA 规则保持不变。
- 重复执行的 shard assignment、计数、匹配记录和聚合哈希一致。
- 禁止继承当前 30k partial scan，除非另建并通过专门的 checkpoint/reuse 合同审查。

正式全量重提之前应先做 representative、冷缓存可辨识的吞吐 preflight，因为四路读取是否能加速取决于共享文件系统，而不是 CPU 数量。

## 6. Track recommendation

下一步只允许：

1. 实现确定性四路只读分片扫描器；
2. 完成独立 code review；
3. 运行一次小规模、0-GPU、claim-ineligible 的 R0 吞吐与分片正确性 preflight。

当前不授权完整 R0 正式扫描自动续跑。preflight 通过后，仍需根据实测速率重新确定 walltime，并对正式 R0 submission 单独过审。

继续禁止 R1 full catalog、R2 homology graph/split、GPU S0、S1 hierarchical/open-set，以及任何 claim。

## 7. Risks and blockers

- 四进程可能受同一存储带宽限制，吞吐不升反降。
- shard 定义或边界错误可能造成静默遗漏、重复扫描或不均衡。
- 多进程共享输出可能产生覆盖、交错写入或非确定性聚合。
- HDF5 并发读取配置不当可能触发锁、打开失败或库级异常。
- 不完整 shard 被误当作完整结果，是最高级别语义风险。
- 未做整文件 SHA 时，源文件被原位替换仍存在残余风险。
- attr 编码、缺失 attr、重复名称和 consensus SHA 冲突必须保持 typed failure，不能隐式归一化。
- 直接申请 5–6h 串行资源会重复支付确定可预见的 I/O 等待成本；48 GiB 和4 CPU也明显过度配置。
- 反复全量试跑会增加共享文件系统负载和计费浪费。
- 旧 `ACTIVE_GOAL.json` 继续存在路线指标错配，不能用其 progress/tuning 字段指导本审计。

## 8. Next action

运行一个新的有界实验：**`SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT`**。

资源建议：

- 4 CPU，16 GiB RAM，0 GPU；
- walltime 20 分钟；
- 四个互斥且覆盖不同 accession/path 区域的 representative shard；
- 每 shard 至少扫描约 10,000 datasets；
- 输出仅为吞吐、计数、分片覆盖和确定性报告，禁止输出 recovery/absence 结论。

提交前 code-review 必测：

- synthetic H5 上 union 完整、intersection 为空、每条 dataset 恰好一次；
- exact-case 正例/反例、重复名称、缺 consensus/model attr、非唯一 accession；
- 单 shard 故障、SIGTERM、截断输出和聚合中断均 fail closed；
- shard 输出隔离及最终原子聚合；
- 两次执行 assignment 与聚合哈希一致；
- 源文件只读、不修改 raw state；
- 输入 identifier/occurrence 守恒；
- 13/13 既有合同测试无回归。

停止规则：

- 任意遗漏、重复、输出竞争、HDF5 错误或非确定性，立即停止；
- 任一 shard 未完成，禁止聚合；
- 冷缓存聚合吞吐低于约 **60 datasets/s**，或保守投影不能在 90 分钟内完成全量扫描，不提交 2h 正式作业；
- preflight 出现的任何 279 匹配只作诊断，不得晋级为 recovery；
- 不得自动切换到长 walltime 串行方案。

## 9. Confidence

**High。**

失败类型、部分结果边界和禁止晋级条件都有直接证据支撑；“替换串行 traversal 并先做吞吐 preflight”的决策稳健。唯一仍不确定的是四路读取在实际共享存储上的加速幅度，这正是该有界 preflight 要回答的问题。
hook: Stop
hook: Stop Completed
tokens used
35,440
说明：本地命令沙箱因 namespace 资源耗尽，无法读取 `$tri-review` 文件及直接复核产物；以下严格依据题面提供的冻结合同、结果与审计事实独立完成，不依赖其他 reviewer。

## 1. Overall judgment

**replace-component**

应替换的是低吞吐的串行 HDF5 attribute traversal 组件，而不是 direct-superfamily 路线、身份语义或数据源。当前失败属于明确的资源—实现不匹配；9.32% 的部分扫描既不能证明 279 个标识不可恢复，也不能支持任何生物学结论。

## 2. SOTA gap interpretation

**N/A。**

这是 claim-ineligible 的资产身份审计，不存在 SOTA、模型性能差距或可解释的 `gap_to_target`。模型超参数 tuning 完全无意义；当前只适合做有界的工程吞吐与确定性验证。

旧 `ACTIVE_GOAL.json` 与本路线指标不兼容，因此 `validate_goal=failed_run` 只应解释为强制停止信号，不能用于路线优劣、调参许可或晋级判断。

## 3. Comparability and benchmark fairness audit

| 维度 | 审计判断 | 依据与限制 |
|---|---|---|
| dataset/source version | 合同充分，实际结果未完成 | 冻结 Dfam 3.9 partition 3、64 GB H5、布局/大小/FamDB 元数据和终端计数。未做整文件 SHA 留有较小的位级漂移风险，但不构成本次取消原因。 |
| denominator/exhaustiveness | **未满足** | 合法终点必须覆盖 321,856 datasets、321,856 consensus attrs、321,818 model attrs。当前仅 30,000 datasets，即 9.321096%，不能作为 valid negative。 |
| identity semantics | 设计正确 | exact、case-sensitive `name` attr；仅“唯一 versioned accession + consensus SHA”可恢复。禁止 prefix、casefold、substring 和 genome-copy fallback。 |
| preprocessing | 无引入偏差 | 当前仅做 canonical `Families/...` 全量 attr traversal，没有 clustering、split、标签重写或模型执行。 |
| external assets | 基本充分 | 冻结 279 identifiers、6,432,583 occurrence mass、Dfam/FamDB 元数据和精确终端计数。正式重跑仍须重新核验这些输入守恒量。 |
| resource profile/claim | 语义公平，资源规划失败 | 0 GPU、CPU-only、claim-ineligible 符合合同；但串行扫描预计 4.41h，与 2h walltime 明显不匹配。资源失败不能转化为身份证据。 |

## 4. Semantic success and reproducibility audit

| 项目 | 判断 |
|---|---|
| metrics/audit parseability | 审计状态、metrics、manifest 可解析，并明确记录 `semantic_success=false` 和 `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`。 |
| finite values | 进度、覆盖率、时间、RSS、CPU 和读盘量均为有限且合理值；不存在完整 recovery 指标。 |
| execution health | 扫描在取消前健康推进，无 traceback，内存稳定。失败原因是确定的 walltime/吞吐不匹配，而非输入损坏或 identity 逻辑异常。 |
| partial-result guard | **通过**。30,000 条中的 0 candidates 仅作 telemetry，没有被提升为 valid negative。 |
| logs/config/manifests | 配置、原始进度、Slurm stderr、审计覆盖层和 18-entry hash manifest 足以复现“为何停止”。原始 `STATUS=RUNNING` 必须继续保持不可变，并由审计状态覆盖解释。 |
| Slurm accounting limitation | `sacct` 不可用削弱了完整资源核算，但 exact cancellation stderr 加上 `squeue` 清空足以确认作业已终止；不影响 failed-run 判定。 |

因此，本轮是工程执行意义上的可解释失败，不是语义成功，也不是 valid negative。

## 5. Architecture/implementation assessment

结果证明无索引 traversal 路径可以正确进入并读取 `Families` attrs；它没有证明任何目标标识存在或不存在。主要缺陷是逐 dataset 的小 attribute 访问使任务受存储延迟支配，4 CPU 基本闲置。

| 修复方案 | 优点 | 主要风险 | 建议 |
|---|---|---|---|
| A. 确定性四路只读分片 | 最可能在短 walltime 内完成；利用已申请 CPU；保持 exhaustive 语义 | 共享存储并行读可能不加速甚至抖动；分片遗漏/重叠；输出竞争；一个 shard 失败后错误聚合 | **首选，但必须先做小型吞吐与正确性 preflight** |
| B. 5–6h 串行重跑 | 代码变化最少，确定性最容易维持 | 计费浪费明显；4 CPU 中大部分闲置；重复读取已知慢路径；仍可能受文件系统波动超时 | 仅当并行 preflight 证明无收益后，另行评审 |
| C. 可恢复串行 checkpoint | 中断后可续跑，降低重复工作 | 不改善首次完整扫描的总成本；需严格绑定源指纹、游标、计数和输出哈希；错误 checkpoint 会漏扫/重复 | 可作为后续可靠性增强，不应是首个修复 |

四路实现至少需要以下 fail-closed guards：

- 每个 dataset path 精确归属一个冻结 shard；最终 union 无遗漏、pairwise intersection 为空。
- 各 shard 独立只读打开 H5，独立输出到隔离目录；父进程仅在全部成功后原子聚合。
- 任一 shard 异常、被取消或计数不完整，整体必须失败且禁止生成 recovery 结论。
- 聚合后严格满足三个终端计数以及 279 identifiers、6,432,583 occurrence mass 守恒。
- exact-case 匹配和唯一 accession/consensus SHA 规则保持不变。
- 重复执行的 shard assignment、计数、匹配记录和聚合哈希一致。
- 禁止继承当前 30k partial scan，除非另建并通过专门的 checkpoint/reuse 合同审查。

正式全量重提之前应先做 representative、冷缓存可辨识的吞吐 preflight，因为四路读取是否能加速取决于共享文件系统，而不是 CPU 数量。

## 6. Track recommendation

下一步只允许：

1. 实现确定性四路只读分片扫描器；
2. 完成独立 code review；
3. 运行一次小规模、0-GPU、claim-ineligible 的 R0 吞吐与分片正确性 preflight。

当前不授权完整 R0 正式扫描自动续跑。preflight 通过后，仍需根据实测速率重新确定 walltime，并对正式 R0 submission 单独过审。

继续禁止 R1 full catalog、R2 homology graph/split、GPU S0、S1 hierarchical/open-set，以及任何 claim。

## 7. Risks and blockers

- 四进程可能受同一存储带宽限制，吞吐不升反降。
- shard 定义或边界错误可能造成静默遗漏、重复扫描或不均衡。
- 多进程共享输出可能产生覆盖、交错写入或非确定性聚合。
- HDF5 并发读取配置不当可能触发锁、打开失败或库级异常。
- 不完整 shard 被误当作完整结果，是最高级别语义风险。
- 未做整文件 SHA 时，源文件被原位替换仍存在残余风险。
- attr 编码、缺失 attr、重复名称和 consensus SHA 冲突必须保持 typed failure，不能隐式归一化。
- 直接申请 5–6h 串行资源会重复支付确定可预见的 I/O 等待成本；48 GiB 和4 CPU也明显过度配置。
- 反复全量试跑会增加共享文件系统负载和计费浪费。
- 旧 `ACTIVE_GOAL.json` 继续存在路线指标错配，不能用其 progress/tuning 字段指导本审计。

## 8. Next action

运行一个新的有界实验：**`SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT`**。

资源建议：

- 4 CPU，16 GiB RAM，0 GPU；
- walltime 20 分钟；
- 四个互斥且覆盖不同 accession/path 区域的 representative shard；
- 每 shard 至少扫描约 10,000 datasets；
- 输出仅为吞吐、计数、分片覆盖和确定性报告，禁止输出 recovery/absence 结论。

提交前 code-review 必测：

- synthetic H5 上 union 完整、intersection 为空、每条 dataset 恰好一次；
- exact-case 正例/反例、重复名称、缺 consensus/model attr、非唯一 accession；
- 单 shard 故障、SIGTERM、截断输出和聚合中断均 fail closed；
- shard 输出隔离及最终原子聚合；
- 两次执行 assignment 与聚合哈希一致；
- 源文件只读、不修改 raw state；
- 输入 identifier/occurrence 守恒；
- 13/13 既有合同测试无回归。

停止规则：

- 任意遗漏、重复、输出竞争、HDF5 错误或非确定性，立即停止；
- 任一 shard 未完成，禁止聚合；
- 冷缓存聚合吞吐低于约 **60 datasets/s**，或保守投影不能在 90 分钟内完成全量扫描，不提交 2h 正式作业；
- preflight 出现的任何 279 匹配只作诊断，不得晋级为 recovery；
- 不得自动切换到长 walltime 串行方案。

## 9. Confidence

**High。**

失败类型、部分结果边界和禁止晋级条件都有直接证据支撑；“替换串行 traversal 并先做吞吐 preflight”的决策稳健。唯一仍不确定的是四路读取在实际共享存储上的加速幅度，这正是该有界 preflight 要回答的问题。
