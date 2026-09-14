## 结论先行

**现有证据足以形成一篇完整的“TE material 检测与可操作注释之间的证据边界”研究初稿，但不足以宣布已经完成可广泛部署的物种通用 TE 注释器。**

最可信的中心论点是：

> **Sequence-only genomic models learn TE-associated material, but material agreement, comparator-run topology, biological insertion identity, and low-risk annotation utility require separate validation.**

这不是把负结果包装成“万能模型”，而是保留真正成立的阳性——共享模型的内部材料检测、增加训练坐标覆盖的收益、HN 的信息增量——同时说明这些收益为什么尚未转化为可靠的结构恢复、低风险 gap 动作或下游效用。

### 可保存文件

[完整交付：中文决策＋完整英文稿＋证据账本](sandbox:/mnt/data/te_manuscript_review/ab_initio_TE_research_review_and_manuscript_20260914.md)

[英文论文初稿＋逐项证据附录](sandbox:/mnt/data/te_manuscript_review/manuscript_en_with_evidence.md) ｜ [中文研究决策报告](sandbox:/mnt/data/te_manuscript_review/review_zh.md) ｜ [完整审阅包：含核算脚本、JSON、索引与可编辑数据表](sandbox:/mnt/data/ab_initio_TE_review_bundle_20260914.zip)

### 核查范围

我已实际解压 ZIP，确认 **2,882 个文件**，建立逐文件散列索引，读取关键源码、协议、TSV 和 JSON，并重算可用的混淆计数、宏平均、HN 误差分解及旧 C 的 F1 差值。ZIP 注释与提交 `c6781414794c120e41f67d9b43859a4d28453065` 一致，但这不等于独立验证了 Git 历史或远端状态。

没有访问 HPC、原始数据、checkpoint 或完整预测缓存，也没有运行新实验。**12652888 的失败状态来自附件中 2026-09-14 的归档核查记录，不是本轮重新连接 Slurm 的结果。**该记录明确区分了新 P3 smoke 的工程失败与旧 C 的科学阴性。

下文 **E01–E25** 是本轮建立的本地证据编号；完整账本列出附件相对路径、字段、评价对象和 SHA-256。正文后附主要数字定位表。外部文献另用原始论文或官方文档支持。

---

# A. 十问决策表

| 问题与直接判断                                                  | 已核实证据、数值及分母                                                                                                                                                                                                         | 解释边界                                                                                                              | 稿件位置                                            | 最小缺口                                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| **1. 基座比较：有价值，但没有完成严格公平的总排名**                            | FINAL **495 行＝9 个 checkpoint/config variants ×5 窗口×11 物种**，每行 1,200 windows。EBAR 每个 recipe 有18 animal、15 plant chromosome/species 行。已有 DNABERT2、GENERanno、HyenaDNA、NTv2 及后续 NTv3 探索。[E02]                           | 495 行不是495次独立重复；9 variants不是9种独立架构。训练呈现量、覆盖bp、历史 Unknown 处理与评估版本不完全匹配。[E03]                                       | 主文作为设计选择背景；全矩阵补充。不能写严格 backbone 因果优势或最终 SOTA 排名 | 只有保留“某基座更优”claim才需2基座×2seed的小型同坐标、同预算比较；本中心论点不依赖它                             |
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

# B. 中心论点与完整英文初稿

以下稿件将**共享NTv2材料检测、人类P3结构机制、gap信息与效用**作为不同实验系列；不把它们写成一个已经端到端验证的统一模型。英文文件包含完整证据附录。

## Title

**From transposable-element material detection to actionable annotation: a controlled evaluation of genomic language models**

**Authors and affiliations:** [TO COMPLETE]

## Abstract

Genomic language models can identify sequence patterns associated with transposable elements (TEs), but agreement with a base-pair annotation mask does not establish recovery of biological insertions or safe downstream masking. We evaluated these distinctions using a shared multi-species material detector and separate, controlled human annotation experiments. On an internal development panel comprising six training species and 24,541,946 callable bases, the shared model achieved a species-macro base-pair F1 of 0.8888, compared with 0.4459 for comparator-run matching and 0.2044 for IoU-qualified joint-boundary matching. Expanding the independent worm training-coordinate pool improved development performance in two seeds under a matched update budget. In contrast, enabling cross-half attention did not satisfy the frozen context-improvement criterion; worm development F1 remained 0.7942. In a separate gap experiment, adding nucleotide-transformer logits and seam features reduced negative-fraction mean squared error by 8.5905% and increased action average precision from 0.3036 to 0.3872. Nevertheless, none of 60,497 tied-score thresholds satisfied even optimistic necessary conditions for low-risk whole-gap filling. Truth-assisted gap-mask additions also failed to recover additional correct coding-sequence chains in a completed nine-core gene-prediction experiment. These results support an experimentally useful TE-material detector and identify specific coverage and information effects, while separating them from unestablished claims of universal generalization, biological insertion reconstruction, and downstream benefit. Independent-panel qualification, matched contemporary tool comparisons, and release-level reproducibility remain necessary before broader deployment claims. [E04–E11, E15]

## Introduction

Transposable-element annotation involves several related but non-equivalent questions. A base may contain recognizable TE-associated sequence even when the boundaries, ancestry, and integrity of the original insertion cannot be reconstructed. Conversely, two annotated fragments can belong to the same historical insertion while intervening sequence is not wholly attributable to that element. RepeatMasker explicitly accommodates fragmented and nested matches, while RepeatCraft and Earl Grey provide procedures for organizing or defragmenting repeat annotations. These procedures motivate distinguishing material detection from insertion reconstruction rather than treating every discontinuity as an error to fill. [R2–R4] ([repeatmasker.org][1])

Genomic foundation models offer a different source of evidence: representations learned from DNA sequence. The Nucleotide Transformer study establishes a general representation-learning framework for genomic prediction, and the GENERanno project provides an eukaryotic checkpoint used in a separate series of experiments here. Neither a foundation-model designation nor sequence-only inference removes dependence on training labels, pretraining exposure, or task-specific evaluation. [R1, R5] ([Nature][2])

We therefore distinguish three targets. **L1** is a binary mask of TE-associated material relative to a specified computational comparator. **L2** is the topology of contiguous comparator runs, including interval agreement and joint boundary agreement. **L3** is biological insertion identity, which requires evidence beyond adjacency or mask continuity. We additionally distinguish a predictive score from an action: filling a gap changes an annotation and can mask non-TE sequence even when the score contains useful information.

