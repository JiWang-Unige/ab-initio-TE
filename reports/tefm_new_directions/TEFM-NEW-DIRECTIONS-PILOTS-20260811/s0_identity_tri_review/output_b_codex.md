### 1. Overall judgment

**comparability-blocker**

当前阻塞点是注释来源与预注册 Dfam 3.9 身份空间不一致，尚未形成满足同源去泄漏要求的可比较数据集。

### 2. Scientific interpretation

本结果不支持也不否定 direct-superfamily annotation 的可用性。此次运行仅证明：

- CSV 宽字段解析问题已被有效修复。
- 冻结 RepeatMasker 注释中的 P-state family name 不能全部一对一解析为 Dfam 3.9 accession。
- 因数据身份层未通过，训练、推理及所有 S0 科学指标均未执行。

因此，缺失的 `main4_conditional_macro_f1` 不能解释为模型失败。S0 的科学结论仍为未知；S1 hierarchical/open-set correction 继续禁止，直至 S0 完成并满足预注册阈值，且经过 result-log、validate、tri-review 和 pivot 的明确授权。

### 3. Data/comparability/leakage audit

| 审计项 | 判定 | 依据 |
|---|---|---|
| Source identity | **Fail** | 大量 generic、ambiguous 和 custom `DR...` family 无法一对一绑定到 pinned Dfam 3.9 accession/consensus。 |
| Split semantics | **Unknown** | 设计上的 held-out-order/component split 合理，但数据未 materialize，实际 split 未生成或审计。 |
| Unresolved-family handling | **Pass** | 系统正确终止为 typed block，没有删除、降格为 BG/U 或启用随机 fallback。 |
| Coverage bias | **Unknown** | 当前没有引入删除偏差，但尚未证明修复后的 identity layer 能无选择性地覆盖全部 P-state records。 |
| Leakage protection | **Unknown** | 预注册规则较强，但 homology component 尚未构建，component/clade overlap=0 尚无执行证据。 |
| Metric readiness | **Fail** | 无 DATA PASS、无正式 split、无训练或预测，科学指标不可计算。 |
| Claim eligibility | **Fail** | 本运行明确为 claim-ineligible CPU gate，且 `semantic_success=false`。 |

### 4. Semantic/reproducibility audit

- `DATA_TYPED_BLOCK` 与 `DFAM_FAMILY_IDENTITY_UNRESOLVED` 相互一致；`DATA_PASS_MANIFEST.json` 缺失是正确行为。
- terminal manifest 和 output manifest 可验证，`scientific_screen_executed=0`、`hierarchical_stage_authorized=false` 准确表达了执行边界。
- `validate_goal.py` 因科学指标缺失返回 `failed_run`，这是确定性目标闸的预期结果，不应解释为科学负结果。
- CSV 修复范围局部，使用 `try/finally` 恢复全局限制，并通过 15/15 tests 和真实宽表 probe；有充分证据表明上一轮 parser capacity bug 已解决。
- 当前失败属于有效的 foundational typed block：它揭示了数据来源契约中的错误假设，而不是重复的解析实现故障。
- 再进行一次有界修复是合理的，但必须先完成 identity provenance 审计；直接原样重提 CPU DATA 没有信息增益。

### 5. Repair options

