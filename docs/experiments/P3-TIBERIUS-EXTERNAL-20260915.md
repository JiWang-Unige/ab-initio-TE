# P3 mask 的外部哺乳动物下游验证

用户 2026-09-15 授权的新实验；不是原人类 20-core 实验的修改或再选阈值。

## 固定问题与范围

比较固定人类 P3（四状态 U-Net、8192 bp 窗口、P(TE)≥0.5）产生的 softmask，是否在外部哺乳动物改善 Tiberius 的参考 CDS-chain/locus 一致性。选择牛 ARS-UCD2.0（GCF_002263795.3）和鸭嘴兽 mOrnAna1.pri.v4（GCF_004115215.2）：覆盖真兽类和单孔类，均不在当前 Tiberius checkpoint 的 29 个训练物种清单中。P3 是人类训练模型；其结果不归给共享 D 模型。

每物种取 assembly report 中最长的十条常染色体，各在 1/3、2/3 位置附近取一个 5 Mb core；两侧各 100 kb halo。区域在模型输出前按长度决定，不按基因密度或指标挑选。总计 40 cores、200 Mb 主评价范围。若 assembly/report 无法支持该几何，先记录资格失败，不事后选择易获阳性的区域。

## 五个配对输入

| 模式 | 输入 | Tiberius checkpoint | 用途 |
|---|---|---|---|
| U_soft | 全大写 | mammalia_softmasking_v2 | 同 checkpoint 的输入干预对照 |
| U_nosm | 全大写 | mammalia_nosofttmasking_v2 | 官方适用于无 mask 的流程对照 |
| P | 固定 P3 TE mask | mammalia_softmasking_v2 | 本方法 |
| R_TE | 实际 RepeatMasker TE-only mask | mammalia_softmasking_v2 | 同语义主要参考对照 |
| R_all | 同一次 RepeatMasker 的全部 repeat mask | mammalia_softmasking_v2 | 常用全部重复序列流程 |

原生 RepeatMasker 固定版本/库，使用对应物种 lineage；显式记录 curated/uncurated 范围和未知类处理。不用旧 UCSC track 冒充本次 native 输出。所有 FASTA 的大写字符必须完全一致；检查 actual encoding 与相应 mask 设置，完整记录每个 cell 的原生调用。

## 评价与停止

匹配 assembly 的 NCBI GFF3 为基因参考；解析 gene→transcript→CDS，排除 pseudogene、明确 partial、异常翻译等不适用条目，并单列 NM/NP 与 XM/XP 支持，不能把较好注释当成完美生物真值。以唯一 gene locus 为单位，任一合格完整 CDS isoform 精确匹配计为该 locus 正确；保留错误预测链、未命中 loci 和边界排除分母。

每物种分别报告 P−U_nosm、P−U_soft、P−R_TE、P−R_all 的 precision/recall/F1 变化和 gain/loss。按十条染色体配对 bootstrap，避免把同一染色体的两个 core 当完全独立样本；固定 10,000 次、seed42。主比较是 P−R_TE，流程效用比较为 P−U_nosm；报告效应区间，无显著优势时不声称优于 RepeatMasker。

原人类 1% 正确位点损失要求及失败结论保持不变。本批也报告相对对照的原正确位点损失率，明确它是否超过 1%；平均提升不能替代损失风险。该实验不自动支持临床、全动物通用或部署安全结论。

先作两物种各一个 core 的工程 smoke，资格通过后完成全部预定区域；smoke 可复用为全批对应 cell，不重复随机实验。所有 cell 完成和输入/坐标资格通过后统一计分，不按早期得分修改面板。无 P3/Tiberius 再训练、无阈值搜索、无多 seed。

资源上限：准备 CPU 16 threads/96 GB；GPU 每个 core 一张 3090、8 CPUs、96 GB、6 h，最多并行 2 cores。输入准备及库下载独立于 GPU 推理。

## Reference 库资格修复

准备12732000识别到 Dfam4 导出忽略缺失 uncurated 分区却返回exit0。原注释保留为不完整库尝试，不用于本批五臂比较。12732197首次修复缺少引擎启动所需库路径挂载而失败，12732214在相同40个core重新运行完整 Dfam3.9 lineage curated+uncurated + RepeatMasker4.2.4；`run_core.py`要求 `complete_library_export=true` 后才允许推理。原始参考基因和区域几何均不改变。

执行依赖为 reference12732214 → 两core smoke12732021 → 全40core12732547 → 全200cell评分12732548。后两级只在前级全部成功后启动；full runner同时检查两份smoke五arm资格。已完成smoke复用。P3导出后释放PyTorch未使用的GPU缓存，再启动同GPU的TensorFlow子进程，模型与阈值不变。
