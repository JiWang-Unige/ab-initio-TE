OpenAI Codex v0.147.0
--------
workdir: /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 019ff4df-51f4-70c2-8db4-233f73e711c5
--------
user
You are Reviewer B (Codex). You are independent from the other reviewers.


You are an independent external reviewer. Do not assume a special role. Review all dimensions and recommend the single next decision most likely to advance a publishable TE foundation-model project. Output professional Simplified Chinese and include the exact heading `### 1. Overall judgment`.

## 1. Research question, scope and north star

The long-term north star is a publishable TE foundation model with rigorous leakage-safe, cross-species evaluation. This experiment is a claim-ineligible CPU information-sufficiency audit for one fragmentation component: can immutable positive TE fragments be grouped into biological parent copies using only label-blind leaf-sequence evidence mapped to frozen TE consensus identity, strand and consensus coordinates?

This is not a whole-genome benchmark. Truth is Rice T1 positive-only; unlabelled genome is unknown, not negative. Whole-genome/bp/segment precision, recall and F1 are forbidden. The experiment cannot claim SOTA or authorize GPU work.

## 2. Method under test

- Frozen Rice RGAP7 assembly, EDTA v2.3.0 positive truth and Rice consensus library; all hashes were verified before execution.
- Sampled 756 truth groups (2–12 rows), 2,450 immutable leaves across Chr1–Chr12, and 304 topology-evaluable groups. Sampling was stratified by class root and row-count bin without reading mapping/evaluator outcomes.
- Public assembler receives only leaf coordinates/sequences; truth parent IDs, parent boundaries, classes, names and topology markers are physically evaluator-only.
- Fixed k=13 exact seeds, stride 4, repetitive posting cutoff 64, diagonal tolerance ±32 bp, at least 3 query seed positions, seed query-bp coverage ≥0.08 and winner margin ≥0.02. These produce consensus identity/strand/coordinates; they are not directly a join rule.
- A chromosome-wide DAG links only monotonic consensus-coordinate evidence for the same consensus identity and strand, followed by deterministic minimum path cover. It never reads genomic gap or truth.
- Every leaf is retained exactly once. Comparators are RAW singleton and experiment-local positive-only GAP20/GAP100. A deterministic evidence-shuffle null tests whether evidence carries signal.
- Promotion requires mapped fraction ≥0.60, recovery/harmonic improvements over the best comparator, exact recovery improvement over shuffle, false fusion ≤0.05, comparator-safe boundary/fusion/topology metrics, topology ≥0.95 and leaf retention exactly 1.

This mechanism was deliberately designed outside abandoned DEC-001/002 cousins: no threshold smoothing, HMM, CRF, duration/survival loss, local fragment graph, lightweight interval head or leaf deletion. Do not recommend tuning those cousins.

## 3. Result and trend

Job 11531090 completed 0:0 in 25 seconds with exact 8 CPU/32 GiB/2h/0GPU. Route-local semantic success is true; scientific screen executed; claim eligibility and whole-genome metrics are false. All input, command, scheduler, environment and 17 payload hashes independently verify. Values are finite; 1,000 chromosome-block bootstrap replicates used pooled sufficient statistics and reselected the best comparator inside each replicate.

Candidate CONSENSUS_COLLINEARITY:

- mapped leaf fraction 0.555102; leaf retention 1.0
- exact group recovery 0.138889; complete group recovery 0.142857
- pairwise same-parent purity/recall/harmonic 0.924138/0.184930/0.308188
- cross-RM-ID false fusion 0.075862; safety 0.924138
- topology preservation 0.105263
- boundary within 5/10/25/50 bp 0.186508/0.189153/0.195767/0.227513

Best comparators:

- GAP100 exact recovery 0.371693, harmonic 0.669109, topology 0.473684, all boundary curves 0.376984, false fusion 0.090995.
- GAP20 exact recovery 0.202381, harmonic 0.516570, topology 0.355263, false fusion 0.051622, safety 0.948378.
- Shuffle null exact recovery 0.001323, harmonic 0.000540, false fusion 0.988095.

Bootstrap candidate-minus-best-comparator:

