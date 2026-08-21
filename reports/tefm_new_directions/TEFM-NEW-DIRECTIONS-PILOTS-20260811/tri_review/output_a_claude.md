---

# 独立全范围研究审阅 — Reviewer A (Claude)

## 1. 总体判断

**`run-sanity-check-first`**

理由：本 cohort 是 fail-closed asset-gate 的工程成功——五个 exp 全部通过语义成功门禁、code review 全部 PASS、所有 typed block 精确物化、无静默降级或冒充 scientific result、资源合规（0 GPU-hours，919 s formal allocation wall）——但从科研进展角度，四个方向 F/S/G/E 停在"证据未齐、不得运行"状态，B 停在"denominator 尚不可用"状态。因此当前唯一合理的下一步是**修复 blocker 以解锁有效 scientific evidence**，而非 scale、tune、更换架构或放弃路线。这不是"模型跑崩了需要 sanity check"的传统含义，而是"asset gate 正确地拦住了未就绪的方向，现在需要补齐资产以通过 gate"——在本 cohort 的 fail-closed 语义下，这等价于 `run-sanity-check-first`。

---

## 2. SOTA Gap 解释

| 字段 | 值 |
|---|---|
| Current metric | N/A（无可比 scientific metric） |
| SOTA metric | N/A（本 cohort 禁止 claim，无可比 SOTA benchmark） |
| Absolute gap | N/A |
| Relative gap | N/A |
| Is tuning justified? | **no** — 没有任何 scientific screen 被执行，不存在可调参的 learned model。`validate_goal.py` 的 generic tuning advisory 对离散 identity/asset matrix 不适用且被显式标记为不授权替换或 scaling。在 B 的 Dfam/FamDB/container identity 和 F/S/G/E 的 truth/split/provenance 合同被物化之前，调参讨论无意义。 |

---

## 3. 可比性与 Benchmark 公平性审计

| 维度 | Pass / Fail / Unknown | 备注 |
|---|---|---|
| Dataset version | **Pass** (B) / **Fail** (F/S/G/E) | B 使用 SHA-256 冻结的 official tiny fixtures；F 缺少 Real-T0 与 tiered registry；S 仅 S0 snapshot 冻结；G 五个 anchor 无 run records；E 缺少 exact bindings 与 backend/weight identity |
| Official split / same split | **N/A** | 无可比 SOTA split。B 是 identity smoke（无 split）；F/S/G/E 的 split 合同均未冻结。Evaluator contract §3 已声明所有路线为 internal screen only |
| Metric implementation | **Pass** (B) / **Pass** (F/S/G/E，作为 asset gate) | B 的 `run_smoke.py` v1.0.3 经 code review 验证，坐标转换（GFF start-1/end → BED half-open）正确；F/S/G/E 的 `verify_asset_gate.py` v1.1.0 经独立 code review PASS |
| Preprocessing | **Pass** (B) / **N/A** (F/S/G/E) | B 无可拟合 preprocessing，adapter 输出经 schema 验证；F/S/G/E 未执行 scientific pipeline |
| External weights / pretrained backbone version | **N/A** | 无模型训练发生。E 的 pretrained/untrained weights identity 是 blocker 之一 |
| Test-time inference protocol | **N/A** | 无 inference 发生 |
| Resource profile supports claim? | **N/A** | 所有 profile 为 smoke/requested screen，本 cohort 禁止 claim |

**审计结论**：无可比性 blocker——因为本 cohort 从未进入可比性阶段。所有 typed block 是合同层面的缺失，不是可比性争议。Evaluator contract（`docs/19`）与 code review log（`docs/21`）对 B 的坐标/输出 schema 已做充分验证。当 blocker 解除后进入 scientific screen 时，必须重新审计 split leakage、同源去冗余与 truth tier 对齐。

---

## 4. 语义成功与可复现性审计