This study asks which of these claims are supported by the available experiments. A shared-model series tests internal multi-species material detection, coordinate coverage, and information exchange between adjacent sequence halves. A separate human series tests boundary supervision, cross-species structural transfer, gap-risk prediction, and gene-prediction utility. Historical backbone, typing, representation, and routing experiments provide secondary evidence but are not assembled into a hypothetical universal model. Our central contribution is an evidence-resolved assessment of the transition from material prediction to actionable annotation, including informative negative results and explicit limits to their interpretation.

## Results

### 1. A shared model detects TE-associated material within a six-species panel, but does not establish universal annotation

The shared D model was evaluated on 500 development tiles from each of six species represented in training. Across 3,000 tiles, the evaluation contained 24,541,946 callable bases, including 7,452,597 comparator-positive bases. Species-macro base-pair F1 was 0.888761. The corresponding macro interval F1 at intersection-over-union (IoU) 0.8 was 0.445884, and IoU-qualified joint-boundary F1 at 5 bp was 0.204361. These metrics answer different questions and should not be interpreted as interchangeable estimates of accuracy. [E04]

| Species      | Callable bp | Positive bp | Base-pair F1 | Run F1, IoU ≥0.8 | Joint-boundary F1, 5 bp |
| ------------ | ----------: | ----------: | -----------: | ---------------: | ----------------------: |
| *C. elegans* |   4,076,828 |     389,795 |     0.797565 |         0.304933 |                0.136771 |
| Chicken      |   4,094,383 |     157,905 |     0.831720 |         0.378378 |                0.150579 |
| Human        |   4,092,984 |   1,921,941 |     0.940310 |         0.544222 |                0.288808 |
| Mouse        |   4,090,361 |   1,598,850 |     0.941998 |         0.566082 |                0.297714 |
| Pig          |   4,095,493 |   1,140,557 |     0.893138 |         0.500507 |                0.215211 |
| Zebrafish    |   4,091,897 |   2,243,549 |     0.927836 |         0.381181 |                0.137085 |

**Table 1.** Internal DEV results for D, seed 42. Counts and F1 were independently checked from the archived confusion counts. Structural matching is performed on tile-level comparator runs, not independently verified biological insertions. All six species contribute to training. Source: E04, `per_species` and `summary`.

Only worm fell below 0.8 in this particular table. This observation does not establish that worm is the only difficult species in general: historical panels include different species, plants, labels, and model recipes. Nor does a near-threshold result change the frozen acceptance decision. The wider L1 programme remained incomplete, and no executed mixture-of-experts (MoE) result was found in the submitted tree. [E02, E06, E15, E20]

### 2. Coordinate coverage provides a replicated benefit, whereas additional cross-half attention does not pass its matched test

The upstream coverage comparison changed the worm training-coordinate pool from 1,500 to 3,000 tiles while retaining the shared-model objective, sampling balance, and 4,000-update budget. Other species retained 1,500 tiles each. Worm SCREEN comprised 512 separated tiles with 4,163,080 callable bases; the reused worm DEV panel comprised 500 tiles with 4,076,828 callable bases. SCREEN contained new coordinates on training chromosomes and was not an unseen-species test. [E05, E21]

| Seed |    SCREEN F1, L → D |       DEV F1, L → D |
| ---- | ------------------: | ------------------: |
| 42   | 0.789994 → 0.802736 | 0.783315 → 0.797565 |
| 17   | 0.794581 → 0.807310 | 0.788782 → 0.807216 |

**Table 2.** Matched coverage comparison. Average precision also improved in both seeds on both panels. These paired directions support a coverage effect at the tested budget; they do not establish stable satisfaction of all release criteria. The existing closure explicitly records that absolute usability remained unstable. [E05]

An archived label-oracle diagnostic obtained worm DEV F1 of 0.994498 under the implemented token-constant output constraint. This is not a learned-model result, but it shows that the six-base output grid alone cannot account for an observed ceiling near 0.8. It does not exclude limitations of input tokenization, optimization, or available context. [E05]

PAIR8 subsequently tested a narrower hypothesis: whether the two original 4,096-bp halves benefit from exchanging information. PAIR8 and BLOCK4 used the same packed encodings, output mapping, supervision, and update budget; only attention connectivity differed. PAIR8 increased worm SCREEN F1 from 0.809500 to 0.812998 but decreased worm DEV F1 from 0.795764 to 0.794154. The DEV difference was −0.001610, and the SCREEN difference of 0.003497 was smaller than the registered 0.005 minimum. PAIR8 macro DEV F1 was 0.892187, but this aggregate did not rescue the failed worm criteria. Seed 17 was not released. [E06]

A separate score diagnostic constrained precision and recall to at least 0.75. For seed-42 worm DEV, the best scalar-threshold oracle F1 was 0.799613, only 0.002048 above the deployed result. Thus, threshold adjustment alone could not meet the 0.8 target on that panel. Replacing the H0 encoder with the native pretrained encoder while using the same fresh classification head also failed its matched test: P0R DEV F1 was 0.791441 versus 0.803254 for H0R. These findings further limit threshold-only and initialization-only explanations; they do not prove that all calibration or pretraining interventions are ineffective. [E24]

These experiments identify coordinate diversity as useful under the tested conditions while providing no accepted benefit for this specific cross-half attention intervention. They do not rule out all longer-context architectures and do not justify automatically adding experts or model capacity.

### 3. Boundary alignment does not explain the human structural improvement, and transfer remains endpoint-dependent

A separate GENERanno-derived human P3 series evaluated whether aligned edge supervision improved structural recovery. The matched P3-R2 experiment compared an aligned boundary target with a jointly permuted boundary target that retained target mass and distribution within each window. Evaluation used the first 1,200 windows of length 8,192 bp on human chromosome 17, containing 14,253 comparator runs. [E07]

Aligned supervision achieved interval F1 of 0.407518, whereas the matched permutation control achieved 0.447522. Joint-boundary F1 at 5 bp was 0.215538 versus 0.250507, respectively. Base-pair F1 was similar, at 0.931778 and 0.932072. Thus, improvements relative to the earlier P3 recipe cannot be attributed specifically to correct boundary alignment in this experiment. This is a mechanism test, not evidence that arbitrary boundary targets are universally preferable. [E07]

