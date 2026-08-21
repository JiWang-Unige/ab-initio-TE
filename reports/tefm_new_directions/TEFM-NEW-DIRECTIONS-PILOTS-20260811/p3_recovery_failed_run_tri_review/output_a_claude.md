---

# 独立全范围研究评审报告

**评审人**：A=Claude（独立外部评审）  
**评审对象**：`SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1`  
**评审日期**：2026-08-12  
**评审依据**：全范围书面材料 + 全部磁盘产物逐项验证

---

## 1. 总体判断

**`continue-current-route`**

本实验是一次正确的、被 walltime 不足截断的身份恢复扫描。它不是语义失败、数据损坏或设计错误——它是在正确轨道上跑到一半被资源上限挡住的执行。实现质量（独立代码审查 PASS、13/13 分配侧测试通过、无 traceback、RSS 仅 121 MiB、checkpoint 按约每 10,000 datasets 触发、进度 JSONL 可解析）足以支撑"同路线修复后重跑"而非"换路线"。失败模式是**资源规格错误**（2h walltime vs. 串行扫描所需的 ~4.4h），不是方法错误。

**排除的判断及理由**：
- `abandon-route`：不正确。上次 Job 11523938 因假设 ByName 索引存在而失败，本次已正确移除该依赖并取得正确进展。两次失败原因不同，本次是纯资源维度，不应放弃已验证正确的语义路径。
- `scale-to-track-b`：不适用。这是 CPU 资产审计，没有 Track A/B 语义。
- `tune-only-if-near-sota`：不适用。没有 SOTA 比较维度。
- `change-backbone` / `change-objective-or-loss`：不适用。没有模型架构或损失函数。
- `return-to-literature`：不正确。不需要新文献——问题已被精确定位为串行 I/O 形状与 walltime 的不匹配。

---

## 2. SOTA 差距解读

**N/A**。本实验是 Dfam 3.9 partition 3 的身份元数据完整性审计（CPU 资产验证），不涉及模型训练、benchmark 指标或 SOTA 比较。`validate_goal.py` 正确地返回 `failed_run`（rc3），其 `gap_to_target=null`、`tuning_allowed=null` 是因为当前 `ACTIVE_GOAL.json` 仍是旧的 selector/decoder goal，与本路线的度量空间不兼容。这不是 validate_goal 的缺陷——它在不兼容场景下正确地只提供了"停下来"的信号，没有输出无意义的 gap/tuning 建议。

**调参是否有意义**：不适用。串行 h5py 小属性访问是 I/O 形状问题，不是超参数问题。

---

## 3. 可比性与 benchmark 公平性审计

| 维度 | 状态 | 详情 |
|---|---|---|
| **数据集/源版本** | ✅ 通过 | Dfam 3.9 partition 3 (`dfam39_full.3.h5`, 63,939,647,016 bytes)，由 Job 11524255 的身份审计 payload（SHA 已 pin）冻结 |
| **分母/穷举性** | ✅ 通过 | 合约要求扫描全部 321,856 个 Families datasets、321,856 个 consensus 属性、321,818 个 model 属性。代码在扫描完成后会做 `DATASET_COUNT_DRIFT` / `CONSENSUS_ATTRIBUTE_COUNT_DRIFT` / `MODEL_ATTRIBUTE_COUNT_DRIFT` 硬性校验 |
| **身份语义** | ✅ 通过 | 严格大小写精确匹配 `name` 属性。已冻结禁止：前缀猜测、casefold、子串匹配、基因组 copy 代理、聚类、split 构造、模型执行 |
| **预处理** | ✅ 通过 | consensus 做 `.upper().replace("U","T")` 标准化后 SHA-256。无训练集拟合、无 test-time 校准 |
| **外部资产** | ✅ 通过 | 7 个 pin 输入全部通过 SHA-256 校验（identity_config、identity_evaluator、identity_layout_manifest、identity_payload、identity_identifier_audit、evaluator_contract、famdb_rmlib_config），`P3_EXPECTED_EXPLICIT_BYNAME_ABSENCE` 守卫通过 |
| **资源 profile / claim** | ✅ 通过 | 0 GPU、claim-ineligible。代码审查 verdict=PASS，`pre_submit_gate.py` 通过，owner lock 机制就位。`sbatch` 脚本无 `--gres`、显式 `test -z "${SLURM_JOB_GPUS:-}"` 守卫 |

