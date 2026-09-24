# 2026-09-18 论文收束：统一基座与补充实验

本记录落实作者本轮“把剩余工作推进至完成，可并行，长 CPU/GPU 任务用 private”的指令。新训练/新比较已被明确提出，不再以 2026-09-17 的“暂不新增训练”建议阻止执行。历史结果、封存数据限制、已冻结的历史比较和他人的未提交文件保持原义。

## 2026-09-25 更新：旧冻结批次完成，新中心实验另行启动

旧七项协议现均达到可解释终态。鸡EDTA原生FINAL/ANNO在13190938实际完成，失败发生于随后导出器误将内部副本计作多个候选；只修复导出后，13192771成功，未重跑原生注释。最终binary/class评分13192796/13192797完成且计数核对通过，已有D/RM2指标没有变化。斑马鱼EDTA的128 GB OOM与鸭嘴兽RM2的24h超时仍为资源限NA，不能说所有方法均成功。

固定独立chr10/20上，鸡D/EDTA/RM2的binary F1为0.479174/0.592021/0.699844；统一NTv2-class/EDTA/RM2的known-five macro-F1为0.625913/0.464938/0.609440。鸡条件TE-four仍是RM2略高于模型。斑马鱼D/RM2的binary F1为0.878294/0.871789，class primary为0.760377/0.688569。不能将这些结果写成模型普遍优于传统方案。

鸡EDTA全部失败、恢复和导出累计49h44m31s；D鸡CPU推理110h39m04s，没有CPU速度优势。最终比较、原生日志、正确序列ID、失败状态和累计成本见[终态报告](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/FINAL-COMPARISON-20260925.md)。下方9月24日及更早“待运行/未完成”段落为保留的历史快照，以本节为当前状态。

作者随后明确授权执行与Pro讨论的纯生信中心实验，并明确暂不加入湿实验。新工作独立登记为 `FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925` 与 `FUNCTIONAL-MASK-EVIDENCE-20260925`：先以既有鸡/斑马鱼暴露过的用途面板检验等掩码预算及保守化解释，同时构建独立宿主/自主TE证据表；不改变旧结果、阈值、训练或原比较分母。Nature Communications是投稿目标，不是实验成功标准。完整独立确认实验仍需依据pilot和证据可得性收敛，不能把开发面板升级为未见物种验证。[新授权与中心假设](../20260924/central-claim-discussion.md)

## 2026-09-24 更新：终态与恢复边界

### 20:21 UTC复核：Helitron完成，原生RAW合并步骤仍需补齐

`13189902`的Helitron分支已完成（子进程1775.75s），FASTA/GFF3/BED均非空；filter于20:20:50 UTC完成并进入FINAL。但stderr报告缺失`galGal6.fa.mod.EDTA.intact.raw.gff3`：分支式恢复入口跳过了EDTA.pl在RAW之后执行的intact汇总步骤。因此当前仍不可用于完整EDTA比较，即使后续退出码为0也不能直接采纳。当前原生作业保留运行，评分`13189916`/`13189917`已hold，待按EDTA原生规则补齐聚合并核实受影响的FINAL/ANNO产物后再放行。没有新增科学分数或改变参数/分母。

源码核实表明，可复用已完成raw和combine过滤产物，在新目录补做EDTA.pl ALL段原有的intact FASTA/GFF聚合，再以`--step final --overwrite 0 --sensitive 1 --anno 1`重做FINAL→ANNO；不复制本次受影响的final/TEanno缓存。当前作业终态后按实际Slurm耗时扣减原预算再执行，不重跑TIR、Helitron或filter。

在确认该缺口使当前FINAL→ANNO必须重做、修复脚本及真实输入均就绪后，停止`13189902`以避免继续消耗固定预算；Slurm为CANCELLED、实际3,255s，全部文件保留，不改其可能残留RUNNING的原status。新作业`13190938`在fresh `EDTA-aggregate-final-13190938`补做原生聚合及FINAL→ANNO，预算为431,681s。两个既有评分已将依赖改为`afterany:13190938`，更新native根后解除hold，不重复提交。尚无新的完整EDTA科学结果。

### 19:29 UTC复核：TIR已完成，EDTA下游仍缺失

鸡EDTA `13189201`在44m29s后失败，但这次TIR Module4、postprocessing及检查点消费均已实际成功；失败发生于随后的`edta_filter_final_annotation`（88.98s、exit2）。不能将TIR中间产物视为完整EDTA注释。该次2,669s成本保留，原生cell预算余434,936s，后续只允许同协议工程恢复。原生日志已定位为Helitron原始产物缺失：原流程尚未执行该分支，恢复脚本过早跳至filter；将补齐同参数Helitron分支后再过滤，不用`--force`或替代库，不重做已成功TIR。

依赖其终态的binary/class评分`13189350`/`13189351`已分别在103/197s完成，所有已存在数值与前次RM2比较完全相同；鸡EDTA仍为失败NA，斑马鱼EDTA仍为OOM/NA。新的完整JSON使用已修正RM2组成摘要，既往科学指标未改写。本批尚未全部收束。[本次评分记录](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/SCORE-FOLLOWUP-20260924.md)

Helitron续跑`13189902`在private以16 CPU/128 GB、无GPU启动，fresh `EDTA-helitron-cont-13189902`复用已成功的TIR及此前raw产物；原预算剩434,936s。后续binary/class评分`13189916`/`13189917`均依赖`afterany:13189902`，写入fresh `score-helitron-cont-20260924`，不覆盖前两轮评分。作业启动不构成原生注释完成。

