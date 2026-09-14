# 中文研究决策

来源：ChatGPT 6 Pro，2026-09-14；送审 Git c6781414794c120e41f67d9b43859a4d28453065。[原对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。本文件从完整回复按章节提取；原文见 pro-full-response.md。

# A. 十问决策表

| 问题与直接判断                                                  | 已核实证据、数值及分母                                                                                                                                                                                                         | 解释边界                                                                                                              | 稿件位置                                            | 最小缺口                                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| **1. 基座比较：有价值，但没有完成严格公平的总排名**                            | FINAL **495 行＝9 个 checkpoint/config variants ×5 窗口×11 物种**，每行 1,200 windows。EBAR 每个 recipe 有18 animal、15 plant chromosome/species 行。已有 DNABERT2、GENERanno、HyenaDNA、NTv2 及后续 NTv3 探索。[E02]                           | 495 行不是495次独立重复；9 variants不是9种独立架构。训练呈现量、覆盖bp、历史 Unknown 处理与评估版本不完全匹配。[E03]                                       | 主文作为设计选择背景；全矩阵补充。不能写严格 backbone 因果优势或最终 SOTA 排名 | 只有保留“某基座更优”claim才需2基座×固定单seed42的小型同坐标、同预算比较；本中心论点不依赖它                             |
| **2. 窗口：完整 sweep 放补充；真正的机制对照进正文**                        | 早期 GENERanno 4096 F1=.943030；NT500 4096=.945780、8192=.939567，均来自早期 screen。PAIR8/BLOCK4 是另一实验。[E02、E06]                                                                                                              | 同样1,200窗口不等于相同bp；不能据此断言长上下文本身有害，也不能跨表选最佳值组成一条升级曲线                                                                 | 主文简述窗口选择，并呈现 PAIR8；完整 sweep、edge bins 放补充       | 已有 PAIR8，不建议再泛搜窗口。只有新的明确上下文假设才值得另立受控比较                                        |
| **3. 通用模型/MoE：共享模型已实现，通用验收未完成；未找到执行过的 MoE 结果**           | D 内部六物种：3,000 tiles、**24,541,946 callable bp**，macro F1=.888761。PAIR8 macro=.892187，但 worm DEV=.794154，BLOCK4=.795764，D=.797565；冻结门失败，seed17未释放。[E04、E06]                                                           | 六物种均参与训练。“只有worm低于.8”仅对这个内部表成立；广历史panel另有beetle/plants等低分。**接近.8可发表，不等于冻结PASS**。独立标签完成不等于独立泛化完成。[E15]             | 正文，明确 internal characterization；通用/外部部署声明暂缓     | 合格独立panel；不需要先做MoE。独立panel成功也不能事后改变PAIR8的失败判定                                 |
| **4. 泛化推演：现有部署F1点预测不可靠，但不能推出基因组特征原则上无信息**                | 156个 species–anchor 记录：in-sample R²=.820308，LOSO RMSE=.304043。选中路由特征在22物种中 LOSO contains-best=19/22，leave-clade=13/22；.007083是 oracle shortlist regret。后续 transfer 因5/5 anchor provenance缺失未执行。[E14]                | F1点预测、anchor shortlist、逐bp校准、OOD risk是四个任务。目标注释来源变量不能充当新基因组可用输入                                                   | 补充＋讨论；不能作为已可用 confidence system                 | 真正执行固定信息预算的probe及abstention评估；bp calibration另行验证，不能用路由ECE代替                   |
| **5. hg19→hg38→hs1“后来证实”：全树未找到可核实的已完成证据**                | 找到的是标签来源一致性与方案；未找到坐标级候选、旧预测时间冻结、旧库日期及后续确认链。[E20]                                                                                                                                                                    | “未找到”不是实验失败。现代模型回看旧组装首先是 retrospective recovery，不自动等于预测未来                                                         | 讨论中的独立未来课题；结果暂缓                                 | 历史快照、同源可比区、新增组装序列/映射失败处理、预训练暴露及匹配负例                                           |
| **6. gap：有限候选已结清，未穷尽；当前无可部署修复或已证实下游收益**                  | HN：60,569 known DEV gaps、3,449,084 bp，MSE−8.5905%，AP .303599→.387216；随后 **60,497 阈值、0可行点**。[E08、E09] 旧C：27 cells、243 chains，MW Δ0、MP Δ.000971，但 gain=loss=0。[E10] 新P3 job12652888 FAILED1:0/21m58s，无60-cell结果。[E11] | 信息阳性≠whole-gap动作。旧C科学阴性≠新P3工程失败。material检测仍有研究价值，但Tiberius/调控收益不能用潜力替代                                            | 主文中心                                            | 只有gene-utility claim依赖原U/P/R协议完成；不重开旧C或固定HN阈值搜索                               |
| **7. “superfamily”：实际为粗TE类型分类，尚不足广泛使用**                  | 4,915,200 labelled positions；pretrained TE F1=.904104，main4=.864415，all6=.814575，Unknown recall=.388597；binary-H0 main4=.863267，但 Unknown recall=.042627。[E12]                                                      | SINE/LINE/LTR/DNA不是完整superfamily层级。main4宏平均不含BG/Unknown自身得分，但它们的混淆仍进入主类型FP/FN。adapter6/6只是工程成功，严格S0未完成。[E23]      | 补充；不能作为“通用superfamily工具”的主卖点                    | 正确ontology、全类混淆、reject/risk-coverage、family/copy/homology隔离；删去广泛工具claim则不必补训练 |
| **8. Dfam/contrastive/clustering：未支持GLM优于基本特征或无监督新家族发现** | 同一1,800-fragment/10-cluster panel：ARI A0 .079557、A1 .224190、C0 .142266、C1 .708307；450-fragment holdout F1 .238251/.413748/.338528/.421935。[E13]                                                                     | family labels构造对比目标是监督；ARI/NMI在train+holdout上算；标准化用全pool；fragment split未隔离family/homology。不能混入其他panel的.9208/.7987 | 补充＋限制；通用发现工具暂缓                                  | train-only预处理、严格身份划分、保留C0/C1。公开探索代码可以，不能称已验证的新家族发现工具                          |
| **9. 传统benchmark：有严格局部结果，完整公平矩阵未完成；CPU测试应服务于可用性claim**   | r6.68全组装143,726,002 bp、1,870 contigs、4,972 positive union runs。HiTE/Base/DAPT bp recall=.448982/.003408/.018514，segment recall=.216412/0/.000402。另有后来完成的P3诊断。[E07、E16] CPU只有8,206 bp smoke。[E19]                    | T1 positive-only不能计算全基因组P/F1；旧Base/DAPT/P3不等于当前D。完整workflow应计建库成本                                                 | 已有有限比较正文/补充；全面速度或质量优势待补                         | 当前D＋合格旧HiTE＋第二完整传统workflow；代表性CPU/GPU计时。Omnibenchmark适合薄包装，不必迁移全部历史           |
| **10. 遗漏研究：优先纳入有辨识力的完成项**                                | coverage两seed、token oracle、J0阈值余量、初始化对照；P3 matched-control及FlyBase；C5仅6/4,820 seeds有≥2copies，segmentF1 .189411→.189637；naive ensemble未过结构门；标签/坐标审计及DNA-only入口。[E03、E05、E07、E17–E19、E24]                             | C5失败仅针对冻结whole-seed检索；错误互补不等于MoE已合理；接口可跑不等于下游有益                                                                   | coverage与机制对照正文，其余按贡献放补充或Methods                | 主结果对应预测/版本归档，不需要把每条支线重新训练一遍                                                   |

## 需要特别纠正的实现细节

**第一，`main4_conditional_macro_f1` 不能按名字猜定义。** 源码在全部有效六类输出上计算各类F1，再平均四个主类型；BG/Unknown混淆没有被剔除。真正限制 true label 属于main4的是 `main4_conditional_accuracy`。[E12]

**第二，路由器有两层过度解读风险。** `.6364`属于其他特征组；所选 `baseline_plus_kmer` 的跨clade结果实际为 `.5909`。而“local probe regret”直接取top2中已经观测到的真实F1最大值，是oracle shortlist指标，并非执行过的部署probe。[E14]

**第三，当前共享D沿用 NTv2-500M H0 loader。** 它不是历史NTv2-250M recipe，也不是HN中作为附加输入的NT logit分支。[E21]

**第四，same insertion relation 不等于 whole-gap positive mask。** RepeatMasker以同源匹配为核心；RepeatCraft整理已有重复注释；Earl Grey、HiTE等完整workflow还可以包含de novo发现或目标基因组资源构建，不能统称“都必须先有外部reference library”。两端属于同一历史插入，也不保证中间每个bp都应归为该TE。([repeatmasker.org][1])

---

# E. 完整初稿、已支持 claim 与投稿缺口的最终区分

| 层次             | 当前状态                                                                                                                    |
| -------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **完整初稿**       | 已交付完整英文叙事、Results、Discussion、Methods、Availability、已核查参考文献，以及中文决策、逐panel图计划和最小补证据表；全部可保存修改                               |
| **已支持的claim**  | 内部六物种TE-material检测；固定预算下coverage收益；特定boundary/context/init机制未获支持；HN信息增量与whole-gap动作不可行并存；旧C无新增正确链；辅助任务存在清楚的拒识、身份隔离及泛化限制 |
| **尚未支持的claim** | 外部物种通用模型、MoE、广泛可用superfamily工具、全无监督新家族发现、hg19→hg38→hs1时间外证实、固定HN低风险部署、新P3基因注释收益、独立转录调控效用、全面速度或质量优势                      |
| **投稿证据缺口**     | 主结果预测/版本/完整frontier归档；当代同实例传统workflow对照；保留外部泛化则补独立panel资格与结果；保留高效部署则补CPU/GPU性能；保留gene benefit则完成原U/P/R                  |

**最终建议：收敛成一篇范围清楚、机制证据扎实的评估论文，不再把“通用模型验收完成”当成所有已有科学结果能否成文的唯一开关；同时，也不因论文已经写成，就把尚未完成的验收、工具可用性或下游价值写成已完成。**

[1]: https://www.repeatmasker.org/webrepeatmaskerhelp.html "https://www.repeatmasker.org/webrepeatmaskerhelp.html"
[2]: https://www.nature.com/articles/s41592-024-02523-z?error=cookies_not_supported "https://www.nature.com/articles/s41592-024-02523-z?error=cookies_not_supported"
[3]: https://www.nature.com/articles/s41467-024-49912-8?error=cookies_not_supported "https://www.nature.com/articles/s41467-024-49912-8?error=cookies_not_supported"
[4]: https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281 "https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281"
[5]: https://academic.oup.com/bioinformatics/article/35/6/1051/5079332 "https://academic.oup.com/bioinformatics/article/35/6/1051/5079332"
[6]: https://academic.oup.com/mbe/article/41/4/msae068/7635926 "https://academic.oup.com/mbe/article/41/4/msae068/7635926"
[7]: https://huggingface.co/GenerTeam/GENERanno-eukaryote-0.5b-base "https://huggingface.co/GenerTeam/GENERanno-eukaryote-0.5b-base"
[8]: https://docs.sylabs.io/guides/latest/user-guide/environment_and_metadata.html "https://docs.sylabs.io/guides/latest/user-guide/environment_and_metadata.html"
[9]: https://docs.omnibenchmark.org/latest/tutorial/ "https://docs.omnibenchmark.org/latest/tutorial/"
[10]: https://docs.omnibenchmark.org/latest/reference/ "https://docs.omnibenchmark.org/latest/reference/"
[11]: https://docs.omnibenchmark.org/latest/howto/ "https://docs.omnibenchmark.org/latest/howto/"
