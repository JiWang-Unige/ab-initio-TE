# 第三轮最终科研梳理与投稿定位

2026-09-15，送审快照 `5ca4d336407bde995e170aed81c9678acc26764f`。**ChatGPT 6 Pro 已在内置浏览器通过 GitHub 连接器读取关键协议、源码与结果并完成审阅。当前有可写成正文的结果，但“所有论文实验已完成”不成立，现稿尚未投稿就绪。**

Pro 与 Codex 的共同建议是将主线收敛为：**参考注释如何影响模型评价 → TE 材料识别为何不同于结构恢复 → 模型 mask 的基因注释收益与局部损失。** 无须让 MoE、聚类、分类和 linking 全部取得阳性，才能完成这篇论文。

## 五个问题的结论

| 问题 | 当前结论 | 下一步取舍 |
|---|---|---|
| 覆盖缺口能否形成好结论 | 能形成参考依赖的诊断结论；严格匹配 FP/TN 新注释支持为 13.88%/10.84%，差异主要在边界。海胆新比较注释仍暴露 D 漏检 | 同 assembly/engine/context 的新旧库比较＋盲法独立支持。不能称旧 FP 普遍被证实或据此修正 F1 |
| 可训练 NTv2 无监督聚类 | **尚未完成**。当前 NTv2 只训练监督投影；历史 trainable 是 GENERanno 类别监督。当前强 6-mer 对照优于冻结 NTv2 投影 | 可选有限 encoder 适配对照；保留强 k-mer、容量控制、同源隔离。它不是当前主稿必做项 |
| 分类设计是否修复、1200 是否足够 | **部分修复**：四物种 480 窗口重放，没有六物种新训练闭环；旧 VAL 评分还漏线虫。main4 不是具体 superfamily | 若保留工具主张，修复 ontology、验证选择与完整独立评价；人/鼠可作锚点。否则放补充，不以窗口总数证明代表性 |
| Gap/下游是否成功 | 已评估 Gap 路线未得到满足联合约束的结构改善；真实 linking 尚未检验。P3 的人类平均效用阳性，但低损失门失败；没有优于 R 的证据 | 主文并列收益与损失；先解释已有相异 loci。跨物种效用是新研究，不能用于挽救原冻结门 |
| Benchmark 是否完成 | 三物种有限区域矩阵与 Omni 重放完成；完整公平 accuracy benchmark **未完成** | 先补合格独立评价与适合全基因组 de novo 的比较，再扩工具。不能用 coverage 排准确率 |

当前 native benchmark 软件为 RepeatMasker 4.2.4 + Dfam 3.9、HiTE 3.3.3、RepeatModeler2 2.0.9→RepeatMasker 4.2.4，另有冻结 D 缓存。物种是鸭嘴兽、海胆、**C. briggsae**，各 4×1 MiB。12 格中 11 格有读数，鸭嘴兽 RM2 原预算 TIMEOUT 保留空指标。本批没有 EDTA、EarlGrey、REPET、RepeatCraft 或 TEtrimmer。

## 最值得保留的实际阳性

人 hg38 chr16/18，20 个 core、726 个 gene loci、固定 Tiberius softmask 模型：P3 mask 将 locus-F1 从 **0.6363 提升至 0.6994**；P−U 的 95% CI **[0.0365, 0.1068]**。但原 U 正确 loci 损失 **16/510=3.14%**，超过预设 1%，原门继续为失败。R mask 为 0.6954；P−R 的区间 **[−0.0026, 0.0134]**，不能写优越或等效。

本轮追加的描述性集合分析发现：P/R 各新增 55 个正确 loci，其中 53 个相同；P 损失的 16 个 U-correct loci 全部也被 R 损失，R 另损失 1 个。这个重叠结果有助于选择后续机制核实对象，但不改变原判定。原精确 CDS 匹配终点下的“损失”不等于基因在生物学上被删除。

R 是 UCSC all-repeats mask，并非本批新运行的 native RM 产物；P3、共享 D、hg19 NTv2、retrieval 表示属于不同模型系列，不能拼成同一个万能模型的成绩。Tiberius 当前官方默认配置还有 unmasked/softmask checkpoint 的区别；相对固定 softmask 模型的 U 收益不能直接写成优于正确配置的完整工作流。

## 有限推进顺序

1. **先闭合主稿与复现材料：**将历史草稿中的“等待结果”替换为最新实测，锁定每个结果对应的模型、标签和评估版本；列明可复现资产和发布范围。此轮完成审阅记录，完整论文重写与发布包整理仍是后续交付。
2. **优先参考控制与公平 benchmark：**同 assembly/engine 的 library 控制、独立核实的误差分层、合适规模 native 比较与完整成本。这两项最能改变现有主张可信度。
3. **有条件补下游、分类或表示支线：**跨物种应用主张才依赖新外部效用；独立分类功能才依赖新 ontology 训练；表示学习主贡献才依赖真正 family-label-free NTv2。具体方案见下方链接。

不扩大 MoE、不重搜冻结 Gap 阈值、不为了让原 Tiberius 门通过更换输入条件、不新增多 seed。Pro 提出的候选臂数、2000 updates 或两个 genome 都是设计建议，不是期刊硬门槛或已批准执行的协议。

## 投稿定位

以下是根据证据成熟度和官方 scope 的研究判断，不是接收承诺：

| 当前/未来条件 | 较合理的定位 |
|---|---|
| 收窄当前主张，完成写作与可复核修订 | **Mobile DNA、BMC Bioinformatics** 更贴近现有研究形态；当前散落旧稿仍不宜直接投稿 |
| 完成独立评价和公平比较，形成可复用的方法/评价贡献 | **NAR Genomics and Bioinformatics** 值得考虑（Codex 补充）；有明确方法新意可争取 **Bioinformatics**；有充分一般性生物/方法洞见可考虑 **PLOS Computational Biology** |
| 出现强独立生物发现、权威资源或稳定改变注释实践的新方法 | 再考虑 **Genome Research、Genome Biology、Nature Communications、NAR**。当前不能称已达到此定位 |

更高定位依赖核心贡献，而非消融数量。TE_Bench、TEtrimmer、Dfam profile-HMM 和 Tiberius 既有研究也意味着：“library 不完善”“repeat masking 有用”“把工具装入 workflow”本身不够构成新颖性。需要说明本研究增加了什么可验证的诊断、能力或用途。各官方来源和具体边界见 [source-notes](source-notes.md)。

## 阅读与证据入口

- [完整事实核对、数字与源文件](verified-status.md)
- [Pro 审阅范围与意见记录](pro-review-record.md)；[内置浏览器中的完整 Pro 回复](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)
- [有限补实验方案](finite-experiment-options.md)
- [官方期刊范围及相关原始研究](source-notes.md)
- [Tiberius 新增位点重叠分解](tiberius-locus-overlap.json)与[复现脚本](../../../scripts/manuscript/summarize_tiberius_locus_overlap_20260915.py)

本轮没有启动新训练、推理、benchmark 作业或后台监控。旧协议、sealed 边界、原成功/失败结论均保留。Pro 完整回复已在浏览器读取；本地审阅记录是提取与整合稿，未冒称成功下载三个独立附件。