Frozen P3-R1 transfer further separated material agreement from topology. On the mouse chromosome-1 diagnostic, base-pair F1 was 0.902004 but interval F1 was 0.096592. On the exact FlyBase r6.68 positive-only panel, P3-R1 interval recall at IoU 0.8 was 0.078037, with 51.557723 predicted fragments overlapping each truth run on average. This later P3 diagnostic was completed and must not be omitted merely because it was absent from the earlier three-cell benchmark. The FlyBase truth set comprised 4,972 flattened positive runs; it did not certify negative genomic sequence and therefore cannot support genome-wide precision or F1. [E07, E16]

The original same-assembly benchmark included HiTE, historical Base-CE, and DAPT-CE. Their positive-base recalls were 0.448982, 0.003408, and 0.018514; interval recalls were 0.216412, 0, and 0.000402. These are results for those particular frozen models and workflows, not a ranking of current shared D against traditional annotation. HiTE is a full TE-detection and annotation approach with its own discovery and boundary procedures, so any contemporary comparison must record the workflow and library resources rather than compare only model labels. [E16; R6] ([Nature][3])

### 4. Additional gap information improves risk prediction without enabling a low-risk filling policy

The HN-O experiment tested whether nucleotide-transformer logits and seam features add information about gaps left by the frozen human prediction. It used 90,081 training candidates and 60,574 DEV candidates, of which 60,569 were fully known under the computational comparator. Known DEV gaps contained 3,449,084 bases. The head predicted the negative-base fraction within a gap; lower predicted risk favoured filling. HN-O was compared with an otherwise matched H0-O control, with three training seeds. [E08]

HN-O reduced length-weighted negative-fraction MSE from 0.06148917 to 0.05620693, a relative reduction of 8.5905%. Action average precision increased from 0.30359897 to 0.38721622, an absolute increase of 0.08361725. The direction of the information improvement was consistent across the three seeds. Because nucleotide-transformer logits and seam features were introduced together, the effect cannot be assigned to the transformer alone. [E08]

Fraction MSE and literal base-level Brier error must also be distinguished. For gap length \(L_g\), observed negative fraction \(r_g\), and a constant gap prediction \(s_g\),

$$
\mathrm{Brier}
=
\frac{\sum_g L_g(s_g-r_g)^2}{\sum_g L_g}
+
\frac{\sum_g L_g r_g(1-r_g)}{\sum_g L_g}.
$$

The second term is irreducible under a constant within-gap score. Accordingly, literal Brier error decreased from 0.10562713 to 0.10034488, or 5.0008%, not 8.5905%. Neither improvement establishes safe masking. [E08]

A subsequent fixed-score feasibility analysis enumerated 60,497 distinct tied-score thresholds, plus abstention. None met the optimistic necessary conditions for whole-gap action. These required at least 1,000 selected candidates, recovery of at least 10% of known positive gap bases and 5% of the designated long-gap positive bases, and strict negative/unknown masking budgets. The optimistic genomic span was 47,185,920 bp, allowing at most 471.8592 known negative bases under the 10-bp-per-Mb budget. [E09]

The largest risk-admissible action selected 822 gaps, recovering 4,449 of 461,733 known positive bases while adding 441 known negative bases. The first threshold satisfying the utility requirements selected 8,414 gaps and recovered 46,251 positive bases, but added 24,747 negative bases—approximately 52.45 times the optimistic negative budget. Since even these necessary conditions failed, no deployment calibration or gene-safety evaluation could rescue this fixed ordering within the tested monotone-threshold policy family. This is a bounded no-go result, not proof that all gap models or all partial-gap actions are impossible. [E09]

### 5. Completed gene-utility results do not establish benefit, and a separate base-mask experiment remains incomplete

The completed C experiment evaluated nine human chromosome-13 cores under three masks, yielding 27 valid cells. The reference contained 243 distinct complete coding-sequence (CDS) chains represented by 330 source rows. M0 was the existing P3 mask—not an unmasked genome. MW added comparator-known all-positive whole gaps; MP added comparator-positive bases within candidate gaps. Both additions were truth-assisted diagnostic interventions rather than deployable predictions. [E10]

M0 and MW each yielded 54 true positives, 37 false positives, and 189 false negatives, corresponding to micro chain F1 of 0.323353. MP yielded 54 true positives, 36 false positives, and 189 false negatives, with F1 of 0.324324. Its increase of 0.000971 reflected a net change in false positives, not recovery of a new correct chain. Neither addition gained or lost a correct reference chain, so the registered gain requirement failed. The result is scientifically negative for these interventions on these cores. [E10]

A distinct P3 base-mask experiment was designed to compare unmasked U, P3-masked P, and reference-repeat-masked R across 20 larger cores, for 60 planned cells and a different gene-locus endpoint. The archived 14 September status records smoke job 12652888 as FAILED, exit 1:0, after 21 min 58 s, with `KeyError: BASE_MASK_OBSERVATION`. There are no complete 60-cell utility results. This engineering failure neither establishes nor refutes the benefit of P3 masking relative to unmasked input. **[NOT YET ESTABLISHED: P3 base-mask benefit for gene annotation.]** No completed independent transcription-regulation utility experiment was found. [E11, E20]

### 6. Auxiliary studies constrain broader annotation claims

Historical backbone/window screens contain substantial exploratory evidence, including 495 rows spanning nine checkpoint/configuration variants, five windows, and eleven species. Each row used 1,200 windows, not an independent training seed. Unequal sequence exposure, coordinate coverage, and historical label/evaluator differences prevent a clean causal ranking of architectures or context lengths. These results are retained as recipe-development evidence in the Supplementary Results. [E02, E03]

Direct classification used BG, SINE, LINE, LTR, DNA, and Unknown. These are coarse output types, not a comprehensive biological superfamily taxonomy. On 4,915,200 labelled positions, the pretrained initialization achieved TE-detection F1 of 0.904104 and four-type macro F1 of 0.864415, but Unknown recall was 0.388597. Binary-H0 initialization retained four-type macro F1 of 0.863267 while Unknown recall fell to 0.042627. The field named `main4_conditional_macro_f1` averages globally computed class F1 values for the four selected types: background/rejection confusions still contribute false positives and false negatives, although BG and Unknown do not receive their own terms in that average. A broadly usable superfamily annotator is therefore not established. [E12, E23]

