# 面向作者讨论的论文收束草案

2026-09-17。状态：已完成本轮 ChatGPT Pro 讨论，供作者选择；不是新增实验授权或已完成补充结果。原 20260916 全项目稿、冻结协议和阴性结果均保留。审阅范围、双方共同建议与有限执行顺序见 [Pro 讨论归纳](pro-review-and-decision.md)。下文保留详细论证和英文写法示例。

## 建议的研究问题

**序列模型产生的重复序列 material mask，能否在不调用目标物种 TE 参考库的推理过程中，改善哺乳动物基因结构注释？**

目前可支持：冻结的人类 P3 模型在三个哺乳动物面板上，相对无 mask 对照提高了参考基因结构一致性；牛和鸭嘴兽还优于官方无 mask Tiberius 流程。当前尚未证明对强 reference-mask 流程的优势、正式非劣效、跨所有类群的可用性，或在实际库匮乏条件下的独特优势。

“完整 TE insertion 注释”“同家族片段连接”“超家族分类”“无监督家族发现”不是这个研究问题的必需输出。v1 可以输出逐碱基 mask 和可用的注释流程，不必先解决所有 TE 问题。

## 已核实的 P3 实现与来源

- P3 导出直接调用序列 tokenizer 和冻结模型，以四状态概率汇总 P(TE)，阈值 0.5。外部输入 JSONL 的 labels 是全零占位，不是目标物种 TE 注释。参考 RM 仅供对照臂构造；未用其结果修补 P3 mask。
- 研究用五臂 runner 会要求参考臂准备完成才能运行整场实验，因此它本身还不是脱离所有研究数据即可运行的公开单臂产品入口。发布时需要一个独立 FASTA→P3 softmask 入口和准确的模型卡；不应把“五臂评测依赖”误说成“模型推理依赖”。
- P3 来源为 GENERanno 0.5B 基座与四状态 U-Net 的人类监督适配。原始 chr1/chr11/chr17-prefix 数据用于训练/验证/测试；它不是共享 NTv2 D。正式方法节应逐项引用实际 checkpoint 元数据及训练脚本，而不混用计划中的多染色体协议。
- 原 P3-R1/R2 是结构任务探索：R1 未通过全部碎片化门，R2 的对齐边界监督也未优于置换对照。改以基因注释效用为问题是合理的任务转移，但不能据此宣称边界监督机制已经被验证。

代码：[P3 导出](../../../scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py)、[外部输入与推理](../../../scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/run_core.py)、[输入准备](../../../scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/prepare.py)。历史来源：[P3-R2 结论](../../experiments/P3-R2-CLOSURE-20260830.md)。

## 主文与补充的拟议分工

| 内容 | 拟议位置 | 保留条件与解释 |
|---|---|---|
| P3 的输入、训练来源、输出和支持物种范围 | 正文方法概览，细节补充 | 基座预训练与目标标签来源明确；不写 annotation-free training。 |
| 人类面板效用 + 牛/鸭嘴兽完整五臂结果 | 正文核心 | 同时呈现 U_nosm、U_soft、P、R_TE/R_all；人类 R 来源不同，分开标注。 |
| P−R_TE 未建立优势、原人类 1% 损失门未通过 | 正文简洁陈述，完整表放补充 | 这直接限定核心应用结论，不宜只藏在仓库。不是说模型因此不能发表。 |
| 全部 loci 得失、逐 core 结果、参考支持分层、CI、版本 | 补充材料与 Source Data | 保持所有预定分母和空子集，不删困难区域。 |
| 已有 GLM 基座/窗口比较 | 按与 P3 的匹配程度筛选 | 能解释 P3 选择且任务/数据可比的最小比较可入正文；其余补充或不纳入。不可用 D 的跨物种分数证明 P3。 |
| P3-R2 边界机制诊断 | 方法来源/补充或明确不主张该机制 | 若强调四状态边界监督是创新，则必须报告对照；仅作为历史未选模型时可不展开整个路线。 |
| D 六物种、D 长序列 benchmark、D 库敏感性 | P3-only 版本可整体不纳入 | 前提是不再宣称 D 通用性/传统工具优势，不借用 D 阳性结果来支撑 P3。保留公开研究记录。 |
| Gap、MoE、聚类、分类、多 prototype、时间注释 FP rescue | 可整条留给独立后续研究 | 不列为 v1 已完成能力，不只截取各支线最好看的子结果。 |
| 库匮乏应用、独立支持的基因修正、端到端部署 | 补实验后正文 | 当前不能画成已完成的主结果。 |

