# ChatGPT 6 Pro 第三轮审阅记录

2026-09-15，在内置浏览器的[原研究对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)中完成。送审固定提交为 `5ca4d336407bde995e170aed81c9678acc26764f`。本文件是 Codex 提取的审阅范围与意见记录，**不是完整原文**。页面“复制回复”取得 27,133 字符，已完整读取；完整回复留在上述对话。三个独立附件的本地下载未得到验证，因此不将本地文件称作已下载的 Pro 附件。

## 实际访问范围

Pro 明确报告并在页面展示了：整包 ZIP 下载因网络解析失败，raw 直连也未成功；随后经 **GitHub 连接器**成功读取冻结提交的关键文件。没有把此前 ZIP 或旧稿作为最新证据。

| 研究线 | Pro 报告实际读取的关键内容 |
|---|---|
| 最新状态 | DIRECTIONS-FOLLOWUP、20260914 manuscript README、results-addendum |
| Benchmark | native 与 Omni 协议，final-12708424 的 registry/metrics/execution，real_panel.py |
| Retrieval | improve 协议、training-controls-12708540/metrics.json、improve_retrieval.py |
| 历史 Dfam | 恢复报告，B1/B2/consensus 配置，恢复的 run_experiment.py |
| SF5 | 平衡重放报告、metrics、原 superfamily5_task.py、ontology 审计 |
| 注释变化 | hg19 matched-result、exact-support-12708578.json、library sensitivity |
| Adapter/MoE | pilot 与 sea 适配结果 |
| Tiberius | 最终 RESULTS/result/independent_recheck、冻结协议、base_mask.py 相关实现 |
| Gap/模型比较 | Phase0/1、ensemble、HN 信息与动作、旧 C、window/FINAL/EBAR、内部 CONF、CPU/GPU 报告 |

这是指定研究线的文档、源码和结果审阅，**不等于全仓库每行审计**。Pro 没有连接 HPC、没有完整读取所有大型 JSON locus 列表/历史矩阵、原生 GTF、checkpoint、基因组或预测缓存。它复算了紧凑计数，没有重跑原生独立评分或 bootstrap；仓库中的独立复算结果与 Pro 本轮算术复核应分开。

## Pro 的总体判断

- 当前最强的新证据是：P3 material mask 在固定人类面板上确有下游平均收益；同时低损失联合门未通过。二者必须并列报告。
- D 外部预测、头部 MoE 与海胆适配已经运行，但独立真值、结构质量及原域保留性仍不足，不能称通用模型完成。
- **现稿尚未投稿就绪**。主要缺口是独立评价证据、合适规模的公平 workflow 比较、主张与复现材料闭合；并非必须让每条探索支线都取得阳性。
- 建议主线为：**标签依赖 → 材料与结构分离 → 基因效用与局部损失**。
- Backbone、完整 window sweep、SF5、embedding/retrieval、multi-prototype 主要放补充；linking fixture 不能作为真实效果图。停止扩大 MoE、救固定 Gap 阈值和通过换 checkpoint/core/threshold 挽救原 Tiberius 门。

建议题名：*Sequence-based transposable-element masking: annotation dependence, structural limitations and gene-prediction utility*。

## 对五个问题的关键意见

