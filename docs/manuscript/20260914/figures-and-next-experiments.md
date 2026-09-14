# 图表安排与补实验建议

来源：ChatGPT 6 Pro，2026-09-14；送审 Git c6781414794c120e41f67d9b43859a4d28453065。[原对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。本文件从完整回复按章节提取；原文见 pro-full-response.md。

以下是第一轮Pro建议；第二轮执行与状态以[并行实施记录](../../experiments/DIRECTIONS-EXECUTION-20260914.md)为准。新增训练按用户要求固定单seed42；资源量级未经实测。归档应先复用现有版本、坐标和运行记录，不把新增逐文件散列作为默认要求。新实验遵守原项目的实际批准边界；报告建议不改变冻结规则。

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
| **两基座公平小对照**                 | 仅“backbone A优于B”依赖；2backbone×固定单seed42，固定坐标、呈现量、窗口、任务和校准；同时报告质量与计算成本 | GPU十小时级起，模型差异另计                                  | 相近即删优势claim，不扩成全尺寸×全窗口搜索                                                 |
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