## 五张主图的候选结构

1. **方法与适用范围。** 序列→P3 material mask→Tiberius；训练/验证/应用物种和数据来源。配一项真正与 P3 匹配的必要模型比较，若现有数据不足则暂不声称架构贡献。
2. **已完成的下游效用。** 三面板 F1、外部官方无 mask 与同 checkpoint 对照、RM 对照；gain/loss 小面板。所有组在同一图中，不只突出最大提升。
3. **目标库可用性的影响。** 完整/按预定规则删减的库，加 Red 与 de novo RM2→RM；展示何种条件下 P3 有实际价值。待补。
4. **哪些基因被改善。** 对全部 gain/loss 进行外部证据分层，再以预定选择规则展示典型纠错和局部损失。待补独立支持，不能只挑案例。
5. **可复用的实际应用。** 一个事先选定的外部哺乳动物全基因组、端到端成本、模型发布和复现入口。待补。若应用与图 3 重合，可合并为四图，避免凑图。

## 最多三个补充实验包（待商议，不执行）

### A. 直接检验“没有好 TE 库时为什么需要本方法”

优先复用现有 cow/platypus 固定区域和已经完成的五臂结果，增加 Red 与 de novo RepeatModeler2→RepeatMasker。再增加一种按预定物种/谱系及同源规则限制的参考库条件，以 rich-library RM 为已知资源充分的锚点；它模拟资源减少，不能直接冒充真实库匮乏物种。

主 endpoint 为参考 CDS-chain/locus F1、gain/loss，附 TE mask 覆盖及 CDS 被掩蔽情况。P3、Tiberius、阈值、区域及计分保持冻结。Red/RM2 的原生设置、建库输入和资源预算在看结果前确定：RM2 若需全基因组建库，不应为了省成本只喂很短局部输入再宣称其表现差。新增对照不是改写旧主比较；各条件完整报告。

有限停止规则：完成预定方法×条件后结束；不按得分更换物种、删减库规则或调 P3 阈值。若优势仅存在于弱对照，缩小应用主张；若与强替代方案相近但确有成本优势，可讨论有界质量/成本价值，不能用不显著差异自动宣称非劣。

### B. 将参考注释一致性提升落实到有证据的基因结构

先收集 cow/platypus 中全部变化 loci 的并集，覆盖相对 U_nosm、U_soft 与 R_TE 的 gains 和 losses；加入预定匹配的未变化 loci。使用与模型训练/选择隔离的 RNA 剪接、长读长转录本、蛋白与正交同源证据，盲于方法身份核实链结构。

主 endpoint 为有外部支持的结构修正与有外部反证的损失数量/比例；分母包括无足够证据的未定项。RNA 无表达不能等同于错误。若公开证据已被 NCBI 参考注释采用，应标记为来源共享的旁证，而不是独立真值。旧参考相对 F1 与 1% 损失门保持原样，不以新分型回写失败结果。

有限停止规则：按预定证据范围完成全部变化集合；不因支持少继续寻找新数据库直到变阳性。若独立证据不足，只保留 annotation-relative utility 的结论，不宣称发现真实新基因。

### C. 一个真实外部应用与 P3 专属成本/可用性验证

只选一个符合当前哺乳动物适用域、预先确认目标 TE 库确实有限且有可用基因证据的物种/组装。若找不到同时满足条件的数据，不以植物/真菌仓促替代，也不把人为删库叫真实匮乏。可以先用有可靠基因证据的外部组装完成全基因组部署，明确资源情景是受控模拟。

比较固定 P3、官方无 mask、Red、RM2→RM 及可得的原生 RM，使用全基因组一致分母。记录建库/推理/基因注释各阶段时间、硬件、CPU/GPU 小时、内存和峰值显存；一次性建库与重复使用成本分开。现有 D 的 CPU benchmark 不可复用为 P3 的速度结论。公开推理入口、checkpoint、参数、权重许可/获取方式和一份可复现示例。

