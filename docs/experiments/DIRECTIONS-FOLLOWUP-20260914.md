# 追加实验与结论收敛

本轮承接用户提出的六个问题：脊椎动物结论与 MoE、FP 匹配核实、k-mer 重训、分类映射、Gap/下游效用和 benchmark。只用 seed42 开展新的模型实验；历史结果和 sealed 区域保持原合同。

## 当前可说到哪里

五个参与训练的脊椎动物在内部 DEV 的 bp-F1 为 0.832–0.942。这个范围支持“已测试的训练物种内部表现”，不支持所有脊椎动物。外部鸭嘴兽四区域的已标注 TE-positive bp 召回为 0.9593，但 LINE/SINE 占主要分母，DNA 约0.1845、LTR 约0（仅10条记录）；整体高分不能掩盖类别弱项。海胆另一个 uncurated-library comparator 上的召回为0.4289，缺少独立负例，不能说其绝对 F1 低于鸭嘴兽多少。

“传统工具也可能受 library 覆盖、类别和进化距离影响”是合理待检验解释；现有结果同时显示 library 缺口和模型在新增 comparator positives 上的漏检，不能用前者消除后者。无脊椎动物不是统一的进化域，当前只有少量固定区域，不能归因于整个类群的共同进化路线。

MoE 先做有限开发对照：固定 D encoder，比较相同CAL重新校准D、dense residual adapter、双专家 gate 和固定平均专家；另保留原D完整CAL参数在同一DEV子集上的描述性对照。相同训练数据/预算、每物种指标及 worst-species 都保留；这只是预测头专家模型，不称为完整GLM稀疏MoE。海胆区域1/2用于适配TRAIN、3用于CAL、4用于探索性EVAL时，要明确该面板已看过且不再是zero-shot证据。

首轮六物种作业12708683已完成（19分22秒，P100，seed42）。在各物种各32个固定DEV tiles上，四个同CAL流程和历史参数对照的结果如下；它们不能直接与原500 tiles/物种的全DEV数字比较。

| 预测头 | macro bp-F1 | 最弱物种bp-F1 | macro segment-F1@IoU0.8 | macro boundary-F1@25bp |
|---|---:|---:|---:|---:|
| 原D，历史完整CAL参数 | 0.876984 | 0.750981 | 0.454633 | 0.391215 |
| 原D，同子集CAL重新校准 | 0.878221 | 0.756681 | 0.446629 | 0.383899 |
| dense residual adapter | 0.878234 | 0.756263 | 0.444525 | 0.382054 |
| 双专家soft gate | 0.879017 | 0.762329 | 0.401691 | 0.345218 |
| 固定平均双专家 | 0.878389 | 0.756263 | 0.444119 | 0.382775 |

门控相对D重新校准的平均bp-F1仅增加0.000795，最弱物种（本子集为chicken）仍低于0.8，片段与边界指标下降。当前不据此扩大MoE；该结果也不等于否定所有MoE结构。海胆单物种适配继续作为有限对照，并报告在原六物种上的保留性，不能称七物种通用模型。[完整指标](../../reports/D-ADAPTER-MOE-PILOT-20260914/main-summary.json)

## 已完成的补充

- **ontology与漏检分层**：12708396完成。六ID train/val/test编码及metadata一致。Known-other TE没有误入BG，但被合并入Unknown；没有标注的区域会编码为BG。补充了外部各class、长度、divergence、区域和原始类别的保留分母。[审计结果](../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/RESULTS-20260914.md)
- **k-mer与投影重训**：12708302完成。长度4/6/8的centroid top-1为0.3872/0.4255/0.3915；k=4 prototype数和k-mer长度已明确分开。NTv2监督对比投影的centroid top-1/macro-F1由0.3234/0.3103升到0.5106/0.5048；235个已见EVAL中130个accepted，accepted accuracy0.7231，不是可保证99%准确的工具。[详细结果](TE-IDENTITY-RETRIEVAL-IMPROVE-20260914.md)
- **CPU/GPU同输入前向测速**：CPU12696616与GPU12708296全部完成。同1MiB和batch12，CPU第二次前向733–758秒，TITAN X/P100为31–34秒；各硬件与加载时间另列，不能当传统端到端工具速度或整基因组外推。[测速结果](../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/CPU-GPU-TIMING-20260914.md)

监督投影改善还需区分表示与目标函数的贡献，因此完成固定三臂控制12708540：L2 6-mer+supcon、L2 NTv2+supcon、L2 NTv2+cross-entropy，均50epoch、128d、同TRAIN/CAL及seed42；CAL选epoch，既往EVAL只算最终结果。top-1/macro-F1依次为0.6426/0.6057、0.5064/0.4994、0.2809/0.2687。6-mer投影参数量更大，CE结果仅是其投影后centroid检索，不是充分调优的分类结果。这否定了用“raw→trained NTv2提升”独自证明GLM胜过基本特征的解释。[图及完整限制](../manuscript/20260914/figures/followup-controls-captions.md)

