## 独立全范围研究审阅

---

### 1. Overall judgment

**run-sanity-check-first**

---

### 2. SOTA gap interpretation

N/A。本实验是 CPU 工程可行性探针，不涉及模型训练、指标比较或 SOTA claim。实验目标是验证 Dfam 3.9 FamDB Leaf API 能否对 6 个冻结版本化 accession 在 12 个分区间实现 exact-once 检索——这是数据访问层的身份/完整性闸门，非模型性能比较。

---

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset/version identity | N/A | 非模型 benchmark；6 个 accession 已冻结版本化，但观测结果未持久化，无法验证 identity |
| Split/leakage | N/A | 无训练/测试 split；12 分区为 CPU 并行结构，不涉及泄漏风险 |
| Metric implementation | N/A | 非模型评估；PASS 标准为 exact-once + 全部冻结字段相等，属确定性布尔判定 |
| Preprocessing | N/A | 无数据预处理 |
| External weights | N/A | 无模型权重 |
| Test-time protocol | N/A | 非推理任务 |
| Resource profile supports claim? | N/A | screen profile，永不能 claim；本实验本身 claim-ineligible |

---

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Result payload exists | **Fail** | 72 次 FamDBLeaf 调用在内存中返回但从未写入磁盘；`AUDITED_MANIFEST_11533175.sha256` 验证了两个失败 payload manifest，但科学观测 payload 缺失 |
| Values finite | Unknown | 观测值未持久化，无法验证 |
| Failure classification is correct | **Pass** | `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`，`semantic_success=false`，`valid_negative=false`——分类准确。这是 rc2（failed-run），非 rc0（valid negative） |
| No unsupported inference | **Pass** | 审计明确禁止从"函数在内存中返回"推断科学结果——这是正确的纪律 |
| Logs/config/artifacts sufficient | **Pass** | 两个不可变失败 bundle 存在且 manifest 验证通过；stdout/stderr、code-review gate、semantic audit 均独立闭合 |

---

### 5. Architecture/component assessment

**这是 cleanup 组件失败，不是 exact-access 科学失败。** 具体分析：

- **科学探针层（72 次 `get_family_by_accession` 调用）**：函数在内存中成功返回，说明 Dfam 3.9 FamDB Leaf API 的只读访问路径在功能上是可工作的。没有证据表明 accession 检索本身失败。
- **清理/生命周期层（`FamDB.finalize()`）**：`FamDBLeaf.__init__` 在只读模式下未定义 `added` 属性（这是写模式才需要的簿记字段），但 `FamDBLeaf.finalize()` 无条件访问它。这是 API 生命周期管理缺陷——读模式不应触发写模式清理路径。
- **结果持久化层**：runner 在 cleanup 之前未将内存中的 72 个观测值写入磁盘。cleanup 的 `AttributeError` 导致整个进程以失败退出码终止，已获取的科学观测随进程消失。

**close-only 修复与重试失败旧代码是可区分的：**

| 维度 | 旧代码（Job 11533175） | 提议的 close-only 修复 |
|---|---|---|
| 72 次探针调用 | 不变 | 不变 |
| `FamDB.finalize()` 调用 | 有（无条件） | 无（读模式移除） |
| 底层 HDF5 handle 关闭 | 依赖 finalize | 显式 close |
| 结果持久化时机 | cleanup 之后（从未执行到） | cleanup 之前（确定性 staging） |
| cleanup 失败能否擦除结果 | 能（结果未落盘） | 不能（先落盘再清理） |

这不是"重试相同的失败代码"——这是对生命周期管理组件的一次**独立、有界、单点修复**，科学探针完全不变。

**但需注意**：该路线已消耗两份不同的实现合约（Job 11528885 的聚合 roundtrip + Job 11533175 的独立 leaf probe），两次均在 `FamDBLeaf.added` 上失败。这表明 API 的读/写模式边界设计存在系统性缺陷，不是随机偶发错误。

---

### 6. Track recommendation