**公平性结论**：本次审计与 SOTA 比较无关；其可比性合约（资产身份而非模型指标）在输入 pin、穷举分母、大小写语义和禁止回退路径四个维度上均被代码强制实现，无缺口。

---

## 4. 语义成功与可复现性审计

| 维度 | 状态 | 详情 |
|---|---|---|
| **指标/审计可解析性** | ✅ 通过 | `metrics.audited.json` 是合法 JSON，所有字段类型正确。`validate_goal.json` 可解析。`scan_progress.jsonl` 每行合法 JSON，包含 3 个 checkpoint 事件 |
| **有限值** | ✅ 通过 | `datasets_scanned=30000`、`projected_full_scan_seconds=15878`、`elapsed_seconds_before_cancel=1480` 均为有限正数 |
| **执行健康** | ✅ 通过 | 无 traceback、无 NaN、无 OOM。RSS ~121 MiB、CPU 累计 ~8s。磁盘读取持续增长（正常 I/O-bound 特征）。13/13 分配侧测试全部通过 |
| **部分结果守卫** | ✅ 通过 | 9.32% 覆盖率被显式标记为 `partial_scan_is_scientific_evidence: false`、`zero_hit_claim_allowed: false`。未产生身份恢复结论、未授权 R1/R2/GPU/S1 |
| **日志/配置/清单** | ✅ 通过 | 18 条 SHA-256 清单全部通过（含 `AUDITED_STATUS`、`JOBID`、`code_review_gate.json`、`metrics.audited.json`、`result_semantic_audit.json`、`validate_goal.json`、8 个 preview 产物、scan_progress.jsonl、env.json、RUN_MANIFEST.json） |
| **Slurm 计费限制** | ⚠️ 已知限制 | `slurmdbd` 拒绝连接导致 `sacct` 不可用。精确 MaxRSS/billing 未知，但 cancellation 由 Slurm stderr 行（`CANCELLED … due to SIGNAL Terminated`）和 squeue 消失确认。这不影响本次评审的结论——失败原因是 walltime 不足，已有充分证据 |

**可复现性**：输入全部 pin、代码全部 hash、环境快照（Python + h5py 版本）写入 `env.json`。在相同 H5 文件上重跑相同代码应得到相同进度曲线。唯一不可复现的因素是 I/O 性能（取决于集群文件系统负载），但数量级（~4.4h）是稳定的。

---

## 5. 架构/实现评估

### 结果意味着什么

本次运行证明了两件事：
1. **ByName 索引依赖已正确移除**（与 Job 11523938 的关键区别）。`iter_family_datasets()` 通过后序深度优先遍历 `Families` group 成功访问了所有 dataset 及其 `.attrs`，且显式守卫 `Lookup/ByName` 不存在时才会继续。
2. **串行 h5py 小属性访问在 63.9 GB HDF5 上的 I/O 代价被低估了**。尽管 CPU 累计仅 ~8s、RSS 仅 ~121 MiB（说明不是计算密集或内存密集），但 2h 内只能完成 ~9.3% 的穷举扫描。瓶颈是 HDF5 的 per-dataset attr read 的寻道/元数据开销——321,856 个 dataset 每个都需要独立的 attr 访问。

这不是代码缺陷，而是**资源规格假设与实际 I/O 形状之间的差距**。

### 修复选项比较

#### 选项 A：确定性 4 路只读不相交分片扫描（推荐）

**方案**：将 `Families` 树按 accession 前缀（如 `Families/DR/`、`Families/DT/`、`Families/DM/`、`Families/DL/` + 其余）分为 4 个不相交的子树区间，每个子进程独立打开 H5（只读）、扫描分配区间、产出候选行。主进程在子进程全部退出后合并候选行并做 union/count/conservation 校验。

**优势**：
- 可将 walltime 压缩到 ~1.1–1.5h（4 路并行时每路约 1.1h 外加 merge 开销），适用原 2h 限额
- 利用已分配的 4 CPU
- H5 只读打开不冲突（h5py 在只读模式下多进程安全）

**必须的失败守卫**：
1. **不相交分片验证**：分片边界必须在代码中显式定义（如按第二级子 group 名前缀），且启动时做 `assert len(set(shard_intervals)) == total_subgroups` 防重叠/遗漏
2. **每路独立 count 校验**：每路返回自己扫描的 dataset 数，主进程做 `sum(child_counts) == 321856` 硬闸
3. **候选行 union 后去重**：按 `(identifier, versioned_accession, consensus_sha256)` 去重，确保分片边界不产生重复
4. **occurrence mass conservation**：最终 `resolve_targets` 的 conservation 检查不变（已有代码）
5. **输出原子性**：只有主进程写 staging 目录产物；子进程只通过 stdout/临时文件返回候选行
6. **全部子进程退出码检查**：任一非零 → 整体 `RECOVERY_FAILED`