### 本轮18:39 UTC后的最新终态

两个RM2完整注释均已完成（mask-only 13180772/13180877），共同binary评分13180901和class评分13180902也已完成。固定独立chr10/20上，D/RM2的binary F1为鸡0.479174/0.699844、斑马鱼0.878294/0.871789；鸡的高precision不足以补偿低recall。统一NTv2-class/RM2的primary known-five macro-F1为鸡0.625913/0.609440、斑马鱼0.760377/0.688569，但鸡条件TE-four端点为0.641398/0.654189，模型并非所有端点更好；完整八状态差值亦很小。所有固定类别、物种、失败臂均保留，无事后调参或换分母。

RM2按原发现＋失败恢复＋完整mask的累计Slurm时间为鸡38h18m36s、斑马鱼35h49m05s；D鸡完整CPU为110h39m04s，因此当前没有CPU速度优势证据。GPU推理单列，不能用不同硬件直接宣称同资源优势。六个预声明TE根类别及Unknown构成binary native预测口径；鱼的PLE原标签在审计中保留但不在binary接纳列表内，不在看到分数后更改规则，亦不以小F1差宣称普遍优越。

RM2的GFF派生摘要有两处工程错误：把Target中的Motif当类别、类别区间跨contig合并。binary和class评分均直接读`.out`，数值不受该描述性错误影响；保留原摘要后修正，已完成score文件不重写。报告与紧凑导出明确排除旧无效描述字段。

鸡EDTA恢复13180896在启动TIR前因检查器误查`*.csv_dtypes.txt`而失败（真实文件为`*_dtypes.txt`），306秒成本保留；修正后的13189201已在fresh目录继续，剩余437,605秒。斑马鱼EDTA仍为原128 GB OOM/NA。最后缺口仍是鸡EDTA原协议续跑及其同口径比较，本批尚未全部收束。[binary比较与累计成本](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/RM2-COMPARISON-13180901.md)；[class比较与逐类边界](../../../reports/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/RM2-COMPARISON-13180902.md)。

新恢复日志已明确显示`Successfully loaded checkpoint`、Module4/Step7及随后Step8，确认从原检查点续跑而非重做前段。两项后续评分13189350（binary）/13189351（class）等待`afterany:13189201`，输出fresh `score-edta-retry-20260924`。RM2派生摘要修正13189316已完成（70秒），原GFF摘要作版本备份，canonical摘要和旁路副本使用真实`.out`类别、按contig统计的类别union；原注释、status和已完成评分数值不改。

### 早次heartbeat记录（保留历史状态）

9月23日22:42 UTC的实时检查确认原批次已无运行作业。下文9月18日的运行中描述是历史快照；当前科学结果和失败状态如下。

- 统一NTv2训练、配对表示、长度诊断、有限LoRA和两个外部动物评价均已完成，既有解释边界不变。
- 鸡和斑马鱼的固定非哺乳用途均完成；斑马鱼的新增完整结果见下方。两者是AUGUSTUS用途，不是Tiberius或未见物种泛化。
- 两物种D完整GPU推理及鸡完整CPU推理均完成；独立chr10/20的两物种class map亦完成。native方法未完成之前，不能由这些产物宣称完整公平benchmark已经完成。
- 两个RM2发现阶段原生完成，但RepeatClassifier因FamDB运行时路径错误而未产生classified库。已授权只修复分类和masking后续阶段，复用完整discovery产物，保持原输入、程序和评价；原失败与累计成本保留。恢复使用的数据库版本和分类知识条件须明示。
- 鸡EDTA在TIR阶段失败，斑马鱼EDTA在同阶段OOM。不得以`--force`跳过TIR、改变分母或将未完成输出当完整EDTA对照。
- 鸭嘴兽RM2达到其冻结的24小时预算，尚无完整classified库；下游RM2 receiver和评分未启动。该臂按资源限终态保留为NA，不扩预算，既有RED和Tiberius阳性结果仍有效。[终态记录](../../../reports/PLATYPUS-STRONG-MASK-CONTROLS-20260917/TERMINAL-20260924.md)

两个RM2恢复在private CPU分区启动（鸡13180658、斑马鱼13180659，各16 CPU/128 GB，无GPU），使用原benchmark的Dfam4.0资产并保留完整发现库。两者均已分类成功，但RepeatMasker的默认FamDB目录挂载仍缺失，分别7m57s/15m34s后失败；修复后13180772（鸡）及13180877（斑马鱼）只复用现有classified库执行mask，已启动，不重复分类。时限已从各自原7天预算扣去原发现与该次失败的Slurm时间；原失败根不覆盖。后续评分使用各物种fresh `RM2-mask-recovery-v2`目录。

鸡EDTA已有TIR Module4/Step7检查点，已完成兼容修复的序列等价验证并排队续跑，斑马鱼EDTA保留128 GB OOM终态。新分类模型自身评分已完成，native失败行显式NA。D完整输入的同口径评分13180826亦已完成（private、4 CPU/32 GB、无GPU、79秒，fresh `score-d-terminal-20260924`），读取已结束的原native单元并保留NA；恢复产物完成后另补共同方法比较，不将待运行恢复输出当成终态。

恢复链现已接好：鸡EDTA 13180896等待`afterany:13180772`，维持最多两个native恢复并行。完整binary评分13180901及固定chr10/20 class评分13180902均等待`afterany:13180772:13180877:13180896`，写入独立`score-recovery-20260924`目录。EDTA小fixture的标量/修复序列8条完全相同、named TIR_type访问通过；合成小输入未复现原swifter分支，故原故障以实际12888165日志取证，不虚报合成复现成功。四次fixture共27秒计入鸡EDTA预算，剩余437,911秒，未改科学参数。[当前作业登记](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/recovery-jobs-20260924.json)

