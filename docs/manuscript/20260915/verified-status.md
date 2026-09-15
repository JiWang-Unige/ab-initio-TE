# 第三轮审阅：已核实的实验状态

证据快照：Git `5ca4d336407bde995e170aed81c9678acc26764f`，2026-09-15。本文由 Codex 根据仓库协议、源码和结果核对；ChatGPT Pro 的独立审阅另存。完成运行、得到可解释结果、达到预设标准、支撑广泛应用是不同状态。本轮仅整理结果与补实验设计，没有启动新训练或改变任何冻结标准。

## 完成矩阵与论文位置

| 方向 | 实际完成范围 | 能支持的结论 | 当前论文位置 / 缺口 |
|---|---|---|---|
| GLM 与窗口 | 历史 FINAL 495 行：9 个 checkpoint/config 变体 × 5 窗口 × 11 物种；每次 1200 窗口 | 特定设置的描述性材料识别比较 | 主要作补充材料；不等于 9 种独立架构，bp/compute/Unknown 口径并非完全匹配。若正文主张架构优势，需同坐标、同数据与合适预算的有限对照 |
| 六物种共享 D | 六个训练内物种与已固定外部面板完成；MoE 预测头、海胆适配及原六物种保留性完成 | 材料识别与片段质量、物种适配与保留性之间存在差异 | 可作正文。不能称所有脊椎动物可靠或只有线虫表现弱；未见物种的标签资格和完整分母仍不足 |
| 注释版本 / library | hg19 chr1 训练、chr2/3/4 评价、严格映射与 exact-sequence 匹配背景；海胆 library 敏感性完成 | 参考依赖的模型–标签分歧与模型漏检并存 | 可作正文诊断结果；尚非独立证实的新 TE 或修正后的生物学 F1 |
| SF5 分类 | 已审计真实训练/验证/测试覆盖；既有测试前缀的 4×120 窗口平衡重放完成 | 四物种既有面板的粗类别表现及覆盖偏差 | 原六物种设计未完全修复；当前更适合作补充材料，不能宣称细 superfamily 注释器验收完成 |
| 聚类 / 检索 | k-mer 消融、监督投影训练、冻结 NTv2 表示检索完成；历史 trainable GENERanno 记录恢复 | 同面板训练后 6-mer 是强基线；不支持现有 NTv2 的普遍优势 | 检索可作补充结果。可训练 NTv2 + 无标签学习 + 聚类的闭环仍未完成 |
| multi-prototype | natural-copy 同面板单 medoid、多 medoid、centroid 完成 | 多 medoid 可优于单 medoid，但本面板 centroid 更强 | 探索性补充；没有证明 multi-reference annotation 全流程优于单 consensus |
| Gap / ensemble | 既有 HMM/CRF/decoder、HN、Stage1、多 GLM 诊断完成；限定标准下未获得可操作的联合改善 | bp 材料得分不能代替结构与插入身份恢复 | 可作正文关键限制。Fragment linking Phase0/1 只有 toy 工程结果，真实生物实例路线尚未执行 |
| Tiberius 效用 | 人 hg38 chr16/18、20 cores×3 arms 全部完成，独立复算完成 | P3 mask 提高固定 softmask 模型的平均 locus-F1，同时损失部分原正确 loci | 可作正文收益–损失结果；预设低损失标准失败，未证明优于 R，也未验证跨物种效用 |
| Benchmark / Omni | 三物种固定小面板、12 格矩阵保留 1 个 TIMEOUT；GitHub 固定提交 Omni 实跑完成；同输入 CPU/GPU 计时完成 | native workflow 可运行性、覆盖/一致性与本面板性能成本 | 完整 benchmark 尚未完成：没有独立 accuracy 真值，4 MiB 不能代表全基因组 de novo 表现 |

## 1. 参考覆盖缺口可以成为结果，但不能成为免责解释

