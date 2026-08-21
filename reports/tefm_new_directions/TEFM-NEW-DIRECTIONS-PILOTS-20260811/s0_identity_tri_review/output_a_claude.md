---

# Reviewer A · Claude — 独立全范围研究审查

**实验标识**：`SF-DIRECT-BASELINE-SCREEN-20260811-R2`（CPU DATA 阶段）  
**审查日期**：2026-08-11  
**审查范围**：数据合约、身份解析失败、修复选项、S0→S1 路径

---

## 1. 总体判断

**`replace-component`**

需要替换的是**身份解析组件**（`resolve_dfam_identities` 的逻辑 / `homology_component_policy.identity_resolution` 策略），而非整体数据管线、训练代码或模型架构。管线其余部分（parser 修复、窗口采样、标注绘制、split 语义、资产验证、历史精确重联）全部通过，不应被替换。

---

## 2. 科学解释

**本轮结果说明了什么**：

1. **CSV parser 修复已验证成功**：11522718 的 `csv.field_size_limit` 溢出是纯工程缺陷，11523252 将其局部提升至 2,000,000 字符并用 try/finally 恢复——15/15 测试 + 495 行 × 17 列真实探针通过，最大字段 1,203,362 字符。此问题已闭合，不应复现。

2. **身份合约暴露了真实的数据边界——这不是"失败"，而是合约正确执行的 typed block**：当前 15 物种 P-state RepeatMasker 输出中存在三类无法通过 Dfam 3.9 FamDB API 精确解析的家族名：
   - **通用/歧义名**：`Alu`（Dfam 中可能有多个 Alu 亚家族，FamDB `get_family_by_name("Alu")` 返回 None 或非精确匹配）
   - **有袋类 Charlie 变体**：`Charlie1a_Marsup`, `Charlie1b_Mars`, `Charlie4b_Marsup`, `Charlie7b_Mars` ——这些可能是宿主特异性亚家族，Dfam 3.9 未收录其精确名
   - **自定义 DR* 家族（占绝大多数）**：`DNA-2-32_DR`, `DNAX-1_DR`, `DR002419729`–`DR002419781`（40+ 个）——这些是 RepeatMasker 运行中生成的 de novo 或自定义库条目，不在 Dfam 3.9 官方名称空间中

3. **对 direct-superfamily 可用性的含义**：此结果**不提供任何关于 direct-superfamily 是否可用的证据**。`scientific_screen_executed=0`，无任何模型训练，无任何 S0 指标。它只说明：当前注释源的家族命名空间与 Dfam 3.9 官方名称宇宙**不是完全一一对应的**，而这是合约明确要求的。这**不意味着** direct-superfamily 不可行——只意味着身份层需要修补。

4. **对 S1 序列的影响**：S1（hierarchical/open-set correction）仍被禁止——`hierarchical_stage_authorized=false`。这一禁止是**正确的**：在 S0 的数据基础尚未通过之前，对 superfamily 误分类的层次化修正无从谈起。

---

## 3. 数据/可比性/泄漏审计

| 审计维度 | 判定 | 依据 |
|---|---|---|
| **源身份** | **FAIL** | 50 个家族无法通过 FamDB 2.0 API 解析为 Dfam 3.9 accession |
| **split 语义** | **PASS**（设计层面） | 合同要求 homology component 级 split + order-level clade 隔离；`validate_species_holdout` 已验证 fit 与 primary test 的 order_taxid 不相交 |
| **未解析家族处理** | **PASS**（合约执行） | 合同规定 `missing_or_ambiguous_identity: DATA_TYPED_BLOCK`——禁止静默删除/随机 fallback。代码正确抛出 `DataContractTypedBlock`，未绕过 |
| **覆盖偏差** | **Unknown** | 数据未物化，无法计算 `eligible_main4_coverage`；如果 DR* 家族富集于特定物种/clade，排除它们可能改变测试集的分类分布 |
| **泄漏保护** | **PASS**（设计层面） | `homology_component_overlap_count_max=0`，`primary_clade_overlap_count_max=0`；历史窗口通过 SHA-256 精确重联；无随机/chromosome split |
| **指标就绪** | **FAIL** | 无物化数据 → 无 `main4_conditional_macro_f1` 等任何科学指标 |
| **claim 资格** | **N/A** | `screen` profile 永不能 claim；数据阶段尚未通过，此问题不存在 |

**关键发现**：泄漏保护设计正确，但身份解析的 gap 在**数据进入管线之前**就被合约正确拦截——这是合约的价值，不是缺陷。

---

## 4. 语义/可复现性审计

