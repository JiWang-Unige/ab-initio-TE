所有证据已验证完毕。以下是独立评审。

---

### 1. Overall judgment

**abandon-route**

本实验是一次执行质量极高的 **有效负结果（valid negative）**：冻结输入、哈希验证、deterministic 采样、独立 code review、精确资源合同、原子化发布、17/17 合约测试、1000 次 chromosome-block bootstrap——每一步都可复现且闭合。但科学结论明确：固定 exact seed-chain consensus collinearity 证据**不足以**恢复 parent-copy grouping。55.5% 的 mapping 覆盖率未达 60% 门限；13.9% 的 exact recovery 远逊于 GAP100 的 37.2%（bootstrap 95% CI 全负）；topology 仅 10.5%；false fusion 7.6% 超过 5% 上限。该路线不应继续。

这不是实验执行失败——它是**信息充分性审计成功**：用最严格的合同回答了"这个证据类型够不够"的问题，答案是"不够"。应该记录为保守限制（conservative limitation），写入 `docs/10_findings.md` 和 `docs/09_decisions_log.md`，并设定明确的科学重入条件。

---

### 2. SOTA gap interpretation

- **Current metric**: information_sufficiency_gate_pass = 0.0（二进制 gate，未通过）
- **SOTA metric**: N/A — 本实验是 claim-ineligible CPU 信息充分性审计，不涉及 SOTA 比较
- **Absolute gap**: N/A
- **Relative gap**: N/A
- **Is tuning justified?** **No，且不适用。** 本实验不涉及可调参模型。固定 seed-chain 参数（k=13, stride=4, posting cutoff=64, diagonal tolerance ±32bp, seed_coverage≥0.08, winner margin≥0.02）的调优被显式禁止，且即使放开调参，mapping 覆盖率 55.5% 与 GAP100 在各维度上的巨大差距（harmonic gap ~0.36, topology gap ~0.37, boundary gap ~0.19）暗示**这不是参数问题，而是证据类型的根本信息不足**。符合 CLAUDE.md §3 的"gap ≥ 0.05 优先怀疑架构假设"原则。

---

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset version | Pass | Rice RGAP7 `all.con` SHA-256 `db8b7efb...`、EDTA v2.3.0 positive TSV `06ac8f7c...`、consensus `rice7.0.0.liban` `bb470806...`，全部冻结哈希，pre/post 一致 |
| Official split / same split | Pass | 按 `class_root × row_count_bin` 分层采样，deterministic seed=20260812，不看 evaluator outcome；truth 字段物理隔离于 public bundle |
| Metric implementation | Pass | 仅允许 T1 positive-only 指标；禁止 whole-genome precision/recall/F1；1000 次 paired chromosome-block bootstrap 内每 replicate 重选 comparator max；无 topology truth 的 chromosome 显式排除 |
| Preprocessing | Pass | 冻结输入同时哈希验证；public bundle 物理排除 truth 字段；17 项合约测试覆盖 |
| External weights / pretrained backbone version | N/A | 无模型、无训练、无 checkpoint |
| Test-time inference protocol | N/A | 无推理 |
| Resource profile supports claim? | N/A | Profile 为 `rice_t1_cpu_information_sufficiency_audit`，claim-ineligible，明确不授权任何 claim |

---

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Metrics file exists and is parseable | Pass | `metrics.json` 382 行，schema_version 明确，所有键完整 |
| Values finite / no NaN or Inf | Pass | 所有 candidate/comparator/bootstrap 值均有限；无 NaN/Inf |
| Loss trend or expected pattern is sane | N/A | 无训练损失 |
| Seed variance known or not needed | N/A | Deterministic 方法，无随机种子；bootstrap 不确定性的 95% CI 已报告 |
| No suspicious leakage signal | Pass | 17 项合约测试包括 `test_public_bundle_physically_excludes_truth_fields`、`test_truth_tamper_cannot_change_assembler_output`；evaluator 不向 assembler 暴露 truth |
| Logs/config/artifacts sufficient to reproduce | Pass | 17-file AUDITED_MANIFEST 全部哈希匹配；preflight log、environment snapshot、scontrol snapshot、slurm job info、code review gate 均留档；`docs/experiments/` 记录完整合同 |

