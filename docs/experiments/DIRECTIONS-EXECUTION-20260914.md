# 新方向的并行实施记录

2026-09-14。第二轮 ChatGPT Pro 对话：[科研梳理与论文初稿](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。完整方案已取得；可见正文归档为 `docs/manuscript/20260914/pro-round2-visible-response.txt`（22,515字符）。页面曾显示服务错误，复制按钮失败，因此使用已显示正文保存；表格和公式的纯文本排版可能丢失，数学解释以原浏览器显示及下方规范化记录为准。随后Pro已读取三份新增取证附件，完成最终[事实勘误](../manuscript/20260914/pro-round2-fact-correction.md)。本文记录本轮判断与实际推进，不把咨询当实验结果。

## 当前优先级

论文核心补证据是固定共享模型的外部评价、同输入传统方法比较和下游效用。历史标签修订与 fragment association 是可以独立成立的研究问题。RC、双GLM、contrastive 和多prototype采用有限消融；不要求所有支线阳性才能完成论文。

所有新增训练采用预先固定单 seed42；既有多seed结果保留，空间/拷贝单位不确定性不冒充初始化方差。旧失败只约束原问题，不自动否定新问题；新问题也不允许改写旧门或把封存测试变成调参集。

| 工作线 | 第一轮具体动作 | 对照/评价重点 | 当前边界 |
|---|---|---|---|
| D外部泛化 | 固定seed42 checkpoint与已有CAL；鸭嘴兽/海胆/CB4各4×1MiB固定区域 | 每物种及最差物种；区分比较注释一致性、独立accuracy、pretraining与TE监督暴露 | GPU12696615三组推理已完成；按明确TE类别核对并重评分，有限面板不等于whole-genome通用验收 |
| adapters/MoE | 新协议中先做dense/coverage目标与同参数adapter对照，证实专家互补再有限MoE | 监督适配与zero-shot分开；路由不读目标F1；计算量、每物种损益及router collapse | 尚未训练；若外部结果指导架构，那个panel转为开发证据，不再宣称未触碰的最终测试 |
| 注释版本与FP | 同assembly旧/新注释资格审计；原生GLM hg19 chr1训练和固定跨染色体评估 | apparent-FP、匹配背景、TP/FN全分母；独立支持比例与剩余未解；mapping失败保留 | mm10实际改变已确认；CHM13 2022注释与4chains已取得；hg19训练12696116进行中，评价12696405依赖等待；尚无FP rescue |
| Unknown | 保留原六类混淆矩阵，独立核对ontology，再复核Unknown→main4/Unknown/BG | `.3886`是预测Unknown召回；重分类正确性需独立证据 | chrX90条历史Unknown中85条为SVA/Helitron等被既有映射合同折叠的具名类；不是85条人工漏注，更不证明model family正确 |
| Tiberius效用 | 原批准20core×U/P/R；smoke-r2→full→CPUscore→独立NumPy复算 | 固定输入六通道、exact complete-CDS gene-locus终点与原门 | smoke12687393完成；full12694349进行中；score12696406依赖等待。独立复算已实现并通过fixture，实际60cell结果尚未完成 |
| RC/strand | 当前D先做正向/RC映射诊断；有限augmentation/consistency消融 | material输出在RC下映回原坐标；方向型输出保持等变；匹配曝光及成本 | 历史mouse NT推理合并已经存在，新RC训练未做 |
| 双GLM互补 | 重用历史错误分型，为局部风险或pair关联提供第二源特征 | 单源同容量、简单融合、学习融合；材料与关系终点分开 | HN有ranking增量但whole-gap动作无可用点，不重扫旧阈值 |
| Fragment linking | Phase0合同及Phase1距离/规则/轻量pair学习器工程对照 | 候选召回、pair PR、误融合、闭包错误；输出edge不填gap | Phase1的5项测试通过，受控样例36fragments/19pairs；尚无自然插入恢复结果。M2/M3下一步可用真实copy半模拟输入做机制实验，再验证自然样本 |
| Dfam contrastive | 42个历史文件已恢复；同panel强k-mer对照和真实split先闭合 | coarse class与family分开；family标签参与contrastive不是全无监督 | Phase7强B1无raw闭环；consensus exp002无找到的完成指标，不合并不同panel |
| Multi-prototype | 同一TRAIN集合single medoid、k4 medoids、random4、centroid，以及公版Dfam consensus参照 | 精确repName、source interval/相似性组件隔离；CAL固定pair误接纳预算；公版consensus来源另列 | 1600天然区间/40标签已抽取；共同29标签235query真实6-mer检索已完成。k4 top1=.3191、single TRAIN medoid=.2766、centroid=.4255、公版consensus=.6000；不足以支持通用工具或“多reference必优” |
| Omnibenchmark | 一个小型fixture→现有converter→T0/T1evaluator→collector真正执行 | canonical坐标、truth tier、失败/unsupported分母；不以dry当成功 | 0.6.0真实host执行完成6个jobs；T0/T1及collector通过，详见OMNIBENCHMARK-SMOKE记录；真实方法矩阵/CPU-GPU速度未完成 |

## 论文定位

正文优先呈现：基础TE-material结果、受控模型/训练设计差异、合格的外部迁移、同输入传统比较；Tiberius达到原终点后可加入效用结果。注释修订若有独立候选支持及完整分母，可形成独立结果段，措辞为回顾性注释支持，不能称真正时间前瞻或所有FP都是真TE。

窗口、RC和结构失败的有界消融放补充，并在正文解释影响主结论的局限。Fragment linking只有从受控真值走到可靠真实样本后才上升为生物学结果。Contrastive、多prototype先作为检索/表示研究；若独立性或效果不足，保留补充或后续工作，不把它们包装成通用家族注释工具。

## Pro 讨论后的具体收敛

接受Pro建议，将工作组织为三条科学线：标签与material检测、fragment association、家族表示/检索；Omni和Tiberius作为公平比较及效用支撑。主线不等待MoE，也不要求所有支线都阳性。

- **历史注释：** 从原生pretrained GLM重新开始TE任务训练，不能使用已经监督见过其他染色体/新版标签的D/P3/H0 checkpoint，却声称只学过hg19一条染色体。后续用户授权执行后，已按[具体固定协议](HG19-CHR1-REVISION-20260914.md)落实chr1 TRAIN、chr11 CAL、chr13 DEV、chr2/3/4 EVAL 20.48Mb；两步训练与小型推理接口均通过，正式4000步运行中。独立作业12698548确认六条允许染色体的有效TE/ignore材料标签与UCSC2009初始注释完全一致；仅repFamily表示不同，完整原始记录不完全相同。chr16/18保留效用用途，chr19–22及跨版本对应区域保留封存。GLM预训练暴露仍未闭合，当前实验也不构成真实时间前瞻。
- **完整分母可能改变直觉：** 若旧TP/FP/FN为 $T,F,N$，新版新增阳性中 $a$ 来自旧FP、$b$ 来自模型未预测背景（暂不含阳性删除），则 $F1_{new}=2(T+a)/(2T+F+N+a+b)$。因此新版支持若同时引入很多新FN，F1未必上升。先测“旧FP独立支持相对匹配背景的富集”，再量化整体影响，不能先宣布F1被低估多少。
- **第二物种：** mm10资格作业12693564已完成：明确TE的Current独有6,124,486bp、Baseline独有10,431,606bp；Current总覆盖略低。官方轨道显示软件与库版本共同变化，所以它是实际同assembly注释修订候选，不能称library-only因果对照或预设F1提高。详见[实际审计](ANNOTATION-REVISION-20260914.md)。小鼠属于D训练物种，不能用来证明D的zero-shot物种泛化。
- **RC与融合：** RC四臂包括F、映回的RC、二者均值和两个正向分词相位/切窗均值；先投影bp再映射。新轻量融合的训练预测必须来自底层模型未做任务监督训练的坐标或真实out-of-fold，避免stacking泄漏。对当前D与P3的比较是系统互补，不单归因backbone。
- **Linking：** 单一insertion ID不适用于跨host/nested/background的混合fragment；真实输入应标ambiguous/多身份，不用truth偷偷切纯片段。背景误报的两个空ID不得算same。Phase0目前只证明受控合同；下一阶段还需要host locus、source-copy、homology组件共同隔离及真实curation。
- **Multi-prototype：** 已落实40个精确repName各40天然区间；29标签能精确匹配公版Dfam consensus，11个缺失标签不做宽泛family替换。真实作业12698062及同TRAIN单medoid补充12698524已完成。k=4与single TRAIN medoid构成同来源6-mer容量对照，公版consensus仅是外部reference参照，不能把它与train-only arm差值全归因于表示方式。所有方法采用相同CAL **pair**误接纳预算1%；它不保证top1 query误接纳率或被接纳查询的错误率≤1%。当前GLM/HMM未运行，不否定其潜在效果，也没有达到工具发布依据。详见[检索记录](TE-IDENTITY-RETRIEVAL-20260914.md)。
- **资源与范围：** Pro的77格benchmark、20Mb计时panel、人工盲审样本量及新效应门都是建议，不自动成为已冻结协议。采用版本/既有manifest和实际输出记录；不按Pro模板额外增加无决策作用的hash体系。原Tiberius终点、bootstrap和科学门保持原协议。

## 已交付事实与来源

- `DIRECTIONS-READINESS-20260914.md`：现有结果与Tiberius现场状态；本轮修正了旧DEV状态字段导致的CONF遗漏。
- `TE-FINAL-DFAM-RECOVERY-20260914.md` 及同名reports目录：远端恢复证据。
- `ANNOTATION-REVISION-ASSETS-20260914.md`：组装、注释版本与可用新版官方来源。
- `DIRECTIONS-SOURCES-20260914.md`：候选第二物种、RC、RepeatCraft和library表示的一手来源。
- `OMNIBENCHMARK-PLAN-20260914.md`：完整方法/任务矩阵与最小接入。
- `OMNIBENCHMARK-SMOKE-20260914.md`：实际Omni 6-job执行，独立核对T0 TP/FP/FN=19/4/1，T1 precision/F1为空，5个预期cell保留。UNSUPPORTED/BLOCKED为专用合成状态，非真实工具能力结论。
- `FRAGMENT-LINKING-PHASE0-20260914.md`：9项测试与样例结果；候选未覆盖的真pair、跨split排除、transitive误合并分别保留。
- `DIRECTIONS-PRO-FACT-UPDATE-20260914.md`：送给Pro的本轮纠错，不覆盖原送审记录。

## Git与Pro访问

Pro页面已实际报告读取公开GitHub main `3891293dc3ec7de3e90d167b21ce24c97537c169`；较新的本地 `05f393d` 和后续材料由附件提供，不能把Pro此前读取的旧版本当作当前最新状态。2026-09-14用户随后明确表示“允许推送”，并要求开始推进已审阅方向。已将 `2adbcbab1b1329fa0d8f236f18b0ea916fef10e5` 推送到 `origin/main`，远端引用已核对；本轮代码、配置和紧凑结果继续在此授权范围内提交。原始序列、权重和集群运行大文件保留Baobab。没有声称Pro已经再次读取本轮新提交。