The Dfam-consensus representation panel contained 1,800 fragments and ten clusters. ARI was 0.079557 for raw GLM embeddings, 0.224190 after family-supervised contrastive learning, 0.142266 for basic sequence features, and 0.708307 for contrastively transformed basic features. These combined train-plus-holdout ARIs must not be mixed with results from other panels. Holdout macro F1 on 450 fragments was 0.238251, 0.413748, 0.338528, and 0.421935, respectively. The contrastive objective used family labels, preprocessing included the pooled feature set, and the split did not establish unseen-family or homology-isolated generalization. Thus, neither wholly unsupervised discovery nor superiority over basic features is supported. [E13, E23]

Finally, genomic-feature performance regression achieved in-sample R² of 0.820308 but leave-species-out RMSE of 0.304043 over 156 species–anchor records. A separate conservative router's selected feature set included the best observed anchor in 19/22 leave-species-out cases, but only 13/22 leave-clade-out cases. Its reported mean shortlist regret of 0.007083 used the best observed F1 within the shortlist and is an oracle shortlist statistic, not a validated label-free local-probe outcome. These experiments do not establish deployable F1 prediction, base-level calibration, or out-of-distribution risk control. [E14]

## Discussion

The strongest supported conclusion is that TE-associated material prediction, structural agreement, and safe annotation action require separate evidence. This does not make base-level detection uninformative. It specifies its meaning: agreement with a computationally defined material mask on the evaluated domain. The shared model's material scores and the replicated coordinate-coverage effect are positive results within that scope. However, calling every predicted run a TE insertion would overstate the available biological evidence.

The experiments also clarify why apparently promising interventions did not yield the intended downstream advance. Matched boundary controls did not support the proposed alignment mechanism. Additional gap features improved prediction of composition but could not separate enough useful whole-gap actions from harmful ones at the frozen risk budgets. Even truth-assisted additions failed to produce new correct CDS chains in the completed C experiment. These are different failure modes; none should be used to substitute for the unfinished unmasked-versus-P3 gene-utility comparison.

Nor should traditional annotation be described as uniformly dependent on an externally supplied reference library. RepeatMasker is a homology-based annotation component, whereas workflows such as Earl Grey and HiTE can include de novo discovery and construction of sequence resources from the target genome. Library availability, construction cost, taxonomy, and fragment handling must therefore be specified at the workflow level. Sequence-only GLM inference avoids a target-time library search in the implemented entry point, but does not imply training independence from RepeatMasker/Dfam labels or freedom from pretraining exposure. [R2, R4, R6] ([repeatmasker.org][1])

Several limitations restrict the manuscript. The principal shared-model panel contains training species and reused development coordinates. Computational labels can be incomplete or taxonomically uneven. The prepared independent candidate panel has not supplied completed independent model results, and its label coverage and exposure require qualification. Historical results were produced under multiple implementation versions, and fixes to coordinate handling, Unknown shielding, or tied-score evaluation do not automatically update archived metrics. Several main results are available as compact summaries but not as the underlying predictions needed to reproduce every frontier or interval. No new statistical significance is inferred from the number of bases, tiles, or workflow cells. [E03, E15]

Within these limits, the work argues against indiscriminate expansion of model complexity. The current context test does not justify MoE, and error diversity between backbones is not sufficient evidence for a useful ensemble. Future work should first establish qualified independent evaluation, matched contemporary workflow comparisons, and claim-specific utility. New biological insertion or historical annotation-recovery studies would require their own truth and exposure designs; they are not results of the present study. **[NOT YET ESTABLISHED: unseen-species generalization, biological insertion recovery, historical prediction followed by later confirmation, and independent regulatory utility.]** [E15, E18, E20]

## Methods

### Evidence provenance and experimental separation

The reviewed ZIP contains 2,882 tracked files and identifies the submitted commit in its archive comment. We inspected source code, protocols, archived tables, and compact JSON results and independently recalculated available confusion-derived metrics and aggregate differences. The snapshot excludes raw genomes, checkpoints, full run outputs, and caches. No new training, inference, HPC query, or raw sealed-panel evaluation was performed. A recorded remote job state is cited as an archived check, not a newly observed scheduler state. [E01, E11]

The shared NTv2 series, human GENERanno/P3 series, historical Base/DAPT benchmark, and auxiliary classification/representation studies retain their own input, split, and evaluation contracts. Cross-table comparisons are descriptive unless the experiments explicitly match the relevant factors. **[TO COMPLETE: release manifests linking every main result to immutable input, checkpoint, calibration, prediction, and evaluator hashes.]**

### Targets, labels, and coordinates

L1 denotes TE-associated base-pair material relative to the stated comparator, rather than experimentally verified TE origin at every base. In the current shared series, labels retain positive/unknown/negative priority. `1` supplies positive mass; `0` and hard-negative `H` supply negative mass; `?` is excluded from supervised mass. The implemented priority may retain positive labels at ambiguous sequence positions, so callable status must be taken from the label contract rather than inferred solely from the DNA alphabet. [E21]

The internal species use hs1, mm39, galGal6, danRer11, ce11, and susScr11 assemblies. The separate human gap/utility series uses its own hg38 chromosome contracts. Prepared external candidates include platypus, sea urchin, and *C. briggsae*, but successful label export is not an independent model evaluation. Actual RepeatMasker/FamDB/Dfam versions and curation coverage are recorded in the panel metadata. **[TO COMPLETE: qualified negative-label scope, pretraining exposure statement, and copy/family/homology isolation appropriate to each intended claim.]** [E15]

### Shared material model and matched interventions

The upstream trainer calls the shared NTv2 task without changing its base-model loader; the implementation points to the NTv2-500M H0 checkpoint. This is distinct from historical NTv2-250M comparisons and the separate NT-logit gap input. Each 8,192-bp tile is represented by two independently encoded 4,096-bp halves. Six-mer tokens retain positive and negative base counts; remaining tail bases have their own tokens. Predictions are projected back without changing genomic coordinates. [E21]

For half \(h\), the weighted binary cross-entropy is