在严格双向坐标资格且对应序列完全相同的 18,079 对 FP/TN 匹配对中，后续 CHM13 注释覆盖至少 80% 的比例为 FP 13.88%、TN 10.84%。孤立片段为 17.52% 与 16.77%，主要差异集中于旧 TE 边界邻接片段。因此目前更接近“注释边界和版本相关分歧”，不能写成大量独立新插入已获证实。匹配 TN 有重复使用（最多 775 次），18,079 对也不是 18,079 个独立对照。

海胆替代 uncurated library 给出 844,932 bp 严格 TE 类注释，固定 D 的召回为 0.4289；新增参照覆盖并未消除模型漏检。推荐论文措辞是：**参考注释覆盖和模型识别能力共同决定观察到的误差，二者需要分开度量；较高的碱基一致性也不自动保证结构和下游安全性。**

若要把机制从关联推到更强结论，最有价值的有限补充是：固定同一 assembly 和注释软件版本，只改变旧/新 library；按边界邻近、孤立、低复杂度等层对 FP 与匹配背景作盲法外部核实；使用 region/copy 级独立单位量化不确定性。传统方法的 library 和评估真值不能来自同一证据而不说明循环依赖。人/小鼠可作来源较完整的锚点，但“物种常用”不是独立真值的证明。

来源：[匹配结果](../../experiments/HG19-CHR1-REVISION-20260914-MATCHED-RESULT.md)、[外部 library 敏感性](../../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/LIBRARY-SENSITIVITY-20260914.md)。

## 2. 可训练 NTv2 的真正无监督聚类仍为空缺

历史 `exp004_B1_warm_trainable` 使用 **GENERanno**，`freeze_backbone: false`，但 `same_class_any_species` 根据类别标签构造 InfoNCE 配对，因此是监督对比学习。历史 ARI≈0.693 还存在原始面板/split 溯源不足，不能直接与当前实验排行。恢复目录中的 consensus 配置和脚本也不能代替完成日志与指标。

当前 natural-copy 实验冻结 NTv2-500M，只训练 1024→128 的类别监督投影；不是微调 backbone，也不是无监督。235 个已用于探索的 EVAL query 上，匹配训练方式后 6-mer 的 top1=0.6426、macro-F1=0.6057，冻结 NTv2 投影为 0.5064、0.4994。这个结果应保留，不能用历史异面板数字覆盖它。

Pro 提出的接纳错误比例也已由本地源 JSON 核实：6-mer 为 40/175=22.86%，冻结 NTv2 投影为 43/129=33.33%；CAL pair 错误为 63/6328≈1%。因此 pair-FAR≤1% 不能解释为 query-FDR≤1% 或低风险未知 family 拒识。两种投影可训练参数分别为 524,416 与 131,200，也不能把现有比较说成严格容量匹配。

若继续该支线，有限对照可包括：强 k-mer 表示、冻结 NTv2、冻结 NTv2+无标签投影、可训练 NTv2+相同无标签目标。训练与选择不得利用真 family 标签；按同源组/自然 copy 隔离，类别标签仅在冻结后用于外部聚类评价。报告 ARI/NMI、碎裂/混并、未知类和跨物种行为；若设置真实类别数 K，只能列为 oracle 诊断。固定一个 seed42；保留独立样本层的不确定性。只有相同数据、目标、选择规则下的结果才能回答“可训练 NTv2 是否增加价值”。

来源：[当前检索协议与结果](../../experiments/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914.md)、[TE_final 恢复](../../../reports/TE-FINAL-DFAM-RECOVERY-20260914/)。

## 3. 1200 窗口的问题是覆盖与独立性，不是一个数字阈值

真实 TRAIN 为 5400=6×900，训练没有只取 1200；VAL 为 1440=6×240，但两个模型实际只评分前 1200，遗漏 C. elegans；TEST 为 2160=6×360，但实际前 1200 为小鼠/斑马鱼/鸡各 360、蛙 120，遗漏果蝇和 C. elegans。这同时影响验证选择与测试解释。

