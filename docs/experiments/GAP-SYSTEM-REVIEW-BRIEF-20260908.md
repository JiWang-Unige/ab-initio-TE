# Gap结果系统审阅提纲：结论与Tiberius下游价值

2026-09-08。用户要求的GitHub快照及ChatGPT Pro审阅已完成；见
[审阅记录](GAP-SYSTEM-PRO-REVIEW-20260908.md)。本文件保留发送前的问题提纲。
当前远端仓库JiWang-Unige/ab-initio-TE经GitHub元数据确认是public；用户已于
2026-09-08明确批准公开提交本轮结果。提交不混入跨物种任务、框架退役删除、数据或模型权重。

## 先读证据

- GAP-ROUTE-TERMINAL-AUDIT-20260908.md：路线范围、失败与未执行的区别。
- GAP-A-B1-SCREEN-20260908-R1.md及对应RESULT：前瞻三组/三seed有界筛选。
- GAP-HN-RANK-FEASIBILITY-20260908-R1.md：另立协议的DEV动作必要条件。
- GAP-BRIDGE-C-UTILITY-20260906-R1.md及对应RESULT：固定Tiberius下游干预。
- 对应scripts/experiments和configs；不要仅根据本摘要作代码审阅完成声明。

## 已支持的结论

HN的NT+seam组合相对完整P3输入，DEV fraction-MSE改善8.59%，AP提高0.0836；
仅支持当前抽样、两遍训练下的探索性信息增量。H0-S改善0.377%，未达固定投资门。
HN完整阈值前缀在宽松风险预算下仍无满足最低恢复量的点；不能据平均指标提升部署。
无跨染色体确认、同一TE插入身份或独立NT因果主张。

C实验M0是原P3 softmask，MW是额外whole-gap oracle填补，MP是额外材料级oracle。
固定Tiberius2.0.7、9DEV core、243参考CDS链、27单元：M0 TP54/FP37/FN189；
MW相同；MP TP54/FP36/FN189。两干预均gained0/lost0，未过预定三项合取门。
MP F1微升0.000971仅是FP净变化，且有两个新unmatched身份，不是恢复正确基因。

这说明本面板上**进一步gap填补未证明有Tiberius收益**。它没有比较unmasked与原P3，
因此不能据此证明或否定P3基础softmask的下游价值，也不是所有mask的数学效用上界。

## 请Pro系统审阅的问题

1. 核对代码/协议/结果分母、配对公平性、训练样本规模、DEV复用与oracle干预限制；
   明确哪些结论成立、哪些过强，给出具体文件证据，不制造必须凑齐的评阅问题。
2. 区分TE材料检测、gap修复、locus identity和下游CDS链预测；哪些可成为论文主线？
3. 在不重跑冻结阴性路线的前提下，是否值得另立“基础P3 mask对Tiberius的实际价值”
   实验？若值得，提出最小有判别力的对照、同序列/同checkpoint/实际mask通道验证、
   参考与独立评估分母、主要终点及预先停止规则；不得把建议当已授权执行。
4. 检查Gate L独立标注缺失与empty-site材料缺失的真实后果；不要用LLM代替冻结的
   A1/A2独立生物标注，也不要把资源不可实施改写为科学失败。

审阅必须先说明是否确实能读取指定Git提交。若不能，列出缺失文件，不能声称完成
repository-wide审阅。建议与已验证事实分开，保留P3、旧冻结结果及chr19–22封存。