| 排名 | 方案 | 必需的冻结证据 | 泄漏风险 | 是否改变预注册合同 | 判断 |
|---|---|---|---|---|---|
| 1 | 从产生当前注释的冻结 RepeatMasker library/source run 恢复 exact consensus SHA，并在全部 official/custom consensuses 上预先进行确定性 sequence clustering，以 cluster 作为 homology component | library 文件及 SHA256、RepeatMasker 命令和版本、每个输出名称到 library entry 的唯一映射、consensus sequence/hash、聚类算法/阈值/版本、完整冲突表 | **低至中**；前提是聚类在 split 前全局冻结，不使用标签性能或测试结果调阈值，并将同一 cluster 的所有记录整体路由 | **是**；component 从 Dfam accession 改为 sequence-derived cluster，需版本化 addendum 和全新运行 | **首选。** Consensus SHA 适合证明序列身份，但 SHA 相同仅发现完全重复，不能单独承担同源去泄漏；必须配合预冻结的序列聚类。 |
| 2 | 若旧输出无法唯一回连 library entry，使用同一冻结序列库重新生成带唯一 entry ID 的注释，并验证坐标/类别变化 | 原始 library、完整参数和输入基因组、旧新坐标匹配报告、所有差异清单 | **中**；重生成可能改变命中竞争、坐标或 family assignment | **是**；属于数据谱系变更，必须新 dataset/experiment version | 比模糊名称推断更可信，但只有在旧注释无法恢复 provenance 时采用。 |
| 3 | 获得完整、版本一致的一对一 official alias/accession mapping | Dfam/FamDB 官方版本化映射、alias 冲突处理规则，以及 custom `DR...` family 的可验证来源身份 | **低**，但仅在映射真正完整且一对一时成立 | 全部仍解析到 Dfam 3.9 accession 时可不改；若引入非 Dfam identity，则需要修订 | 理论上最贴近原合同，但 custom families 使其成功概率有限；不能仅覆盖 official 子集。 |
| 4 | 使用 exact normalized RepeatMasker family name 作为 component | 原始名称、规范化规则、collision/alias/case audit、跨物种同名异序列和异名近同源报告 | **高**；异名近同源可跨 split 泄漏，同名异序列又可能错误合并 | **是，且显著削弱合同** | 不接受作为 primary S0 homology component。最多可作为明确标注局限的 comparator/audit-only sensitivity analysis。 |

任何方案中仍无法唯一解析的 P-state record 都必须继续触发 typed block；不得静默删除或重标为 BG/U。

### 6. Risks/blockers

**再次提交 CPU DATA 前：**

- 必须锁定产生当前注释的 exact RepeatMasker library、版本、命令及文件哈希。
- 必须证明每个 P-state record 都能确定性绑定到唯一 identity；模糊名称不得靠字符串相似度猜测。
- sequence-clustering 算法、阈值和软件版本必须在查看 S0 性能前冻结。
- 若 component 定义改变，必须版本化修改配置和 goal contract，并重新进行独立代码/数据审查。
- 测试夹具必须覆盖 `Alu`、Charlie variants、`DR...`、重复名称、同名异序列和异名近同源情形。

**GPU S0 前：**

- 必须产生并验证 `DATA_PASS_MANIFEST.json`。
- 必须证明 homology-component overlap=0、clade overlap=0、fit/test order taxid disjoint。
- 必须报告全量 P-state identity coverage、各物种/订单覆盖和零静默删除。
- 必须通过 fresh code review、pre-submit gate 和完整 CPU materialization。

**S1 前：**

- S0 必须实际执行并满足全部预注册 acceptance thresholds。
- 必须完成 result-log、`validate_goal.py`、独立 tri-review 和 pivot。
- 必须有显式的 `hierarchical_stage_authorized=true`；不得由数据闸通过自动推导授权。

### 7. Next action

**唯一主行动：**对产生现有注释的冻结 RepeatMasker library/source run 执行一次有界、CPU-only identity provenance audit，构建并审查“annotation record → unique library entry → consensus SHA → frozen sequence cluster”的完整映射，但暂不重新提交 S0 DATA。

**客观代码/数据闸：**

- 100% P-state records 映射唯一；
- unresolved 和 ambiguous count 均为 0；
- library、mapping、consensus 和 cluster manifests 均有稳定哈希；
- clustering 参数在 split 和科学指标之前冻结；
- held-out-order 传播后 component overlap=0、clade overlap=0；
- 若 component 定义改变，预注册 addendum 和新版本配置先通过独立审查。

任一条件不满足，则不得重提 CPU DATA，更不得启动 GPU S0 或 S1。

**Confidence：High**