**劣势**：
- 需要知道 `Families` 的子 group 结构来定义分片边界
- 如果子 group 大小严重不均，walltime 由最大的分片决定

#### 选项 B：5–6h 串行重跑

**方案**：将 `--time` 改为 06:00:00，其余不变。

**优势**：零代码改动，已有代码质量已验证。

**劣势**：
- 浪费 4 CPU 中的 3 个（串行只用 1 个）
- walltime 越长，被更高优先级作业抢占的概率越大
- 如果实际 I/O 比线性投影更慢（例如文件系统负载波动），6h 也不一定够
- 不解决"串行访问 32 万个小 attr 效率低"的根本问题

#### 选项 C：可恢复的 checkpoint 串行扫描

**方案**：在选项 B 的基础上增加断点续扫——记录最后完成的 dataset 路径，重启时从该位置继续。

**优势**：不怕再次被 walltime 截断。

**劣势**：
- checkpoint 语义复杂：`iter_family_datasets` 的遍历顺序依赖 `sorted(group.keys(), reverse=True)`，需要在重启时精确定位到同一 dataset
- 断点续扫 = 部分结果可复用，合约当前明确禁止部分扫描提升。需要额外的 code-review 来审计"续扫不等于部分结果提升"
- 总 walltime 仍然长（4–6h），且实现复杂度高于选项 A

### 预提交吞吐量基准测试的必要性

**强烈建议**。在提交任何修复之前，先跑一个 **mini benchmark**：随机采样 10 个 `Families` 的子 group（覆盖不同前缀），串行扫描 1,000 个 dataset 并计时，得到 per-dataset 的平均 attr 访问时间。这可以在 5 分钟内完成（甚至可以在登录节点用 python 一行脚本完成，因为仅读 1,000 个小 attr 不算重计算），提供：
- 更精确的 walltime 估算（不是线性外推 30,000 个点）
- 分片大小不均匀时的最差分片 walltime 估算
- 如果 per-dataset 时间方差大，说明某些子 group 的 HDF5 布局更差，需要据此调整分片策略

---

## 6. Track 推荐

**当前许可**（本轮评审后）：
- ✅ **可执行**：单一有界的 CPU 修复实验，将穷举扫描完成（通过选项 A / B / C 之一）
- ✅ **可执行**：预提交吞吐量 mini benchmark（≤1000 datasets，≤5 min，登录节点可跑）
- ✅ **可执行**：修复后的代码审查（`/code-review-gate`）

**持续禁止**（本轮不授权，需独立 gate 通过）：
- ❌ R1 全量 catalog 阶段
- ❌ R2 同源图/split 阶段
- ❌ GPU S0 direct-superfamily baseline
- ❌ S1 hierarchical/open-set superfamily
- ❌ 任何 claim
- ❌ 部分扫描结果提升为 valid negative
- ❌ 将 `X13_LINE` 从 audit-only 移入 target
- ❌ 前缀猜测/casefold/基因组 copy 回退
- ❌ 合并 identity recovery 与 homology clustering

---

## 7. 风险与阻断项

| 风险 | 严重程度 | 缓解措施 |
|---|---|---|
| **分片边界定义错误导致遗漏 dataset** | 🔴 高 | 必须先发现 `Families` 的子 group 拓扑（`h5ls -r` 或 `visititems`），显式编码分片边界，并用 sum(counts)==321856 守卫 |
| **多进程 HDF5 并发冲突** | 🟡 中 | 只读打开在 h5py 中安全，但必须确认 `te_benchmark` env 的 h5py 是线程安全构建。可改用子进程各自打开独立 file handle（推荐） |
| **I/O 争用** | 🟡 中 | 4 路同时读同一 64 GB 文件可能触发文件系统瓶颈，导致实际 walltime 比线性投影高。mini benchmark 应做 2 路并发 vs 1 路串行对比 |
| **分片不均** | 🟡 中 | `Families/DR/`（Dfam Repeat）可能包含绝大多数 dataset，导致某一路 walltime 远超其他。需先统计子 group 大小，按 dataset 数而非子 group 数分片 |
| **重复计费浪费** | 🟢 低 | 当前 2h/4CPU 的失败作业计费极低（CPU-only、无 GPU、仅 ~25min 实际消耗）。修复后最多再消耗 ~1.5–6h × 4CPU，在 `private-teodoro-gpu` 免费 partition 上零计费 |
| **slurmdbd 不可用** | 🟡 中 | 若下次 sacct 仍不可用，无法获取 MaxRSS 确认。缓解：代码内嵌 `psutil` RSS 采样写入 progress JSONL（可选增强） |

