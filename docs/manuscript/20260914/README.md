# 论文系统梳理：2026-09-14

**最新：**[2026-09-15 第三轮最终科研梳理与投稿定位](../20260915/README.md)已完成。ChatGPT 6 Pro 通过 GitHub 连接器实际读取 `5ca4d33` 的关键源码与结果；Tiberius 已收束、真实区域 benchmark 已结束，但完整科学 benchmark、六物种分类设计修复及真正可训练 NTv2 无标签聚类仍未全部完成。新记录包括有限补实验方案、投稿定位、实际读取范围，以及从冻结 Tiberius 结果新增的 P/R gain-loss 重叠分析。下方保留前两轮历史，不把旧等待状态作为当前状态。

已完成 ChatGPT 6 Pro 的系统审阅和完整英文叙事初稿。建议论文中心为：**DNA 模型能够识别 TE-associated material，但碱基一致性、注释片段结构、生物插入实例和低风险下游操作需要分别验证。** 当前证据支持评估与机制论文；尚不支持通用 TE 注释器已经验收完成或广泛部署的主张。

## 第二轮进展

**最新补充与收敛：** hg19匹配背景和严格序列对应已完成；≥80%新版TE覆盖在双边exact序列对中为FP13.88%、匹配TN10.84%，差异主要在旧TE边界邻接片段。检索重训显示6-mer+监督对比学习可达到top1 .6426，未支持冻结GLM优于训练后的基本特征。粗分类审计发现旧1200窗口评分没有覆盖果蝇和线虫；既有前缀的四物种平衡重放现已完成，Unknown支持仅在斑马鱼，不能推断普遍漏注恢复。六物种MoE预测头pilot和海胆适配均已完成：后者提高海胆材料一致性，却损失片段指标和原六物种表现，不支持据此升级共享模型。[适配及保留性图](figures/sea-adaptation-retention-caption.md)已生成。真实固定区域矩阵已按原预算收束：11/12格有读数，鸭嘴兽RM2+RM为TIMEOUT；最终GitHub固定提交Omni重放保留全部12格及超时空指标。CPU/GPU同输入测速也已完成。Tiberius全60格与独立评分现已完成：P mask将locus-F1由0.6363提升至0.6994，P−U区间[0.0365,0.1068]；但丢失16/510个原U正确locus（3.14%）超过预设1%上限，四门联合标准未通过，按协议停止此固定问题。[Tiberius图及图注](figures/tiberius-base-mask-utility-caption.md)同时保留平均收益与局部损失。本批已启动计算已收束。完整现状以[本轮追加记录](../../experiments/DIRECTIONS-FOLLOWUP-20260914.md)、[最新英文结果段](results-addendum.md)和[新增可复现图](figures/followup-controls-captions.md)为准；下方保留此前推进过程，Pro原稿是历史审阅快照。

用户追加的八个方向已完成第二轮Pro讨论，并启动并行工程推进。最新入口是[并行实施记录](../../experiments/DIRECTIONS-EXECUTION-20260914.md)、[Pro第二轮完整可见正文](pro-round2-visible-response.txt)及[最终事实勘误](pro-round2-fact-correction.md)。后者修正内部CONF遗漏、TE_final恢复状态、hs1库版本和历史RC结果。新增训练统一单seed42，替代第一轮建议中的新增多seed；历史结果保留。

Omni最小流程已实际跑通，fragment-linking Phase0的9项测试通过；这两项都是工程验证。Tiberius修复smoke-r2作业12687393已完成，原20×3全量12694349正在运行，CPU评分及独立复算12696406依赖等待。新增hg19 chr1-only原生训练12696116及正式评估依赖12696405已启动；训练和推理接口smoke均通过。mm10新旧注释实际区间差异与chrX Unknown ontology审计已完成，见[新审计记录](../../experiments/ANNOTATION-REVISION-20260914.md)。论文草稿仍保留此前取证时的完成范围，不将正在运行的实验或toy分数写成研究结果。

后续实际执行又补齐两项证据：固定D在三个外部候选上完成GPU推理，严格类别重评分后仅鸭嘴兽有有效TE阳性分母（F召回95.93%，RC均值96.19%）；海胆/CB4标签资格仍不满足，不能写成泛化失败。天然copy检索的同面板6-mer对照已完成，k4 medoids优于single medoid但仍弱于centroid，未支持多prototype的普遍优势。Omni的RC0四臂工程流程已从GitHub固定提交、不使用dirty完成12个jobs；这不替代真实传统方法的公平比较。具体数字、分母及进行中的补充见[并行实施记录](../../experiments/DIRECTIONS-EXECUTION-20260914.md)。

新增原生NTv2 mean-pooled embedding检索也已完成：相同235个EVAL query上，centroid top1=.3234，高于k4=.2638，但低于6-mer centroid=.4255。现已制作[可复现对比图与图注](figures/identity-retrieval-caption.md)；这是探索性表示消融，没有完成contrastive训练或工具独立验证。hg19 chr1-only正式4000步训练已完成（12696116），跨染色体评估12696405及映射资格12705502随后均已完成：chr2/3/4 pooled旧注释bp-F1=.944286，93,116/97,242区间通过唯一双向等长度资格。随后固定2022 CHM13描述性重叠统计发现3,171/21,235合格旧FP区间被TE注释覆盖≥80%；匹配背景和独立确认仍未完成，不能称FP得到证实或重算F1。

