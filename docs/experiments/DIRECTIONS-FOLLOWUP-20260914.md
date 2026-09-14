# 追加实验与结论收敛

本轮承接用户提出的六个问题：脊椎动物结论与 MoE、FP 匹配核实、k-mer 重训、分类映射、Gap/下游效用和 benchmark。只用 seed42 开展新的模型实验；历史结果和 sealed 区域保持原合同。

## 当前可说到哪里

五个参与训练的脊椎动物在内部 DEV 的 bp-F1 为 0.832–0.942。这个范围支持“已测试的训练物种内部表现”，不支持所有脊椎动物。外部鸭嘴兽四区域的已标注 TE-positive bp 召回为 0.9593，但 LINE/SINE 占主要分母，DNA 约0.1845、LTR 约0（仅10条记录）；整体高分不能掩盖类别弱项。海胆另一个 uncurated-library comparator 上的召回为0.4289，缺少独立负例，不能说其绝对 F1 低于鸭嘴兽多少。

“传统工具也可能受 library 覆盖、类别和进化距离影响”是合理待检验解释；现有结果同时显示 library 缺口和模型在新增 comparator positives 上的漏检，不能用前者消除后者。无脊椎动物不是统一的进化域，当前只有少量固定区域，不能归因于整个类群的共同进化路线。

MoE 继续做有限开发对照：固定 D encoder，比较原D、相同CAL重新校准D、dense residual adapter、双专家 gate 和固定平均专家。相同训练数据/预算、每物种指标及 worst-species 都保留；这只是预测头专家模型，不称为完整GLM稀疏MoE。海胆区域1/2用于适配TRAIN、3用于CAL、4用于探索性EVAL时，要明确该面板已看过且不再是zero-shot证据。

## 已完成的补充

- **ontology与漏检分层**：12708396完成。六ID train/val/test编码及metadata一致。Known-other TE没有误入BG，但被合并入Unknown；没有标注的区域会编码为BG。补充了外部各class、长度、divergence、区域和原始类别的保留分母。[审计结果](../../scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/reports/RESULTS-20260914.md)
- **k-mer与投影重训**：12708302完成。长度4/6/8的centroid top-1为0.3872/0.4255/0.3915；k=4 prototype数和k-mer长度已明确分开。NTv2监督对比投影的centroid top-1/macro-F1由0.3234/0.3103升到0.5106/0.5048；235个已见EVAL中130个accepted，accepted accuracy0.7231，不是可保证99%准确的工具。[详细结果](TE-IDENTITY-RETRIEVAL-IMPROVE-20260914.md)
- **CPU/GPU同输入前向测速**：CPU12696616与GPU12708296全部完成。同1MiB和batch12，CPU第二次前向733–758秒，TITAN X/P100为31–34秒；各硬件与加载时间另列，不能当传统端到端工具速度或整基因组外推。[测速结果](../../scripts/experiments/D-EXTERNAL-RC0-20260914/reports/CPU-GPU-TIMING-20260914.md)

监督投影改善还需区分表示与目标函数的贡献，因此新增固定三臂控制：L2 6-mer+supcon、L2 NTv2+supcon、L2 NTv2+cross-entropy，均50epoch、128d、同TRAIN/CAL及seed42；CAL选epoch，既往EVAL只算最终结果。参数量按输入维度如实报告。作业12708540，未把提交当结果。

## 匹配背景、序列对应与分类修复

FP匹配和adapter回答不同问题。前者检查被旧注释标记FP的区域是否在严格对应序列上、相对同背景TN更常获新TE注释支持；后者检查外部预测是否能适配。FP任务固定原模型、阈值及全TP/FP/FN/TN分母，核实内部chain无gap/indel、正反向对应、hg19与CHM13序列。匹配仅用旧source染色体、精确长度、GC、非ACGT、旧TE边界关系和距离，完成后才接入新版注释支持。[预先固定规则](HG19-CHR1-REVISION-20260914-MATCHED.md)

分类方面，六类结果可以作为既定编码合同下的结果，但以下扩大解释不成立：Unknown高分代表人工漏注、预测出了SVA family、或完成广泛superfamily注释。LINE/SINE/LTR/DNA是粗粒度类别，并非L1/Alu等具体family/superfamily。现有nonsealed资产缺逐位SF5预测，不能凭aggregate反推出新ontology confusion。下一版标签应保留raw class/family，并分开main4、known_other_TE、ambiguous、true_unclassified与明确nonTE；未知区域不能自动充作经验证负例。已有六类指标保留便于复现，新的分类主张需要对应输出头与独立评价标签。

新增实际分母复现12708568已完成：旧SF5两个模型仅按文件顺序评分前1200个test窗口，实际为mouse/zebrafish/chicken各360和frog120；没有fruit_fly/c_elegans。val也省略了c_elegans。这是评价覆盖缺口，不能只凭完整数据集metadata一致就说六物种分类评价完整。已开始限定在旧已评分前缀内的平衡重放，每个上述物种120窗口，保存逐位置预测和分物种混淆；不为补齐分母而自动开放新held-out物种。

## 仍在计算的方向

Tiberius固定U/P/R全60格任务12694349运行，12696406依赖后评分；必须完整结果及独立重算通过后才判断下游效用。Gap已有fragment linking工程验证不能提前写成真实insertion恢复。

Benchmark新增真实native矩阵12708424_[0–8]，三物种固定四区域×RM、HiTE、RM2+RM；同输入但属于real-region feasibility/T2，不是全基因组排名。原D三格纳入共12格固定registry，保留失败和空library；Omni导入/收集成本与Slurm实际caller成本分开。[当前实际接入合同](TE-REAL-PANEL-BENCH-20260914.md)