本批尚未完成最终方法比较和Git结果冻结；不发布新模型权重或新仓库。

| 冻结工作 | 当前可解释状态 | 尚需完成 |
| --- | --- | --- |
| UNIFIED-NTV2-REPRESENTATION | 900步训练、配对表示、有限中心上下文诊断均完成 | 无新增训练 |
| D-BACKBONE-LORA-CLADE | 固定比较完成，未支持替换D | 无新增MoE搜索 |
| EXTERNAL-ANIMAL-CLOSURE | 两个既定物种及class分层完成，草雀低召回保留 | 无新增物种 |
| NONMAMMAL-GENE-UTILITY | 鸡、斑马鱼四臂及CDS重叠诊断完成 | 无新增接收器或区域 |
| WHOLE-GENOME-BENCHMARK | D完整GPU/鸡CPU及RM2两物种完整注释、同口径评分完成 | 鸡EDTA原阶段恢复及共同评分；斑马鱼EDTA为OOM/NA |
| UNIFIED-NTV2-CLASS-MAP-BENCH | 固定chr10/20的NTv2/RM2 class比较完成 | 仅待鸡EDTA完成后的同分母补充 |
| PLATYPUS-STRONG-MASK-CONTROLS | RED可解释；RM2在固定24h预算下无结果，按NA终结 | 不扩预算；保留已完成用途及其区间 |

**新增适用域约束：** D在独立chr10/20上的binary bp-F1，鸡为0.479174（P=0.938901，R=0.321670），斑马鱼为0.878294（P=0.815321，R=0.951810）。完整assembly对应F1为0.559412/0.871752，但其中包含训练/模型选择曾见染色体，不能代替独立测试。鸡原生推理覆盖全部464条contig与完整1,065,365,425 bp，低召回不能归于作业未完成；与既往采样面板分数的差异原因尚未隔离。该结果与其AUGUSTUS用途小幅阳性可同时成立，论文应将材料覆盖和下游效用分别陈述，不能宣称鸡完整TE map覆盖充分。固定阈值、窗口和分母不改。[完整D评分及边界](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/D-RESULTS-13180826.md)

## 统一模型的含义

目标基座为 **NTv2-500M（500M 参数）**。4096 bp 等数值是输入窗口，不是模型参数量。新实验要实际统一 encoder、训练物种、划分及输出定义；不能只将现有 GENERanno SF5 改名为 NTv2，或把历史 D/SF5 的最佳数值拼为单一模型。

论文采用同一 NTv2-500M 基座的两套权重：旧 D 保留为已测量 binary 模型，新 NTv2-class 提供八状态 broad-class 标签。后者实际重新训练，不沿用 GENERanno SF5 的分数。Unknown/ambiguous 的来源状态需显式保留，不能为了分类分数删除难例，也不能把未分类 TE 自动变为 BG。若将新分类模型的非 BG 概率之和用作材料预测，它需要自己的 CAL、逐物种评价、benchmark 和下游行，不能继承旧 D 的分数。

保留 C. elegans 是当前基线定义的一部分。是否增加类群专家要通过受控比较决定，而非删除表现较低物种来提高均值。适用域按实际测量的物种/分支界定；本轮草雀结果表明，不能直接把“脊椎动物”作为整体已支持范围。

## 本批工作和完成标准

| 工作 | 本轮执行 | 可称完成所需证据 |
|---|---|---|
| NTv2 表示与统一分类 | 同样本 pretrained / binary / class；排查旧 BG 图、长度、组成、池化及读出设置；实际统一模型训练 | 模型身份、训练/评价暴露、同一分母的 supervised readout 和 unsupervised cluster 分开；新模型自己的 end-to-end binary/class 结果 |
| 外部物种 | 先按 assembly 和注释来源资格选定可靠面板；非哺乳动物优先；固定模型/阈值 | 每物种完整分母与来源，不能按分数替换；稀疏阳性数据只用于召回支持，不承担生物学 precision/F1 |
| Adapter/MoE | 有限共享适配器与专家/路由对照；同 seed、数据、预算；正式训练前记录可执行规模 | 逐物种、最弱物种、原域保持、专家互补及路由行为；不把小 head mixture 称为 backbone MoE |
| 非哺乳基因注释用途 | 先验证 gene predictor 真正消费 softmask；合格接收器上 D/U/RM/de novo 配对 | 同基因模型与同输入，gene-level 指标及配对区间，全部 gain/loss；忽略 mask 的接收器不能用来测 mask 效果 |
| 整基因组 benchmark | chicken 优先，合格第二物种；完整 EDTA/RM2 构库及 masking；D CPU/GPU 单列 | 整基因组输入与资源记录、原生退出状态、共同 binary/class 指标、Unknown 分母、构库和推理成本分别报告 |
| 代码及发布 | 每项实际结果同步，最终模型确定后固化 | 固定权重/配置/版本、可复现脚本与独立部署接口；未完成作业不标成完整 benchmark |

长任务使用 `private-teodoro-gpu`；纯 CPU 任务不申请 GPU。已运行数小时的旧任务保留，避免只为换分区重复计算。排队中的可迁移任务与新任务按当前指令路由。原生失败保留，工程修复不改变实验分母。

## 对当前科学解释的澄清