有限停止规则：一个事先确定的外部应用，无物种逐一试到成功。第二 gene predictor 是增强可迁移性证据的选项，不是自动增加的硬性实验；只有其 mask 输入语义适合且文章要主张跨 predictor 通用性时再纳入。全基因组数量并不能替代独立生物证据。

## 投稿判断的依据

现有研究已形成真实的下游阳性结果，但“masking 有益”并非新概念。Tiberius 论文和官方用法已经讨论 repeat masking；Red 也提供无需目标库的 repeat detection。因此，面向 Nature Communications 的主要缺口是：相对强实际替代方案的独特价值、能够证实的生物注释收益及可复用的外部应用，而不是再堆模型参数或删除无关阴性结果。

Nature Communications 是目标而非当前证据保证。补充后的决定应以效应量、独立支持和适用范围为依据；若只确认有限 mammalian Tiberius 面板的平均增益，则按计算方法/应用论文定位投稿，不能靠叙事将其升级成泛物种通用突破。

## 怎样积极地写现有结果（英文示例，不替换原稿）

**A frozen human-trained repeat mask improves gene-prediction agreement on external mammalian genomes**

We next asked whether sequence-derived repeat masks could support gene prediction beyond the species used for task-specific training of the masking model. We applied the frozen human-trained P3 model to cattle and platypus, without target-species TE-library lookup in the P3 inference path, and evaluated all 40 predefined genomic cores. Relative to the official unmasked Tiberius workflow, P3 masking increased reference-locus F1 from 0.5486 to 0.6165 in cattle and from 0.5323 to 0.5892 in platypus. The corresponding paired chromosome-bootstrap intervals for the differences were positive in both panels. Comparisons using the same softmask-aware Tiberius checkpoint also showed improvement, separating mask-input effects from the complete-workflow comparison.

Native RepeatMasker-derived masks provided a strong reference condition: TE-only masking yielded F1 values of 0.6174 and 0.5917 in cattle and platypus, respectively. P3 did not establish superiority over this condition, and the experiment was not designed as a noninferiority test. Thus, these data support a downstream benefit over unmasked workflows without establishing replacement of a well-supported repeat-library pipeline. Explicit experiments under limited library availability remain necessary to determine the setting in which the library-independent inference route is most useful.

Aggregate improvements coexisted with local changes in exact reference-chain recovery. Relative to the same-checkpoint unmasked condition, P3 gained 42 and lost 7 reference-matched loci in cattle, and gained 51 and lost 24 in platypus. In the separate human experiment, 16 of 510 previously recovered loci were lost, exceeding the prespecified 1% safeguard despite a positive F1 difference. We retain these losses alongside the gains and distinguish reference-chain agreement from independent biological validation.

这一写法把阳性效应放在结果节开头，用一段交代强对照、一段交代局部得失；不需要把每个失败门变成主图标题，也不需要隐藏它们。

参考：[Tiberius](https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281)、[官方模型/softmask 说明](https://github.com/Gaius-Augustus/Tiberius)、[Red](https://pmc.ncbi.nlm.nih.gov/articles/PMC4513396/)。本稿的实验建议是根据当前证据作出的推断，不是上述来源给出的期刊录用标准。

2026-09-17 定向检索补充：作者维护的 [BRAKER4 README](https://github.com/Gaius-Augustus/BRAKER4/blob/main/README.md) 已列出 Red 作为无需建库的 softmask 选项；[OrionGeno 官方仓库](https://github.com/BGIResearch/OrionGeno) 提供从 FASTA 预测基因结构及可选 repeat 输出的接口。这里仅核实公开功能说明，没有独立复测其性能。这些先例应进入相关工作和新颖性讨论；不能声称首次从序列获得无需目标库的 repeat/gene 注释。是否增加集成式 gene predictor 作为端到端对照，取决于最终论文主张，不自动扩张当前实验清单。

## 本轮状态说明

本轮只整理已完成结果、审阅代码和文献、形成讨论方案。Baobab 的一次实时队列查询成功且未返回 jwang 的在队作业；这不替代各实验已有的完成记录。本地另有 20260917 SIB retreat 探索文件，其中 label-inclusion ablation 文档记录完成且没有总体改善；它不是本文 P3 下游验证的一部分，未纳入本次固定审阅提交，也未将其未跟踪文件混入本次提交。
