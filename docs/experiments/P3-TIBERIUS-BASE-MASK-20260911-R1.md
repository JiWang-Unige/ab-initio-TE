# P3 对固定 Tiberius 的基础 mask 效用 R1

2026-09-11。用户已明确批准该新效用实验，且取消预算上限。实验范围仍是固定的
hg38 chr16/18 二十个 5Mb core、固定 P3-R1、固定 Tiberius 2.0.7 和三个输入臂；
不训练、不扫描 P3 操作点、Tiberius checkpoint、阈值或面板，不访问 chr19–22。

此前 R0 只是材料准备。R1 在任何模型输出前冻结此配置
`configs/P3-TIBERIUS-BASE-MASK-20260911-R1.json` 和本协议。R1 不重开
whole-gap 路线，不修改旧 C 的 CDS-chain 指标、结果或停止门。

## 问题、输入和主比较

固定同一序列、N、核心/halo、Tiberius 容器、权重、model_cfg、切窗和原生后处理：

| Arm | 输入 | 角色 |
|---|---|---|
| U | 全大写 ACGTN；softmask 第六通道为零 | 无 mask 基线 |
| P | P3-R1 四状态输出，P_TE=interior+left+right，阈值 0.5 的 canonical mask | 主处理 |
| R | hg38 UCSC 原始 rmsk 的全部 repeat 区间 | 常规资源参照 |

主比较是 P-U。R-U 与 P-R 只帮助解释面板对常规 repeat mask 的敏感性；R 依赖外部
repeat library，不能称为 library-free 公平替代。P/R mask 覆盖完整 halo，避免上下文
被输入边界裁剪；三臂只有大小写不同，前五个编码通道必须相同。

## 评价合同

参考为 Curated RefSeq 的完整 CDS。gene-locus unit 是
`(chrom, strand, name2)`：R0 只读审计已确认本固定范围内无同键的非相交转录范围。
每个 unit 由 owner core 内、完整落在 owner halo 的任一 complete CDS isoform 构成；
owner 为 CDS 最小基因组坐标所在 core。跨 halo 的转录本在所有臂共同排除。

预测只读取 native CDS 行；同一 transcript 的 CDS 坐标规范化后，若恰好等于 unit 的任一
预注册 isoform，则该 unit 得一 TP。一个 unit 最多一个 TP；不匹配任何 unit 的独特预测
是 FP；未匹配的 unit 是 FN。GTF/GFF3 的 CDS content multiplicity 必须一致。保留每个
core 的 FP，包括无参考 core；不把 20×3 treatment cell 当作独立样本。

主终点是 `F1(P)-F1(U)`，同时报告 TP/FP/FN、precision、recall、gained/lost units 与
unmatched prediction signatures。固定 20 个 core 作配对 cluster bootstrap（10,000 次、
seed 20260908）；区间描述本面板区块重抽样，不是物种、全基因组或预训练独立性区间。

## 预先指定的解释门

P-U 通过投资门须同时满足：absolute locus F1 增益 >=0.01、bootstrap 95% 下界 >0、
recall 差 >=-0.005、且 U 正确 unit 的丢失比例 <=1%。这只支持固定模型/固定面板的
输入效用，并不自动成为论文或泛化 claim。若门不通过，停止此固定 P3+Tiberius 效用
问题；不追加 seed、阈值、checkpoint 或面板搜索。区间宽时写作证据不足，不写作无效。

R0 已验证 chr16/18 不在 P3 任务监督允许列表，未发现本 P3 对这些染色体的既有结果；
但 GENERanno 预训练精确坐标未知。因此结果不得称为完全未见序列、家族或预训练独立
泛化。Tiberius config 列表不含人类也只作模型配置层说明。

## 执行序列

1. CPU-only `prepare` 写入 geometry 与参考合同，不读模型预测。
2. 在 chr16:0 固定区域做 P3 导出、U/P/R 真正六通道观测和三臂 Tiberius smoke；仅
   验证输入与 native CDS 输出，不计算或判定效用门。
3. smoke 通过后，同一不可变实现对全部 20 core 运行三臂。
4. CPU score 只在 60 个 cell 全部完整时计算结果、bootstrap 和门；独立 NumPy 复算
   计数/门后才解释结果。

用户取消预算上限不改变有限候选范围，亦不授权扩展面板、另训模型或访问封存数据。