$$
\ell_h=
\frac{
\sum_j\left\{3P_j[-\log p_j]+N_j[-\log(1-p_j)]\right\}
}{
3\sum_jP_j+\sum_jN_j
},
$$

where \(P_j\) and \(N_j\) are callable positive and negative masses for token \(j\). The two half losses are averaged, followed by equal averaging across the six species sampled at each step. Full-parameter training uses AdamW, learning rate \(2\times10^{-5}\), weight decay 0.01, gradient-norm clipping at 1, 4,000 updates, and 400 warmup updates. The final-step checkpoint is used. There are 24,000 tile presentations per arm, not 24,000 independent tiles. [E05, E06, E21]

L and D differ only in the worm coordinate pool under the matched upstream protocol. PAIR8 and BLOCK4 preserve each half's token phase, tail bases, and supervision while changing cross-half attention visibility. Frozen D is a practical reference; PAIR8 versus BLOCK4 is the direct matched information-path contrast. Registered release gates, including the failed seed-42 gate, were not redefined for this manuscript. [E05, E06]

### Calibration and material/topology evaluation

The shared evaluation fits a non-negative-slope Platt transform on the designated six-species CAL data, with species-balanced fitting, and selects one global threshold under the frozen worst-species-first rule. It does not fit a worm-specific deployment threshold. Reusing this procedure does not establish calibration on an unseen species. Base-pair precision, recall, and F1 are computed from pooled callable counts within each species; the macro result averages species values. Average precision uses grouped tied scores in the current implementation. [E21]

Comparator-run matching uses greedy interval matching at IoU at least 0.8 within evaluation tiles. The archived boundary metric additionally requires both boundaries of an already matched pair to lie within the specified tolerance. It is therefore IoU-qualified joint-boundary F1, not an independently scored endpoint metric. Unknown-coordinate holes are retained rather than removed by concatenating valid positions. Legacy experiments require explicit evaluator-version certification before being pooled with newer results. [E03, E21]

### Human boundary and external benchmark experiments

The P3-R2 comparison holds the GENERanno backbone, U-Net trunk, body targets, seed 42, and 800-update budget fixed while replacing aligned boundary targets with a matched within-window permutation. The aligned target is triangular within ±16 bp of each comparator-run edge. The control jointly permutes left/right target pairs over boundary-valid positions, preserving their distributions and mass while breaking coordinate alignment. Training uses the first 3,000 8,192-bp windows on human chromosome 1, validation uses 800 windows on chromosome 11, and evaluation uses 1,200 windows on chromosome 17.

Mouse transfer is an absolute diagnostic, without an assumed matched mouse baseline. FlyBase r6.68 annotations are flattened into non-overlapping positive runs; 5,734 source annotations become 4,972 union runs on the 143,726,002-bp assembly. Positive-only scoring does not label all remaining sequence negative. Full-assembly inference coverage was checked in the archived benchmark. **[TO COMPLETE: reconcile inconsistent narrative job identifiers and archive canonical prediction manifests for the legacy and later P3 cells.]** [E07, E16]

### Gap-information and actionability analyses

Gap-head training uses the registered human training chromosomes; DEV is chromosome 13. HN-O augments the control input with the frozen nucleotide-transformer logit and seam features together. Three seeds are trained under the matched head schedule, and their risk logits are averaged before applying the sigmoid. Targets are negative fractions; the information metric is base-length-weighted MSE on fully known gaps. Action AP evaluates the registered binary action target rather than general base-level calibration. [E08]

The feasibility analysis orders all candidate gaps by increasing frozen risk score, groups exact ties, and evaluates every resulting whole-gap prefix plus abstention. It applies candidate-count, positive-recovery, long-gap-recovery, and negative/unknown budgets. The genomic span used to derive those budgets is deliberately optimistic; it is not the measured callable denominator. Failure of necessary conditions rejects the fixed-score monotone whole-gap family without opening CAL or sealed panels. **[TO COMPLETE: deposit the full threshold frontier and immutable candidate/score ledger; the compact JSON alone does not reproduce all 60,497 threshold rows.]** [E09]

### Gene prediction

The completed C analysis fixes Tiberius 2.0.7, `mammalia_softmasking_v2`, sequence length 400,050, batch size 1, and the native CDS-only exact-chain scoring rule across nine cores. All cores, including those without reference chains, remain in the denominator. Gains and losses are matched reference-chain changes, not inferred from a net F1 difference. Tiberius itself has been evaluated as a gene predictor with repeat-masking input, but that literature does not demonstrate a benefit of the masks studied here. [E10; R7] ([OUP Academic][4])

The newer P3 U/P/R protocol instead specifies 20 cores and a gene-locus endpoint that permits a match to a prelisted complete isoform. Its engineering smoke failed before complete utility scoring. Its planned sample size, reference counts, and acceptance criteria are not treated as observed results and are not pooled with C. [E11]

### Auxiliary analyses and uncertainty

Coarse typing reports detection, globally defined per-class F1, all-six-class macro F1, and Unknown behaviour separately. Representation analysis distinguishes family-supervised contrastive training from subsequent clustering. In the Dfam panel, 1,350 fragments form the training partition and 450 form a stratified holdout; K-means fits training representations, while reported ARI/NMI cover the combined pool. Pooled standardization and the lack of family/homology isolation limit prospective interpretation. Router shortlist regret is recomputed from observed anchor outcomes and is not interpreted as an executed local selection procedure. [E12–E14]

No confidence intervals or significance values are fabricated from summary tables. Seeds, species, spatial blocks, genomic bases, and workflow cells are different units. Registered gates are reported as decisions; they are not statistical significance tests. Where the main claim requires uncertainty not recoverable from the archive, **[TO COMPLETE: paired spatial-block uncertainty from archived predictions under a fixed analysis plan, without new threshold or model selection].**

## Data and Code Availability

The reviewed code is identified by repository `JiWang-Unige/ab-initio-TE` and submitted commit `c6781414794c120e41f67d9b43859a4d28453065`. The review package includes a file inventory, local evidence ledger, source hashes, a read-only numerical audit script, and an audit-results JSON. It does not redistribute genome data, model checkpoints, full prediction caches, or private HPC outputs. **[TO COMPLETE: stable public release/DOI, checkpoint and calibration artifacts, permissible derived evaluation data and prediction manifests, environment/container digests, license and access conditions.]** Availability of a submitted ZIP must not be represented as a verified public release.

