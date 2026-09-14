# C. briggsae 注释与组装修订：当前可执行边界

2026-09-14，一手来源定向核实。目的有两个：补足固定 D 外部区域的比较注释，以及寻找人类之外的组装/注释修订实例。二者不共用未经核实的 truth。

## 现有 CB4 评价缺口

当前 D 面板采用 CB4 `GCA_000004555.3`；[WormBase ParaSite](https://parasite.wormbase.org/Caenorhabditis_briggsae_prjna10731/Info/Index/)标识该组装。原 Dfam 3.9 curated-only RepeatMasker 结果在四个固定区域中没有合格 TE 阳性；不能据此判断模型召回失败。

已找到的 [RepeatMasker 历史下载](https://www.repeatmasker.org/species/cb.html)是 cb3（Jan 2007），不能直接作为 CB4 坐标真值。当前定向搜索尚未定位到可直接下载、来源明确的 exact-CB4 TE BED/GFF 或独立 TE library；这不是断言该资源不存在。普通 gene GFF/GTF 也不能替代 TE 标注。

## CGC2 是明确的新版本候选

[O'Connor 等的 G3 论文](https://academic.oup.com/g3journal/article/16/8/jkag158/8710937)于 2026 年发表，提供 CGC2 无缺口 T2T 组装。对应 [BioProject PRJNA1451919](https://www.ncbi.nlm.nih.gov/bioproject/1451919)和组装 `GCA_058131755.1`。材料是 AF16 的衍生株 CGC2/PB420，并非与 CB4 完全相同的生物样本；真正序列差异与组装、注释修订必须分开。

论文使用 RepeatMasker 4.2.1 和 C. briggsae 自定义库。[公开工作流分支](https://github.com/AndersenLab/geneAnno-nf/tree/CGC2_geneAnno)的 `main.nf`（检查版本 `d0a17b5e69317ba760f40ab5df6937f8fb6a1bc8`）引用实验室文件系统中的 `c_briggsae.QX1410_nanopore.Feb2020.genome.mask_elements.fa`，不是已验证的公共下载链接。本文没有访问该私有路径。

[Moya 等 2023 年论文](https://link.springer.com/article/10.1186/s12864-023-09582-0)描述了结合 de novo、结构和数据库证据构建、分类并过滤重复库的方法。这可以解释单一现成 curated library 覆盖不足，但不能凭论文方法描述重建其确切库内容。

[CaeNDR 当前 C. briggsae release](https://caendr.org/data/data-release/c-briggsae/latest)在本次读取中指向 `20250626`、QX1410/Feb2020；它不是 CB4 或 CGC2。页面的 `canonical_geneset.gtf.gz`、`annotations.gff3.gz` 未被证明是 TE 专用轨道，不作为 TE truth 导入。

## 收敛动作

1. 优先取得有明确许可、版本和分类说明的 C. briggsae repeat library，并在既有 CB4 固定四区域上运行独立 alternative comparator；模型、概率、CAL 和区域不变。
2. CGC2 修订线先取得原始 TE 轨道/库及可靠 CB4↔CGC2 映射，再限定共同可映射区间。新增加的序列、失败映射及样本差异单列，不能计为旧模型 FP 的“纠正”。
3. 在资产未齐备时，不启动全基因组 de novo 库构建，也不移动现有区域寻找更高的阳性覆盖。取得新版支持后仍比较旧 FP 与匹配背景，并保留旧 TP/FN/TN 全分母。

当前结论：**候选版本和方法来源已明确；exact-CB4 替代 TE truth 与 CGC2 TE 资产仍待取得。尚无跨版本模型 FP 支持结果。**