| 审计项 | 判定 | 详述 |
|---|---|---|
| **终端状态** | **PASS** | `DATA_TYPED_BLOCK` 是合约定义的合法终态，非崩溃。`TERMINAL_STATE.json` 正确记录 `status`、`reason`、`canonical_manifest`、`unlisted_artifacts_are_superseded=true` |
| **manifest 完整性** | **PASS** | `output_manifest.sha256` 列出 8 个输出文件及其 SHA-256；`validate_goal.json` 正确报告 `failed_run`（因 `main4_conditional_macro_f1` 缺失） |
| **parser 修复** | **PASS** | `read_pinned_chunk_manifest()` 局部提升 `csv.field_size_limit`，try/finally 恢复，不对进程全局产生副作用；修复是**最小化且正确的** |
| **是否为有效 typed block vs 实现失败** | **有效 typed block** | `typed_block.json` 明确列出 50 个未解析家族名，`gpu_stage_authorized=false`，`scientific_screen_executed=false`。这是合约在数据边界处正确拒绝，而非代码 bug 导致的崩溃 |
| **是否值得再做一轮有界修复** | **是** | 修复范围明确（身份解析层）、风险可控（共识序列 SHA 聚类是确定性操作）、合同改动最小 |

---

## 5. 修复选项（按推荐顺序排列）

### 选项 A（推荐）：共识序列哈希/聚类替代 Dfam 名称精确匹配

**做法**：对无法通过 `get_family_by_name` 解析的家族，从冻结的 RepeatMasker 库文件（由 `famdb_rmlib_config` 指向）中提取其共识序列，计算 SHA-256，以 `consensus_SHA256` 作为 homology component；若同一共识序列对应多个名称，合并为同一 component。

**所需冻结证据**：
- 冻结的 RM 库文件（`rmlib.config` 指向的 `.hmm`/`.lib`/`.fa` 文件）的 SHA-256
- 每个 DR* 家族的共识序列提取脚本与输出
- 共识序列 → homology component 映射表的 SHA-256

**泄漏风险**：**低**。共识序列来自冻结的 RM 库（在 split 之前即存在），同源性完全由序列内容决定，不依赖外部数据库查询。split 仍然在 homology component 级别进行，order-clade 隔离不变。

**是否改变预注册合同**：**是，但改动最小**。需更新 `homology_component_policy.identity_resolution` 为 `"exact RepeatMasker family name -> Dfam 3.9 accession OR consensus SHA-256 cluster"`，并更新 `missing_or_ambiguous_identity` 为 `"consensus_hash_fallback"` 或新增二级解析路径。**接受阈值不变**。

**优势**：
- 保留 homology-based split 的科学基础（同源 = 同一 component）
- 共识序列是 RM 运行的冻结输出，完全可复现
- 不需要外部数据库或新映射文件
- 确定性、无歧义

**劣势**：
- 需额外代码从 RM 库文件中解析共识序列
- 同一 TE 家族可能因 RM 库中名称不同而被分为多个 component（但这是 RM 本身的不一致性，非方法引入的偏差）

### 选项 B：降级为精确 RM 家族名 component（有明确限制）

**做法**：将 homology component 的定义从 "Dfam 3.9 accession" 改为 "归一化后的 RepeatMasker 家族名（NFKC+uppercase+trim）"。每个 RM 家族名本身就是 component，不经过 Dfam API。

**所需冻结证据**：
- 当前快照中所有唯一 RM 家族名的完整列表及计数
- 确认归一化后无名称碰撞

**泄漏风险**：**低-中**。家族名仍来自冻结的 RM 输出，但不同 RM 运行中同一生物学 TE 可能获得不同名称——这本身不会造成 train/test 泄漏（component 仍然按 holdout 物种分离），但会**降低泛化声明的生物学可信度**：train 中的 "Charlie1a" 和 test 中的 "Charlie1b" 可能实际上高度同源，但按名称被当作不同 component 而允许分别进入 train/test。

**是否改变预注册合同**：**是，且改变对 "homology" 的定义**。需将合同中所有 "homology component" 替换为 "family-name component"，并接受同源 TE 可能跨 split 出现的风险（虽然 order-clade 级别仍隔离）。

**优势**：实现最简单，无需解析共识序列或查询外部 API。

**劣势**：
- 生物学同源性不再被严格保护（名称 ≠ 序列同源）
- 与合同原始精神（"同源元件不得跨 split"）有实质偏离
- 审稿人可能质疑 split 有效性

### 选项 C：获取完整官方身份映射

**做法**：寻找 DR* 自定义家族到 Dfam 官方 accession 的映射——可能来自 Dfam 4.0、RepeatMasker 社区维护的映射表、或手动策展。

**所需冻结证据**：
- 映射表的来源 URL、版本、SHA-256
- 每个映射的溯源（自动匹配 vs 手动策展）

**泄漏风险**：**中**。如果映射来自外部策展，映射中可能包含对测试集物种的先验知识，引入选择偏差。需严格审计映射来源的独立性。

**是否改变预注册合同**：**否**（仅补充映射数据），除非使用 Dfam 4.0 替代 3.9（这将需要更新 `taxonomy_asset_sha256` 并重新审计所有 accession）。

**优势**：与当前合同最兼容。

**劣势**：
- DR* 家族可能根本不在任何官方 Dfam 版本中（它们是 RM 运行生成的 de novo 家族）
- 寻找/验证映射的时间和不确定性高
- Dfam 4.0 迁移会触发全量再审计

### 明确否决的方法