**不是只做过四个基座。** 四个是 human H0 的统一 quick screen。另有 NTv2 50M/100M/250M 与 NTv3 8M/100M/650M、两种上下文变体的 495 行迁移矩阵。远程 hg38 正式 split 还有三基座主比较。完整记录在 [历史盘点](../20260917/backbone-transfer-inventory.md)。这些是不同协议，不能跨表将最高分排名。

**预训练 TE 信息没有被整体否定。** 0.5221 是 GENERanno 在特定 512-bp 面板上的 binary 5-NN macro-F1；它不等于 NTv2 的结果，不等于线性可分性上界，也不等于表示中没有 TE 信息。NTv2 已有 Known-five 0.4885→0.6394、TE-four 0.6342→0.7197 的同样本读出结果。二维图里 BG 聚团可以和全空间读出较弱共存，具体原因需回到原图的样本、标签、尺度与算法核查。预训练随机 MLM mask 与基因组的 TE hard/softmask 是不同操作，官方数据与 tokenizer 处理需分别确认。

**hg19 结果可陈述为后续注释支持。** 固定 hg19 训练模型的一些旧 FP 区间，在同序列对应的 CHM13 注释中有 TE 支持。这是现有结果，不应被说成完全不支持。但匹配背景后，差异集中在旧 TE 相邻边界；isolated 组并无一致的额外支持。可写“注释版本和边界影响性能测量”，不能据此将全部 FP 改为 TP、修正总体 F1，或把 2026 年的回顾性实验说成 2009 年预测了未来发现。[配对及序列核实](../../experiments/HG19-CHR1-REVISION-20260914-MATCHED-RESULT.md)

**低 TE 密度不等于低注释质量。** 物种资格应来自组装/注释版本、来源、已知/未知覆盖、分类方法和独立证据，不能以“TE 多”或“模型分高”选样本。评价 reference consistency 时应直述该比较器口径；即使注释较丰富，也不自动成为完整生物学真值。

**下游效用足以成为论文主线，但比较措辞应对应结果。** 相对未 mask 的提升可以独立成立；“优于 de novo”需要同输入强对照。“相对 RM 区间跨零”不是“已证明不劣于 RM”：正式非劣效性需要事先给出有生物学意义的允许差值，不能从观察结果反推阈值。本批保留效应量与区间，不补一个结果驱动的非劣界值。

**多分类基线不应假设传统方法不会分类。** 构库与分类是不同步骤；native de novo 工作流的 class/family 与 Unknown 输出需保留并映射同一 broad-class ontology。必要的外部分类器以及参考库知识条件单列，不能在后处理时默默增加额外知识。

**公平计算比较不要求所有程序使用相同浮点格式。** 统一输入、CPU 核数/线程、内存上限、硬件范围、时间口径和质量评价；报告神经模型精度及硬件，CPU/GPU 分行。构库成本必须计入 end-to-end 时间，预先存在的 curated 库单列知识条件。

## 本日已完成：独立 RNA 证据

Slurm **12858354 COMPLETED**，34m34s。SRR23268362 全组装比对率 91.84%，盲法候选共 1,083 条。

| Arm | 多外显子候选 | 全部内含子严格支持 | StringTie 精确内含子链 |
|---|---:|---:|---:|
| U_soft | 680 | 262 (38.53%) | 180 (26.47%) |
| D | 689 | 281 (40.78%) | 191 (27.72%) |
| R_TE | 687 | 283 (41.19%) | 189 (27.51%) |

D 对 U_soft 的 49 个 reference-relative gain 中 22 个获全部内含子支持；18 个 loss 中也有 8 个获支持。支持“有用但有取舍”的基因注释效果，不能说所有变化都是改进。事后十染色体配对 bootstrap 的严格支持率差为 +2.25 个百分点，区间 [+1.00,+3.86]；StringTie 支持率差区间跨零。该区间衡量区域敏感性，不是生物学重复。所有预测的 RNA 分母含 halo（104 Mb），reference locus 比较为 100 Mb。[完整结果与图](../../../reports/PLATYPUS-GENE-EVIDENCE-20260917/run-12858354/RESULTS.md)

本批仍是执行中的研究批次，不是最终论文数据冻结。工作进展及新结果按各实验原生报告更新，不以提交作业代替结果分析。

## 本轮新增完整外部结果与解释

固定 D/CAL，两个预先按来源资格选定的非哺乳物种，各 20×5 MiB=104,857,600 bp；完整推理与评分已结束。

| 物种 / assembly | 可调用 strict-known TE 阳性 bp | positive-only recovery | source-comparator P / R / F1 |
| --- | ---: | ---: | --- |
| 河豚 Takifugu rubripes / fr3 | 2,289,458 | 0.833708 | 0.599147 / 0.833769 / 0.697250 |
| 斑胸草雀 Taeniopygia guttata / taeGut2 | 4,476,142 | 0.221228 | 0.810570 / 0.221227 / 0.347588 |

comparator 列另外排除 Unknown/ambiguous/ARTEFACT 区间，故其阳性分母与 positive-only 口径有细小差异；它不是完整生物真值。草雀约 348.6 万 bp 的 comparator FN 不能由“FP 因漏注释而升高”解释。其 20 个区间均低召回，不是一个孤立区域造成。该结果直接限制“普遍脊椎动物泛化”，不取消鸭嘴兽的既有基因用途阳性，也不证明所有草雀 FN 的成因。已启动的有限共享/类群 LoRA 对照保持原合同，不按此分数重选训练或测试物种。

## 已落实的新执行链

