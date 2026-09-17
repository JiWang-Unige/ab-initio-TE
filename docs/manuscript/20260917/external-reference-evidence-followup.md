# 非哺乳外部评价：参考资格与最终物种选择

2026-09-17。最终固定为家蚕和 *D. simulans*，均在当前 D 六物种任务监督之外。选择依据是 assembly/坐标配对和原始论文资源，发生在查看新模型输出之前；历史项目资产暴露和未知的基座预训练暴露分别记录，不声称从未见过这些序列。

## 可执行输入

| 物种 | 固定 assembly 与来源 | 参考资格 |
|---|---|---|
| 家蚕 *Bombyx mori* | `GCF_014905235.1 / Bmori_2016v1.0`；[NCBI 同 accession 目录](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/014/905/235/GCF_014905235.1_Bmori_2016v1.0/)提供 FASTA、`*_rm.out.gz` 和 `*_rm.run`，项目已有配对缓存。 | RM open-4.0.8、Dfam_Consensus-20181026 + RepBase-20181026；`-species 'bombyx mori' -s -no_is -cutoff 255`。是来源依赖的已注释正类，不能把未命中区视为真阴性。 |
| *D. simulans* | `GCA_004382185.1 / ASM438218v1`（wXD1），PacBio assembly，146,773,509 bp，`PRJNA383250`；[UCSC 同 accession 文件](https://hgdownload.soe.ucsc.edu/hubs/GCA/004/382/185/GCA_004382185.1/)提供约45 MB FASTA、3.7 MB RM output和assembly report。 | [RM运行说明](https://hgdownload.soe.ucsc.edu/hubs/GCA/004/382/185/GCA_004382185.1/html/GCA_004382185.1_ASM438218v1.repeatMasker.html)记录open-4.0.8、Dfam_Consensus-20181026 + RepBase-20181026，`-species 'drosophila simulans' -s -no_is -cutoff 255 -frag 20000`。同样不是独立生物学真值。该物种与封存的 *D. melanogaster* dm6 不同。 |

两物种均采用长度决定的四条最长contig中央4,194,304 bp，总计每物种16,777,216 bp，不根据标签密度或模型分数选区。冻结模型、原生推理、结构证据和作业记录见[执行协议](../../experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917.md)。

## 增加的证据层

在同一固定序列上运行 EDTA 2.3.0 的原生 LTRharvest/LTR_FINDER→LTR_retriever 路径，保留完整结构候选的pass list及原生清理结果。该层不读取 D 预测，提供对完整 LTR 的算法正交支持；它仍有方法选择偏好、可能使用蛋白分类及自建序列过滤，不能升级成手工真值，也不能覆盖所有退化或非LTR TE。

分别报告历史库正类和结构正类上的可调用碱基回收率、分母和区域间差异。未标注区保持unknown；不计算由伪负类构成的biological precision/F1。来源层上的positive recovery是允许且有界的指标，不能解释为全基因组真实recall。

## 论文补充材料的实际核实

[Chakraborty等人的论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC7919458/)及[Europe PMC supplementary bundle](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7919458/supplementaryFiles)已实际下载到临时目录并解包。`File_S1.fasta`含2,316条、7,121,885 bp，是结合既有库、REPET发现和新satellite的家族序列库，没有genome coordinates。它可以支持后续同assembly的库来源比较；该派生比较尚未运行，不是本轮已完成的独立验证。

其中193XP经FISH支持，但header明确为`Satellite/Satellite`。对`GCA_004382185.1`的精确匹配及标准RM层空白仅作为卫星重复覆盖控制，**从TE正类、模型TP和TE漏注释主张中排除**。本次补充材料检查没有找到TE-specific独立坐标或TE-specific FISH阳性。实际记录、数量与脚本见[补充材料核实报告](../../../reports/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/sources/chakraborty_supplement_metadata.md)。

因此，当前补齐的是来源清楚的外部正类评价和额外结构支持；独立的全基因组TE生物学准确性仍未建立。公开仓库只包含代码、accession、来源与紧凑结果，不重新分发RepBase库或原始supplementary bundle。

## 未采用的候选

青鳉缓存`oryLat2 / MEDAKA1`是2005年assembly，配套RM open-3-1-6/RepBase 20061006；它不是2017年的`GCF_002234675.1`。因标签过旧且此轮找到更明确的长读长来源，没有新增青鳉推理。Kofler2015的历史*D. simulans* Drive入口未取得可读坐标和确切配对，停止该来源，不以新accession冒充旧坐标。候选取舍均未使用新模型分数。