---

### 5. Architecture assessment

#### 机制假设的含义

结果明确表明：**仅靠 leaf 序列到 frozen consensus 的固定 exact seed-chain identity/strand/coordinate 证据，不足以在 chromosome 尺度上可靠重建 TE parent-copy grouping。** 这不是"证据完全无信息"——shuffle null 的 exact recovery 仅 0.001，candidate 为 0.139，说明 consensus collinearity 确实携带信号。但信号强度远不足以构成实用分组器：近半数 leaf 甚至无法形成有效 mapping（44.5% 未映射），且成功映射的 leaf 在全局 collinearity partition 下产生的分组质量远逊于简单的 100bp genomic gap 合并。

#### 不足归因分析

不足是**多因叠加**，不可归咎于单一组件：

1. **证据层面（mapping）**：`k=13` exact seed-chain 对 diverged TE copies 的 recall 天然有限。55.5% 的 mapping 率说明近半数 leaf 与 consensus 差异过大（插入/缺失/SNP 积累），或在 repetitive 区域被 posting cutoff=64 过滤。**这是 exact k-mer consensus mapping 作为单一证据源的根本局限。**

2. **全局 partition 层面**：chromosome-wide deterministic minimum path cover 仅使用 consensus identity + strand + monotonic coordinates，**完全无视 genomic gap**。这使得同一 consensus 家族在染色体上的所有 mapped copies（正链）被强行压入同一条单调链——而 TE 插入在基因组上天然是散布的，并非 collinear。GAP100 仅仅引入 100bp genomic gap 就把 exact recovery 从 13.9% 提升到 37.2%，说明**genomic proximity 是 parent-copy grouping 的关键信号，不能抛弃**。

3. **truth 限制**：T1 positive-only 不允许区分"candidate 分对了但 truth 未标记"和"candidate 分错了"——未标记空间永远是 unknown。

4. **方法层面**：该机制本质上在做一个很强的假设——同一 consensus 的 TE copies 在染色体上按 consensus 坐标单调排列——而这个假设在生物学上不成立。TE 插入是转座事件，不是 tandem duplication，不存在 consensus-coordinate 单调性。

#### 未来正交机制（仅列举，不推荐现在跑）

1. **Multi-evidence partial labels**：不要求每个 leaf 被确定性地映射到单一 consensus，而是用多个候选 consensus 的软分配（soft assignment）+ partial label learning 框架，让 grouping 在不确定性下联合优化。这直接回应 mapping 率不足的问题。

2. **Counterfactual direct-SF invariance**：不在 fragment 层面做 grouping，而是训练一个 superfamily classifier 对原始 fragment 和 consensus-grouped fragment 做 counterfactual 一致性检验——如果 grouping 正确，superfamily 预测应在 grouped/ungrouped 表示之间保持不变。

3. **Evolutionary-state decay modeling**：为每个 TE copy 显式建模其相对 consensus 的 evolutionary distance（分支长度），用系统发育距离而非 consensus 坐标单调性来约束 grouping。这直接回应"collinearity 假设在生物学上不成立"的问题。

4. **CopyGraph-SSL**：在 frozen leaf embeddings（来自已有 TE-FM checkpoint）上构建 k-NN graph，用 self-supervised link prediction 学习 copy-copy 边，不依赖 consensus mapping。这与当前路线完全正交——证据从"序列到 consensus 的 mapping"切换到"预训练 embedding 空间中的邻居结构"。

---

### 6. Track recommendation

- **不应晋升（Do not promote）。** 候选在所有 promotion gate 上失败（mapping 覆盖率、exact recovery、pairwise harmonic、false fusion、boundary curves、topology），且与 GAP100 的差距在 bootstrap 95% CI 上全负。这不是"接近 SOTA 需要 scale-up"的情况，而是"证据类型本身不够"。

- **该组件应停止（Stop this exact component）。** 固定 exact seed-chain consensus collinearity + chromosome-wide deterministic min-path-cover 路线已被本审计证否。这不是 DEC-001/002 的重演——它是一个独立的正交尝试——但其结论同样明确：该机制假设不成立。不应在调参、换物种、或换 consensus library 上继续消耗 CPU。