- **NTv2 class**：exact-D 坐标重建 TRAIN/CAL/DEV 为 21,000/6,000/6,000 条半窗；原生 D→8-class loader smoke 12888482 已 PASS，初始化 encoder 差为 0。保留旧 binary D，另训同基座 class 权重；不把旧 GENERanno SF5 数值迁移到新模型。
- **BG readout 诊断**：GENERanno pretrained 的 known binary 混淆矩阵为 `[[67,293],[116,805]]`，BG recall=0.186、TE recall=0.874；NTv2 pretrained 为 `[[55,305],[74,847]]`，BG recall=0.153、TE recall=0.920，macro-F1=0.5211。D 后 macro-F1=0.7211。分母为 360 BG+921 TE，不是全部 1,580 条，也不是实际标注 F1。参见 [诊断](../../../reports/UNIFIED-NTV2-REPRESENTATION-20260918/LEGACY-BINARY-DIAGNOSTIC.md)。另固定中心512 bp、改变512/2048/4096上下文的有限诊断，检验长度而不同时变更目标标签。
- **鸡/斑马鱼 AUGUSTUS 用途**：各 50 Mb 核心/52 Mb含halo；1,064/984 个完整 gene loci。两者 native lowercase→`softmask/nep` 提示观察成功，受控200 bp对应原生1001–1200坐标。D mask 12889043/47均已完成；鸡最终评分12889062已完成，斑马鱼12889049/54/63仍执行中。全部新作业为private。这是D训练物种及既有同物种基因参数的用途测量，不是新物种泛化或Tiberius结果。
- **LoRA**：共享 rank16 对固定类群2×rank8、各131,072参数，末两层query/value，单seed、每臂1024步。首次接口失败保留；修复job12888288依赖两个较短D masks，随后与CPU基因预测并行。host memory根据已测RSS缩为32GB，不改训练。
- **整基因组 benchmark**：鸡与斑马鱼 full assembly native EDTA/RM2 已执行中；D CPU pilot/GPU独立。准确率使用实际D TRAIN/CAL/DEV均未覆盖的chr10/20；SF5旧split只作回顾性分层。尚不能写为整基因组比较完成。
- **多分类 TE map 比较**：`UNIFIED-NTV2-CLASS-MAP-BENCH-20260918` 使用新 class 的 CAL-selected checkpoint，在同一鸡/斑马鱼 chr10/20 上生成原生8状态逐碱基输出，再和整基因组 EDTA/RM2 的 native 类别投影比较。该项不新增训练、不调整阈值、不把条件true-TE或token-majority分数替代完整bp分母；是质量对比，不冒充新class的完整基因组CPU计时。native class composition 只能说明输出构成，不能代替此项准确率。
- **鸭嘴兽 Red 强对照**：639同分母loci，Red F1=0.60103；D−Red差−0.002626，95%区间[−0.017075,+0.014020]。不支持D优于Red，也不建立等效。RM2对照仍未完成。

## 读出与执行审计的新结果

旧缓存上的固定线性读出已完成（12889615）：同一1,281条known-five binary分母，NTv2 pretrained macro-F1=0.586682，binary D=0.703148，GC/N/长度组成基线=0.424161。预训练表示存在可读出的信息，但当前证据仍不足以称为“微调前已经很好区分”；该结果也说明0.521的5-NN分数不是表示能力的上限。所有窗口长度同为512，因此组成基线不能检验长度变化效应；长度诊断另行执行。

实际坐标审计12889831已完成：完整1,580条SIB TEST中，3条鸡序列完整落在D TRAIN、9条斑马鱼落在CAL、156条落在DEV（虫149、斑马鱼7），重叠DNA全部相同。必须区分梯度训练与CAL/DEV角色，不能把168条统称训练泄漏；也不能将该完整面板称为未接触的独立测试。保持固定面板作回顾性表示诊断，独立class-map质量比较仍使用已核实的chr10/20。[坐标审计](../../../reports/UNIFIED-NTV2-REPRESENTATION-20260918/EXPOSURE-AUDIT.md)

CPU benchmark旧pilot12888135申请16核但实际Torch intra-op=1，故在41m08s停止并保留原输出及成本。修复后真实推理进程显式设置16线程、interop=1，并在启动时记录affinity/dtype；新pilot另用输出目录。该工程失败不能混入16线程公平速度比较，GPU/native任务继续运行。

## Heartbeat 新完成结果：鸡的非哺乳动物基因用途

鸡的全部10个固定5 Mb core、四臂原生预测和评分均已完成；分母为1,064个完整CDS loci，核心50 Mb，含halo输入52 Mb。完整结果在[鸡用途报告](../../../reports/NONMAMMAL-GENE-UTILITY-20260918/chicken/RESULTS.md)。

| Arm | TP / FP / FN | Gene-level F1 |
| --- | --- | ---: |
| U | 280 / 916 / 784 | 0.247788 |
| D | 285 / 835 / 779 | 0.260989 |
| R_TE | 289 / 819 / 775 | 0.266114 |
| RED | 33 / 591 / 1,031 | 0.039100 |

D−U=+0.013201，染色体配对bootstrap 95%区间[+0.005109,+0.025163]；D−R_TE=−0.005125，区间[−0.010349,−0.001594]。这新增了“learned mask 改善未mask的非哺乳基因预测”的证据，但同组参考TE mask仍更好。R_TE来自同assembly既有UCSC注释，不能将它的分数冒充本轮新运行的RepeatMasker计时/输出。

