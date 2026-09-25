# 固定 TE 模型在完整 BRAKER 流程中的用途验证

2026-09-25，用户明确授权自主完成必要实验，不再等待逐阶段批准。本协议承接已终结的选择性 pilot；旧结果及失败记录不变。新工作集中于传统自动基因注释用途，不增加 GLM 训练、物种或湿实验。

## 问题与固定比较

在相同基因组、短读长 RNA、外源蛋白和资源条件下，仅改变重复掩码来源，比较完整 BRAKER ETP 的最终基因注释。固定鸡 galGal6 和斑马鱼 danRer11；两者均是 D 微调物种，不声称未见物种泛化。

三臂为 D、RM2_FULL、RED_FULL。D 直接复用全基因组已完成的冻结阈值 material_runs.bed；RM2_FULL 复用已完成的全基因组 RepeatModeler2→RepeatMasker 全部 native .out 注释，包括 Unknown、简单重复/低复杂度，不按结果筛选。两者均从原始序列大写版本重建 softmask，避免继承下载 FASTA 中原有的 lowercase。RED 在完整同一大写基因组上运行原生默认算法。只 lowercase A/C/G/T，不改碱基或坐标。旧52 Mb RED不作为本实验对照。

BRAKER 每臂分别自动训练 GeneMark/AUGUSTUS，使用独立工作目录和可写 AUGUSTUS config。测量整个流程效应，不把它叫作固定预测器的纯 mask 效应。复用固定 sandbox（标签 v3.1.1，实测 BRAKER 3.0.8 / AUGUSTUS 3.5.0）；不静默升级，不调用 BUSCO/compleasm rescue。正式运行不能使用官方小样例的 skipOptimize / gm_max_intergenic=10000。

## 输入与证据隔离

部署 RNA 为每物种预先选择的2–4个公开 Illumina paired-end RNA-seq runs。以物种/组织/技术和数据量选取，不读取 D 或基因预测结果。每物种压缩数据下载上限25 GB，保留原生来源、访问时间和大小；同一无注释辅助的 HISAT2 BAM 供三臂共用。蛋白选版本固定的 OrthoDB vertebrata 分库，按源序列 taxon ID 排除 Gallus gallus 和 Danio rerio（所有臂相同）；不得从目标 RefSeq 翻译蛋白作为输入。具体 accession、URL、版本与实际排除规则在数据作业启动前写入本实验 input manifest。

独立 PacBio/作者处理转录本不进入训练或 hints。完整内含子链恢复是结构证据，不能冒充完整 CDS 起止真值；作者使用参考注释过滤、校正或合并的部分须分开列出，无法隔离就降为外部一致性，不伪称独立真值。无表达不能视为阴性。

## 评价（新预测结果前固定）

主比较 D−RM2_FULL，强对照 D−RED_FULL，逐物种报告，不挑选赢家或池化成动物界结论。主参考端点为 exact complete CDS-chain gene-locus precision/recall/F1，使用已固定的同 assembly ncbiRefSeq 完整蛋白编码记录。RefSeq 是参考一致性，不是穷尽真值。

主评价域：所有常染色体，排除 D 的 TRAIN/CAL 整条染色体，再扣除旧 NONMAMMAL-GENE-UTILITY 的10个已暴露 halo 区间。只按坐标生成清单；该域未用于旧用途 pilot，但不是全项目从未看过的 sealed 独立测试。跨入排除区的 CDS 链不计入主域，分母与排除数量在读取新预测前保存。完整常染色体与旧面板另报，不能冒充新增重复。基因组全部仍交给 BRAKER 自训练；评估隔离针对 D 监督暴露，不能称完全 inductive 的基因预测训练/测试分离。

以染色体配对 bootstrap（10000次，固定seed42）描述区域敏感性，保留逐染色体结果、gross gains/losses，不将其当生物重复，不看结果定非劣界值。独立长读长多外显子转录本的完整内含子链恢复率作辅助证据（统一链去重、同 assembly、单独报告组织/参考辅助边界）。TE结构候选仅作有限位点描述；现有22个位点不足以证明宿主/自主TE功能选择性。

