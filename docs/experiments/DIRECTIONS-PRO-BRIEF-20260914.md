# 新研究方向：用户问题与第二轮 Pro 讨论

2026-09-14。延续同一 Pro 对话，前轮送审 `c678141`，前轮归档 `05f393d`。这是新阶段设计讨论；历史NO-GO只约束其实际试验对象，不能用来自动否决明确不同的新假设；也不能把新提案当成完成结果。

## 本轮明确偏好与目标

用户希望研究补充后并行推进，允许探索新方案；明确**同一新实验固定一个seed，暂不做多seed重复**。保留历史结果和既有冻结判定；空间/基因座不确定性与随机初始化不确定性分开，不用bootstrap冒充seed重复。新阶段不要沿用旧三seed草案作为默认要求，也不要宣称模型差异必然大于seed波动——本轮只是暂不测后者。

请给出可执行的、有有限比较的科学方案，不仅是方向列表。每条写：主要假设、最小第一实验、输入/输出、划分与信息访问、对照、主终点、失败后的处理、资源估计依赖、下一阶段条件及正文/补充定位。区分可以立即实施的工程/原批准实验，与仍缺真实数据资格或尚未定义科学选择的部分。不要默认使用多seed、MoE、大规模搜索或重新引入已退役的CLI评审框架。

## 1. 共享模型外部泛化与MoE

六物种共享D内部macro bp-F1=.888761、worm=.797565；六物种参与训练。已知外部候选platypus/urchin/CB4的Label-A工程完成，不等于外部模型评估。请结合随附本轮核查判定当前真正完成到哪一步。

用户询问是否需要补齐固定D的其余物种测试，以及MoE激活不同参数能否稳定多物种。请给出 frozen shared → parameter-matched dense/adapters → 如有专家互补再MoE 的最小比较；明确监督适配与zero-shot泛化不同。路由只能使用部署时可得信息，不得用目标F1选专家。一个seed下仍须保留每物种损益和最差物种，不能只报macro，也不能事后挑物种。旧P3+HN whole-gap草案不能默认覆盖当前D的对象选择，HN后续action NO-GO需尊重。

## 2. 标签不完整：hg19训练、跨染色体与hg38/hs1支持

用户提出：固定一个GLM，在hg19一条染色体训练，在其余染色体预测；部分按旧注释算FP的位置可能被hg38/hs1更新注释支持，从而提示旧标签不完整并压低F1。进一步假设注释贫乏物种受影响更大，并询问可类比的其他物种。

请设计可证伪实验，而非把这个解释预设为真。特别区分：同一assembly更换annotation/library的回顾性恢复、跨assembly共同同源区恢复、新增组装序列和mapping失败。现代GLM在旧基因组上的回顾性分析不能称真实时间前瞻预测；模型预训练暴露与新库信息泄漏要披露。旧标签评估分母应完整保留，不能只挑后来转阳的候选提高F1。对FP转阳、FP未解、FN、TP、匹配未预测背景做分层；新注释仍不是完备真值。给出旧/新library×固定assembly的控制，明确可比同源区和新增序列分开。

请推荐1–2个有可获取官方旧/新注释与组装的其他物种，写具体资源、可比较单位与取舍。若标签稀疏程度解释低F1，怎样区别模型真实失效、物种难度和标签来源？当前项目的chr19–22等封存限制不能因新叙事自动解除，TRAIN/CAL/DEV/TEST要新明确。

## 3. 下游效用与三个新结构方向

### 已批准Tiberius路线

`P3-TIBERIUS-BASE-MASK-20260911-R1.md` 明确已批准固定hg38 chr16/18的20个5Mb core，U/P/R三臂、固定P3-R1与Tiberius2.0.7；smoke通过后同一实现全60cells，再CPU score与规定独立复算。新smoke12652888为缺失BASE_MASK_OBSERVATION的工程FAILED；不是科学阴性。旧C是另一已完成问题，不能混淆。讨论后优先修最小工程原因并继续原协议，无需重复批准原范围。

### a. Strand / biological prior

RC symmetry、正反链建模及有明确可计算定义的biophysical prior能否改善泛化与边界？请先设计固定模型正向/RC映射一致性与推理平均，再比较训练RC增强、等变设计。控制token phase、尾部、边界映射、输入量和算力；binary strand invariance与方向型family/instance信息分开。不要把未定义的“biophysical prior”当万能项。

### b. 两个GLM互补

历史简单ensemble/bridge未过结构门，但HN附加logit+seam给出信息增量。能否用错误分型、局部上下文、材料风险、每bp决策或pair关联构建新的有限对照？请区分新的可检验假设与对已关闭whole-gap阈值的重复搜索。需要single-model、same-capacity单源、简单融合和学习融合对照，必要的alignment/token/calibration控制，以及来源标签伪互补排查。

### c. Fragment linking，显式预测关系

对预测fragment Fi=[si,ei)、Fj=[sj,ej)，目标是 p_ij=P(zi=zj)，zi为TE insertion身份。用户希望递增证据：

