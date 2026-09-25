# 传统基因注释流程作为主要应用验证

2026-09-25：作者明确要求，在科学合理的前提下加强与传统生信流程结合，以纯生信论文为目标。采用这一方向，保留全部历史Tiberius结果及其限制；不因某接收器更容易得到阳性而更换比较口径。

## 当前依据及执行

- Tiberius官方推荐unmasked模型作为较安全默认值，因为softmask特征受训练/部署掩码分布差异影响；这不等于禁止mask或所有mask均无价值。unmasked权重会忽略软掩码，不能用它测软掩码处理效应。既往mask-aware权重输入全大写的U_soft，也不是独立的unmasked权重基线。[官方说明](https://github.com/Gaius-Augustus/Tiberius#choosing-the-model-weights)
- BRAKER明确推荐重复序列softmask，其GeneMark/AUGUSTUS流程与本研究输出有直接接口。[BRAKER](https://github.com/Gaius-Augustus/BRAKER#different-braker-pipeline-modes)
- 现有鸡/鱼固定AUGUSTUS3.5.0实验作为主要的受控应用层：同一参数、序列、区域、参考，仅改变mask。`FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925`正在完成全基因组RM2来源及等预算强对照。旧Tiberius作为第二种接收器证据，不删除不利比较。
- 本ID启动一次BRAKER3容器及入口核查，使用官方BRAKER4当前列出的`teambraker/braker3:v3.1.1`固定镜像，private 4 CPU/16 GB/1h，不申请GPU。[镜像来源](https://github.com/Gaius-Augustus/BRAKER4#installation)

## 分清两种问题

1. **固定接收器的mask效应**：当前AUGUSTUS矩阵回答位置/覆盖量的贡献，不让各臂改变基因模型参数或获得不同RNA/蛋白证据。
2. **实际自动注释流程的效用**：后续BRAKER的GeneMark/AUGUSTUS自动训练是流程自身的一部分。若每个mask独立训练，测到的是整个流程的总效应，不能写成固定模型的纯mask效应。也不能冻结只在D上训练的参数，让其他mask承担不匹配。

后续BRAKER方案先选定一种证据模式，再锁定同一assembly、RNA/蛋白输入、参数及计算预算；D、完整RM2→RepeatMasker、完整基因组RED使用同一套证据。BRAKER官方不推荐无mask，若加入U，只能作为掩码消融，不能把它当作官方推荐基线。当前52 Mb面板的RED结果也不能替代全基因组RED。

BRAKER3（已发表ETP流程）优先作为实际流程；BRAKER4可作为同一GeneMark/AUGUSTUS逻辑的工作流实现，不把版本数增加当作独立验证。ETP需要RNA和合适的多物种蛋白库，不能缺失蛋白后静默换成ET/ES并沿用ETP名称。[输入与训练说明](https://github.com/Gaius-Augustus/BRAKER#braker-with-rna-seq-and-protein-data)

## 证据隔离与启动边界

- 既有鸭嘴兽`SRR23268362`已作为独立评价证据。若将其用于RNA hints或训练，它就不能再作为同一新流程的独立验证；需要另留证据，或明确退回参考注释一致性评价。
- 参考GTF翻译的同目标物种蛋白不能既充当部署输入，又被当作独立验证其CDS正确性的证据。所有臂使用相同的事前限定蛋白知识条件。
- BUSCO/compleasm若参与提示、筛选或基因补救，其同库分数只能是QC，不能作为独立主终点。
- 完整CDS、内含子链、宿主丢失和TE相关误纳分别评价。完整转录本不自动提供CDS起止真值；无RNA不是阴性。
- 新的确认性矩阵需要在读取新结果前固定。当前只执行已有AUGUSTUS矩阵和BRAKER入口准备，不启动未定输入的全基因组训练，不增加物种、GLM训练、湿实验或多seed搜索。

本轮公开产物为协议、脚本、入口日志/状态和明确的资源缺口；镜像留在Baobab。入口成功不等于完整流程可运行，更不等于科学结果成立。下一步是否开展完整BRAKER确认，结合两个固定物种的pilot终态和独立评价证据资格决定。