## 顺序、资源与停止规则

1. 原生 ETP smoke：使用容器自带1 Mb genome、RNAseq.bam、proteins.fa。private 8 CPU / 32 GB / 2 h，无 GPU。使用官方测试的 skipOptimize 与 gm_max_intergenic=10000，加速仅限此工程样例；不用 BUSCO。须有实际非空、可解析的最终 CDS 与 GeneMark/AUGUSTUS 中间产物，版本通过不等于流程成功。
2. 两物种 whole-genome mask 准备：每物种 private 8 CPU / 48 GB / 6 h，无 GPU。生成 D/RM2 masks，执行完整 RED，逐记录核实序列和坐标一致。原产物只读。
3. RNA/蛋白数据准备与比对：精确 manifest 固定后，每物种 private 16 CPU / 64 GB / 24 h；共享蛋白下载/过滤 private 4 CPU / 32 GB / 6 h。不得把运行日记当成功。
4. 正式 ETP：上述输入核实与原生 smoke 通过后，每臂 private 16 CPU / 96 GB / 72 h，无 GPU，最多两臂并发，共六臂。正式默认优化，不给不同 arm 不同预算。总六臂计算上限6912 allocated CPU-hours；预处理单列。超时/OOM按预先预算保留NA，不为获得阳性重复加预算。
5. 全部固定臂无论方向均完成评分；工程失败先基于原生日志定位，必要修复不改科学参数，并保留每次累计成本。不会因鸡/鱼效果不同增加物种、seed、模型或改阈值。

确认缺失的具体输入、工程路径及证据资格由 Agent 继续取证并落实，无需用户重复批准。只有实际不可获得的数据、账户授权或超出上述资源/研究方向的实质变化才另行说明。完整结果产生后再决定中心主张；不预设胜出或期刊录用。

## 本批精确部署输入

输入已在获取前写入 configs/BRAKER-MASK-UTILITY-20260925.inputs.json。鸡选 GSE166257 的 ileum、lung macrophage、ovary、thymus 各rep1：SRR13642599、SRR13642601、SRR13642607、SRR13642613，压缩20,490,058,265 bytes；鱼选 GSE280830 的 WT embryo 24/48 hpf：SRR31188006、SRR31188005，压缩6,055,852,095 bytes。鱼不引入KO，鸡为组织/细胞类型混合、鱼为胚胎，均不是完整组织覆盖；按输入覆盖与成本选择，未依据mask效果。精确GSM、完整run ID、每mate URL/字节与仪器在manifest中。

蛋白为作者发布的OrthoDB v12 Vertebrata，源文件6,188,932,489 bytes；按头部taxid剔除9031和7955全部记录。同一新运行原生统计剔除鸡17,274、鱼25,793条，保留19,350,805条外源蛋白。该库仍含同源知识，不能把外源蛋白说成完全独立于基因注释。

斑马鱼独立长读长固定GitHub commit f5a23b0baed4c3032b7615d279f6c5d0da71d2b5 的 merge.annotated.gtf.gz（5,921,281 bytes）。作者用GRCz11参考做比较；只作结构支持，class=u不等于蛋白编码阳性。RNA缺失不能定义FP。原数据处理来源及引用在manifest中。

## 评价准备中的注释别名处理（目标预测前）

首次全基因组准备揭示鱼主域4组、完整域5组完全相同的染色体/链方向/CDS坐标被多个RefSeq gene name登记。按观测上不可区分的完整CDS链连通合并参考单位，保留全部原始gene IDs、transcript IDs、源文件行号、候选loci数和合并清单；不任意删除行，也不声称这些名称已经被生物学证实是同一基因。鱼主域候选loci14,580→14,576，完整域25,531→25,526；鸡原6,588主域loci无此冲突、保持不变。该处理在任何目标BRAKER预测/评分前固定，全部mask臂同一分母，旧pilot分母不改写。初次失败鱼输出保留，恢复使用独立zebrafish-r2目录，由preparation.json指向；后续评分须使用该目录。
