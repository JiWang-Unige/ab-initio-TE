## 1. Overall judgment

**replace-component**

当前应替换的是与已安装 FamDB 不兼容的 aggregation/export component，而不是调整模型、扩大数据或否定 annotation-time accession-preserving 假设。该科学假设尚未被执行到，证据状态仍是“未检验”。

## 2. SOTA gap interpretation

- Metric：n/a
- SOTA：n/a
- Gap：n/a
- 调参是否合理：**否**

本轮没有产生 accession roundtrip、几何一致性或 direct-label 一致性指标。失败来自确定性的 FamDB API 集成错误，与模型参数、SOTA 差距或统计波动无关。

## 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | Pass | Dfam 3.9、六个 pinned accessions及冻结 manifest 已明确；未发生资产替换。但记录尚未成功导出。 |
| Official split / same split | Unknown | 此 smoke 不涉及训练 split；两臂同序列、同顺序合同尚未在真实导出物上完成验证。 |
| Metric implementation | Unknown | 37/37 测试支持实现的静态一致性，但几何语义 hash 未对真实 RepeatMasker 输出执行。 |
| Preprocessing | Fail | FamDB 对象构造阶段失败，name-header/accession-header FASTA 未完整生成并进入比较流程。 |
| External weights / tool versions | Pass | Dfam 3.9 与 RepeatMasker 4.2.2 已冻结；无模型权重。RepeatMasker 的实际行为仍未执行。 |
| Test-time inference protocol | Fail | RepeatMasker 没有启动，双臂 annotation/roundtrip protocol 未执行。 |
| Resource profile supports claim? | Fail | 6-record、CPU-only、claim-ineligible preflight 明确不能支持性能或 SOTA claim。 |

## 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown | Notes |
|---|---|---|
| Metrics file exists and is parseable | Pass | 已有 audited metrics 与 semantic audit，明确记录 `run_ok=false`、`semantic_ok=false`。 |
| Values finite / no NaN or Inf | Unknown | 没有科学 primary metric；运行状态字段可解析不等于产生了可审计数值。 |
| Scientific payload executed | Fail | FamDB 构造即失败；未完成六条 consensus 导出，RepeatMasker 未运行。 |
| No leakage signal | Unknown | 未发现实际泄漏，但 payload 未执行，不能据此验证 exact-once、跨 partition 或 homology leakage 合同。 |
| Logs/config/manifests sufficient | Pass | 冻结 state、RUN_MANIFEST、Slurm 日志、审计 JSON 和 SHA manifest 足以定位当前工程失败层。 |
| Stop rule honored | Pass | 唯一 repair retry 已结束且未继续自动提交第三次运行；必须保持这一状态。 |

## 5. Architecture/component assessment

本轮对科学假设本身没有正面或负面证据。它既没有证明 RepeatMasker 能保留 accession，也没有证明 accession header 会改变几何或 direct labels。唯一可信更新是：

1. 上轮资源 guard 问题已经关闭。
2. 当前聚合层错误地假设 `FamDBLeaf` 存在 `.added` 属性。
3. 已安装 FamDB runtime 与当前 aggregation implementation 的对象合同不兼容。

可考虑的非调参组件选择：

1. **Leaf-level exact-access adapter（推荐）**：绕开失效的 aggregation bookkeeping；逐 partition 使用已安装官方 leaf API，以 accession 为唯一键，强制 exact-once，并独立核验 accession、metadata、length 与 consensus SHA。
2. **官方 CLI/export adapter**：仅当已安装官方命令支持 exact accession 查询，并能证明输出无 name/prefix/case fallback、无重复解析时才可采用。
3. **匹配版本的 FamDB code/data runtime**：把 FamDB 实现与 Dfam 3.9 数据格式作为一个冻结版本对，而非混用不同实现。该选项变更面较大，应排在 leaf-level probe 之后。
4. **条件性终止**：如果官方 leaf API/CLI 均不能对六条 accession 实现确定性的 exact-once consensus recovery，则停止该 annotation-time export route，不得退回模糊名称匹配或 copy-derived identity。

## 6. Track recommendation

- 第三次 retry：**不允许**。无论是否只改一行，继续提交同一 preflight 都会违反既定 stop rule。
- 新实验：**只允许一个新 exp_id 下的 read-only/API contract probe**；它不是 retry，也不得运行 RepeatMasker。
- 组件方向：优先验证并替换为 **leaf-level exact accession access**，不要继续修补当前 aggregation 对 `.added` 的假设。
- 资源上限：`1 CPU、≤4 GiB、≤10 分钟、0 GPU`；禁止 representative/full DATA、homology construction、GPU S0 和 S1。

重新进入 preflight 提案阶段必须同时满足：

- 六个 pinned accession 各自 exact-once 命中；
- 记录可追溯到明确 leaf/partition；
- accession、name、raw class、length、consensus SHA 与冻结期望逐项一致；
- 重复执行结果确定性一致；
- 不使用 name、prefix、case、alias 或 genome-copy fallback；
- 通过后只能提出“新实现 + fresh code review”的新 preflight，不能自动提交。

任何一条失败，都应关闭此 export route；不得通过降低分母或放宽 identity 合同重新进入。

## 7. Risks and blockers

- FamDB 代码与 Dfam HDF5 schema 可能存在版本错配；绕开 `.added` 不代表其余 API 合同兼容。
- 同一 accession 在多个 partition 中的重复、遮蔽或优先级规则可能破坏 exact-once。
- Leaf-level fetch 即使成功，也尚不能证明 accession header 会被 RepeatMasker `.out` 原样保留。
- FASTA header 的规范化、截断或特殊字符处理仍可能产生科学 valid-negative。
- 六记录 smoke 只能验证机制可执行性，不能证明 6,432,583 occurrences 的完整覆盖。
- 新 custom-library benchmark 与旧 `-species + overlay` S0 不可直接继承指标或分母。
- 当前没有任何证据授权 homology split、representative DATA、GPU direct S0 或 hierarchical/open-set S1。

## 8. Next action

执行一个独立的 **leaf-level FamDB exact-access read-only contract probe**：在上述资源上限内检查已安装实现，并对六个 pinned accession 验证 exact-once leaf 定位及 accession/name/class/length/consensus SHA 全匹配；不导出 benchmark library、不启动 RepeatMasker、不提交第三次 preflight。全通过后才允许提出新的 leaf-adapter preflight；任一失败则终止该 export route。

## 9. Confidence

**Medium**

失败位置、stop rule 和授权边界都很清楚，因此“替换组件、禁止第三次 retry”的判断较稳健。但科学 payload 完全未执行，而且本轮执行环境的 namespace 资源错误使我无法直接打开本地 artifact，只能依据你提供的冻结结构化摘要审阅，故不能给 High。未修改任何文件。
