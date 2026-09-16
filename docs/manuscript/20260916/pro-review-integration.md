# Pro收敛审阅：结论与本地采纳记录

2026-09-16。审阅对象固定在`34bb71c7f7697671710d6c06d6b4353086211c58`，来源为[原Pro对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。以下是Agent整理及核对，不是第三方审稿决定。

## 稿件取舍

| 研究线 | 保留的结果 | 位置 | 不支持的主张 |
|---|---|---|---|
| hg19库配置控制 | 同FASTA、halo、引擎下的库配置敏感性；高覆盖层上匹配FP有描述性超额支持 | 正文；全匹配/蛋白支持补充 | 单独年代效应、独立FP证实、改标或F1纠偏 |
| NTv2无family标签适配 | 末两层确实更新；收益依赖端点，未稳定胜过raw NTv2/k-mer控制 | 补充，正文一句 | 完全无监督发现、通用表示优势、物种留出 |
| SF5 | 完整六物种窗口与显式class/status结果 | 补充，Methods定义标签 | 仍只有四物种的旧说法、真正superfamily工具、ontology的因果性能提升 |
| 长输入benchmark | 固定D模拟召回不足；完整CPU流程无观察到的优势；CB4参考不足以全基因组排名 | 模拟阴性正文，完整成本/失败补充 | 普遍准确率或速度优势、新family测试、真实precision/F1 |
| P3/Tiberius | 已完成的人类平均收益与原正确locus损失；外部结果尚待完整评分 | 核心正文 | 把P3阳性归给D、优于/等效RM、原低损失门已过 |
| Gap/linking | 材料、结构、关联和用途的证据边界不同；保留有限阴性 | 必要机制正文，其余补充 | gap已解决或真实insertion recovery |

前三项结束不要求原先的强假设被支持。模拟的构造材料真值直接显示漏检，不能用CB4自然参考不完整来解释模拟FN。D阴性与P3阳性不矛盾，但两者不属于同一模型。论文主线的箭头表示评价层次，不能冒充已经证明的因果链。

## 会影响解释的具体问题：已本地核实

1. **库支持字段的分母不同。** `control.py`第497–507行中，`difference_pp`只用匹配pair，而`fp_supported`统计包括未匹配在内的全部候选FP；`fp_fraction_of_all_cases`也有自己的全候选分母。不能统一除以5,540。当前已发表到仓库的匹配差值来自正确的`difference_pp`，无需重算或改标签；在结果文档追加字段说明，后续作图按该说明取数。
2. **“容量匹配”只匹配投影头。** metrics中的k-mer head为1,081,728参数，扩大后的冻结NTv2 head为1,081,642；可训练NTv2末两层另有33,570,816参数。这个对照没有匹配encoder更新臂的总可训练参数，不能声称已完全隔离微调的额外容量效应。结果表名与正文现明确匹配对象，不追加训练。
3. **唯一对照不等于独立样本。** 5,540对仅覆盖21,235合格FP中的约26.1%，15,695未匹配仍保留；空间/同源相关与可匹配子群选择性未自动消失。报告描述性差值，不补造显著性。
4. **SF5 pooled class macro不是species macro。** 0.833687先汇总全部位置，再平均四个大类F1。material合并全部非BG标签，包括ambiguous/unclassified。原结果已说明，该定义继续保留。
5. **Tiberius对照的因果含义不同。** P−U_soft是在同一个softmask-aware checkpoint中改变mask；P−U_nosm还更换checkpoint，是完整流程比较；P−R_TE才是预定同语义mask主比较。不能拿其中一项替另一项。

## 当前投稿定位

Pro建议以Mobile DNA或BMC Bioinformatics的受控评价与应用边界研究作为现实候选。Agent本轮另外核对官方scope：Mobile DNA覆盖TE研究及相关生物计算工具；BMC Bioinformatics覆盖计算模型、软件、ML与序列分析，强调清楚研究问题及科学有效性。[Mobile DNA](https://link.springer.com/journal/13100/aims-and-scope)、[BMC Bioinformatics](https://link.springer.com/journal/12859/aims-and-scope)。这是主题适配判断，不是接收保证。

若外部预定P−R_TE出现可信效用增益，可重新评估Bioinformatics的适配性；仅增加实验数量或P−U阳性不会自动形成算法创新。该刊对新方法要求真实数据上的既有方法比较、独立评价及序列同源处理。[Bioinformatics scope](https://academic.oup.com/bioinformatics/pages/scope_guidelines)。不为维持某个期刊目标扩张实验。

## 剩余工作

Pro审阅时EarlGrey恢复、新评分及Omni仍待完成。审阅后的现场证据已经补齐这部分：12739911两输出资格通过，score12739923与新Omni均完成，13合格完成+1项CB4 EDTA原生失败。旧EarlGrey遗漏库分数不进入排名；EDTA保留null，不加force。剩余仅为外部Tiberius完整200cell后的固定评分，以及稿件/图表/可用性整理。

外部Tiberius最终须逐物种、按染色体重采样、保留gain/loss和参考支持限制。牛470参考loci中220含NM；鸭嘴兽639无NM，其相应空子集应为null。新外部结果不能改写人类16/510损失及原1%门失败。Gap不新增；single seed42与封存范围保持。

结束条件是所有已批准运行达到可解释终态、稿件与证据一致，而不是全部支线阳性。benchmark冻结执行已完成；外部Tiberius仍未完成。替代score12740044已按afterok12738295提交，旧score12732548的UID0取消记录保留，原因未知。
