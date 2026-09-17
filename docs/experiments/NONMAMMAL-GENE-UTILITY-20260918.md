# 鸡和斑马鱼：固定 D 掩码对原生 AUGUSTUS 的用途

2026-09-18 在获取本实验预测结果前固定。本实验补足非哺乳动物和第二种基因预测器的用途证据。两物种属于 D 监督物种，AUGUSTUS 也使用既有同物种参数；不能称作未见物种泛化。当前 Tiberius 非哺乳公开模型不消费 softmask，故不将本实验归为 Tiberius。

每物种取 10 条最长、符合条件的常染色体，每条 5 Mb 核心区域，左右各 100 kb halo。起点按接近染色体中部的 1 Mb 格点顺序选取；完整 halo 不得接触 D 的 TRAIN/CAL。选区不读取基因、TE 标签或模型分数。固定 50 Mb 评分、52 Mb 预测输入。未满足几何条件时停止，不按效果换区。

四组为 uppercase 未掩码 U、固定六物种 NTv2-500M binary D、同版本 UCSC 历史 TE 掩码 R_TE，以及在同一 52 Mb 面板运行的原生 Red 全重复掩码。R_TE 保留 Unknown TE，排除 simple/low complexity/satellite/RNA；不是新运行计时的 RepeatMasker。Red 检测全重复、没有类别标签，其语义差异明确保留。

AUGUSTUS 3.5.0 固定原生 chicken/zebrafish 参数，`--softmasking=1 --UTR=off --gff3=on --stopCodonExcludedFromCDS=false`，关闭 alternative sampling/evidence，不输入 RNA/protein hints。仅大小写变化，各组大写序列必须完全相同。原生 AUGUSTUS 默认可能不把终止密码子计入 CDS，本实验显式统一为计入，以匹配 RefSeq 的 CDS 坐标。

基因参考为精确 assembly 上的全部完整 protein-coding ncbiRefSeq isoforms，不仅选择 curated 子集。沿用既有 Tiberius 实验的完整 CDS-chain/locus TP、FP、FN、precision、recall、F1；首 CDS 碱基位于 core、完整链在 halo 内。主比较 D−U，同时完整报告 D−R_TE、D−RED。10 条染色体配对 bootstrap 10,000 次，seed 42，是区域敏感性区间，不是生物学重复。不得将无显著差异解释为非劣性。

准备阶段发现同一 gene symbol 的不同完整转录本可有不相交 CDS，旧 hg19 parser 的“CDS span 必须连通”假设不适合这些参考。首次两作业 12888279/80 在任何模型预测前停止，保留失败输出。修复为按 `(chrom,strand,name2)` 内连通的 transcript spans 定义 locus；同一 locus 保留所有完整 CDS isoforms，真正分开的 transcript loci 单独列为单位并报告。不会丢弃难例或更换选区。FASTA 跨行坐标与同 locus 不相交 CDS 的确定性实例已核验。

原生机制 smoke 在 100 kb 输入中仅将固定 200 bp 改为 lowercase，使用 `--printHints=true` 核对 native `nonexonpart` hints；这是工程验证，不进入用途评分。

首次 smoke 12888475/76 原生预测成功，但 GFF3 模式未打印内部 hints。查阅 [v3.5.0 官方 augustus.cc](https://github.com/Gaius-Augustus/Augustus/blob/v3.5.0/src/augustus.cc) 的 `sfc.prepare(..., Constant::printHints && !(Gene::gff3))`，确认是输出观察开关冲突。只将机制 smoke 设为 GFF3 off 后重跑；正式四组仍输出 GFF3，参数、输入与评分不变。原失败记录保留。

所有耗时 CPU/GPU 步骤进入 private-teodoro-gpu。准备 2 h，D 每物种 1 h GPU / 32 GB host memory，原生预测每 core 24 h CPU、最多同时 4 cores。D 资源申请依据刚完成的相同 checkpoint 100 MiB 推理（12887633：31m52s、MaxRSS 4.4 GiB）缩小，以减少私有分区等待；不改推理参数。先运行第一个 core 验证原生输入、输出和坐标解析，再运行其余固定 core；不按烟测效果决定是否完成。

完成标准是两物种全部 80 个原生预测格、固定分母和完整配对评分。无论结果方向都保存。该批不训练基因模型、不调整 D、不更改阈值。全基因组 EDTA/RM2 另批执行，不能把此处 panel Red 计时冒充全基因组 benchmark。

执行配置：`configs/NONMAMMAL-GENE-UTILITY-20260918.json`；入口：`scripts/experiments/NONMAMMAL-GENE-UTILITY-20260918/utility.py`。
