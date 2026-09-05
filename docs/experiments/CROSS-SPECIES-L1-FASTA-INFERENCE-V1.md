# L1 sequence-only FASTA 接口 V1

2026-09-05：初始化训练扩展科学NO-GO后的已授权有界工程。
不训练、不改变冻结校准/阈值/原评估器、不释放任何保留面板。
实现与验证进行中，不将接口就绪等同模型有效性或公开发布。

## 输入与输出契约

- 输入：plain/gzip FASTA、已存在的NTv2 token-classification final model、
  tokenizer/model-code目录和该模型原有的六物种共享CAL校准JSON。
- 不接收labels、RepeatMasker注释或Label-A Unknown/callable mask。
- 每个contig从0开始按4096bp无重叠分窗，短尾使用实际序列长度；复用
  `calibrate_evaluate_x0.py` 的6-mer/单碱基尾部投影与冻结Platt变换。
- 概率轨覆盖全部输入碱基；BED只使用校准文件内阈值的`>=`规则，
  跨相邻窗口/批次合并连续阳性，不跨contig，不补gap、不筛长度。
- 单独输出非ACGT输入的ambiguity QC BED。歧义输入由已有tokenizer
  规则映射，QC轨不能作为删掉预测的标签替代物。
- 输出为material概率及connected-run BED，不是生物学插入实例ID，
  没有family/superfamily预测。坐标为0-based half-open。
- 分批推理、流式写概率/片段，避免累积全染色体浮点预测数组；FASTA
  读取可保留一条contig序列。输出目录是独立运行产物，不写checkpoint。

## 验证边界

首先用合成margin provider验证坐标、短尾、批次边界、跨窗连通、
多contig、gzip和ambiguity不删预测；校准源不匹配必须在推理前拒绝。
随后仅对合成FASTA使用冻结D seed42完成一次小型真实模型工程smoke，
沿用项目Slurm运行环境。可将相同合成序列直接送入已有推理helper，
比对完整概率与冻结阈值结果；这是接口一致性，不是新的科学测试。
不读取CONF、reserved worm、horse/opossum/dm6/cattle资产。

现有历史 `pipelines/PIPE-TEFM-FINAL-20260623/infer_fasta_to_bed.py`
是8192bp、single_nt_nospecial、固定0.5的CE桥，不适配本NTv2 6-mer
加Platt模型；不改它的冻结语义。新接口独立位于
`scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/`。

## 效用与发布范围

工程通过最多支持“可对无标签FASTA生成完整坐标概率/材料片段”的声明。
不能由此声称跨物种泛化、碎片重建、插入边界恢复或独立下游效用。
后续实用比较应冻结模型/校准、真实使用单位、资源成本和决策终点，
把material coverage与严格topology负面对照同时保留；不放宽gap或指标。
独立utility数据、最终保留面板、同源/家族/历史暴露和多seed确认仍需
单独协议与用户审阅。公开代码/权重/服务、改变可见性与随包素材的选择
不由本接口自动授权。来源与许可现有记录及缺口仍见
`CROSS-SPECIES-L1-RELEASE-READINESS-20260905.md`，本次不作法律结论。