本组RED是在固定52 Mb输入panel上运行的原生默认方法，D−RED虽为正，不能据此概括优于所有RED设置或完整基因组训练的RED。保留其明显下降及实际mask覆盖诊断；不按结果调参或删臂。AUGUSTUS绝对F1和Tiberius鸭嘴兽分数不能跨物种、接收器直接排名。

固定输入的事后mask/CDS重叠诊断显示：50 Mb核心内先合并isoform CDS，得到2,034,021 bp编码区；D、R_TE、RED分别遮盖283、1,192、1,023,600 bp，即0.0139%、0.0586%、50.3240%的CDS。对应全部核心遮盖比例为1.3553%、4.1827%、66.1640%。RED大幅遮盖编码序列与其低召回相符，支持overmasking这一解释，但没有单独隔离其因果贡献；不得把所有被mask碱基都当成TE真值。[诊断与逐核心计数](../../../reports/NONMAMMAL-GENE-UTILITY-20260918/chicken/POSTHOC-MASK-CDS-DIAGNOSTIC.md)

## CPU 可行性终态与继续执行范围

两次修正后的1 MiB CPU试跑均完成，实际Torch intra/inter=16/1、FP32。鸡12889857为2,467.58 bp/s，线性估计约5天，完整CPU作业12891439已提交。斑马鱼12891218为2,397.31 bp/s，对固定1,679,203,469 bp完整输入估计约8.11天，超过预先设定7天门槛，因此**未提交**斑马鱼完整CPU运行。它是按预算规则未执行的完整计时单元，不是实测8.11天，也不是运行到7天超时。不得以缩短输入或沿用鸡速率补齐此单元。

LoRA 12888288已完成固定训练及CAL/DEV结果，class 12889091也已完成900步及一次DEV评价；后续配对表示、class-map按既有依赖推进。四个整基因组native任务、D GPU和鸭嘴兽RM2仍运行中。完整benchmark和最终论文数据冻结尚未完成。

鸭嘴兽RM2首个GPU接收器12857410已原地补充调度依赖`afterok:12856283,afterany:12898018`：科学前提仍是其原始RM2 mask成功，另等待修复后的class-map GPU数组结束以保持最多两条GPU执行链。它不依赖class-map分数或成功与否，未改输入、模型、mask或评价。旧public RM2继续运行，无重启。

## 有限类群 LoRA 的终态结果

作业12888288在private单RTX3090上完成，耗时44m57s。共享rank16与固定类群2×rank8均为131,072个可训练参数、1,024步、seed42；数据为每物种固定256 TRAIN、128 CAL、128 DEV个8,192-bp tile。各臂只在CAL拟合Platt参数与单一全局阈值，DEV不用于选择参数。该表属于本次固定子面板，不能与历史完整DEV分数混用。

| 臂 | 六物种平均bp-F1 | 最低物种bp-F1（鸡） | 最低物种segment-F1@IoU0.8（C. elegans） |
| --- | ---: | ---: | ---: |
| D，匹配CAL重校准 | 0.891834 | 0.817015 | 0.333758 |
| 共享rank16 | 0.890150 | 0.810191 | 0.336250 |
| 固定类群2×rank8 | 0.890696 | 0.810814 | 0.344565 |

类群LoRA的平均bp-F1相对匹配D低0.001138，相对共享LoRA高0.000546；后一个小差异没有多seed或不确定性分析支持稳定改善。最低物种的bp-F1也未提升。局部改善应保留：C. elegans的bp-F1由0.832674升至0.836074（+0.003400），而其余五物种均略降。线虫segment指标的有限上升属于区间拓扑结果，不能据此宣称恢复生物学insertion或普遍泛化。目前没有支持替换D或扩大MoE主张的证据。

该路由按已知taxonomy固定：五个脊椎物种使用expert0，C. elegans使用worm-only expert1；未知taxonomy回退D。两臂匹配的是总可训练参数；单次输入的活动LoRA参数为共享131,072、类群65,536，因此不是活动容量完全相同的对照。没有学习到的gate，也没有本次适配器的外部物种测试，不能将其称为通用稀疏MoE或据此解释草雀结果。本次结果只约束这个固定方案，不否定其他MoE设计。本轮不按DEV分数改rank、路由、训练步数或物种构成。[终态分析](../../../reports/D-BACKBONE-LORA-CLADE-20260918/RESULTS.md)

## 统一 NTv2 class 的训练终态

作业12889091已完成（1h02m05s），实际执行固定900步，CAL按八状态token-majority macro-F1选中第900步（0.6022688），重载该checkpoint后仅评价一次DEV。6,000条4,096-bp半窗共24,576,000 bp；DEV token macro-F1为0.6066181，原始逐碱基标签上的macro-F1为0.6067215，bp accuracy为0.9053371。pooled DEV八类均有真实support，保留完整类别分母。

| 类别 | DEV bp-F1 |
| --- | ---: |
| BG | 0.9495 |
| SINE | 0.9061 |
| LINE | 0.8827 |
| LTR | 0.7797 |
| DNA | 0.7589 |
| KNOWN_OTHER_TE | 0.4028 |
| AMBIGUOUS_TE | 0.0000 |
| UNCLASSIFIED | 0.1740 |

这首次给出同D基座、同六物种和坐标体系下实际训练出的class结果，支持继续既定TE map与表示对照。BG和四个主要TE类别的pooled结果有用，但其他类别和未确定来源状态尚弱，不能概括为完整八状态均可靠。来源状态分类失败不自动等于binary材料漏检；是否被错分为BG或其他TE类需按完整混淆矩阵区分。逐物种macro按该物种真实support非零的类别计算，不能默认所有物种都有相同八类分母。