## 匹配背景、序列对应与分类修复

FP匹配和adapter回答不同问题。前者检查被旧注释标记FP的区域是否在严格对应序列上、相对同背景TN更常获新TE注释支持；后者检查外部预测是否能适配。FP任务固定原模型、阈值及全TP/FP/FN/TN分母，核实内部chain无gap/indel、正反向对应、hg19与CHM13序列。匹配仅用旧source染色体、精确长度、GC、非ACGT、旧TE边界关系和距离，完成后才接入新版注释支持。[预先固定规则](HG19-CHR1-REVISION-20260914-MATCHED.md)

分类方面，六类结果可以作为既定编码合同下的结果，但以下扩大解释不成立：Unknown高分代表人工漏注、预测出了SVA family、或完成广泛superfamily注释。LINE/SINE/LTR/DNA是粗粒度类别，并非L1/Alu等具体family/superfamily。现有nonsealed资产缺逐位SF5预测，不能凭aggregate反推出新ontology confusion。下一版标签应保留raw class/family，并分开main4、known_other_TE、ambiguous、true_unclassified与明确nonTE；未知区域不能自动充作经验证负例。已有六类指标保留便于复现，新的分类主张需要对应输出头与独立评价标签。

新增实际分母复现12708568已完成：旧SF5两个模型仅按文件顺序评分前1200个test窗口，实际为mouse/zebrafish/chicken各360和frog120；没有fruit_fly/c_elegans。val也省略了c_elegans。这是评价覆盖缺口，不能只凭完整数据集metadata一致就说六物种分类评价完整。已开始限定在旧已评分前缀内的平衡重放，每个上述物种120窗口，保存逐位置预测和分物种混淆；不为补齐分母而自动开放新held-out物种。

hg19匹配已完成12708406/12708553，严格双边exact-ACGT序列分层12708578也完成。18,079对的≥80%新TE覆盖为旧FP13.88%、匹配TN10.84%；孤立片段仅17.52%对16.77%，差异主要在边界邻接片段。只支持注释版本/边界敏感性的描述，暂不支持广泛FP救回或F1校正。控制复用最高775次，不能将pair数当独立重复。[完整结果](HG19-CHR1-REVISION-20260914-MATCHED-RESULT.md)

## 仍在计算的方向

Tiberius固定U/P/R全60格任务12694349运行，12696406依赖后评分；必须完整结果及独立重算通过后才判断下游效用。Gap已有fragment linking工程验证不能提前写成真实insertion恢复。

Benchmark新增真实native矩阵12708424_[0–8]，三物种固定四区域×RM、HiTE、RM2+RM；同输入但属于real-region feasibility/T2，不是全基因组排名。原D三格纳入共12格固定registry，保留失败和空library；Omni导入/收集成本与Slurm实际caller成本分开。[当前实际接入合同](TE-REAL-PANEL-BENCH-20260914.md)

真实部分snapshot12708689已由GitHub固定提交b75ebfa、无dirty模式完成4个Omni jobs：12格中4格有结果（3个原D+1个HiTE），2运行、6无产物；失败/缺失不折算零分。[真实Omni读数](TE-REAL-PANEL-BENCH-20260914-OMNI.md)

六物种adapter/MoE主试验12708683已完成并收回结果，见上表。海胆适配12709012完成TRAIN/CAL/EVAL为256/128/128 tiles的标签物化和TRAIN/CAL特征提取后，因单个全masked训练tile退出；此前12708891因坐标体系不一致而取消。两次均无最终模型结果。已修复坐标、无损失步处理及单物种CAL传参，CPU回归12709166通过后，按原配置重提12709175，保留独立失败记录和输出。海胆各臂使用同一新mask，并报告原六物种保留性，不称zero-shot。[适配协议与记录](D-ADAPTER-MOE-PILOT-20260914.md)

SF5平衡重放首作业12708712遭遇配置字段接口失败；已修复真实配置的消费字段并通过入口合同检查，以12708861按同480个旧已评分窗口重提，最新检查已运行。该作业将保留逐物种、逐类混淆，原始逐位置输出仅留Baobab。[SF5重放协议与作业记录](SF5-BALANCED-REPLAY-20260914.md)

用户要求继续等待，本线程已建立每30分钟跟进（automation id `te`）：仅对这些已授权既有作业收取、固定评分、修复明确接口故障、记录及Git推送，有实质变化才通知；完成本轮结果处理后暂停。此跟进不授权新研究路线、增加训练预算或开放sealed数据。