## References

| ID     | Verified source                                                                                                                                                                                                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1** | Dalla-Torre, H. et al. *Nucleotide Transformer: building and evaluating robust foundation models for human genomics.* Nature Methods 22, 287–297 (2025). DOI: `10.1038/s41592-024-02523-z`. ([Nature][2])                                                                                                                     |
| **R2** | RepeatMasker. *Web RepeatMasker help*, official documentation, accessed 14 September 2026. ([repeatmasker.org][1])                                                                                                                                                                                                            |
| **R3** | Wong, W. Y. and Simakov, O. *RepeatCraft: a meta-pipeline for repetitive element de-fragmentation and annotation.* Bioinformatics 35, 1051–1052 (2019). DOI: `10.1093/bioinformatics/bty745`. ([OUP Academic][5])                                                                                                             |
| **R4** | Baril, T., Galbraith, J. and Hayward, A. *Earl Grey: A Fully Automated User-Friendly Transposable Element Annotation and Analysis Pipeline.* Molecular Biology and Evolution 41, msae068 (2024). DOI: `10.1093/molbev/msae068`. ([OUP Academic][6])                                                                           |
| **R5** | GenerTeam. *GENERanno-eukaryote-0.5b-base*, official model card. Associated work: Li, Q. et al., *GENERanno: A Genomic Foundation Model for Metagenomic Annotation*, bioRxiv (2025), DOI: `10.1101/2025.06.04.656517`. The model card is the checkpoint source; this is not the separate SegmentNT paper. ([Hugging Face][7]) |
| **R6** | Hu, K. et al. *HiTE: a fast and accurate dynamic boundary adjustment approach for full-length transposable element detection and annotation.* Nature Communications 15, 5573 (2024). DOI: `10.1038/s41467-024-49912-8`. ([Nature][3])                                                                                         |
| **R7** | Gabriel, L., Becker, F., Hoff, K. J. and Stanke, M. *Tiberius: end-to-end deep learning with an HMM for gene prediction.* Bioinformatics 40, btae685 (2024). DOI: `10.1093/bioinformatics/btae685`. ([OUP Academic][4])                                                                                                       |

---

## 主要数字的附件定位

以下路径相对于解压后的仓库根目录。**完整25项、62个来源引用及散列见下载稿的 Evidence Appendix**；这里列出正文关键数字的直接入口。