1. **参考覆盖：**13.88% vs 10.84% 支持描述性差异，孤立片段仅 17.52% vs 16.77%；18,079 对中只有 2,729 个独特 TN，不能把 pair 当独立样本。海胆来源的 assembly/region 上下文也不同。建议同 assembly/engine/halo、只改 library，完整误差转移表、限制背景复用，以及盲法独立核实。若只剩边界效应，就收束为边界敏感性，不给旧 F1 自动纠偏。
2. **无监督 NTv2：**当前缺少真正 encoder adaptation + family-label-free clustering 闭环。历史 B1 是 GENERanno、类别监督设计；raw/panel 尚未闭合。当前 pair-FAR 约 1% 不等于 query-FDR：已接纳 query 中 k-mer 错误 40/175=22.86%，冻结 NTv2 投影错误 43/129=33.33%。Pro 建议可选的有限六臂：原始 k-mer、原始 NTv2、维度/头容量匹配的 k-mer SSL、冻结 NTv2 SSL、仅最后两个 NTv2 blocks 可训练、容量匹配冻结表示头；2000 updates/seed42 是它提出的设计建议，未冻结或执行。若输入按 TE 注释筛选，准确名称应是 TE-enriched、family-label-free adaptation，不能称整个 annotation 流程完全无监督。
3. **分类：**四物种平衡重放修复权重和解释，没有完成六物种新 ontology 分类器。窗口/bp 总量不能替代独立 locus、copy、family、空间块和每类支持。人/鼠可作新设计锚点，但库不是独立真值；新旧 ontology 分母不同，不能直接相减 F1 作为模型改进。保留分类工具主张才需要相应新训练闭环。
4. **Gap/下游：**信息互补、信息评分改善和可行动作不同；现有结构路线失败不意味着所有关联方案都不可能。P3 的总体效用阳性可进入正文，原接受门仍失败；P−R 区间跨零，既无优越也无等效结论。精确 CDS 不再匹配不等于生物学上基因被删除。现有 gains/losses 可做机制解释；跨物种效用应另立新协议。
5. **Benchmark：**12 格矩阵、8 native + 3 D 数值、1 timeout 与 Omni 收集/重放是真实工程成果。Omni 模块读的是已有 Slurm native 输出，不是在 Omni 内重跑全部 native 软件。4 MiB 不是全基因组 de novo benchmark；没有独立真值不能报 absolute precision/F1。Pro 建议最小新科学比较可先选两个资格合格、TE 组成不同的 genome，至少一个不属于 D 任务训练物种，使用拟发布模型与现有三 native 流程，补独立评价层及完整成本；两物种不是期刊硬门槛。

Pro 同时提醒：Dfam 已提供 profile-HMM 和 consensus，不能把传统方法简化为每 family 一个字符串。保留 multi-reference 优势主张时，应考虑同 TRAIN copy 构建的 profile-HMM 等任务匹配对照。TE_Bench 已提供模拟/真实 TE workflow benchmark，Omni 编排本身不足以承担主要创新。

## 建议的五个 Results 标题

1. Sequence models recover TE-associated material, with recipe- and domain-dependent limitations.
2. Reference coverage and boundary revisions affect measured errors without eliminating model false negatives.
3. Material-score gains do not consistently translate into structural recovery or cross-domain retention.
4. Additional gap information does not yield a feasible low-risk whole-gap policy.
5. A learned TE mask improves gene prediction while failing a prespecified locus-retention safeguard.

特别区分 Shared D（NTv2-500M）、P3/Tiberius（GENERanno/P3-R1）、hg19 独立原生 NTv2 任务、冻结 NTv2 retrieval。不能将四条线最好的数字拼成同一个模型的完整能力。

## Pro 英文结论草稿（原文摘录）

> Our results support sequence-based prediction of TE-associated material as a useful input to genome annotation, while separating this capability from biological insertion reconstruction and low-risk deployment. Reference-annotation revisions affected the interpretation of apparent errors, particularly near existing TE boundaries, but additional comparator coverage also exposed substantial model false negatives. In a fixed human panel comprising 726 gene loci across 20 genomic cores, the P3-derived mask increased pooled locus F1 from 0.6363 to 0.6994 relative to unmasked input, with a paired-core 95% bootstrap interval of 0.0365–0.1068 for the difference. This overall improvement coexisted with the loss of 16 of 510 previously correct loci, exceeding the prespecified 1% loss limit; the joint acceptance criterion therefore remained unmet. The comparison with the UCSC repeat mask established neither superiority nor equivalence. Together, these findings show why material agreement, annotation provenance, structural recovery and downstream gains and losses should be evaluated as distinct outcomes. They do not establish a universal TE annotator, label-free family discovery or completed insertion recovery. Broader claims require independently qualified evaluation data and workflow-level comparisons at an appropriate genomic scale.

## Pro 的投稿判断

- 收窄现有证据并完成写作、复现修订后：**Mobile DNA**；当前/最小证据包后：**BMC Bioinformatics**。
- 最小包后且贡献足够：**Bioinformatics**（新方法价值、独立测试、同源隔离），或 **PLOS Computational Biology**（显著的一般性生物/方法洞见）。不是标准 GLM 应用或多个负结果集合就自动适合。
- **Genome Research、Genome Biology、Nature Communications** 需要更强的核心生物发现、权威资源或实质方法优势。当前 **NAR** 不优先。
- 不把额外消融数量、训练容量或固定 panel 扩大等同于期刊定位提升；不作影响因子或接收概率保证。

这是 Pro 的科研与投稿建议，不是编辑意见、执行授权或新冻结协议。Codex 对官方来源的独立核对见 [source-notes.md](source-notes.md)，本轮整合后的优先级见 [README](README.md)。