| 方法 | 否决原因 |
|---|---|
| **静默删除未解析家族** | 选择偏差：DR* 家族富集于特定 TE 类型/物种，删除会扭曲分类分布 |
| **将未解析家族标记为 BG/U** | 信号丢失：这些是 P-state 阳性标注，改为 BG/U 会降低 recall 并引入假阴性偏差 |
| **随机/chromosome split 回退** | 泄漏风险：旁系同源可能跨 split 出现，违反基因组 split 硬约束 |
| **立即跳入 S1/GPU** | S0 未通过，`hierarchical_stage_authorized=false`；无数据基础时训练模型无意义 |

---

## 6. 风险/阻塞项

### CPU DATA 重试前的硬阻塞

1. **身份解析策略必须选定并冻结**：选项 A/B/C 只能选一个，不能混用。推荐 A，需先提取并冻结所有未解析家族的共识序列 SHA-256 列表。
2. **`homology_component_policy` 必须更新**：合同 YAML 中的 `identity_resolution` 和 `missing_or_ambiguous_identity` 字段必须反映新策略。
3. **更新后的代码必须通过新的 `/code-review-gate`**：当前 gate `PASS` 仅涵盖 parser 修复版本，身份解析逻辑变更后需重新审查。
4. **需确认共识序列可提取**：若选 A，需先验证 `rmlib.config` 指向的库文件格式可解析且包含所有 50 个问题的共识序列。若某些 DR* 家族的共识序列也不可获取（极端情况），需要三级 fallback 策略。

### GPU S0 前的硬阻塞

5. **`DATA_PASS_MANIFEST.json` 必须存在且冻结**：当前缺失。数据物化成功后的 manifest 必须记录所有 partition 的文件 SHA-256、窗口数、class/state 分布、coverage 指标。
6. **数据泄漏审计必须通过**：`verify` 子命令必须返回 `pass: true`，`homology_component_overlap_count=0`，`primary_clade_overlap_count=0`。
7. **GPU smoke test**：`gpu_smoke.windows=1, full_window_backward=true` 必须通过（验证 4096-bp 窗口 + GENERanno-0.5b 在 ≤23.5 GiB VRAM 下可运行）。
8. **新 code-review-gate**：从 CPU DATA → GPU 的 pre-submit 检查（`pre_submit_gate.py`）必须通过。

### S1 前的硬阻塞

9. **S0 必须通过数值闸门**：`validate_goal.py` 报 `success` 或至少 `progress`，并通过 `/tri-review` + `/pivot` 显式授权 `hierarchical_stage_authorized=true`。
10. **S0 结果必须写回 docs/04、docs/06、docs/10、docs/15**。

---

## 7. 下一步行动

### 唯一主要下一步

**执行身份层有界修复（推荐选项 A：共识序列哈希聚类），产出更新后的 `direct_s0_data.py` 与 `configs/SF-DIRECT-BASELINE-SCREEN-20260811-R2.yaml`（更新 `homology_component_policy`），然后重新提交 CPU DATA 作业。**

具体步骤：
1. 从 `famdb_rmlib_config` 指向的 RM 库文件中提取 50 个未解析家族的共识序列
2. 计算共识序列 SHA-256，确定聚类（相同 SHA → 同一 homology component）
3. 在 `resolve_dfam_identities()` 中增加共识序列 fallback 路径：先尝试 FamDB 精确匹配 → 失败则查共识 SHA 映射表
4. 更新合同 `homology_component_policy` 字段
5. 冻结共识序列映射表为独立的 frozen asset（SHA-256 写入 config）
6. 运行现有 15 项测试套件（`test_direct_s0.py`）确保不退化
7. 新增共识序列提取的确定性测试

### 客观代码/数据审查闸门

**在重新提交 CPU DATA sbatch 之前，必须通过以下闸门**：

| 闸门 | 内容 | 通过条件 |
|---|---|---|
| **test_direct_s0.py 全绿** | 现有 15 项 + 新增共识序列测试 | 0 failures |
| **共识序列映射表冻结** | 映射表 SHA-256 写入 config | 哈希不匹配时构建失败 |
| **新 `/code-review-gate`** | 独立审查更新后的 `direct_s0_data.py` + config | PASS，0 blockers |
| **contract drift check** | `diff` 旧/新 `homology_component_policy` | 所有变更在 docs/09 记录 |

### 置信度：**High**

理由：  
- Parser 修复已独立验证且通过  
- 剩余所有冻结资产（ontology、snapshot、holdout、checkpoint、历史数据）的 SHA-256 身份验证全部通过  
- Split/泄漏保护设计正确且未被触发（数据在身份层就被正确拦截）  
- 问题范围明确（50 个家族名，全部已知且列出），修复路径清晰（共识序列是 RM 运行的冻结输出，可确定性提取）  
- 唯一的不确定性在实现层面（RM 库文件格式是否可解析），不涉及科学假设或外部依赖

---

**审查人签名**：Reviewer A · Claude · 独立审查  
**审查模式**：只读，未编辑任何文件，未运行任何计算