| 证据                   | 相对路径                                                                                                                 | 字段／评价对象                                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **E02** 历史矩阵         | `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`                                              | `model_key, window, species, n_windows, te_f1`；495行的组成                                                                      |
| **E02** 早期窗口         | `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep_current.tsv`                                       | 各checkpoint/window的早期F1；不得与当前DEV混分母                                                                                         |
| **E03** 历史版本问题       | `docs/experiments/REPOSITORY-SYSTEM-REVIEW-20260906.md`                                                              | Unknown→0、坐标压缩、interval painter、AP ties与训练暴露审计                                                                              |
| **E04** 共享D          | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D/dev_metrics.json`                                      | `per_species.*.{tiles,callable_bp,positive_bp,bp_tp,bp_fp,bp_fn,bp_f1,segment_f1_iou_0_8,boundary_f1_5bp}`；`summary`        |
| **E05** 覆盖比较         | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed{42,17}/{L,D}/{screen,dev}_metrics.json`                    | 八个明确组合文件；worm `bp_f1/bp_average_precision`及相同分母                                                                             |
| **E05** token oracle | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904.md`                                                             | D0-C exact-ceiling归档段落；.994498不是本轮运行结果                                                                                      |
| **E06** PAIR8        | `reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-decision.json`                                                      | `contrasts`、`absolute_readiness`、`scientific_gate_pass`、`release_seed17`                                                    |
| **E07** P3机制及外部结果    | `docs/experiments/P3-R2-CLOSURE-20260830.md`                                                                         | Human matched table、Mouse段落、Exact FlyBase r6.68 T1表；完整预测未包含在ZIP                                                             |
| **E08** HN信息         | `reports/GAP-A-B1-SCREEN-20260908-R1/result.json`                                                                    | `training_rows/dev_rows/known_dev`；`results.{arm}.known_DEV.{rows,bp,fraction_mse,irreducible,pseudo_base_brier,action_ap}` |
| **E09** HN动作         | `reports/GAP-HN-RANK-FEASIBILITY-20260908-R1/result.json`                                                            | `unique_score_thresholds/feasible_thresholds`及两个decision points；完整frontier不在ZIP                                             |
| **E10** 旧C           | `reports/GAP-BRIDGE-C-UTILITY-20260906-R1/result.json`                                                               | `core_count/completed_cells/reference_distinct_chains/reference_source_rows`；`modes.*.metrics`、`paired_vs_m0`               |
| **E11** 新P3失败        | `docs/experiments/MANUSCRIPT-LIVE-STATUS-20260914.md`                                                                | 12652888终态、exit、elapsed、异常及smoke-only记录                                                                                     |
| **E11** 新效用协议        | `docs/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1.md`                                                              | 20core×3与gene-locus端点；这些是计划，不是完成结果                                                                                          |
| **E12** 粗类型          | `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/superfamily5.tsv`                                               | `*_support/*_f1/unknown_recall/te_detect_f1/main4_conditional_macro_f1/macro_f1_all6`                                       |
| **E12** 指标定义         | `pipelines/PIPE-TEFM-LOCK-20260619/superfamily5_task.py`                                                             | `compute_metrics`，尤其main4 macro与conditional accuracy的区别                                                                     |
| **E13** Dfam表示       | `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`                                 | `setting,n,n_clusters,ari,nmi,holdout_macro_f1`                                                                             |
| **E14** F1点预测        | `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/selector_formula_results.json`                                 | `n_rows`、`deployable_random_forest`的in-sample R²及LOSO RMSE                                                                  |
| **E14** 路由器          | `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/selector_conservative_router_summary.tsv` | 固定 `feature_set=baseline_plus_kmer` 后比较split、contains-best及regret                                                           |
| **E15** 独立panel      | `docs/experiments/CROSS-SPECIES-L1-PANEL-METADATA-20260908.md`                                                       | assembly accession、修复后标签产物、库覆盖及暴露资格                                                                                         |
| **E16** 传统benchmark  | `docs/experiments/LEMMI-TE-BENCH-20260824-R1.md`                                                                     | assembly/truth flattening、三个有效T1 cell与运行台账                                                                                  |
| **E21** 当前训练/评分      | `scripts/experiments/CROSS-SPECIES-L1-20260903/cross_species_token_task.py`；同目录 `calibrate_evaluate_x0.py`           | 模型loader、token质量权重、CAL-only Platt、阈值规则和结构端点                                                                                 |
| **E24** J0/初始化       | `docs/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1.md`                                                               | J0阈值oracle表、P0R/H0R/D结果、停止决定及归档空间区间                                                                                         |
| **E25** gap路线状态      | `docs/experiments/GAP-ROUTE-TERMINAL-AUDIT-20260908.md`                                                              | 已完成、未执行、缺生物真值路线的分类；不是“所有方案均失败”                                                                                              |

---

# C. 主图与补图逐 panel 规划

**重要限制：不能根据紧凑JSON凭空生成完整PR曲线、HN frontier、UMAP或基因组浏览器例图。** ZIP没有相应底层数组的地方，应标 `[TO COMPLETE]`，而不是画示意曲线冒充结果。

## 主图

| 图                               | 逐panel内容                                                                                                                                                                     | 数据入口与科学信息                                                    |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Fig.1：材料检测与结构端点分离**           | **a**：L1/L2/L3及action的任务定义；**b**：六物种D的bp F1及.8冻结线；**c**：逐species的bp/run/joint-boundary三端点；**d**：positive/callable分母                                                          | E04、E21。表明内部材料检测与结构恢复不同；不得标题为“unseen-species generalization” |
| **Fig.2：coverage与context的受控比较** | **a**：L/D只改变worm坐标池，更新预算相同；**b**：两seed、SCREEN/DEV的F1/AP配对变化；**c**：PAIR8/BLOCK4相同token相位与监督、不同attention；**d**：PAIR8、BLOCK4、D在worm上的点值与冻结门                                     | E05、E06。coverage有复制方向；该context干预未过门。不能只画PAIR8 macro隐藏worm失败  |
| **Fig.3：P3结构机制及外部诊断**           | **a**：aligned vs matched permutation三端点；**b**：Mouse bp与run F1；**c**：FlyBase HiTE/Base/DAPT及后来P3的positive-only run recall；**d**：同一FlyBase truth上的fragments/truth、missed与split | E07、E16。体现机制否证和端点依赖；不同来源单独标识，T1无P/F1                         |
| **Fig.4：信息增量不等于可行动作**           | **a**：H0-O/HN-O/H0-S及组合输入；**b**：fraction-MSE与literal Brier分解；**c**：action AP及seed方向；**d**：risk极限与utility极限两个已记录点，加“60497阈值0可行”                                               | E08、E09。完整frontier须取回原文件；当前只能画已记录点，不能伪造全曲线                   |
| **Fig.5：真实基因效用与未完成问题**          | **a**：M0已为P3，MW/MP为真值辅助增补；**b**：27cells的TP/FP/FN及gain/loss；**c**：另一个U/P/R问题及smoke失败状态                                                                                        | E10、E11。旧C不能替代新P3。若主图数受限，Fig.5改正文结果表即可                       |

## 补图与补表

| 图      | 逐panel内容                                                                | 来源及限制                                                |
| ------ | ----------------------------------------------------------------------- | ---------------------------------------------------- |
| **S1** | **a** backbone/window全矩阵；**b** EBAR分kingdom；**c** edge bins             | E02、E22；来源分面，chromosome SD不是seed SD                  |
| **S2** | **a** token oracle；**b** J0阈值headroom；**c** FN来源构成                      | E05、E24；oracle不是可部署成绩，FN按Label-A/tile解释              |
| **S3** | **a** P0R/H0R/D；**b** 已归档空间CI                                           | E24；CI按原区块设计解释，不扩成跨物种显著性                             |
| **S4** | **a** matched Base/DAPT；**b** naive ensemble；**c** C5 query→copy漏斗      | E22、E18、E17；不同分母不能串成升级曲线，A2/A3未执行                    |
| **S5** | **a** 六类F1/support；**b** Unknown recall/F1；**c** all6与main4定义对照         | E12；完整risk-coverage曲线需要预测概率，不能由两个宏平均推造               |
| **S6** | **a** 同一Dfam panel的ARI/NMI；**b** holdout F1；**c**监督、预处理和划分的数据流          | E13；保留C0/C1，不把pipeline叫全无监督                          |
| **S7** | **a** F1预测LOSO；**b** 路由LOSO/leave-clade；**c**oracle regret和abstention说明 | E14；不同feature set分开，真实probe未执行                       |
| **S8** | **a** label-source资格；**b** Unknown/坐标/evaluator版本审计；**c**工程失败台账         | E03、E15、E11、E16；exit0不自动代表产物有效                       |
| **S9** | **a** DNA-only入口；**b** CPU/GPU throughput；**c**完整workflow资源             | E19；b/c `[TO COMPLETE]`，8,206bp smoke不能充当速度benchmark |

---

# D. 最小补实验清单与 Omnibenchmark 判断

## D1. 投稿前必要，或由所保留 claim 决定是否必要

以下成本是**资源规划量级，不是本轮实测，也不是完成时间承诺**。任何新数据访问或模型执行都仍需另行授权，不改变旧冻结协议。

| 项目                                | 依赖claim与最小动作                                                                                            | 成本量级                                                          | 停止条件                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| **N0：主结果可复核归档——必要**               | 当前稿全部主结果。取回已有canonical坐标/预测、模型与calibration hash、评估版本；补HN完整frontier；统一LEMMI与closure的job manifest；只重算已有输出 | 无新训练；CPU与I/O级，通常约 \(10^0–10^1\) CPU h规划范围，存储另计                | 无法证明同分母/同版本的结果降为历史探索；不能因“代码已修”自动恢复旧数值有效性                          |
| **N1：独立L1 panel——保留外部泛化claim则必要** | 最小候选为冻结D；先资格审查platypus/urchin/CB4，再一次性评估。检查历史项目使用、预训练/同源暴露及标签覆盖                                         | 元数据CPU级；固定tile诊断约 \(10^0–10^1\) GPU h，完整约2.9Gb面板可能显著更多        | 标签贫乏不等于确定负例；资格不合格则停止独立真值声明。差分数照报，不调阈值换panel；小诊断不替代原完整协议           |
| **N2：同实例当代传统对照——实用方法比较必要**        | 当前D＋可验证复用的HiTE＋第二完整workflow，建议RepeatModeler2建库→RepeatMasker注释。先一个合格实例，不先做全五工具×全物种                       | 第二完整de novo workflow约 \(10^2–10^3\) CPU h量级预算；D推理从GPU小时级估算后修订 | 预定资源cap；失败/超时保留。T1只能recall；要P/F1必须有合格negative/callable comparator |
| **N3：CPU/GPU代表性性能——部署/高效claim必要** | 同一10–50Mb真实FASTA，固定线程/批量，cold/warm分开，3次计时，检查输出一致性，记录throughput/RSS/VRAM；另报完整建库＋注释                       | CPU约 \(10^1–10^2\) core-hours及少量GPU小时规划范围                     | 不从45秒小smoke线性外推whole-genome；OOM/timeout保留；无数据不写速度优势               |

我的优先级是：**先N0，再一个合格的当前模型/传统workflow对照。** 保留“未见物种泛化”时必须补N1；保留“高效可部署工具”时必须补N3。若稿件严格收敛为内部评估/机制研究，可以明确删掉这些广泛claim，而不是假装它们已经完成。

尤其不能继续沿用“HN mechanism GO”时提出的whole-gap增补设想，忽略随后固定模型的动作 NO-GO。**机制筛选阳性没有自动释放新的六物种完整训练或部署。**[E09、E15、E25]

## D2. 增强但非本中心论点必需

| 项目                           | 最小比较与依赖claim                                                     | 成本量级                                             | 停止条件                                                                     |
| ---------------------------- | ---------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------ |
| **原P3-Tiberius U/P/R**       | 只有“P3基础mask改善gene annotation”依赖。先修工程，再按原20core×3、原gene-locus端点完成 | smoke后按实测预算；完整60cells为GPU十小时级或更高的规划，不能套用旧短core耗时 | 原ΔF1≥.01、paired core bootstrap下界>0及recall/loss guards不改；阴性即停止，不换端点或挑core |
| **两基座公平小对照**                 | 仅“backbone A优于B”依赖；2backbone×2seed，固定坐标、呈现量、窗口、任务和校准；同时报告质量与计算成本 | GPU十小时级起，模型差异另计                                  | 相近即删优势claim，不扩成全尺寸×全窗口搜索                                                 |
| **真实routing／bp calibration** | 实际执行固定信息预算probe，明确是否需要外部标签；bp calibration单独验证                    | CPU为主，必要时少量冻结模型推理                                | oracle regret不称部署收益；abstain100%不称有效路由                                    |
| **身份隔离的typing/embedding**    | 先建立family/copy/homology身份，train-only预处理，C0/C1必须保留                | 身份整理可能主导，训练可小规模                                  | 无法建立身份就停止新家族claim；GLM不优于C1不继续扩模型                                         |
| **生物实例／历史验证**                | L3或hg19→hg38→hs1后证实claim独立立项                                     | 专家标注与来源整理为主                                      | 无独立真值、旧冻结预测或可比mapping就不建立claim                                           |

### P3 smoke 的最小工程修复方向

源码中，smoke使用 `singularity --cleanenv`，却只在宿主环境设置 `BASE_MASK_OBSERVATION`；wrapper在`try/finally`之前直接读取该变量。这与官方文档所述的环境清理行为和已归档KeyError相一致，因此是**高可信原因推断，但不是已经验证的修复**。最小改动应是显式容器传参、保留six-channel及原始输入字节观测，并让异常也写终态；不是改变科学评价口径。([Sylabs][8]) [E11]

## D3. 不建议继续

**不建议重开固定HN的Platt/阈值/长度分层搜索、未过门后的PAIR8 seed17、旧C同predictor/panel扩张、缺乏新多拷贝材料的C5 A2/A3，或默认增加MoE。**

这不是说新的partial-fill、关系模型或MoE在原理上不可能；而是现有证据没有提供足以改变决策的新假设、真值或专家互补性。它们不应成为挽救当前稿件claim的无限续轮。[E06、E09、E10、E17、E18、E25]

## D4. Omnibenchmark：可行，但只做最薄的一层

官方Tutorial提供YAML形式的data→methods→metrics依赖、Git引用、软件环境和metric collectors。它适合把已有adapter、评分器和结果追溯组织起来；**不解决本项目的truth资格、library公平、ontology或sealed独立性。**([docs.omnibenchmark.org][9])

| 层           | 最小合同                                                                | 本项目必须保留的限制                                    |
| ----------- | ------------------------------------------------------------------- | --------------------------------------------- |
| `data`      | assembly SHA、split role、truth tier、callable/Unknown、标签来源与exposure清单 | method只接收DNA和必要运行元数据，不接收评价真值                  |
| `methods`   | 固定D、HiTE、第二完整传统workflow；canonical material BED及运行状态                 | 保留native输出和建库文件，不偷偷更换genome/library           |
| `metrics`   | L1 bp、L2 run/boundary、T1 positive-only分开                            | 没有负类就不能输出P/F1，L2不改名L3                         |
| `collector` | 按assembly/method/library/split/evaluator/seed保留结果行及资源               | FAILED、TIMEOUT、PRUNED、SKIPPED显式保留，不跨panel随意平均 |

当前CLI支持 `ob validate plan`、`ob run ... --dry`、Snakemake参数透传和性能记录汇总。CLI将`--dry`定义为只生成Snakefile；**dry成功不是benchmark运行成功**。能力筛选也可能裁剪节点，因此必须在计划分母中保留被跳过的任务。([docs.omnibenchmark.org][10])

HPC可经Snakemake官方Slurm executor/profile接入，但必须验证版本兼容及站点资源映射。可复用现有容器；CPU资源记录与GPU VRAM应区别处理，不能默认框架自动测得全部GPU指标。([docs.omnibenchmark.org][11])

**最低成本顺序：先规范三种方法的输入输出和已有评分器 → 补一个同实例对照 → 再把adapter套进Omnibenchmark。** 不建议把迁移数月历史实验列为投稿前置条件。当前快照没有已执行的Omnibenchmark整合benchmark；上述只是方案判断。

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