海胆替代Dfam uncurated库的同区域重评分也已完成：844,932bp严格TE类注释上，冻结D的F召回=.428937，RC平均=.424200。它不构成独立生物学accuracy，但暴露了当前外部覆盖上的低召回，不能将共享模型描述为只在C. elegans较弱。具体修复和来源见[库敏感性报告](../../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/LIBRARY-SENSITIVITY-20260914.md)。

## 阅读入口

- [审阅后新增实验的英文结果段](results-addendum.md)：已完成的原生hg19跨染色体评价、映射资格、外部标签覆盖诊断和6-mer/NTv2检索比较，可供下一版论文整合；不代表Pro再次审阅。
- [完整英文初稿](manuscript-en.md)：Title、Abstract、Introduction、六节 Results、Discussion、Methods、Availability、References 和主要数字来源表。
- [中文十问决策](review-zh.md)：逐项结论、正文/补充材料取舍与最小缺口。
- [主图、补图与补实验](figures-and-next-experiments.md)：5张主图、9组补充材料及有条件的实验优先级；这是设计，图尚未制作、实验尚未执行。
- [Pro 完整回复原文](pro-full-response.md)：未经重写的完整 Markdown，保留原始建议与原对话的附件链接。
- [取证与交付记录](../../experiments/MANUSCRIPT-SYNTHESIS-20260914.md)、[当前远程状态](../../experiments/MANUSCRIPT-LIVE-STATUS-20260914.md)、[已更正证据导航](../../experiments/MANUSCRIPT-EVIDENCE-BRIEF-20260914.md)。
- [内置浏览器 Pro 对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。

## 来源和保存方式

送审快照是本地 Git `c6781414794c120e41f67d9b43859a4d28453065` 的2,882个已跟踪文件。Pro 实际完成用时46分22秒；本轮通过页面“复制回复”保存62,590字符的完整原文，再按章节提取阅读文件。原文保留文件卡片及 `sandbox:` 链接，它们只在原对话中使用；内置浏览器附件下载未落盘，不能把本地提取稿称为成功下载的独立附件或完整审阅ZIP。下载稿中特有的完整25项证据附录、核算脚本、JSON和索引没有在本地归档；本地已保存完整论文正文、中文判断、图表计划和正文主要数字来源。

这是**完整初稿，不是投稿定稿**。原稿的 `[TO COMPLETE]`、缺失图版和发布信息须处理；Methods中描述ZIP审阅的段落须改为面向论文读者的实际实验方法。Pro的资源预算和新增归档方案只是建议，不是实测或已批准的执行计划。其新增散列建议不作为默认要求；优先用已有版本、坐标、预测和运行记录回答会改变结论的问题。

## 第一轮核实的关键更正

1. `main4_conditional_macro_f1` 在全部有效六类位置上计算每类F1，再平均四主类型。BG/Unknown混淆仍贡献FP/FN；与仅限制true label的conditional accuracy不同。已修正送审导航。
2. 所选 `baseline_plus_kmer` 的leave-species contains-best=19/22，leave-clade=13/22；.6364属于其他组。源码取top2已观测真实F1的最大值，因此.007083是oracle shortlist regret，不能称已执行probe收益。
3. 当前共享D的loader为NTv2-500M H0；与历史250M recipe、GENERanno/P3和HN附加NT-logit输入保持分开。
4. 从D六物种原JSON重算：3,000 tiles、24,541,946 callable bp、7,452,597 positive bp；物种macro bp-F1=.8887612459、run-F1@IoU.8=.4458837761、IoU-qualified joint-boundary-F1@5bp=.2043614175。六物种均参与训练。
5. 第一轮Tiberius smoke 12652888为工程FAILED，`BASE_MASK_OBSERVATION`缺失；后续12687393修复重跑已通过，完整20core×3仍无最终结果。旧C无新增正确链是另一已完成科学结果。

## 下一步取舍

优先补齐支撑正文的已有结果与版本记录（包括HN完整frontier），再完成一个当前D与传统完整workflow的同实例比较。要保留未见物种泛化、高效部署或基因注释改善的主张，分别依赖合格独立panel、代表性CPU/GPU性能实验、原Tiberius U/P/R协议结果。无需默认做MoE，也无需为这篇机制论文重开已关闭的HN阈值或旧C路线。

第一轮交付时没有启动新训练、推理、benchmark、Tiberius修复或作业重提；后续实际执行更新见上方入口。原冻结规则保持有效。origin为public；用户随后明确允许推送，`2adbcba`及包含本轮主要源码的`1d4bcfa`、Omni GitHub配置`48cfb5d`均已推送并核对远端。Pro的原始回复和附件是当时快照，不能当作对本轮新运行结果的再次审阅。