| 检查项 | Pass / Fail / Unknown | 备注 |
|---|---|---|
| Metrics file exists and is parseable | **Pass** | 全部 5 个 `metrics.json` 存在、JSON 合法、schema 版本明确 |
| Values finite / no NaN or Inf | **Pass** | 全部数值有限。B: 0/0/4/1/0 cells；F: 9 个 finite metrics；S: 6 个 finite metrics；G: 8 个 finite metrics；E: 6 个 finite metrics |
| Loss trend or expected pattern is sane | **N/A** | 无模型训练、无 loss curve |
| Seed variance known or not needed for screen | **N/A** | 无可训练模型。单 seed 对 identity smoke / deterministic asset gate 适用 |
| No suspiciously high jump / leakage signal | **Pass** | B 输出 manifest 764 entries 全部通过；adapter synthetic fixtures PASS；F/S/G/E 均未执行科学计算，无泄漏可能 |
| Logs/config/checkpoints sufficient to reproduce | **Pass** | 所有 exp 有 config SHA-256 + code SHA-256 + input manifest SHA-256 + metrics SHA-256。B 有完整 Slurm log；F/G 与 S/E 的 short allocation log 各 1-2 秒。Output manifest 可重验。Code review gate machine JSON 均写入 |

**可复现性评估**：B 的完整 fail-closed 矩阵可在任何有相同 SIF/container 的环境下重跑并得到确定性相同的 cell status。F/S/G/E 的 asset gate verifier 是确定性的（输入 manifest hash → 输出 status），可在秒级重验。**当前缺失的是 blocker 解除后的 scientific screen 可复现性——这需要先冻结 split/truth/container/weight identity。**

---

## 5. 架构评估

### B `BENCH-5TOOL-SMOKE-20260811-R1`

- **架构假设**：五个 exact workflow 可形成可复现 canonical denominator。
- **当前停止原因**：**data identity / provenance**——不是架构问题。RM2+RM 缺 Dfam/FamDB 配置；EDTA 的 exact patch identity 不可验证（payload 只报 `v2.3`）；Earl Grey 缺 Dfam 4 配置；HiTE 缺本地接受的 exact 3.3.3 SIF；TEtrimmer 的 canonical output/Pfam closure 未完成。
- **结构/合同层面的具体动作**：
  1. **为 RM2+RM 和 Earl Grey 配置并冻结 Dfam 4.0 FamDB 分区**，通过 FamDB 查询验证后写入 input manifest。
  2. **获取或构建 HiTE 3.3.3 的本地接受 exact SIF**（non-negotiable：legacy unpinned 3.0 已被显式禁止）。
  3. **为 EDTA 添加 patch-level version verification**——当前 `v2.3` 不满足 `2.3.0` 的 exact match；需修改 adapter 或获取能输出 patch version 的 EDTA build。

### F `FRAG-PARENT-LATTICE-SCREEN-20260811-R1`

- **架构假设**：immutable leaves + typed parent joins + richer/global evidence 改善 biological interval reconstruction。
- **当前停止原因**：**data identity / comparator contract**——不是架构问题。block codes 为 `F_A0_H0_PIN`、`F_A4_NO_REAL_T0_OR_TIERED_INPUT_REGISTRY`、`F_A5_CENTER70_MERGE_STRICT_MERGE_LOOSE_AND_ACCEPTED_POSTPROCESS_UNFROZEN`。
- **结构/合同层面的具体动作**：
  1. **建立 Real-T0 truth registry**：至少一个 species 的 expert-curated TE interval annotation 作为 biological ground truth（synthetic T0 仅可验证 evaluator semantics，不得支持 whole-genome precision/F1）。
  2. **冻结所有 comparator（CENTER70/MERGE_STRICT/MERGE_LOOSE/accepted postprocessor）的 exact code/config/阈值**，使其成为 immutable reference。

### S `SF-HIER-OPENSET-SCREEN-20260811-R1`

- **架构假设**：hierarchical abstention/open-set head 减少 severe remote-family errors。
- **当前停止原因**：**data identity / ontology / split**——不是架构问题。blocker 包括 production ontology 未冻结、homology blocks/clade split 缺失、direct-head rejoin 未 pin。
- **结构/合同层面的具体动作**：
  1. **冻结 production ontology target/crosswalk**：定义哪些 superfamily 属于 known/seen、哪些属于 open-set/Unknown，以及 Unknown 不得当作普通 biological superfamily 处理。
  2. **物化 homology component + clade split**：在 S0 canonical snapshot（105 annotation + 15 genome links）上运行 CD-HIT/MMseqs2 同源聚类，按 component 分 split，确保同源 copy 不跨 train/test。

### G `DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1`

- **架构假设**：genome-level decay/transfer surface 支持保守 anchor routing。
- **当前停止原因**：**provenance**——不是架构问题。五个 anchor（animal/cross/human_h0/insect/plant）全部 `PROV_RUN_RECORD_MISSING`。
- **结构/合同层面的具体动作**：
  1. **为每个 anchor 重建 exact training run record**：包括 training genome、code version、config、evaluator 的完整 provenance chain。不能将历史 bundle 当作 frozen provenance。
  2. 只有在所有 anchor run records 可重验后才授权下一阶段。

