现在我有了完整的证据链。以下是独立外部评审。

---

# 独立全量科研评审 — F Job 11529694

**评审人**：Reviewer A=Claude（独立外部）　|　**日期**：2026-08-12　|　**Confidence**：High

---

## 1. 总体判断（Overall Judgment）

**`run-sanity-check-first`**

这是一个 pure gate-installation 闭合失败，不是算法失败、不是科学假设证伪、也不是数据/资源配置问题。15 个 exp-owned 文件全部通过独立 delta review（hash 匹配、17/17 测试通过），唯一缺失的是共享 `scripts/pre_submit_gate.py` 在 `code_review_gate.json` 的 `reviewed_files` 闭合表中缺失。allocation-side `runtime_hashes.py` 正确执行了 fail-closed 行为。**不存在科学 payload 被执行**——因此本实验的方法假设（consensus-collinearity DAG 能否恢复 T1 parent groups）完全没有被测试，不应做任何架构或方向判断。

---

## 2. SOTA Gap 解读

**n/a**。本实验是 claim-ineligible CPU-only information-sufficiency audit，不涉及 SOTA comparison。primary metric = null，semantic_success = false，validate_goal = `failed_run`。不存在可解读的 gap。

Tuning is **not justified**（且与此失败模式无关）。

---

## 3. Comparability/Fairness 审计

| 维度 | 状态 | 备注 |
|---|---|---|
| Dataset | ✅ Frozen | Rice RGAP7 `all.con` SHA `db8b7efb...` 已冻结，但**未被读取** |
| Split/Truth Tier | ✅ T1 curated-positive only | `edta_v230_positive_segments_v1` SHA `06ac8f7c...`；unlabeled ≠ negative |
| Metric | ✅ Allowlist 预定义 | 16 个 T1 允许指标 + 6 个 forbidden 指标；但**未计算** |
| Preprocessing | ✅ 固定 seed/strata/rank rule | sampler 确定性，但**未执行** |
| External Assets | ✅ Frozen EDTA consensus | `rice7.0.0.liban` SHA `bb4708...` 冻结，但**未读取** |
| Resource Claim Eligibility | ✅ 合同明确 | 8CPU/32GiB/2h/0GPU；claim-ineligible by design |
| Comparator Fairness | ⚠️ 未验证 | GAP20/GAP100 是 experiment-local positive-only comparator，不与历史 MERGE_* 等价；但**payload 未执行** |

**Comparability 结论**：合同层面无问题。所有资产、指标、资源边界在设计上已正确约束。唯一失效在 gate installation 闭合层，不影响 comparability 契约本身。

---

## 4. Semantic Success / Reproducibility 审计

| 维度 | 状态 | 证据 |
|---|---|---|
| Metrics parseable | ❌ n/a | primary_metric = null；无可解析 metrics |
| Metrics finite | ❌ n/a | 同上 |
| Scientific payload executed | ❌ | elapsed=0s；assembly/truth/consensus 均未读取 |
| Leakage check | ⚠️ 未执行 | `check_data.py` 未被调用；但 config 层面已声明 T1 truth-only fields 物理隔离 |
| Logs/manifests 完整 | ✅ | `AUDITED_MANIFEST_11529694.sha256` 覆盖 9 个 artifact；`preflight_gate_and_tests_11529694.log.tmp.3520923` 含完整 traceback |
| Fail-closed 行为 | ✅ 正确 | `runtime_hashes.py:43` 在发现 `scripts/pre_submit_gate.py` 不在 `reviewed_files` 时立即 `RuntimeError`，阻止了任何未审查代码在 allocation 侧执行 |
| STATUS 一致性 | ✅ | `IMPLEMENTED_NOT_RUN` 未被错误覆写为 COMPLETED |

**Reproducibility 结论**：fail-closed 行为是正确且可复现的。所有 artifact hash 可验证。traceback 唯一且确定。

---

## 5. Method 评估

### 5.1 方法假设（未测试）

本实验的核心科学假设是：

> 仅凭 immutable leaf 的 DNA 序列到 frozen EDTA consensus library 的 exact seed-chain identity/strand/coordinate 证据 + chromosome-wide consensus-collinearity DAG minimum path cover，能否在 Rice T1 curated-positive multirow groups 上比 RAW_SINGLETON 和 positive-only GAP20/GAP100 更好地恢复 truth parent groups，同时保持 leaf retention = 1、低 cross-rm-id false-fusion、以及 boundary/topology 保真度。

**这个假设在本次运行中完全没有被测试。** 因此不应基于本次失败做任何"方法是否可行"的判断——那会把 gate installation error 误读为科学负结果。