此处是comparator-derived DEV标签一致性，不是独立生物验证。三权重配对读出/聚类和512/2048/4096上下文诊断已有下述终态；固定chr10/20的class-map已生成，完整方法比较仍待native对照和评分。训练完成不代替这些结果。新权重暂未公开发布，不能继承旧SF5或binary D的性能主张。[完整训练与逐类别结果](../../../reports/UNIFIED-NTV2-REPRESENTATION-20260918/CLASS-TRAIN-RESULTS-12889091.md)

## 同基座三权重的配对表示结果

主抽取12889676和三个CPU读出12889677–79均完成。三臂使用完全相同的SIB TRAIN/VAL/TEST（1,843/809/1,580条），同tokenizer、池化和1,024维表示；读出和K-means仅在TRAIN拟合。

| 固定端点 | 预训练 | binary D | class D last2 |
| --- | ---: | ---: | ---: |
| known-five 5-NN macro-F1，TEST 1,281条 | 0.4885 | 0.6394 | 0.7261 |
| full-eight 5-NN macro-F1，TEST 1,580条 | 0.4730 | 0.5934 | 0.6512 |
| 条件TE-four 5-NN macro-F1，TEST 921条 | 0.6342 | 0.7197 | 0.8417 |
| known-five K=5聚类ARI | 0.0386 | 0.1105 | 0.2200 |
| 条件TE-four K=4聚类ARI | 0.0713 | 0.0424 | 0.2287 |
| known-five binary线性读出macro-F1 | 0.5873 | 0.7031 | 0.6995 |

这支持同一NTv2基座上类别微调增强ontology-aligned类别信息的可读出性，而不是只沿用旧GENERanno的证据。监督读出与无监督分区需分开命名：K-means不使用训练类别作为优化目标，但端点按注释筛选，ARI也使用标签评分，不能称为完全无标签的生物发现。保留两个不均改善端点：binary D的TE-four K=4 ARI低于预训练，class的binary线性读出略低于binary D。

已知SIB TEST对D TRAIN/CAL/DEV的精确暴露仍完整保留，本结果是固定面板上的回顾性表示诊断，不能证明无记忆或未见物种泛化。预训练binary读出仍属有限信息而非良好分离。[完整配对结果及全部固定K](../../../reports/UNIFIED-NTV2-REPRESENTATION-20260918/REPRESENTATION-RESULTS-12889676.md)

长度分支的首次原生覆盖检查报`covered=0,target=512`，记录为`BLOCKED_NATIVE_OFFSET`，未产生长度性能结论。主SIB结果已独立完成；后续只允许修复明确的offset/坐标工程问题，保留原失败，不跳过覆盖断言、不改变固定中心目标或样本。

该故障已定位为source/local坐标混淆并修复：三个上下文均围绕固定中心`[1792,2304)`取窗，通过长度与目标序列相等检查；length-only重试12897975（5m20s）与CPU评价12897980（20s）均已完成，主SIB抽取和训练未重做。

原class-map数组12890969两个单元在27/25秒后因`<unk>`错误按5字符而非6原始bp展开而失败，未产生科学分数。修复复用训练器的`token_span_lengths()`；新数组12898018使用原checkpoint及原chr10/20，fresh输出`ntv2-span-r1`，排在length-only GPU之后。评分12898022明确读取新目录并等待四个native对照完成；旧从未启动的12890970取消，原失败与52秒GPU成本保留。鸭嘴兽接收器和鸡完整CPU短暂hold以重接新数组，均已release回正常依赖等待。

## 固定中心目标的上下文诊断终态

修复后的3模型×3上下文均完成768条记录的1,024维表示；每条target pooling权重恰为512 bp，中心DNA与标签保持一致。TRAIN/CAL/DEV为384/192/192条（六物种各64/32/32），其中DEV的known-five/binary支持186条、条件TE-four仅65条。它是与SIB不同的有限上下文面板，来源为同一D坐标体系，不能把其数值直接与SIB的921条TE-four或1,281条binary混算。

| 端点 | 512 bp上下文 | 2048 bp上下文 | 4096 bp上下文 |
| --- | ---: | ---: | ---: |
| 预训练binary线性读出macro-F1 | 0.7410 | 0.8635 | 0.8991 |
| binary D的binary线性读出macro-F1 | 0.8571 | 0.8998 | 0.9223 |
| class D的known-five线性读出macro-F1 | 0.7559 | 0.8421 | 0.8688 |
| class D的TE-four 5-NN macro-F1 | 0.8615 | 0.9064 | 0.9211 |

因此，预训练NTv2的TE/BG信息并非不存在：在这个固定中心、小样本面板上，较长上下文下有更强的可读出信号。该结果支持上下文设置敏感性，不能直接证明旧UMAP与SIB读出差异完全由长度造成。并非所有端点单调改善，例如class D的binary线性读出为0.8527→0.9413→0.9347；不据此重选论文窗口。三个上下文的target token数为87/86/86，中心DNA相同但分词边界并非完全相同，因此未单独隔离flanking序列与分词设置的贡献。[完整长度诊断](../../../reports/UNIFIED-NTV2-REPRESENTATION-20260918/LENGTH-RETRY-RESULTS-12897975.md)

## 斑马鱼非哺乳动物用途终态

主评分12889063和事后mask/CDS诊断12899904均完成。四臂各10个固定core完整成功，核心50 Mb、含halo输入52 Mb，同一984个完整CDS loci；未按结果删core或换物种。