**当前不得开放任何 S 下游阶段。** 理由：
- S0 direct-superfamily baseline 必须先通过 data/identity/homology-split/numeric acceptance 四道闸门
- 本实验是 S0 数据闸门的前提——必须先确认 FamDB leaf API 能正确检索冻结 accession，才能进入后续的 DATA materialization、homology construction
- 实验合约明确声明："Even PASS only makes a separately designed leaf-adapter CPU preflight proposal eligible. It never authorizes RepeatMasker, representative/full DATA, homology, GPU S0 or S1."
- GPU、annotation generation、S1 hierarchical/open-set 均未获授权

---

### 7. Risks and blockers

| 风险/阻塞 | 严重程度 | 说明 |
|---|---|---|
| **API 生命周期设计缺陷** | 高 | `FamDBLeaf` 读/写模式未正确分离——`__init__` 不设 `added`，`finalize()` 却无条件访问。这是 Dfam 3.9 API 的固有设计问题，修复在调用侧只是 workaround |
| **重复失败风险** | 中 | 两次不同实现合约在同一 API 属性上失败；close-only 修复若未覆盖所有代码路径（如异常路径中的 cleanup），仍可能再次失败 |
| **结果持久化顺序** | 中 | 提议修复的核心是把 staging 移到 cleanup 之前——若 staging 本身触发异常，结果仍会丢失 |
| **路线消耗** | 中 | 已消耗两份实现合约 + 一次性执行授权；第三次尝试是最后一次有界机会 |
| **范围蔓延** | 低 | "只修改 read-mode handle closure/result publication"的边界清晰，但需 code review 严格验证未触及 72 次探针逻辑 |
| **科学不可知** | 低 | 即使 PASS，6 个 accession 的 exact-once 检索成功不能保证全量 FamDB 的可靠性；这只是 leaf 层面的点探针 |

---

### 8. Next action

**准予一次、且仅一次、独立审查的 close-only 生命周期修复。** 硬性重入条件如下：

1. **禁止调用 `FamDB.finalize()`**：在只读模式下完全移除对该方法的调用。读模式 handle 通过显式关闭底层 HDF5 文件句柄完成资源释放。

2. **结果先于 cleanup 持久化**：在进入任何清理逻辑之前，将 72 个观测值写入不可变 payload 文件（JSON + SHA256 manifest）。清理失败不得擦除或升级已持久化的观测结果。实现合成行为证明（synthetic behavior proof）：在测试中故意使 cleanup 抛异常，验证已落盘结果完好无损。

3. **72 次探针调用完全不变**：`get_family_by_accession` 的调用方式、参数、顺序与 Job 11533175 的冻结合约完全一致，一字不改。

4. **不重用已消耗的闸门**：新的 code-review gate 记录（独立于 `11533175` 的 code review），BLOCKED 不得提交。

5. **一次性有界 CPU 尝试**：最多 1 次提交，相同资源配置（1 CPU, 4 GiB, 10 min, 0 GPU），`submit-and-handoff`。

6. **永久终止条件**：任何进一步的 API/生命周期失败（`AttributeError`、HDF5 句柄泄漏、结果文件缺失/损坏、或其他 `FamDBLeaf` 运行时异常）→ **永久关闭此 FamDB export/access 路线**，不得再次授权修复。`rc2`（failed-run）计为终止事件。

7. **PASS 后的权限边界**：即使 PASS，仅使 leaf-adapter CPU preflight proposal 成为合格候选；不得自动授权 RepeatMasker、DATA materialization、homology construction、GPU S0 或 S1。

---

### 9. Confidence

**Medium。**

理由：失败原因明确且可复现（确定性 `AttributeError`），修复范围受严格约束（仅 cleanup 生命周期），科学探针不变。但降为 Medium 而非 High 的理由有二：① 同一 API 属性（`FamDBLeaf.added`）已导致两次独立失败的实现合约，可能存在未发现的读/写模式边界问题；② 72 个观测值的内容是未知的——即使修复后成功持久化，仍可能发现 accession 缺失、重复或字段漂移（rc0），这将是另一种性质的阻塞。
