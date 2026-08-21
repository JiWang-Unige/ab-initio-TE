## 1. Overall judgment

**run-sanity-check-first**

这是纯粹的审查清单闭包失败：科学 payload 在读取任何数据前即被 fail-closed 阻断，因此既不能支持也不能否定 consensus-collinearity 方法假设。

## 2. SOTA gap interpretation

- SOTA gap：**n/a**
- 当前没有可用科学指标，不能计算相对 RAW、GAP20、GAP100 或任何 SOTA 的差距。
- 调参是否合理：**否**。尚无算法运行结果，且失败与模型、阈值、目标函数无关。

## 3. Comparability/fairness audit

| 项目 | 审核结论 |
|---|---|
| Dataset | 计划使用 frozen Rice T1 curated-positive subset；本作业未读取 assembly、truth TSV 或 consensus library |
| Split / truth tier | T1 positive-only truth；不支持未标空间负例推断，不支持 whole-genome precision/F1；本次未执行评估 |
| Metric | 计划比较 parent recovery、leaf retention、cross-rm-id false-fusion、boundary/topology；实际 primary metric 为 `null` |
| Preprocessing | mapping、strand/coordinate evidence、chromosome-wide DAG 均未运行，无法审计实际输出 |
| External assets | frozen EDTA consensus 已在合同中声明，但本作业未读取；不存在运行时版本漂移证据 |
| Resource | 调度资源符合 exact 8 CPU / 32 GiB / 2 h / 0 GPU；elapsed 0 秒 |
| Claim eligibility | **claim-ineligible**；本次既不是科学结果，也不是 valid negative |

## 4. Semantic success/reproducibility audit

| 检查项 | 结论 |
|---|---|
| Metrics parseable | **是**；audited metrics 与 `validate_goal` 可解析，但科学指标为空 |
| Finite values | **n/a**；没有产生需要有限性检查的科学指标 |
| Scientific payload executed | **否**；allocation-side contract tests、数据读取、mapping、DAG 和 evaluator 均未执行 |
| Leakage | 未发现实际泄漏，因为 truth 和数据均未读取；只能确认静态合同禁止 assembler 使用 `rm_id`、parent boundary 和 class，不能替代运行时验证 |
| Logs/manifests | **充分定位工程根因**；traceback、job-scoped audit、manifest 与哈希材料能够复现失败边界 |
| Fail-closed behavior | **正确工作**；`runtime_hashes.py` 检出共享运行时代码未进入独立审查文件集并立即终止 |
| Semantic success | **false / failed_run**，判定正确 |

## 5. Method assessment

方法假设仍然**完全未测试**。本次失败只说明审查清单没有覆盖全部 `runtime_code_files`，不说明 consensus identity、strand、coordinate evidence 或 chromosome-wide collinearity DAG 不足。

现阶段没有证据支持更换 backbone、loss、assembler 或引入新的结构替代方案。尤其不能因此退回 DEC-001/002 已否决的 gap、HMM、CRF、轻量 interval head 或 local fragment-graph cousins。

## 6. Track recommendation

允许一次**同一 exp_id 的窄重试**，无需创建新实验，但必须同时满足：

- 将 `scripts/pre_submit_gate.py` 以实际路径和 SHA 纳入 `code_review_gate.json.reviewed_files`；
- 对该 machine gate 修复进行 fresh independent delta review；
- 重新运行 login-side 与 allocation-side hash closure；
- 除 job-scoped gate/audit 产物外，不修改实现、配置、数据、阈值、comparators 或 evaluator；
- 资源严格保持 **8 CPU / 32 GiB / 2 h / 0 GPU**；
- 保持 preflight ≤300 秒、payload 5940 秒、publish headroom 900 秒；
- 禁止资源 override、自动 retry、GPU、full F 或 claim 升级。

若任何其他 runtime 文件或科学代码发生变化，则该授权失效，必须重新接受相应范围的独立审查。

## 7. Risks/blockers

- `reviewed_files` 与 `runtime_code_files` 可能再次发生集合不闭包。
- 仅修复已知路径而不执行集合相等检查，可能遗漏其他共享依赖。
- T1 positive-only truth 无法支持 whole-genome precision/F1 或未标区域 false-positive 结论。
- 即便重试得到 `INFORMATION_SUFFICIENT`，也只能授权另行审查的 bounded follow-up，不能直接进入 GPU/full F。
- 同一 exp 重试必须保持 job-scoped artifact 隔离，避免覆盖 `11529694` 的失败证据。

## 8. Next action

**把 `scripts/pre_submit_gate.py` 及其实际 SHA 加入该实验的 machine `reviewed_files`，通过 fresh independent delta review 后，以原定 exact 8 CPU / 32 GiB / 2 h / 0 GPU 合同提交唯一一次同-exp sanity retry。**

## 9. Confidence

**高（0.98）**。失败根因和执行边界证据明确；对方法科学有效性的置信判断为 **n/a**，因为 payload 从未运行。