| Arm | TP / FP / FN | Gene-level F1 |
| --- | --- | ---: |
| U | 211 / 1,412 / 773 | 0.161872 |
| D | 250 / 688 / 734 | 0.260146 |
| R_TE | 244 / 720 / 740 | 0.250513 |
| RED | 225 / 803 / 759 | 0.223658 |

D−U=+0.098274，按染色体配对bootstrap的95%区间[+0.080732,+0.114279]；D−R_TE=+0.009632，[+0.002451,+0.017094]；D−RED=+0.036488，[+0.025937,+0.048305]。因此本固定斑马鱼面板支持D mask改善AUGUSTUS基因预测，且相对两个既定mask对照也有正向效应。R_TE是同assembly已有参考TE注释，不是本轮新运行RM2的结果；RED是在固定52 Mb panel上执行，不能推广为优于整基因组训练的所有de novo方法。区间反映10个染色体的区域敏感性，不是生物学重复。

与鸡一起，两种非哺乳动物都支持D相对未mask有益，但相对参考TE mask的结果并不一致（鸡略低，斑马鱼略高）。两物种均在D微调物种集合中，AUGUSTUS也使用既有同物种参数；本结果不证明未见物种泛化，也不能与鸭嘴兽Tiberius绝对F1跨接收器排名。

固定core中先合并isoform CDS，斑马鱼CDS union为1,845,174 bp；D/R_TE/RED分别遮盖25,830/15,464/77,267 bp（1.3999%/0.8381%/4.1875%）。RED虽总mask少于D，但CDS重叠更多，因此其较低用途分数不能只按总mask比例解释。该事后诊断与基因区overmasking解释相容，未隔离因果贡献。[完整结果](../../../reports/NONMAMMAL-GENE-UTILITY-20260918/zebrafish/RESULTS.md)

## 整基因组D推理的实测终态

下表来自终态native summary和Slurm，输入包含完整assembly及其非ACGT位置。原JSON中的`callable_bp_per_second_end_to_end`实际以总FASTA bp为分子，因此此处正确称为input-bp/s。child wall与Slurm elapsed分列，不以1 MiB pilot外推替代实测。

| 物种 | 部署 | 总输入bp | 推理子进程wall（s） | input-bp/s | Slurm elapsed |
| --- | --- | ---: | ---: | ---: | --- |
| 鸡 | RTX3090 GPU | 1,065,365,425 | 17,223.32 | 61,864.51 | 4h47m22s |
| 斑马鱼 | RTX3090 GPU | 1,679,203,469 | 27,093.44 | 61,978.34 | 7h31m56s |
| 鸡 | 16 CPU，FP32 | 1,065,365,425 | 398,324.46 | 2,674.62 | 4d14h39m04s |

斑马鱼完整CPU仍为事先预算规则下未提交，不能补为实测8.11天。该表是部署成本，不含模型预训练/微调，也不证明任何质量优势；与native方法比较时，后者完整构库、分类与masking成本必须分别保留，不能把本表直接与某个native局部阶段排名。[完整终态及恢复记录](../../../reports/WHOLE-GENOME-BENCHMARK-20260918/TERMINAL-EVIDENCE-20260924.md)

## 统一NTv2在独立染色体上的class-map评分

CPU评分13180656完成；取得原生失败登记后，13180671在相同输入上补全NA元数据，两次各1m15s，科学指标一致，原结果均保留。主记录采用后一份。固定鸡和斑马鱼chr10/20未出现在D的TRAIN/CAL/DEV坐标清单中；这是同微调物种的独立染色体评价，不是未见物种测试。比较层为同assembly UCSC RepeatMasker，非穷尽的生物学真值。

| 物种 | primary known-five macro-F1 | primary support bp | full-eight端点macro-F1 | 全部ACGT bp |
| --- | ---: | ---: | ---: | ---: |
| 鸡 | 0.625913 | 34,478,839 | 0.446293 | 34,515,527 |
| 斑马鱼 | 0.760377 | 95,026,056 | 0.463252 | 100,505,689 |

primary按预先冻结规则只使用来源BG/SINE/LINE/LTR/DNA位置，完整八状态混淆保留其余来源状态。macro按来源support非零类别计算；鸡的KNOWN_OTHER_TE无support，full-eight端点实际平均7类，斑马鱼平均8类，不改变原规则以提高分数。逐主要类别F1如下，其precision分母也限定在primary来源位置，不能当作全基因组所有来源状态上的precision。

| 物种 | BG | SINE | LINE | LTR | DNA |
| --- | ---: | ---: | ---: | ---: | ---: |
| 鸡 | 0.991170 | 0.251809 | 0.848604 | 0.624628 | 0.413354 |
| 斑马鱼 | 0.901428 | 0.715361 | 0.587482 | 0.747530 | 0.850082 |

统一class权重已能形成可测量的TE map，主要类别具有明显的物种差异，不能概括为所有类型可靠。鸡SINE和DNA仍弱；两物种AMBIGUOUS_TE和UNCLASSIFIED召回均为0，斑马鱼KNOWN_OTHER_TE亦为0。来源不确定状态被预测为主要TE类不等于已确认其真实类别，不能据此宣称解决Unknown分类。条件true-TE的“被判为任一主要TE类”召回为0.837376/0.933259，衡量材料检出而非精确类别正确率，不替代上述macro-F1。

四个原native cell在本次结果中均为NA，D binary的class指标为N/A。待原协议内恢复输出完成，再在相同分母下补RM2/EDTA比较；当前无传统方法分类优越性结论。完整8×8计数及所有类别support保留在[终态评分](../../../reports/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/results/score-ntv2-terminal-ledger-20260924/result.json)。
