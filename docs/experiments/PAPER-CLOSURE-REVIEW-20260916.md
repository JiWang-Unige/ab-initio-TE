# 补实验完成情况与本轮 Pro 审阅入口

2026-09-16。本文件汇总已完成证据与尚在运行的工作，供同一 Pro 对话读取最新 Git 提交。它不是“全部实验完成”的声明。实时作业以 [持续跟进入口](PAPER-CLOSURE-FOLLOWUP-20260915.md) 为准。

## 前三项补实验已完成

1. **同 assembly/engine 库配置控制与匹配。** 相同 hg19 的 2,500 个 8,192 bp 中心窗口、相同 4,096 bp halo、相同 RepeatMasker 4.2.2。对比 2018 Dfam/RepBase 全局库与 Dfam3.9 human curated 库。年代、物种范围、curation 和 RepBase 内容仍混杂，不能称为单纯版本效应。无复用匹配有 5,540 对，两个库的 >=50%/80% 支持均在 FP 相对背景富集，但支持并非独立生物确认；strong RepeatPeps 支持在这些匹配候选中均为零。不能重标 FP 或“纠正”模型 F1。见 [结果及来源](../../reports/ANNOTATION-LIBRARY-CONTROL-20260915/RESULTS.md)。
2. **真正可训练的 NTv2 无 family 标签适配。** 末两层更新、2,000 steps、seed42，806/266/259 个 TRAIN/CAL/EVAL copy 记录；独立分组 725/240/240。六臂完整，已核实权重变化。相对原始冻结 NTv2，EVAL 内 ARI 0.236074→0.256677，但 NMI 0.615995→0.612937，TRAIN 聚类应用到 EVAL 的 ARI 0.221511→0.216809。因此不是稳定改善；TE/family 富集的上游面板也不能称为完全无监督发现。见 [完整六臂结果](../../reports/NTV2-LABELFREE-CLUSTER-20260915/run-12732191/RESULTS.md)。
3. **完整六物种分类与 ontology。** 新训练完整覆盖 TRAIN/VAL/TEST 5,400/1,440/2,160 个窗口；TEST 8,847,360 个有效位置。material F1 0.884305、main4 macro 0.833687、ontology macro 0.767866、status macro 0.630650。mouse material/main4 为 0.958057/0.849131。旧六类在同 TEST 的 main4 为 0.834947，因此没有稳定整体提升的证据。当前是 SINE/LINE/LTR/DNA broad class 加注释状态，不是 family/superfamily；BG 仍是 comparator 未覆盖。见 [分母、逐物种和逐类结果](../../reports/SF5-ONTOLOGY-CLOSURE-20260915/run-12731987/RESULTS.md)。

分类报告还保留了一个具体信息限制：三个 status 的 one-vs-rest 计数之和不是合并 Unknown 的精确混淆矩阵，只能报告精确 status micro 和二值合并范围，不能制造未保存的精确值。

## Tiberius 外部效用尚未结束

两个哺乳动物为 cow ARS-UCD2.0 与 platypus mOrnAna1.pri.v4，40 个 5 Mb core、每侧100 kb halo；五臂 U_soft/U_nosm/P/R_TE/R_all，共200cell。固定 P3/8192、原0.5阈值；主要比较 P−R_TE，辅以 P−U_nosm 等对照。参考 loci 为 cow470、platypus639，均只支持参考注释相对效用。已排除 Tiberius 的29个训练物种；不因此消除所有预训练、注释或同源暴露问题。

当前34/40core完整，恢复12738295继续；score12732548等待全部200cell后执行。不得由已完成core推断外部效用阳性。原人类 P−U F1 +0.063056、P−R 未建立优势、16/510 原正确locus损失及1% loss gate失败均保留。

## 长输入比较：已有重要阴性，仍有两项工程恢复

两个输入分别为 TE_Bench/GARLIC 派生100Mb模拟及 CB4 全基因组108.384Mb。固定D使用4096bp窗口与既有CAL阈值0.42330056285498807；五种native方法为fixed RM4.2.4、RM2 2.0.9→RM、HiTE3.3.3、EDTA2.3.0和EarlGrey7.3.0，另列D GPU/CPU，总计14cell。

- 模拟严格TE真值54,481,086bp；D P/R/F1为0.887689/0.301975/0.450648。合格fixed RM、RM2、HiTE、EDTA F1分别0.976293、0.946999、0.637386、0.844020。D CPU完整流程6h38m，本批未显示CPU速度优势。366个生成库条目全部按名称/accession被固定RM库覆盖，是已知库表示的模拟挑战；不代表新family发现，也不代表所有自然基因组。
- CB4 Label-A原生表严格TE阳性只有23个SINE条目、1,571bp，LINE/LTR/DNA均无来源阳性。D覆盖972bp、漏599bp。不能把105.4Mb未被参考覆盖的callable序列当真阴性；真实数据只支持稀疏参考召回和完整运行成本，不支持全基因组accuracy排名。fixed RM与来源同类引擎/库的100%召回不是独立敏感度。
- EDTA模拟已完成；CB4在完成TIR/Helitron后因完整LTR候选为空而未通过默认检查，保留FAILED，不加force、不计零分。
- 两个EarlGrey旧续跑曾COMPLETED，但后来核实 `RepSub` 仅在已跳过的初始函数赋值，导致最终库遗漏起始lineage。这是协议不合格，旧低分不用于方法比较。当前12739911_[0,1]恢复变量和最终RM/merge，复用原discovery、保留原预算与全部耗时。新score12739923等待两项终态，再用新bundle回放Omni。
- 旧score12738470和Omni的4job干净回放已经完成，仅能证明其block聚合算术可复现，不能补救EarlGrey库资格。旧bundle及失效原因保留，不覆盖。

详见 [长输入结果解释](../../reports/TE-LONG-BENCH-20260915/RESULTS.md)、[参考资格](../../reports/TE-LONG-BENCH-20260915/reference-qualification/RESULTS.md)、[EarlGrey修复](../../reports/TE-LONG-BENCH-20260915/earlgrey-recovery/RECOVERY.md)。

## 请 Pro 收敛回答

请实际访问本轮提供的 Git commit，读取上述源码/协议/完整结果，而非只复述本导航。分别判断“工程完成”“比较有效”“主张成立”；说明实际读取范围，无法访问就明确说未读到。

请给出可直接用于论文修订的结论、正文/补充位置、需要删除或收窄的句子，并指出会改变解释的真实漏洞。尤其判断：本轮前三项是否回答了原问题；负模拟结果和稀疏CB4参考如何影响方法定位；Tiberius未完成时有哪些结论必须等待。新增建议只限与保留的claim直接相关、确实必要的最小证据，不以所有支线变阳性或增加模型复杂度为目标。Gap不新增方案，single seed42、封存边界不变；建议不自动授权新实验。

投稿定位应区分现在与剩余已批准实验完成后；不要给接收概率或把期刊名称当实验停止规则。最终完整论文需要等Tiberius、EarlGrey及新Omni结束后再把结果填齐；当前可先完成固定范围的科学审阅与稿件结构修订。
