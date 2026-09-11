# 基础 P3 mask 效用：只读面板准备

2026-09-08，用户在 Pro 系统审阅后要求继续推进。本阶段仅核实已有资产及参考面板，
不运行 P3/Tiberius 推理、不训练、不访问 chr19–22 标签、不选择新操作点。
输出不作为效用或独立泛化结果。旧 C 及 gap 各停止结论不变。

## 在读取候选面板注释之前固定的几何

hg38 chr16、chr18，各十个5,000,000bp core：第 i 个为
`[7,000,000*i, 7,000,000*i+5,000,000)`，i=0..9；左右100,000bp halo，
左端裁切到0。共100Mb core，core/halo之间不重叠，不按基因、TE或预测选择区域。
这是准备面板，不是全基因组随机抽样；不因参考数量少而事后扩展/换区。

## 已核实与待核实

- 远端实际 P3 training_meta.json 确认四状态P3-R1，直接GENERanno base初始化，
  800steps；不是文件名相似的decoupled P3-R2，也不经过其他跨物种模型。
- 实际human_h0_w8192 metadata允许train chr1/3/5/7/9、val chr11/13/15、
  test chr17/19/20/21/22。chr16/18均不在列表；这比推测prefix更保守。
  准备脚本验证此不相交条件，不读取test数据或封存标签。
- 现有记录中的P3历史评价是chr17前缀，gap训练/评价为chr3/5/13。
  仓库定向搜索未找到该P3在chr16/18的历史结果，但搜索无命中不是完整无暴露证明。
- GENERanno预训练精确坐标未知，保持pretraining_overlap_unknown。新问题只能先
  限定固定模型的配对输入效用；不能声称完全未见序列、同源家族或无预训练暴露。
- 固定Tiberius源配置mammalia_softmasking_v2列出29个训练物种，不含Homo sapiens；
  这只是公开配置级证据，不认证全部开发过程独立性。
- 已有hg38 FASTA、RefSeq Curated表与schema、UCSC原始rmsk表均存在。
  参考表name2为gene symbol，不直接冒称稳定GeneID；准备阶段统计symbol/strand键，
  并查同键不相交转录范围。正式gene-locus终点仍需冻结身份及一对一规则。

## CPU检查与改变决策的用途

读取限定染色体的RefSeq字段，报告每core完整CDS链与symbol键数量、边界排除；
读取同范围rmsk区间，确认常规mask不是仅TE-strict衍生表，报告全部repeat union覆盖。
不读取基因组序列或计算任何模型得分。其他染色体行仅检查seqid后跳过，不解析标签。
若参考/常规mask为空、格式不符或监督允许列表重叠，则停止正式实验准备并报告原因。
若通过，也仅是材料准备通过；仍需新实验预算、实际mask通道检查、gene-locus
评价合同与模型暴露边界审阅。Pro的+0.01 F1/-0.005 recall等数值尚未采纳为冻结门。

## 实际准备结果

CPU12522313 COMPLETED 0:0，11秒；结果已收回本地并复制到
`reports/P3-TIBERIUS-BASE-MASK-READINESS-20260908/result.json`。未使用GPU。
20个固定core共2034条distinct完整CDS链、726个全局symbol/strand键；没有
同symbol键不相交的转录范围。23条来源记录因owner halo边界不完整而排除，
chr16第5core无合格参考链，保留该core，不按基因密度换区。
常规原始rmsk区间非空，包含所有repeat类别，不冒充TE-strict mask。

决定：材料足以提出有界实验，不以未达到Pro举例1000loci为由扩样；726是当前
准备口径，不冒充已冻结gene-locus主分母。缺失的是完整的历史暴露认证与正式
gene-locus身份/边界合同，而不是请用户提供已有FASTA/参考表。
见[新实验方案草案](P3-TIBERIUS-BASE-MASK-PROPOSAL-20260908.md)。