### E `EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1`

- **架构假设**：pretrained embeddings 在 sealed budget 下优于强 sequence controls。
- **当前停止原因**：**data identity / backend / weights**——不是架构问题。blocker 包括 2,200 Dfam fragments 缺 exact family/copy/component/accession bindings、genomic rows 缺 assembly bindings、backend/weights identity 不完整。
- **结构/合同层面的具体动作**：
  1. **为全部 2,200 Dfam + 2,000 genomic fragments 补全 exact bindings**（family/copy/species/component/accession），建立 sealed split。
  2. **冻结 pretrained embedding backend 与 exact weights version**（如 `DNABERT-2` 的 exact HuggingFace commit SHA），以及 untrained/random control 的初始化 seed。

### 架构评估总结

**所有五个方向的当前停止原因均非架构假设被证伪，而是 data identity / provenance / comparator contract / split contract 层面的前置资产缺失。** 没有任何 evidence 表明需要更换 backbone、改 objective/loss、或 abandon route。每个 blocker 都是精确的、可操作的合同缺失——不是模糊的"模型不 work"。这是 fail-closed 设计的预期行为，且 code review 确认了所有 verifier 正确拒绝了未就绪状态下的 scientific execution。

---

## 6. Track A / Track B 建议

| 候选 | 可否晋升？ | 理由 |
|---|---|---|
| B (5-tool smoke) | **不可晋升** | 0/5 engineering pass；smoke profile 永远不能晋升。但它是 valid negative——证明了 denominator 当前不可用，且精确指出了每个 workflow 缺失什么 |
| F (fragment lattice) | **不可晋升** | asset gate 未通过；scientific screen 从未运行。A0/A4/A5 blocker 必须先解除 |
| S (superfamily hierarchical) | **不可晋升** | asset gate 未通过；5 个 blocker（ontology/homology/clade split/algorithm pins/direct-head rejoin）必须先解除 |
| G (decay transfer) | **不可晋升** | asset gate 未通过；5 个 anchor 全部缺 run records |
| E (embedding falsification) | **不可晋升** | asset gate 未通过；4 个 blocker（bindings/split/backend/weights）必须先解除 |

**核心原则**：不推荐 scale——scientific screen 从未运行。Track A 尚未开始。所有候选当前必须保留在 asset-gated 状态。

---

## 7. 风险与 Blocker

### 优先级排序的 Blocker 列表

| 优先级 | Blocker | 影响范围 | 严重性 |
|---|---|---|---|
| **P0** | Dfam 4.0 FamDB 配置与 promotion | B（RM2+RM, Earl Grey）| **最高**——两个最常用的 TE annotation workflow 完全不可用。不解决则 denominator 缺失 2/5 |
| **P0** | HiTE 3.3.3 exact local SIF acquisition | B（HiTE）| **最高**——HiTE 完全无法运行。legacy 3.0 已被显式禁止 |
| **P1** | EDTA exact patch version verification (2.3.0 vs 2.3) | B（EDTA）| **高**——EDTA 已可启动、可解析 GFF、可在 tiny 输入上跑通部分流程，但版本身份不可验证 → 未来任何 EDTA 结果不可比 |
| **P1** | F 的 Real-T0 truth registry | F | **高**——没有 biological truth 就没有 fragmentation 评估。synthetic T0 不能支持 claim |
| **P1** | S 的 production ontology + homology split | S | **高**——没有 split 就没有 scientific screen 的前提；同源泄漏在此领域是致命错误 |
| **P2** | G 的五个 anchor exact run records | G | **中**——缺失 provenance 则无法验证 anchor 是否真的训练过、用什么数据/代码训练的 |
| **P2** | E 的 exact bindings + sealed split + backend/weight identity | E | **中**——没有 bindings 则 embedding comparison 的"相同预算"前提不成立；split leakage 风险 |
| **P2** | TEtrimmer canonical output + Pfam closure | B（TEtrimmer）| **中**——TEtrimmer 已可启动（v1.7.4 source overlay over 1.7.2 host），但无 interval output 就无法进入 denominator |
| **P3** | F 的 comparator freeze（CENTER70/MERGE_STRICT/MERGE_LOOSE/postprocessor） | F | **低-中**——comparator contract 必须先于任何 fragmentation 比较冻结 |