本轮平衡重放只用既有前缀的 480=4×120，没有新分类训练，也没有补齐剩余两个物种。主四类 pooled macro-F1 为 0.8478/0.8458，物种等权平均为 0.7337/0.7450（base/H0）；不能只报 pooled 数字。小鼠 binary-F1≈0.960，但主四类 macro-F1≈0.836/0.847，DNA 类 F1 只有 0.509/0.578。Unknown 真阳性支持只来自斑马鱼，其他物种应是 N/A，而不是高召回。

这些标签为 LINE/SINE/LTR/DNA 粗类型，不能改称具体 superfamily。Unknown 混合 known-other、ambiguous 和 unclassified；unannotated BG 也未经过真阴性确认。现有坐标被保留，但窗口来自连续区域，数百万 bp 不等于数百万独立样本。

若要保留独立分类贡献，需要先冻结层级 ontology、ambiguous/Unknown 处理和支持分母，再恢复覆盖完整的验证选择、评价各物种/类别/独立区域。新 held-out 面板与旧的已见面板分开；必要的新训练写成新协议，不能事后声称旧 checkpoint 按完整验证集选出。人和小鼠适合作锚点，但应加至少一个注释来源合格的外部分支，才能讨论跨物种。样本量由稀有类别支持和 region/copy 级区间精度决定，没有“1200 必然够/不够”的通用结论。

来源：[真实评分前缀审计](../../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/run-12708396/scored-prefix-12708568.json)、[ontology 审计](../../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/run-12708396/ontology_audit.json)、[平衡重放](../../experiments/SF5-BALANCED-REPLAY-20260914.md)。

## 4. Gap 与 Tiberius：分别记录结构问题、平均效用和局部损失

现有多 GLM ensemble 能小幅提高 bp-F1（例如均值 ensemble 0.9432），但未同时改善片段结构；最佳 bridge 的 fragments/truth 仍比更好的单模型高 6.59%，fusion 也增加。HN 全 gap 前沿和其他已冻结路线同样没有达到联合标准。正确表述是“所评估方法在预设约束下未解决该问题”，不是“所有可能方法都失败”。真实 fragment-linking 仍未检验；toy 工程指标不能证明识别同一 TE insertion。

Tiberius 使用人 hg38 chr16/18 的 20 个 5 Mb core、100 kb halo，共 726 个 reference loci，同一 `mammalia_softmasking_v2` checkpoint：

| 输入 | TP | FP | FN | Locus-F1 |
|---|---:|---:|---:|---:|
| U：无 mask | 510 | 367 | 216 | 0.636307 |
| P：固定 P3 mask | 549 | 295 | 177 | 0.699363 |
| R：UCSC all-repeats mask | 548 | 302 | 178 | 0.695431 |

P−U=+0.06306，paired-core bootstrap 95% CI [0.03650, 0.10683]；但损失 16/510=3.14% 原 U 正确 loci，高于冻结的 1% 上限，因此 `P3_BASE_MASK_UTILITY_GATE_NOT_MET`。P−R=+0.00393，区间 [−0.00261, 0.01337]，没有显著优越证据，也没有预设等效界限所支持的等效结论。

本轮用既有 `result.json` 的 `(core, reference_locus_id)` 集合补做描述性分解：P、R 各新增 55 个 U 未命中的正确 loci，其中 53 个相同；P 损失的 16 个 U 正确 loci 全部也被 R 损失，R 另损失 1 个。P 相对 R 多命中 NOD2、DCC、MALT1，少命中 CCNF、TIGD7。该面板上没有 P 独有的 U-correct 损失，提示两种 mask 的收益/损失高度重叠；这不是等效性检验或机制确认，也不改变 P 的失败门。有限的后续机制核实可先检查这 16 个共同损失及 5 个 P/R 不同位点的输入 mask、预测链和参考转录本，不必立即开新模型搜索。该面板已见，不能同时拿这些位点调方法并宣称独立验证。分解结果在 [JSON](tiberius-locus-overlap.json)，由 [脚本](../../../scripts/manuscript/summarize_tiberius_locus_overlap_20260915.py) 直接从冻结结果生成。