---

### 7. Risks and blockers

| Risk / Blocker | Severity | Mitigation |
|---|---|---|
| `validate_goal.py` 报告 `failed_run`（selector schema 不兼容） | **Medium** — 不改变 route-local valid-negative，但 `/pursue` 的确定性闸门会硬停 | 需在 `/pursue` 恢复前修订 `ACTIVE_GOAL.json` 使其 schema 与该 milestone 对齐，或显式 waive selector keys |
| 当前 `ACTIVE_GOAL.json` 仍指向旧的 selector/decoder milestone | **Low** — `/pursue` 会因 `failed_run` 硬停，不会静默续跑 | 通过 `/revise-goal` 或 `/route-reset` 更新 goal 合约 |
| 无进一步 F 计算授权 | **Info** — 这是设计意图，不是阻塞 | 明确等待 re-entry conditions 满足后才能申请新一轮 CPU/GPU |
| TE consensus collinearity 作为 grouping 信号的生物学不合理性未被广泛认知 | **Low** — 本审计提供了严格的实证 | 将 mechanisistic insight 写入 `docs/10_findings.md` 供后续参考 |

---

### 8. Next action

**立即行动（非计算）**：将本路线归档为 `DEC-003: ABANDONED_CONSENSUS_COLLINEARITY_INFORMATION_INSUFFICIENT`，写入 `docs/09_decisions_log.md`。

**归档内容必须包含**：
- 路线摘要：fixed exact seed-chain consensus collinearity + chromosome-wide deterministic min-path-cover
- 终态：`VALID_NEGATIVE_INFORMATION_INSUFFICIENT`
- 关键数字：mapping 55.5%、exact recovery 13.9% (GAP100 37.2%)、topology 10.5%、false fusion 7.6%
- 机制级教训：consensus-coordinate 单调性在生物学上不成立（TE 是转座而非 tandem duplication）；genomic proximity 是不可丢弃的信号
- Cousin 列表：DEC-001（gap/HMM）、DEC-002（local-graph/lightweight-head）、现 DEC-003
- 与 DEC-001/002 的区别：本路线不使用 prediction-confidence、genomic-gap、HMM/CRF；失败原因不同（信息不足 vs 过拟合/架构不当）

**科学重入条件（explicit re-entry criteria）**：
1. 新的证据类型必须能覆盖 ≥80% 的 leaf（解决 55.5% mapping 瓶颈），**或**
2. 新的 grouping 机制必须同时使用 genomic proximity + 至少一种其他正交信号（如 embedding similarity、evolutionary distance、或 partial consensus assignment），**且**
3. 必须在同一 frozen Rice T1 采样上通过当前全部 promotion gates（不降低标准），**且**
4. 必须先通过 CPU-only bounded falsification（不越过本审计的资源预算：8 CPU/32 GiB/2h），**且**
5. 须显式解释为何新机制不受"consensus-coordinate 单调性假设不成立"这一机制级教训的影响。

**之后**：运行 `/note-gate` 将本讨论的机制级洞察（consensus collinearity 失败原因、genomic proximity 必要性、未来正交方向）路由到 `docs/15` 和 `docs/10`。

---

### 9. Confidence

**High**

理由：
1. 实验执行质量极高：冻结输入、17/17 哈希验证、独立 code review (PASS)、精确资源合同、17 项合约测试全部通过、1000 次 bootstrap、原子化终态发布。
2. 所有指标方向一致：没有一个 promotion metric 接近通过——这不是"差一点调参就行"，而是全面的、bootstrap 意义上显著的结构性不足。
3. 机制假设在生物学上有根本性问题（consensus-coordinate 单调性 ≠ TE 插入模式），这意味着即使放开 mapping 参数调优也不可能逆转结论。
4. 唯一的"不确定"来源——`validate_goal.py` 的 `failed_run`——是 ACTIVE_GOAL schema 不兼容导致的自动化硬停，不改变 route-local 科学结论，且已被正确识别和隔离。