### 专项审计

| 审计维度 | 状态 | 备注 |
|---|---|---|
| **Leakage** | **Pass（当前）** | 无模型训练、无 split、无 calibration——当前无泄漏风险。但 F/S/E 进入 scientific screen 后必须运行 `check_data.py`（基因组 group/同源 split 强制） |
| **Silent dependency substitution** | **Pass** | Code review 确认：HiTE legacy 3.0 SIF 被显式拒绝；TEtrimmer 的 1.7.2 host 不会被静默报告为 1.7.4；Dfam 4.0 gz candidates 不被当作已配置的 FamDB partitions；EDTA version mismatch 被正确分类为 VERSION_MISMATCH 而非静默接受 |
| **Stale status** | **Pass** | Code review 确认：所有 verifier 先写 RUNNING；evidence/semantic drift 被正确转为 INVALID_RUN + semantic_success=false + exit 3；sbatch wrapper 保护 verifier 写入的 INVALID_RUN 不被覆盖 |
| **Claim inflation** | **Pass** | 全部 5 个 exp 的 `claim_eligible=false`；B 的 `primary_metric=0.0` 被正确标记为 valid discrete negative；F/S/G/E 未执行 scientific screen 被显式记录；COHORT_EVIDENCE_INDEX 声明 `claim_eligible: false` 与 `new_gpu_hours: 0.0` |
| **Resource compliance** | **Pass** | 总 formal allocation wall 919 s（远低于 12h/job cap）；0 GPU-hours（远低于 24 GPU-hours cap）；最多 2 个并行方向（F+G 共享 job `11519717`，S+E 共享 job `11519729`)—（低于 3 并行上限） |
| **Ghost run** | **Pass** | 所有 job COMPLETED，STATUS 文件正常；无 RUNNING 残留；`iter_ledger.py` 无 stale_signal |
| **Abandoned cousin re-entry** | **Pass** | F 的 verifier 正确保留了 DEC-001/002 re-entry boundary（A0/A4/A5 合同缺失 = 拒绝执行，而非静默复用旧 cousin）；G 的旧 formula/router 已标记为 triage-only |

---

## 8. 下一步行动

### 单一首要 blocker-resolution 步骤

**配置并冻结 Dfam 4.0 FamDB 分区，使 RepeatModeler2+RepeatMasker 和 Earl Grey 的最小输入流程可通过 identity/database/min-launch gate。**

这是解锁 B denominator 最关键的一步——解决了 2/5 workflow 的 FOUNDATIONAL_TYPED_BLOCK，且 Dfam 4.0 配置是 Earl Grey 的唯一 blocker（Earl Grey 的 identity/help 已验证通过）。具体操作：
- 将 Dfam 4.0 candidate partitions（`dfam_candidates/`）通过 FamDB 工具转换为可查询的 `.h5` 分区
- 写入 RepeatMasker 和 Earl Grey 的配置文件，使其指向 frozen Dfam 4.0 partitions
- 重新运行 B smoke，预期 RM2+RM 和 Earl Grey 从 FOUNDATIONAL_TYPED_BLOCK 升级为至少 partial pass 或新的 typed block（如 min-launch 在真实数据库下失败）
- 更新 input manifest hash 与 code review gate

### 可选正交方向（最多两个）

1. **[OPTIONAL] 获取或构建 HiTE 3.3.3 exact local SIF**：HiTE 3.3.3 的 source/digest 已知，但本地接受的 exact SIF 缺失。可从官方 repo 构建 Apptainer/Singularity image 并冻结 SHA。这是 B 的第二个 P0 blocker，且与 Dfam 配置完全正交（不同 workflow、不同依赖链、不同文件系统路径），可并行推进。

2. **[OPTIONAL] 建立 F 的 Real-T0 truth registry**：为至少一个 species（建议从 FlyBase 或 Rice 开始，因为这两者的 annotation 已在上下文中被提及）收集 expert-curated TE interval annotation，建立 tiered truth registry（T0 = expert-curated, T1 = positive-only support, T2 = computational consensus）。这是 F 从 asset gate 进入 scientific screen 的前提，且与 B 的 denominator 工作正交。

---

## 9. 置信度

**High** — 所有五个 exp 的 metrics/config/code review/verifier 行为均被独立验证且一致；typed block codes 精确且与 disk evidence 对齐；无科学结论需要推断；每个 blocker 的根因是合同/资产缺失而非架构失败，判断直接有据。
