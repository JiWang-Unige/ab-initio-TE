# 第三轮科研审阅：当前原始研究与期刊要求核对

核对日期：2026-09-15。以下为 Codex 实际打开的官方来源与原始研究，不代表这些作者或期刊评价了本项目，也不代表 ChatGPT Pro 已经读取这些页面。投稿适合度是研究判断，不能从 scope 推导接收承诺。

## 会影响本项目定位的原始来源

1. [Tiberius 官方 README](https://github.com/Gaius-Augustus/Tiberius/blob/main/README.md)：当前说明区分使用与不使用 softmask 通道的模型，指出 softmask 模型接收无 mask 输入会发生输入分布不匹配，且不同建库/遮罩方法也会影响性能。对本项目的含义：固定 mammalia_softmasking_v2 的 U/P/R 比较仍是合法的输入干预实验；P 优于 U 不能单独证明比推荐的完整工作流更优。部署级比较需要区分正确配置的 unmasked 模型与 softmask 模型，不能事后替换本次冻结对照。
2. [HiTE，Nature Communications 2024](https://www.nature.com/articles/s41467-024-49912-8)：贡献是针对完整 TE 的边界调整和发现/注释方法。对本项目的含义：若声称改进片段结构，必须比较实际完整结构指标；不能用 bp F1 替代，亦不能以 4 MiB 探针输入的表现代表完整 de novo pipeline。
3. [TEtrimmer，Nature Communications 2025](https://www.nature.com/articles/s41467-025-63889-y.pdf)：自动化 TE 人工整理中的关键步骤，利用系统树和聚类改善序列集合与边界；包含六种生物和三个模拟基因组的评估。这说明“library 质量重要”已是已有认识。新贡献应体现可验证的改进操作、独立发现或明确可量化的新诊断，而非只重复 library 不完善。
4. [TE_Bench，Mobile DNA 2026](https://link.springer.com/article/10.1186/s13100-026-00405-z)（[PubMed](https://pubmed.ncbi.nlm.nih.gov/42458629/)）：2026-07-16 发表的 Snakemake benchmark 工作流，包含模拟与真实序列，并比较 EDTA、RepeatModeler2、Earl Grey。对本项目的含义：Omnibenchmark 接入的工程完成不能单独当作一个新的 TE benchmark 科学贡献；应复用或对照相关评价思路，解释我们的标签版本、L1/L2/L3 与效用分析究竟增加什么。
5. [TEclass2 原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12785036/)：对 TE consensus 序列作十六种 superfamily 分类。对本项目的含义：若以后评价 consensus 分类，应纳入与任务一致的分类工具；本项目的逐 bp LINE/SINE/LTR/DNA 粗分类不能直接与这类 consensus superfamily 指标作排名。
6. [EDTA 官方说明](https://github.com/oushujun/EDTA/blob/master/README.md)：提供全基因组 de novo 注释及基于整理后的 rice library 的评估资源。它可帮助设计来源可追溯的比较，但 library 导出的参考注释依然不是对所有负例的独立生物真值。
7. [Dfam community resource，2021](https://link.springer.com/article/10.1186/s13100-020-00230-y)：Dfam 的 family 表示包括 profile-HMM、MSA 与辅助 consensus；profile 可表达位置特异变异与 indel。因此 multi-prototype 的科学比较不能把传统体系统一抽象为单一 consensus 字符串，亦应考虑任务匹配的 profile-HMM 对照。该事实已由 Codex 打开原论文核实；未据此声称本项目已经完成 HMM 比较。

以上来源供设计和定位参考，不新增实验授权，也不要求把所有工具纳入同一个任务。引用的是论文及官方说明中的特定内容，不能把不同论文的任务、版本与数据直接拼接成排行榜。

## 官方期刊范围及其实际含义

| 期刊 | 已核对的官方要求 | 对当前项目的含义（本项目判断） |
|---|---|---|
| [Mobile DNA](https://link.springer.com/journal/13100/aims-and-scope) | 聚焦 TE 的机制、功能、进化及相关生物计算工具 | 以 TE 领域问题为中心的严谨诊断、注释评估或工具研究具有主题契合性；已有 TE_Bench，仍需说明新增价值 |
| [BMC Bioinformatics](https://link.springer.com/journal/12859/aims-and-scope) | 关注计算方法、模型、工具与生物数据分析，以科学有效性、清楚问题和合适方法为基础，而非预计影响力 | 收敛后的严谨评估/诊断稿有范围契合性，但不能保留不成立的六物种分类、无监督或独立 accuracy 主张 |
| [NAR Genomics and Bioinformatics](https://academic.oup.com/nargab/pages/scope_and_criteria) | 包含 foundation models、benchmark、ontology；要求可重复性、开放实现、可量化价值和合适方法对照 | 独立且可复用的评价面板、受控 library 分析与完整比较可能契合；参数扫描或薄封装本身不足。它与 NAR 是不同期刊 |
| [Bioinformatics](https://academic.oup.com/bioinformatics/pages/scope_guidelines) | 新方法须对照相关先进方法；机器学习须明确独立测试集及同源隔离；一般不接受小幅增益或标准方法的简单套用 | 若作为方法稿，需要一个明确的新方法优势和可信的独立评价；现有小范围已见面板与框架接入不满足这个要求 |
| [PLOS Computational Biology](https://journals.plos.org/ploscompbiol/s/journal-information) | 强调有重要意义的生物或方法洞见、创新、严谨方法和充分证据；不强制每篇都有新湿实验 | 方法改进或普适的评价机制结论需要实证支撑；不能按影响因子把它当作容易的备选 |
| [Genome Biology](https://link.springer.com/journal/13059/aims-and-scope) | 包含基因组学新方法、软件及研究 | 研究范围契合不等于当前结果已达到竞争力；仍需清楚且有影响的新贡献及更广验证 |
| [Genome Research](https://genome.cshlp.org/) | 关注提供新基因组生物学洞见的研究及先进计算/高通量方法 | 更适合由新 biological/resource insight 或扎实方法优势支撑，而不是把许多探索支线累加 |
| [Nature Communications](https://www.nature.com/ncomms/aims) | 期望对领域专家有重要意义的进展 | 需要可复现的核心突破或广泛成立的新洞见；更多模型/窗口运行不自动提高期刊档次 |
| [Nucleic Acids Research](https://academic.oup.com/nar/pages/criteria_scope) | 方法须有高原创性与广泛用途，比较优势应在真实数据、适当的全基因组规模上体现；通常不鼓励缺少重要新结论的程序比较 | 当前不能以万能 TE 注释器、普遍优于库方法或完整 benchmark 已完成来定位 NAR 方法稿 |

当前没有核算或使用影响因子、接收概率。是否需要特定数量的物种、窗口或重复，应由要估计的效应、任务范围和误差结构决定，不能从期刊名反推一个任意实验数量。