- B0：distance-only f(dij)。
- B1：RepeatCraft-like rule，distance/orientation/predicted family/overlap/fragment length；示例 d<150且family相同且方向相同。150是待评估规则值，不当成RepeatCraft官方默认。
- M2：sequence embeddings hi,hj及distance。
- M3：再加gap、left/right context和orientation，以区分同源外观与两个独立插入。

请正面评估这个方向的价值。link输出可以连接两个fragment而不把中间bp标成TE，应把relation输出与material mask分开。关键是same-insertion真值来自哪里：RepeatMasker ID/family或相邻标签不应被假装成独立生物学真值。请提出受控模拟/半模拟、curated子集或可用实例证据的可行入口；嵌套、截断、同family邻接、方向未知和不确定pair如何处理。训练/测试按insertion及同源关系隔离；pairwise PR/AUPRC、cluster fusion/fragmentation和传递闭包误差分别评分，候选生成召回不遗漏。是否应暂时只发布association而非biological reconstruction？

## 4. Unknown与标签不足

用户认为部分Unknown只是人工注释不足，模型可能识别对应family；询问这是否解释已有现象。前轮coarse分类Unknown recall=.388597，binary-H0=.042627；main4宏F1=.864415，BG/Unknown混淆仍计FP/FN。请先准确解释Unknown recall方向，它表示true Unknown被预测Unknown的比例，并不直接量化正确重分类。给出Unknown→known、Unknown→BG、known→Unknown及独立重注释验证；不能把Unknown当缺失TE标签、背景或新家族三者的同义词，也不能直接用模型自我一致性证明改标正确。评估时保留旧标签结果，同时单列独立支持的reclassification。

## 5. 重新核查Baobab TE_final的Dfam实验

用户明确指出真正相关实验在SSH后的TE_final，表现远超basic+contrastive。已派独立subagent定位、读取并复制紧凑代码/结果到项目；具体事实以新增恢复报告为准，不能在未查前默认用户记错，也不能把旧1800/10clusters表或另一panel数字当作同一实验。请根据恢复出的真实panel、split、指标、实现判断是否应更正上一轮论文结论，以及重现实验、身份隔离和工具可用性还缺什么。

## 6. 完整公平的Omnibenchmark

用户明确希望后续搭建完备的公平benchmark。请设计可增量执行的完整矩阵，而不是仅停留于“可以包装”。复用现有canonical adapter和不同truth tiers；传统完整workflow计建库+注释，fixed-library检索另列。方法可以分批补齐但失败/超时/不适用仍在分母；不要将所有方法强塞相同不适合的任务。

CPU/GPU速度以代表性真实FASTA、固定线程/批量、cold/warm和重复计时报告；计时重复不等于重训seed。确认当前Omnibenchmark schema与教程可能有差异：spec-reference显示software_environments为列表、支持named entrypoint及host/apptainer和optional storage；先规范1个端到端工程实例，再扩方法/物种。目标是可执行公平benchmark，不默认建S3或发布网站。

## 7. 单seed执行

所有新增方案采用同一预先固定seed（优先42以对应当前模型），不要求新训练多seed；旧协议未执行部分如需改变seed合同应写明新阶段而不追溯改变旧PASS/NO-GO。科学误差仍可来自样本、标签与架构差异，报告本次无法估计初始化方差即可。不要把多seed当本轮并行推进的前置条件。

## 8. Multi-reference / multi-prototype表示假设

用户希望检验“一个family一个consensus是否丢失within-family diversity”。比较single Cf与multiple {Cf1...Cfk}，或embedding prototypes {ef1...efk}，score=max_j sim(e(x),efj)。这与扩大GLM是不同问题。

请确认传统资源并非都只有single consensus：Dfam profile HMM本身表达位点变异和indel；需要把consensus序列检索、profile-HMM、多个序列prototype和embedding检索分清。给出真正隔离表示效果的控制：single/多prototype、随机matched-k、简单特征和GLM、相同训练copy来源、family/copy/homology划分、固定阈值校准与多候选最大分数偏差。测试copy不能参与prototype或profile构建；核对family size/novelty/fragment length strata。只有consensus资产时如何获得独立copy集合？先以检索任务验证，怎样再接到genome annotation并计FP和完整成本？

## 请交付

1. 对八点逐项明确赞成/修改/暂缓及证据，不自动接受用户或上一轮助理的假设。
2. 建议主线与并行依赖图：哪些现在可以开始，哪些仅能先做数据资格与协议；给最小第一轮和明确停止条件。
3. 可执行的单seed矩阵、数据合同、endpoint、对照及现有代码复用路径；不以大框架取代实验设计。
4. 更新论文取舍：补成方法论文需要哪些核心阳性；如果某方向阴性，论文如何收敛，而非无限加实验。
5. GitHub访问请实际调用当前可用工具，报告读到的仓库、分支、commit和一个具体文件；不能把工具名出现或链接可打开当成功读全库。若无法读取，请明确限制并使用已上传快照及新补充包。本地代码/compact报告可进Git，原始数据、权重、秘密和无授权生物资产不随仓库公开。
6. 请把完整结论放在可复制的回复正文，以便归档，不仅给下载链接。无需重写整篇英文稿，重点是科学方案、实质纠错和并行实施次序。