### 5.2 与 DEC-001/002 的正交性（设计层面确认）

Config 和 experiment doc 明确声明：
- candidate join **不使用** prediction-confidence、genomic-gap 或 test-tuned threshold
- **不使用** HMM、CRF、duration/survival loss、local fragment graph、frozen/lightweight interval head
- assembler **不读取** `rm_id`、truth parent boundary、class
- partition 使用 consensus-collinearity DAG（非 genomic gap DAG）

这些设计选择与 DEC-001/002 的否决范围正交。**从 config 层面看，方法设计是符合 re-entry 约束的。**

### 5.3 结构替代方案

**当前不需要。** 在 gate 修复并成功运行之前，没有科学证据支持任何架构变更。若修复后运行结果显示 INFORMATION_INSUFFICIENT，再根据具体指标缺口考虑：
- 更丰富的 consensus evidence（multi-consensus co-linearity、partial consensus-path consistency）
- 更全局的 partition 约束（跨 chromosome 的 consensus-family 一致性先验）
- 但所有这些都**必须保持 immutable leaves 和不读 truth 的前提**

---

## 6. Track 建议

### 6.1 授权范围

**允许一次 narrow same-exp retry**，条件如下：

| 条件 | 要求 |
|---|---|
| 修复内容 | 在 `code_review_gate.json` 的 `reviewed_files` 中增加一项：`"scripts/pre_submit_gate.py": "4996364f5641014dc9bd5e7531586cbf9967c87a02d61e3df0bcd207c1122be1"`（共 16 个 reviewed files） |
| 独立 delta review | 修复后必须重新通过 **独立**（separate_codex 或同等）delta review；review scope：变更的 `code_review_gate.json` 是否完整闭合 `runtime_code_files` |
| Machine gate | `pre_submit_gate.py` login-side + `runtime_hashes.py` allocation-side 双重验证通过 |
| Resource | exact 8CPU/32GiB/2h/0GPU（不变） |
| No-override 边界 | 禁止 GPU、禁止 full F、禁止 whole-genome metrics、禁止 claim、禁止改 config 逻辑或采样 seed、禁止改 `runtime_code_files` 列表（只修 gate JSON） |
| Exp ID | **保持不变** `FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1`（这是 gate 修复，不是新实验） |

### 6.2 不授权

- ❌ 新 exp_id
- ❌ GPU 或 full F
- ❌ 自动 retry（需人工确认 delta review 后再提交）
- ❌ 跳过 `/tri-review` + `/pivot`
- ❌ whole-genome precision/F1

---

## 7. Risks / Blockers

| 风险/阻断 | 严重度 | 说明 |
|---|---|---|
| Gate 闭合遗漏 | **已触发** | `reviewed_files` 缺少共享 `scripts/pre_submit_gate.py`——这是本次唯一阻断 |
| 共享脚本未纳入审查闭合的复发 | Medium | 未来若其他 exp 也在 `runtime_code_files` 中引用共享脚本，可能重复此类错误。建议：`/implement` 或 `/code-review-gate` 输出时做 `runtime_code_files ⊆ reviewed_files` 的自动校验 |
| Scientific 未知 | Low（本次） | 方法假设尚未测试；即使 gate 修复后运行成功，INFORMATION_SUFFICIENT 也只是 bounded followup 授权，不是 biological claim |
| 资源无竞争 | Low | 8CPU/0GPU/2h，Baobab private partition 资源充足 |

---

## 8. Next Action（唯一下一步）

**修复 `code_review_gate.json`**：将 `"scripts/pre_submit_gate.py": "4996364f5641014dc9bd5e7531586cbf9967c87a02d61e3df0bcd207c1122be1"` 加入 `reviewed_files`（第 16 项），使 `reviewed_files` 完整覆盖 config 的 `runtime_code_files`（共 12 个路径）。然后：

1. 通过独立 delta review（只审 gate JSON 变更是否闭合 runtime_code_files）
2. 走 `/smart-sbatch` 重新提交（同一 exp_id、同一 config、同一 resource contract）
3. 若 payload 执行完成：走标准 `/result-log` → `/note-gate` → `/tri-review` → `/pivot` 链

**不走 `/implement`、不改代码、不改 config 逻辑、不新建 exp_id。**

---

## 9. Confidence

**High**

证据充分且无歧义：traceback 唯一、root cause 可复现、15/15 实现 hash 匹配、17/17 测试通过、共享文件 SHA 已验证匹配（`4996364f...`）、fail-closed 行为符合 `runtime_hashes.py:43` 的确定性逻辑。这不是"可能的原因"——这是唯一的、确定的原因。修复路径明确且范围极度受限。
