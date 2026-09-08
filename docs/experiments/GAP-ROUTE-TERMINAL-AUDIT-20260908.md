# Gap 路线收尾：本轮有限候选结清，尚无可部署修复

更新：2026-09-08 用户恢复指令已取消机器 goal、强制第三方评阅及人数门槛。
Claude OAuth/评阅缺额不再是阻塞；不重试或替换评阅者。以下科学冻结规则仍有效。

当前任务是将已提出的 gap 路线按冻结规则结清，不是重跑已经失败的路线，
也不是用 C 的结束代替所有路线。跨物种模型构建任务另行推进；这里不修改其目标。

本轮持续授权下的新A/B1筛选、后续HN动作必要条件诊断均已执行并收齐结果。
结论：HN有探索性信息增量，但低风险whole-gap动作必要条件仍无解；H0-S未过筛选门。
本轮有限候选按预定停止分支结清，不再追加GPU。不是“所有可能路线均已实验失败”。
累计6.593333/24GPUh，P3不改、chr19–22封存。核心证据见
[A/B1结果](GAP-A-B1-SCREEN-20260908-R1-RESULT.md)与
[HN动作诊断](GAP-HN-RANK-FEASIBILITY-20260908-R1.md)。

## 已核实的路线范围

| 路线 | 当前证据 | 科学状态 | 剩余动作 |
|---|---|---|---|
| 旧结构化 decoder / interval / fragment graph | docs/09 DEC-001/002 的已关闭实验 | 已有失败结论，保持关闭 | 不复跑旧 cousins |
| Fragment gap topology | FRAGMENT-GAP-TOPOLOGY-20260831-R1.md | 描述性审计完成，不是修复方法成功 | 无部署规则获准 |
| 神经 Stage0 oracle | GAP-BRIDGE-NEURAL-STAGE0-RESULT-20260902.md | PASS_TO_STAGE1，非可部署模型 | 后续 Stage1 已执行 |
| G/R/H whole-gap readouts | GAP-BRIDGE-NEURAL-STAGE1-R1-CLOSURE-20260905.md | NO_ACTIONABLE_ARM，科学 NO-GO | 保持 P3/封存，不重开 |
| B0 尾部/Brier/seam 诊断 | GAP-BRIDGE-ROUTE-REASSESSMENT-20260905.md，三个已完成 CPU 诊断 | 诊断完成；没有推翻 G/R/H NO-GO | 不把描述归因成新训练证据 |
| A H0/HN 冻结 NT 增量 | 新配对screen及独立复算完成 | HN-O MSE降低8.59%、AP提高0.0836，探索性筛选阳性 | 原全量仍未执行；不把组合效应孤立归因于NT |
| C MW whole-gap oracle utility | 12416179，27 单元取证与复算一致 | delta0，gain0，loss0：冻结继续门 FAIL，已收尾 | 不复跑，不扩大此 predictor/panel 的 gene-utility 路线 |
| C MP material oracle utility | 同上 | delta+0.0009710309111506943，gain0，loss0：冻结继续门 FAIL | 不以 FP 净减替代 gain 门，不自动启动 partial-fill 学习 |
| B1 ordered/shuffled H replay | 新配对screen及独立复算完成 | H0-S MSE降低0.377%，未达5%门，有限实现停止 | 原全量未执行，不泛化为所有顺序策略失败 |
| HN 排序动作必要条件 | CPU12520644，60497完整tie阈值及决策点直接复算 | 即使放宽为DEV全跨度预算仍0可行点；固定模型动作NO-GO | 停止CAL/部署推进，保留信息增量阳性 |
| 生物学 Gate L | FBTI-GATE-L-EXECUTION-20260901：172包工程面板已存在，缺独立专家标注 | RETIRED_UNEXECUTED_RESOURCE_INFEASIBLE，非生物学失败 | 取消CLI评阅不替代A1/A2生物标注和裁决 |
| Gate O/E及partial-atom relation模型 | FBTI-EXTANT-LOCUS-PHASE0-R1：依赖L/O/E的顺序前提 | 前提真值未建立，未执行，不记科学失败 | 不用二值TE comparator替代locus identity |
| Comparative empty-site rescue | Phase0第4节rank3仅提20-locus方案，reassessment确认无可执行成对panel | 已授权材料范围内暂不可实施，非生物学失败 | 与Gate L区分；FlyBase同组装packets不是orthologous empty-site证据 |

## 全目标完成条件审计

- 12416179 的真实终态、27 单元收集、重新计算：已完成，见
  `outputs/GAP-BRIDGE-C-UTILITY-20260906-R1/collection_audit.json`。
- result-log、两臂 `validate_goal.py`：已完成。两臂 `not_yet` 是合法阴性，
  run_ok/semantic_ok 为 true；没有改变冻结三项门或 ACTIVE_GOAL.json。
- 历史独立评阅仅Codex完成；其余未完成的事实不改写。用户现已明确取消该交付要求，
  无待补评阅。Agent依据已验证结果执行原冻结停止规则，C收尾完成；不宣称评阅共识。
- “所有路线都得到实验成功或失败”：**不作此声明**。原全量A/B1未执行，旧全量
  两遍实耗47:30:23超过本轮24GPUh；新screen不能替代其科学结论。Gate L及其依赖、
  empty-site缺真实材料，属于资源/证据性未执行，不改写为生物学失败。
- C 阴性按冻结规则停止本 predictor/panel 的 gene-utility 扩张；不对全部
  TE material 修复作普遍否定，不事后放宽 gain、loss、端点或面板。
- 持续授权已覆盖范围内新实验、训练、配置、预算和前瞻门的自主选择，本轮据此执行。
  停止来自实际结果与已记录分支，不是缺评阅、机器goal或常规批准；不突破总预算、
  旧冻结协议、封存数据或对外发布边界。未动机器goal状态。
- 当前无本轮待执行/待收集作业。新screen三组、三seed、两遍、完整DEV和独立复算
  已完成；HN后续必要条件失败，不继续CAL或用剩余额度扫描超参。阶段协议和结果分别
  保留，不用后续NO-GO抹去前序筛选阳性。

## 验证器口径说明

### A 输入缺失的实际分布（2026-09-08补核）

已取回原coverage_audit.json并汇总原strata，未重新推理或读取科学CAL指标：
chr3 TRAIN52、chr5 TRAIN22、chr13 CAL-FIT4、CAL-GATE11，共89crop；全部
comparator_known=1，DEV0缺失。故缺失确实影响训练和校准输入，不可将其解释为
仅unknown或无关推理窗口。原leading800N sentinel实际仅覆盖686/4096bp；
重新跑相同token预算不保证恢复。以上是恢复初查时点；随后新screen前瞻规定两臂共同
排除所选TRAIN内51个缺失crop，未改旧母体。DEV无缺失，已完整预测；本轮未推进CAL。

通用 validate_goal 的 0/1 退化检查针对绝对性能，不适用于合法的零增量。
本次只把绝对 arm micro-F1 用于通用语义检查，真正的 success_criteria 仍为
delta>0、gained>=1、lost=0，完整性 guard 为 27 单元与 243 链。未改共享脚本。
通用输出的 tuning_allowed/claim_gate 不能覆盖当前协议“不调门重跑”的停止规则。
