# 当前论文结果与收束决定

2026-09-17。本表以作者最新九项主线为准；本轮已在内置浏览器与 ChatGPT 6 Pro 完成讨论。Pro读取的是当时GitHub固定提交；新增HPC结果由本项目原生输出支持，不能称Pro独立验证。

## 论文主线

**从DNA表示获得TE材料及类别信息，在明确适用域内形成不依赖推理时TE参考库的注释流程，并测量其对基因注释的用途。** 当前不使用“通用动物模型”“已解决TE插入重建”或“全面优于传统软件”作为中心结论。

binary材料检出与broad-class分类回答不同问题：Tiberius只需要材料mask；TE map还需要类别及来源状态。当前D（NTv2）、SF5（GENERanno）和P3（GENERanno人类模型）的训练与输出不同。可以写成两个明确模块或并列模型，不能把三者拼成一个模型的最佳性能。

如果把D和SF5串接为一个部署流程，监督物种并集是八种（D额外有人/猪，SF5额外有蛙/果蝇）。因此“蛙是D的监督外物种”不能变成“蛙是整套D+SF5流程的监督外物种”。当前先分别报告已有两模型；不能在没有端到端运行、成本及错误传播结果时宣布整合TE map已交付。

## 九项主线的实际状态

| 作者主线 | 当前实际结果 | 论文安排与剩余任务 |
|---|---|---|
| 1. 基座、参数量和窗口 | 已找回四基座×五窗口20个quick-screen单元、495行NTv2/v3迁移矩阵，以及TE_final的hg38正式三基座结果 | 正文用同协议主表；完整尺寸/窗口矩阵放补充。不能跨协议排名“最佳model” |
| 2. 预训练已含TE信息 | 旧Dfam/片段结果存在；本轮NTv2同样本配对已完成 | 用readout/cluster分别回答。没有随机或组成对照时，不写成已证明预训练机制 |
| 3. 六物种模型外部泛化 | D六物种DEV已完成；已有鸭嘴兽/海胆/CB4外部结果；本轮蛙/蜂/甲虫固定screen完成 | 完整报告参考覆盖及最弱物种。不能称独立全基因组泛化已闭合；先完成合格外部面板，再决定adapter或MoE |
| 4. 标签、库和序列证据 | hg19匹配对照、库扩展、历史human-library RM、长输入模拟均有结果；本轮192窗口组成保留干预完成 | 组织成“标签来源和序列结构如何影响测量”，不组织成“所有FP其实是TP”或“已经排除记忆” |
| 5. embedding解释 | NTv2 pretrained→D和GENERanno pretrained/binary/SF5三权重的同基座配对均完成 | GENERanno类别微调的读出与类别几何均改善；NTv2几何不是全部改善。完整状态保留，Known/TE-only单列，不称已排除记忆 |
| 6. 多分类TE map | 当前SF5全2160窗口结果及完整/已知/条件TE重新计分完成 | 正文报告端到端完整分母；条件分类放解释图，不当成检出准确率；四大类不称细粒度family |
| 7. Tiberius应用 | P3在人/牛/鸭嘴兽已有结果；本轮追加固定D在鸭嘴兽20core的同对照实验 | D结果不能借用P3。当前非哺乳vertebrates/insecta模型不消费softmask，需另有合格接收器才能测此用途 |
| 8. 公平benchmark | fixed RM、RM2→RM、HiTE、EDTA、EarlGrey与D的100Mb模拟/完整CB4有限比较已闭合；13合格+1原生失败；CPU资源匹配，GPU单列 | 当前真实参考太稀疏，真实准确率排名仍缺证据；Omnibenchmark已回放评分图，不等于所有原生caller均已移植 |
| 9. 可用模型与代码 | 独立可安装FASTA接口、相对bundle、真实序列notebook和模型卡已准备；CPU/GPU真实权重loader parity均通过 | 新GitHub/HF权重尚未发布；当前研究仓库保存代码和结果，最终模型确定后导出 |

## 本轮已经得到的新数值

**NTv2表示配对。** 相同512-bp序列、train/val/test为1843/809/1580，排除padding和特殊token后mean pooling。监督5-NN macro-F1：Known五类0.4885→0.6394，完整八状态0.4730→0.5944，条件TE四类0.6342→0.7197。无监督K-means的Known五类ARI为0.0386→0.1105，完整八类0.0623→0.1096，条件TE四类0.0713→0.0424。因此不能把监督提升改写为无监督family发现已成功。SIB已被观察，encoder训练坐标及同源暴露未完成审计，定位为配对表示诊断。见 [报告及图](../../../reports/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477/RESULTS.md)。

**GENERanno三权重表示配对。** 同一1580条TEST记录，pretrained→binary FT→multiclass FT的监督5-NN macro-F1：Known五类0.3654→0.4329→0.7674，完整八状态0.2748→0.3123→0.6857，条件TE四类0.4746→0.4990→0.9030。条件TE四类的K-means ARI为0.0417→0.0693→0.2429，类别微调后几何与读出均改善。预训练binary readout只有0.5221，不能写“微调前已很好分开TE/BG”。binary FT为human-only，class FT为六物种，因此不能把差异只归因于loss。保留全部状态和唯一的全N/BG测试窗口；同源拷贝隔离未闭合。[报告与图](../../../reports/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/RESULTS.md)。