- exact recovery mean -0.232150, 95% interval [-0.280093,-0.173410]
- pairwise harmonic mean -0.359041, interval [-0.448915,-0.273644]
- topology mean -0.371362, interval [-0.452308,-0.274306]

Only leaf retention, exact-recovery separation from shuffle and topology evaluability pass. Every comparator, coverage, boundary, false-fusion and topology promotion gate fails. Terminal is `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`.

The prior attempt Job11529694 failed before payload due incomplete reviewed-runtime closure. That sole engineering issue was independently fixed without changing scientific code or frozen inputs; Job11531090 is therefore the first and final scientific result.

## 4. Comparability and known limits

- T1 gives positive recovery/boundary/topology and false-fusion proxy only; it cannot establish whole-genome precision or absence of false positives.
- GAP20/GAP100 are positive-only diagnostic comparators, not production methods and not historical MERGE_STRICT/LOOSE identity claims.
- Current ACTIVE_GOAL.json is an older selector/decoder milestone. `validate_goal.py` returns `failed_run` because selector keys are absent. This is a mandatory automation stop, not a route-local semantic failure.
- No model, training loss, checkpoint, seed variance or SOTA comparison applies. Treat those review rows as N/A, not as evidence of failure.
- No further F compute is currently authorized. Do not propose tuning fixed seed thresholds on these test families, Fly/H0 escalation, or revival of abandoned gap/HMM/CRF/local-graph/lightweight-head cousins.

## 5. Decision question

Decide whether this component should be recorded as a conservative limitation or abandoned component/route, and give explicit scientific re-entry conditions. Assess whether the above is a trustworthy valid negative, what it implies mechanistically, and whether any genuinely orthogonal future mechanism remains plausible without consuming more compute now.

## Artifacts

- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/metrics.json`
- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/result_semantic_audit.11531090.json`
- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/AUDITED_MANIFEST_11531090.sha256`
- `configs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.yaml`
- `docs/experiments/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.md`
- `docs/09_decisions_log.md` DEC-001/002

## Required output

### 1. Overall judgment
Choose exactly one:
- continue-current-route
- scale-to-track-b
- tune-only-if-near-sota
- replace-component
- change-backbone
- change-objective-or-loss
- run-sanity-check-first
- comparability-blocker
- abandon-route
- return-to-literature

### 2. SOTA gap interpretation
- Current metric:
- SOTA metric:
- Absolute gap:
- Relative gap:
- Is tuning justified? yes/no/only-if-near-sota. Explain.

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset version | | |
| Official split / same split | | |
| Metric implementation | | |
| Preprocessing | | |
| External weights / pretrained backbone version | | |
| Test-time inference protocol | | |
| Resource profile supports claim? | | |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Metrics file exists and is parseable | | |
| Values finite / no NaN or Inf | | |
| Loss trend or expected pattern is sane | | |
| Seed variance known or not needed | | |
| No suspicious leakage signal | | |
| Logs/config/artifacts sufficient to reproduce | | |

### 5. Architecture assessment
- What does the result imply about the mechanism hypothesis?
- Is insufficiency attributable to evidence, mapper, global partition, truth limitations, or another component?
- Name 2–4 genuinely orthogonal future architecture/evidence moves, without recommending a run now.

### 6. Track recommendation
- Should this candidate be promoted? Why?
- Should this exact component stop?

### 7. Risks and blockers

### 8. Next action
Give one concrete non-compute decision or blocker-resolution step and explicit re-entry criteria.

### 9. Confidence
High / Medium / Low, with reason.

2026-08-12T07:28:26.831036Z ERROR codex_core::shell_snapshot: Shell snapshot validation failed: Snapshot command exited with status exit status: 2: /home/users/j/jwang/.codex/shell_snapshots/019ff4df-51f4-70c2-8db4-233f73e711c5.tmp-1786519704100932437: line 636: syntax error near unexpected token `('

hook: SessionStart
hook: SessionStart
hook: SessionStart Completed
hook: SessionStart Completed
codex
我会按 `$tri-review` 的独立审阅规范核对给定产物、配置与既有弃线路由，重点区分“运行失败”与“可信的科学负结果”。本轮只做只读评审，不修改项目文件，也不提出追加计算。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/bash -lc "sed -n '1,240p' .agents/skills/tri-review/SKILL.md" in /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
 exited 1 in 0ms:
bwrap: Creating new namespace failed: No space left on device

codex
只读 shell 当前因节点命名空间资源耗尽（`bwrap: No space left on device`）未能启动。我先重试最小化读取；若仍失败，将严格基于你提供的已审计数值完成评审，并把“未能二次打开本地产物”明确计入置信度，而不会伪称已复核。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/bash -c "pwd && sed -n '1,260p' .agents/skills/tri-review/SKILL.md" in /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
 exited 1 in 3ms:
bwrap: Creating new namespace failed: No space left on device

codex
### 1. Overall judgment

**abandon-route**

这是一个可信的、可复现的有效负结果。共识序列证据显著优于 shuffle，证明其中含有真实生物信号；但该信号不足以单独完成 parent-copy reconstruction。候选在覆盖率、恢复率、边界、融合安全性和拓扑保持上全面未过预注册门槛，且 bootstrap 区间远离零。

应终止的是“仅凭 consensus identity、strand 和 consensus-coordinate collinearity，再用全染色体 DAG/path cover 分组”这一确切路线，而不是整个 fragmentation 研究问题。论文中可将其作为保守 limitation：共识坐标证据适合作为辅助证据，不足以成为独立 parent-copy assembler。

### 2. SOTA gap interpretation

- Current metric：不存在可用于 SOTA claim 的当前指标。内部诊断值为 exact recovery `0.138889`、pairwise harmonic `0.308188`、topology preservation `0.105263`。
- SOTA metric：N/A；本实验没有已发表 SOTA 对照，且按合同明确 claim-ineligible。
- Absolute gap：对内部最佳 comparator 而言：

  - exact recovery：`-0.232804`（相对 GAP100）
  - pairwise harmonic：`-0.360921`（相对 GAP100）
  - topology：`-0.368421`（相对 GAP100）

- Relative gap：相对最佳 comparator 分别低约 `62.6%`、`53.9%` 和 `77.8%`。
- Is tuning justified? **no**。差距大且方向一致，bootstrap 95% 区间均完全低于零；同时 mapped fraction 仅 `0.555102`，说明问题不只是某个阈值稍有偏差。用测试 families 调 k-mer、margin 或 tolerance 会构成 test-set tuning，也不可能由当前证据支持。

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset version | Pass | Rice RGAP7、EDTA 2.3.0 truth 和 consensus library 已冻结并核验哈希。 |
| Official split / same split | Pass | 候选、RAW、GAP20/GAP100 和 shuffle 使用同一冻结样本；但这是内部 T1 positive-only audit，不是官方 whole-genome benchmark。 |
| Metric implementation | Pass | 指标范围与 T1 truth tier 相符；未把未标注基因组当负类。bootstrap 按 chromosome block 重采样，并在 replicate 内重选最佳 comparator。 |
| Preprocessing | Pass | immutable leaves、分层抽样和 evaluator-only truth 隔离清楚；抽样不读取 mapping/evaluation outcome。 |
| External weights / pretrained backbone version | N/A | 无模型、checkpoint 或外部预训练 backbone。 |
| Test-time inference protocol | Pass | 固定、确定性、预先规定；候选没有读取 parent ID、boundary、class 或 topology marker。 |
| Resource profile supports claim? | Fail | CPU information-sufficiency audit 明确 claim-ineligible，不能支撑 whole-genome、SOTA 或模型性能主张。 |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Metrics file exists and is parseable | Pass | route-local semantic audit报告科学 payload 成功，且相关 payload/manifest hash 已独立核验。 |
| Values finite / no NaN or Inf | Pass | 所报指标与 1,000 次 bootstrap 结果均有限。 |
| Loss trend or expected pattern is sane | N/A | 无训练过程或 loss。候选显著优于 shuffle，符合“证据有信号但不足”的预期模式。 |
| Seed variance known or not needed | N/A | 算法确定性；不需要训练 seed。bootstrap 已量化染色体层面的抽样不确定性。 |
| No suspicious leakage signal | Pass | truth parent 信息物理隔离，sampling label-blind；高 purity、低 recall 也不呈现可疑的近完美泄漏模式。 |
| Logs/config/artifacts sufficient to reproduce | Pass | 配置、scheduler/environment 信息、命令、semantic audit 和 17 个 payload hash 构成充分的复现链。前次 runtime-closure 失败没有被当作科学结果。 |

### 5. Architecture assessment

- 结果否定了强机制假设：consensus identity、strand 和 consensus-coordinate monotonicity 不能单独充分识别 biological parent copies。
- shuffle separation 表明证据并非无效；`0.924138` 的 pairwise purity 与仅 `0.184930` 的 recall 表明它主要产生保守但严重欠连接的分组。
- insufficiency 至少同时涉及：

  - **证据覆盖不足**：只有 `55.5%` leaves 被映射，未达到最低覆盖门。
  - **证据非唯一性**：同一 consensus 上的坐标顺序无法可靠区分不同 genomic copies。
  - **partition 表达不足**：minimum path cover 能保证确定性分解，却缺少识别真实 copy 边界、nested structure 和重复映射歧义的信息。
  - **truth 限制**：T1 positive-only 限制了可作出的结论，但无法解释候选相对同集 comparators 的大幅退化。

未来仍合理、且与当前路线正交的方向包括：

1. 跨多个同源 copy 的 copy-consensus boundary voting，而非逐叶到单一 frozen consensus 的映射。
2. 使用 TSD、LTR/TIR 配对、结构域和唯一侧翼等多来源 partial evidence，并显式建模缺失标签。
3. 在泄漏安全的 family/homology split 上学习全局 CopyGraph 自监督表示，而不是恢复已否决的局部 fragment graph。
4. 由长上下文 genome encoder 直接预测 interval/set 与 parent assignment，把 copy formation 纳入模型内部，而非事后叶片拼接。

这些只是未来架构候选，不构成当前运行建议。

### 6. Track recommendation

- **不应晋升。** 所有关键 promotion gates 均失败，且相对最佳 comparator 的退化具有统计稳定性。
- **该确切组件应停止。** 保存 mapper/collinearity evidence 作为未来系统的辅助 feature 是合理的，但不得把当前 DAG/path-cover assembler继续包装为可调候选。
- broader fragmentation objective 不应随之废弃；被否定的是“单证据独立组装器”假设。

### 7. Risks and blockers

- T1 positive-only 不能估计 genome-wide false positives，cross-RM-ID false fusion 仅是 proxy。
- 304 个 topology-evaluable groups 限制了复杂结构结论的外推范围。
- 同物种 frozen consensus 的结果不能自动外推至 cross-species、novel-family 或 degraded-copy 场景。
- 当前设计没有充分的条件分层，无法严格量化 mapper failure 与 partition failure 各自贡献；但这不影响停止整条组合路线。
- `ACTIVE_GOAL.json` 与本 cohort 不一致，使 `validate_goal.py` 报 `failed_run`。这是自动化合同阻塞，不应误记为科学运行失败。
- 任何基于本次 Rice T1 test families 的阈值调优都会污染后续验证。

### 8. Next action

执行一个非计算闭环：把该确切路线登记为 **abandoned route**，同时在 limitation 中记录“consensus collinearity carries signal but is insufficient as a standalone parent-copy assembler”，并保留 broader fragmentation objective。

科学 re-entry 必须同时满足：

1. 引入至少一种当前路线没有的新信息源，而非调整 seed、stride、margin、tolerance 或 path-cover 规则。
2. 在独立 development families 上预注册机制和阈值，Rice T1 不参与选择。
3. 使用 family/homology/clade 隔离的数据合同，并保持 truth 信息 evaluator-only。
4. 独立开发审计先证明 evidence coverage 明显超过当前 `0.555`，且 parent discriminability 不依赖 genomic-gap shortcut。
5. 在未触碰最终测试集前，同时达到预定 recovery、false-fusion、topology 和 leaf-retention 门槛。
6. 若要进入 publication claim，另行取得 whole-genome truth 与 leakage-safe cross-species evaluation；本 T1 结果不能升格。

在这些条件满足前，不应为 F 路线追加计算。

### 9. Confidence

**High**。运行语义、输入冻结、truth 隔离和统计不确定性均有清楚说明；候选相对 comparators 的负差距很大，所有关键结论方向一致。当前环境的只读 shell 因节点 namespace 资源耗尽，未能再次打开本地产物，因此本判断依据所提供的独立 semantic/hash 审计摘要；这一限制不改变路线决策，但应保留在审阅边界中。
hook: Stop
hook: Stop Completed
tokens used
33,256
### 1. Overall judgment

**abandon-route**

这是一个可信的、可复现的有效负结果。共识序列证据显著优于 shuffle，证明其中含有真实生物信号；但该信号不足以单独完成 parent-copy reconstruction。候选在覆盖率、恢复率、边界、融合安全性和拓扑保持上全面未过预注册门槛，且 bootstrap 区间远离零。

应终止的是“仅凭 consensus identity、strand 和 consensus-coordinate collinearity，再用全染色体 DAG/path cover 分组”这一确切路线，而不是整个 fragmentation 研究问题。论文中可将其作为保守 limitation：共识坐标证据适合作为辅助证据，不足以成为独立 parent-copy assembler。

### 2. SOTA gap interpretation

- Current metric：不存在可用于 SOTA claim 的当前指标。内部诊断值为 exact recovery `0.138889`、pairwise harmonic `0.308188`、topology preservation `0.105263`。
- SOTA metric：N/A；本实验没有已发表 SOTA 对照，且按合同明确 claim-ineligible。
- Absolute gap：对内部最佳 comparator 而言：

  - exact recovery：`-0.232804`（相对 GAP100）
  - pairwise harmonic：`-0.360921`（相对 GAP100）
  - topology：`-0.368421`（相对 GAP100）

- Relative gap：相对最佳 comparator 分别低约 `62.6%`、`53.9%` 和 `77.8%`。
- Is tuning justified? **no**。差距大且方向一致，bootstrap 95% 区间均完全低于零；同时 mapped fraction 仅 `0.555102`，说明问题不只是某个阈值稍有偏差。用测试 families 调 k-mer、margin 或 tolerance 会构成 test-set tuning，也不可能由当前证据支持。

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset version | Pass | Rice RGAP7、EDTA 2.3.0 truth 和 consensus library 已冻结并核验哈希。 |
| Official split / same split | Pass | 候选、RAW、GAP20/GAP100 和 shuffle 使用同一冻结样本；但这是内部 T1 positive-only audit，不是官方 whole-genome benchmark。 |
| Metric implementation | Pass | 指标范围与 T1 truth tier 相符；未把未标注基因组当负类。bootstrap 按 chromosome block 重采样，并在 replicate 内重选最佳 comparator。 |
| Preprocessing | Pass | immutable leaves、分层抽样和 evaluator-only truth 隔离清楚；抽样不读取 mapping/evaluation outcome。 |
| External weights / pretrained backbone version | N/A | 无模型、checkpoint 或外部预训练 backbone。 |
| Test-time inference protocol | Pass | 固定、确定性、预先规定；候选没有读取 parent ID、boundary、class 或 topology marker。 |
| Resource profile supports claim? | Fail | CPU information-sufficiency audit 明确 claim-ineligible，不能支撑 whole-genome、SOTA 或模型性能主张。 |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Metrics file exists and is parseable | Pass | route-local semantic audit报告科学 payload 成功，且相关 payload/manifest hash 已独立核验。 |
| Values finite / no NaN or Inf | Pass | 所报指标与 1,000 次 bootstrap 结果均有限。 |
| Loss trend or expected pattern is sane | N/A | 无训练过程或 loss。候选显著优于 shuffle，符合“证据有信号但不足”的预期模式。 |
| Seed variance known or not needed | N/A | 算法确定性；不需要训练 seed。bootstrap 已量化染色体层面的抽样不确定性。 |
| No suspicious leakage signal | Pass | truth parent 信息物理隔离，sampling label-blind；高 purity、低 recall 也不呈现可疑的近完美泄漏模式。 |
| Logs/config/artifacts sufficient to reproduce | Pass | 配置、scheduler/environment 信息、命令、semantic audit 和 17 个 payload hash 构成充分的复现链。前次 runtime-closure 失败没有被当作科学结果。 |

### 5. Architecture assessment

- 结果否定了强机制假设：consensus identity、strand 和 consensus-coordinate monotonicity 不能单独充分识别 biological parent copies。
- shuffle separation 表明证据并非无效；`0.924138` 的 pairwise purity 与仅 `0.184930` 的 recall 表明它主要产生保守但严重欠连接的分组。
- insufficiency 至少同时涉及：

  - **证据覆盖不足**：只有 `55.5%` leaves 被映射，未达到最低覆盖门。
  - **证据非唯一性**：同一 consensus 上的坐标顺序无法可靠区分不同 genomic copies。
  - **partition 表达不足**：minimum path cover 能保证确定性分解，却缺少识别真实 copy 边界、nested structure 和重复映射歧义的信息。
  - **truth 限制**：T1 positive-only 限制了可作出的结论，但无法解释候选相对同集 comparators 的大幅退化。

未来仍合理、且与当前路线正交的方向包括：

1. 跨多个同源 copy 的 copy-consensus boundary voting，而非逐叶到单一 frozen consensus 的映射。
2. 使用 TSD、LTR/TIR 配对、结构域和唯一侧翼等多来源 partial evidence，并显式建模缺失标签。
3. 在泄漏安全的 family/homology split 上学习全局 CopyGraph 自监督表示，而不是恢复已否决的局部 fragment graph。
4. 由长上下文 genome encoder 直接预测 interval/set 与 parent assignment，把 copy formation 纳入模型内部，而非事后叶片拼接。

这些只是未来架构候选，不构成当前运行建议。

### 6. Track recommendation

- **不应晋升。** 所有关键 promotion gates 均失败，且相对最佳 comparator 的退化具有统计稳定性。
- **该确切组件应停止。** 保存 mapper/collinearity evidence 作为未来系统的辅助 feature 是合理的，但不得把当前 DAG/path-cover assembler继续包装为可调候选。
- broader fragmentation objective 不应随之废弃；被否定的是“单证据独立组装器”假设。

### 7. Risks and blockers

- T1 positive-only 不能估计 genome-wide false positives，cross-RM-ID false fusion 仅是 proxy。
- 304 个 topology-evaluable groups 限制了复杂结构结论的外推范围。
- 同物种 frozen consensus 的结果不能自动外推至 cross-species、novel-family 或 degraded-copy 场景。
- 当前设计没有充分的条件分层，无法严格量化 mapper failure 与 partition failure 各自贡献；但这不影响停止整条组合路线。
- `ACTIVE_GOAL.json` 与本 cohort 不一致，使 `validate_goal.py` 报 `failed_run`。这是自动化合同阻塞，不应误记为科学运行失败。
- 任何基于本次 Rice T1 test families 的阈值调优都会污染后续验证。

### 8. Next action

执行一个非计算闭环：把该确切路线登记为 **abandoned route**，同时在 limitation 中记录“consensus collinearity carries signal but is insufficient as a standalone parent-copy assembler”，并保留 broader fragmentation objective。

科学 re-entry 必须同时满足：

1. 引入至少一种当前路线没有的新信息源，而非调整 seed、stride、margin、tolerance 或 path-cover 规则。
2. 在独立 development families 上预注册机制和阈值，Rice T1 不参与选择。
3. 使用 family/homology/clade 隔离的数据合同，并保持 truth 信息 evaluator-only。
4. 独立开发审计先证明 evidence coverage 明显超过当前 `0.555`，且 parent discriminability 不依赖 genomic-gap shortcut。
5. 在未触碰最终测试集前，同时达到预定 recovery、false-fusion、topology 和 leaf-retention 门槛。
6. 若要进入 publication claim，另行取得 whole-genome truth 与 leakage-safe cross-species evaluation；本 T1 结果不能升格。

在这些条件满足前，不应为 F 路线追加计算。

### 9. Confidence

**High**。运行语义、输入冻结、truth 隔离和统计不确定性均有清楚说明；候选相对 comparators 的负差距很大，所有关键结论方向一致。当前环境的只读 shell 因节点 namespace 资源耗尽，未能再次打开本地产物，因此本判断依据所提供的独立 semantic/hash 审计摘要；这一限制不改变路线决策，但应保留在审阅边界中。