R 是已有 UCSC 库依赖 mask，不是本次重新运行完整 native RepeatMasker 的产物。此实验是 P3 的固定输入干预，不能归给共享 D，也不是跨物种效用。若保留广泛部署主张，应另设外部物种面板，对照正确配置的完整下游工作流；当前 Tiberius 官方建议还区分 unmasked 与 softmask 模型，P>U 不等于优于其推荐默认流程。本次失败的低损失门不以增加物种、改阈值或换 checkpoint 事后挽救。

来源：[ensemble 诊断](../../experiments/TEFM-BACKBONE-ENSEMBLE-DIAGNOSTIC-20260903.md)、[linking Phase1](../../experiments/FRAGMENT-LINKING-PHASE1-20260914.md)、[Tiberius 最终结果](../../../reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/RESULTS.md)、[独立复算](../../../reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/independent_recheck.json)。

## 5. Benchmark 的具体工具和物种

当前新增 native 矩阵使用三个物种：**鸭嘴兽、海胆、C. briggsae**；各 4 个固定 1 MiB 区域，名义输入 4,194,304 bp。它们不是人/小鼠全基因组 benchmark，也不是 C. elegans。

| 方法 | 版本 / 输入 | 三物种完成状态 |
|---|---|---|
| RepeatMasker fixed library | RepeatMasker 4.2.4 + Dfam 3.9 lineage | 3/3 有运行结果 |
| HiTE | 3.3.3 | 3/3 有运行结果 |
| RepeatModeler2 → RepeatMasker | RM2 2.0.9 → RM 4.2.4 | 海胆、C. briggsae 完成；鸭嘴兽原 110 分钟预算 TIMEOUT，指标留空 |
| D | 冻结 F 预测缓存 | 3/3 汇出同坐标读数 |

矩阵保留全部 12 格，11 格有读数；不是删去失败格后的“全部成功”。本批未包含 EDTA、EarlGrey、REPET、RepeatCraft 或 TEtrimmer。Omnibenchmark 已从干净 GitHub 固定提交实跑，完成的是编排和记录闭环。

目前主要终点是 T2 callable coverage / concordance，缺少独立真值，absolute precision/F1 为 null。覆盖率包含分类后的各类输出，不能当作 TE recall；例如 C. briggsae fixed-RM 的 141 bp 全属于 nonTE。4 MiB 尤其不适合代表 de novo 建库的全基因组能力。CPU/GPU 同输入计时已经有 1 MiB 探针，但不能替代完整端到端速度、内存与建库成本。

若要完成正文 benchmark，优先建立可追溯独立评价面板，并让需要全基因组建库的方法在合适规模发现候选，再在同一 held-out 区域评分。预算、超时、训练数据和 library 可用性预先固定；模拟真值用于结构能力，真实盲法整理用于生物有效性，两者分开报告。先覆盖方法实际声称适用的范围，不为凑软件数量加入任务不匹配的工具。

来源：[native 协议](../../experiments/TE-REAL-PANEL-BENCH-20260914.md)、[Omni 记录](../../experiments/TE-REAL-PANEL-BENCH-20260914-OMNI.md)、[最终固定矩阵](../../../reports/TE-REAL-PANEL-BENCH-20260914/final-12708424/)。

## 取舍原则

准备投稿所需的关键补充是独立评价、参考依赖的受控核实，以及保留在主文中的分类/效用主张对应的代表性验证。可训练 NTv2 聚类和真实 fragment linking 是可以单独成立的新问题，但不应自动变成当前论文的全部必做项。继续扩大 MoE、反复搜索 Gap 阈值、重复已见 EVAL 的模型挑选、增加同一实验 seeds，都不是当前优先项。所有新实验仍需具体数据/预算/冻结选择规则，本文不构成作业提交或封存数据访问授权。