**外部动物screen。** 固定D和同一CAL阈值，每种预定4×1MiB。蛙参考阳性1,390,306 bp，恢复率0.885797，参考一致性F1为0.837062；蜂637阳性bp、恢复率0.857143；甲虫3,622阳性bp、恢复率0.579514。蜂和甲虫没有充分负类，不能报告其生物学precision/F1。三者不是新的盲法确认种。见 [报告](../../../reports/ANIMAL-GENERALIZATION-CLOSURE-20260917/RESULTS.md)。

**SF5分母重评分。** 完整八状态上的main4 macro-F1为0.833687；只按参考排除ambiguous/unclassified后为0.838882，保留98.2471%的位置。条件true-TE四类为0.902870，但这个分母不能测量全基因组检出precision。删除未知状态带来的总体变化很小，不能把它当作分类性能问题已由映射完全解释。见 [报告](../../../reports/SF5-READOUT-CLOSURE-20260917/RESULTS.md)。

**序列干预。** 6物种各32个固定D DEV窗口。只打乱BG且保留TE序列及二核苷酸组成时，物种pooled recall变化为−1.50至+0.53个百分点；21/192个窗口绝对变化≥10个百分点。打乱TE内部二核苷酸顺序后，原TE位置预测阳性大幅减少。该结果支持局部高阶序列敏感性与异质上下文效应，不能证明具体进化机制或模拟低召回的主要原因。见 [完整分布](../../../reports/D-CONTEXT-PAIR-20260917/RESULTS.md)。

**可部署入口。** GPU真实权重合成序列smoke逐碱基概率最大差7.77×10⁻⁹，mask一致。另完成CPU作业12853594：固定取human DEV前两条4096-bp记录，预测阳性3,418/8,192 bp，新旧loader的margin、概率、mask和softmasked FASTA完全一致；总作业43秒，不是速度benchmark。真实序列已放入便携包供notebook复现。两次smoke均不作为生物学准确率证据。见 [报告](../../../reports/PORTABLE-D-SMOKE-20260917/portable-d-release-candidate.md)。

## 正文与补充材料

| 正文结果节 | 正文主要图 | 补充材料承担的内容 |
|---|---|---|
| Model selection and the annotation workflow | 同协议基座结果、binary/class输出接口及模型身份 | 完整窗口/参数矩阵、所有历史protocol差异 |
| Task adaptation changes the accessibility of TE information | 同基座、同样本readout配对；聚类结果分别标明 | 完整状态、各物种、旧contrastive/k-mer对照及训练暴露 |
| A fixed shared model transfers across evaluated animal panels | 固定流程逐物种与参考覆盖 | 稀疏positive-only、worst species、全部诊断arm与未支持类群 |
| Annotation provenance and sequence organization shape measured performance | 库覆盖与模型漏检并存、组成保留干预 | hg19背景匹配、human-library旧对照、完整干预分布 |
| Quality and cost under defined benchmark conditions | 合格真实输入上的质量/成本；模拟作为边界 | 全工具、知识条件、CPU/GPU、原生失败、模拟低召回和评分回放 |
| TE masking supports gene annotation with a compatible receiver | 同一最终材料模型与固定gene模型的配对用途 | P3历史、所有gain/loss、各core、接收器资格、部署notebook |

不是每个探索分支都必须进正文。已放弃的Gap算法细节、低信息量的工程尝试可以不展开；但影响主张成立的物种、对照和结果仍放补充或限制。模拟失效不能只解释为“模拟不真实”，Tiberius相对未mask的改善不能改写为已经胜过合格RepeatMasker。

## 剩余工作的优先顺序

1. 完成本轮已启动的D自身20core下游用途；GEN三权重表示配对和CPU部署smoke已完成，保留全部方向。
2. 冻结一个有限、证据合格的外部确认面板，优先补非哺乳动物与库覆盖不足对象。已有古老稀疏UCSC昆虫标签不能单独承担这一确认；先按assembly、标签独立性和项目历史资格选择，再运行。候选名单及规则见 [收束方案](multispecies-closure-plan.md)，不是按分数搜索物种。[候选资产资格审阅](external-panel-reference-qualification.md)已完成：青鳉/家蚕有条件性资产，但尚无独立完整真值；oryLat2旧assembly与2017 RefSeq assembly不能混配。尚未冻结或运行新的确认面板。
3. 若主张“缺乏合适库时帮助基因注释”，需要在同一目标输入上明确限定库知识条件，并与合格同库/异库或库缺失对照配对；当前P3改善未mask与D推理时不读库是支持线索，尚不等于该因果主张完成。
4. D若在开发面板出现稳定、可定位的跨类群缺口，才进行共享adapter/专家对照。没有专家互补证据就不追加MoE。模型变化后，最终benchmark与下游必须补该模型自己的行。
5. 最终输出流程和适用域确定后，导出新GitHub与HF权重、真实序列notebook和可迁移benchmark命令。NTv2权重许可与代码许可分开。

本稿停止新增Gap方向、跨kingdom首训、基座网格和多seed扩张。可以以“有明确适用域、可复用且有下游用途的TE注释方法”收束；是否达到Nature Communications需要看独立外部及下游证据闭合后的实质贡献，不能仅根据已有几张高分表判断。
