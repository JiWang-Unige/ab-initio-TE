# P3 对固定 Tiberius 的基础 mask 效用：有界新实验草案

状态：PROPOSED_NOT_GPU_AUTHORIZED；2026-09-08。本阶段准备作业已完成，
新实验不同于关闭的gap填补路线，不继承旧gap剩余GPU预算。此文不是运行授权。

## 问题和比较

在固定hg38 chr16/18准备面板上，P3产生的基础mask是否改善同一Tiberius的CDS预测？
主比较P-U；R作常规参照。U为全大写ACGTN输入、相同六通道模型的mask通道零；
P为当前四状态P3-R1、冻结操作点/导出规则；R为现有同组装UCSC原始RepeatMasker
全部repeat区间的softmask。所有臂相同字母、N、halo、切窗、checkpoint和后处理。
R依赖外部repeat资源，不宣称library-free对等基线。该实验不是优化no-mask模型。

## 范围和可解释性

使用准备文档在参考读取前固定的20个core/100Mb，保留无基因core，不扩样。
准备结果2034条distinct链/726个symbol-strand键不是功效保证。
chr16/18不在P3任务数据允许列表，现有记录无该P3在两染色体的评价结果；
GENERanno基础预训练坐标未知，完整历史暴露尚不能认证。
因此默认是固定模型、固定面板的前瞻配对效用实验，不宣称独立未见基因组泛化。
chr19–22不访问、不解封；不改旧C指标及停止门。

## 在模型输出前完成的合同

- 参考gene unit使用固定的chrom/strand/name2与转录范围证据；不得仅将isoform
  行数当基因数。同symbol的不同locus必须拆分或报告歧义。每unit最多一个TP，
  完整匹配预注册任一CDS isoform；预测与参考一对一匹配，不允许同一预测重复获分。
- 为一个unit固定唯一owner（所有完整参考isoform的最小genomic CDS start），
  按owner halo统一确定可评估isoform；主分母及边界排除在看模型输出前保存。
  预测按其最小CDS坐标归owner，只匹配owner相同的参考；跨owner的替代isoform
  应列入边界诊断，避免无声的跨core匹配。
- native CDS-only坐标；前五通道与第六mask通道做真实入口检查；三臂均重新运行，
  不复用旧chr13结果。原chain指标为次要终点，不改旧C。
- 主效用Δlocus-F1(P-U)，同时报告TP/FP/FN、precision/recall、gained/lost及
  unmatched身份变化。允许可靠减少FP构成新任务效益，不要求新增正确基因为唯一途径。
- 候选继续门：F1绝对增益>=0.01、20个区块配对bootstrap的95%区间下界>0；
  recall差>=-0.005，且U正确unit丢失比例<=1%。这些是新任务待批准的投资门，
  不是生物学普遍阈值；区间宽时为证据不足，不声称效应不存在。
  分别列出两染色体结果，区块区间不解释为物种/全基因组置信区间。
- 参考是Curated注释的一致性终点，不等于全部真实基因真值；改变的预测另列人工/
  独立转录蛋白证据核验清单，不用该核验事后改变主参考来偏袒任一arm。

## 建议批准的资源和自动停止范围

无训练、无超参或操作点扫描。新总预算建议<=12 GPUh，含工程失败与smoke。
先只做固定首core chr16:0–5Mb（既定halo）的P3导出及U/P/R真实通道smoke，
smoke最多2GPUh、不计算效用门；按实耗保守外推20core总成本。
若预计超过12GPUh或smoke通道不成立，停止并报告，不自动缩小面板或换方法。
正式推理只有在参考合同及定向一对一/isoform/空core测试通过后开始；到总预算
上限停止，不解封、不追阈值、不重开gap。通过工程/数值检查也不自动产生论文claim。

下一步需用户对这个新效用目标、预算和前瞻门明确批准；常规实现、提交、收集及
结果解释在该批准范围内自主完成，不再逐步询问。