---

## 8. 下一步行动

### 推荐的单一有界修复实验

**实验 ID**：`SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R2`

**修复策略**：**选项 A（确定性不相交分片）为主方案，选项 B（延长 walltime 串行）为 fallback**。具体步骤：

1. **预提交 mini benchmark**（~5 min，登录节点可做）：
   - 用 h5py 遍历 `Families` 的直接子 group，统计每个子 group 的 dataset 数量
   - 随机选 5 个子 group，每个扫描前 200 个 dataset 计时，得到 per-dataset attr 访问时间的分布
   - 据此确定分片方案（按 dataset 数大致均分为 4 份）和最差分片 walltime 估算

2. **实现确定性 4 路分片扫描**：
   - 新增 `scan_partition_sharded()` 函数
   - 分片边界基于 `Families` 第二级子 group 前缀显式编码
   - 每路独立打开 H5（`h5py.File(..., "r")`）、独立扫描
   - 主进程 `concurrent.futures.ProcessPoolExecutor(max_workers=4)` 收集结果
   - 合并后做 union 去重 + sum(count)==321856 硬闸

3. **代码审查测试清单**（至少 8 项）：
   - [ ] 分片边界无重叠无遗漏（给定已知的子 group 列表，验证 union 覆盖全集）
   - [ ] sum(child_dataset_counts) == 321856
   - [ ] 候选行去重逻辑正确（同一 identity 出现在两个分片边界 → 只计一次）
   - [ ] 任一子进程非零退出 → 整体失败
   - [ ] occurrence mass conservation 不变
   - [ ] 多进程下 owner lock / SLURM_JOB_ID guard 仍生效
   - [ ] `sbatch` 脚本 `#SBATCH --time=02:00:00` 不变（分片后应能在 2h 内完成）
   - [ ] ByName 缺席守卫、consensus/model count drift 守卫、正式 Slurm 守卫全部保留

4. **资源封套**：
   - Partition：`private-teodoro-gpu`
   - CPU：4（不变）
   - 内存：48 GiB（不变；如 4 路各开 H5 handle 可能略增，但只读 handle 开销极小）
   - Walltime：2h（不变——这是分片方案的核心目标）
   - GPU：0（不变）

5. **停止规则**：
   - mini benchmark 显示 per-dataset 时间 >0.05s → STOP，报告实际 I/O 瓶颈
   - mini benchmark 显示最差分片仍需要 >1.5h → STOP，考虑 8 路分片或回退选项 B
   - 分片后扫描完成但 count drift 触发 → STOP，排查分片边界
   - 2 次连续 `FAILED_RUN`（含本次 R1）→ STOP，通知主人，不自动 R3
   - ✅ 扫描完成 + 全部 count/conservation 守卫通过 → 无论结果是 RECOVERY_COMPLETE 还是 IDENTITY_RECOVERY_TYPED_BLOCK，均为 terminal success，进入独立的 code-review gate 后再决定是否授权 R1 全量 catalog

**仍不授权**：R1 全量 catalog、R2 同源图/split、GPU S0、S1、任何 claim。

---

## 9. 置信度

**High**

理由：
- 全部 18 条 SHA-256 清单已独立验证通过
- 代码审查 verdict=PASS、13/13 测试通过、无 traceback——实现质量无争议
- 失败原因是纯资源维度（walltime 不足），非方法或语义错误。线性外推基于 3 个真实 checkpoint（10k/20k/30k）的进度时间戳，方向正确
- 与上次 Job 11523938 的对比清晰：ByName 依赖已正确移除，本次取得了上次未能取得的正确进展
- 修复方向明确（分片并行），风险可控（只读 H5 多进程安全、sum guard 防遗漏）
- 唯一不确定的是 `Families` 子 group 的具体大小分布——这正是 mini benchmark 要在动手前解决的
