# 跨物种 TE 论文的有限收束方案

2026-09-17。依据作者本轮九项研究主线及内置浏览器 ChatGPT 6 Pro 的新审阅；替代此前把新稿局限于 P3 / 三哺乳动物的建议。旧实验、旧验收和封存范围保留。本文件是执行与稿件组织方案，不把尚未运行的结果写成事实。

## 中心论点与模型身份

候选中心问题：DNA foundation model 的表示能否经有限任务适配，形成有明确适用域的动物 TE 材料识别和 broad-class 注释流程，并在缺少合适 TE 库时帮助基因注释？“缺少合适库仍有帮助”是需要新下游证据支持的应用假说；现有 P3 的哺乳动物结果不能单独完成这个结论。

| 当前对象 | 基座 / 输出 | 监督物种 | 当前定位 |
|---|---|---|---|
| D seed42 | NTv2-500M / binary material | human, mouse, pig, chicken, zebrafish, C. elegans | 第一候选共享材料模型；固定 CAL 阈值 0.42330056285498807 |
| SF5 ontology closure | GENERanno 0.5B / 八类状态 | mouse, chicken, zebrafish, frog, fly, C. elegans | 独立 broad-class 模型及 ontology 证据；不是 D 的类别头 |
| P3 | GENERanno / 人类来源的四状态分割 | human | 已有 Tiberius 阳性应用及历史对照；不是 D 的下游结果 |

最终流程的材料概率记为 q(TE)，分类为条件 broad class。Tiberius 只需固定 q 阈值得到的 mask；TE map 额外输出类别及拒识。分类不确定不应自动把已检测 TE 变 BG。来源的 AMBIGUOUS/UNCLASSIFIED 状态与模型预测置信度分字段保存，不能混称生物学不确定性。

如果使用两阶段模型，发布时必须说明两套权重、计算成本及训练物种并集；不得当成一个单一 backbone 的结果。当前 SF5 可以独立评估；是否给冻结 D 添加小型 class head，要由新的 matched embedding 及现有分类证据决定。仅训练 head 不支持“encoder 被类别训练重塑”的结论。

当前D与SF5监督物种并集为八种；SF5已使用蛙和果蝇。蛙的D外部screen不能被挪作D+SF5整条流程的物种外确认。串接流程在实际端到端运行、代价和错误传播评估前仍是方案，不是已有整合模型结果。

## 六张正文图

| 图 | 正文的问题 | 补充材料 | 尚缺的关键闭合 |
|---|---|---|---|
| 1 模型选择与统一输出 | 可直接比较的基座结果、模型谱系和 material/class 接口 | 四基座×五窗口、NTv2/v3尺寸矩阵、历史配方差异 | 逐行协议表已找回；不重跑整个网格 |
| 2 表示中的 TE 信息 | 同基座、同样本的 pretrained 与 FT probe / cluster | 全状态和 Known、k-mer/组成混杂、监督 contrastive、UMAP | NTv2两权重与GENERanno三权重均已完成；单列训练暴露差异，不追加表示训练 |
| 3 动物泛化与类别图谱 | 固定流程逐物种结果、最弱物种、完整类别分母 | 所有物种与来源状态、阈值、稀疏 positive-only 面板 | 完整外部 screen；再冻结真正前瞻性确认面板 |
| 4 标签与上下文 | 库变化对 apparent FP/FN 的影响；同一 TE 序列的配对干预 | hg19 匹配背景/序列控制、历史 human-library RM、模拟失效 | 固定 D 背景干预已完成；不能将 context 认定为模拟下降的主要原因 |
| 5 公平 benchmark | 真实/模拟质量和完整CPU成本、GPU单列 | 工具版本、知识条件、失败/null、全部成本、Omni评分复现 | 既有长输入有限比较已完成；最终流程若变，仅增加其独立一行 |
| 6 基因注释用途与使用 | 同一最终 mask 在实际消费 softmask 的基因模型上的效用 | P3 历史阳性、全部 gain/loss、支持来源、部署实例 | D→鸭嘴兽20core已完成且相对未mask有改善；非哺乳用途仍缺合格mask接收器，当前通用vertebrates/insecta不消费softmask |

论文以主问题组织；不需要把每次工程失败、每个已放弃方案展开成正文。但凡影响正文结论的反例和完整比较必须在补充或限制中留下：模拟低召回、未支持的类群、P3 与 RM 未建立优势、Gap/instance 未解决、表示不总优于 k-mer。不能仅按正负选择物种、分母或对照。

## 第一批：当前已授权的低成本补充

1. **历史盘点**：不重新训练网格。保存本地矩阵及 TE_final hg38 主表、human-library RM 的小型原始表和 provenance。历史 v1/v2 与 current D 分开。
2. **SF5 重评分**：复用已完成2160窗口的原生混淆矩阵，报告完整八状态、Known、true-TE 条件分类。保留误预测到 BG/未分类的列，不能删除错误。当前已完成，见同日 `SF5-READOUT-CLOSURE`。
3. **D 配对上下文**：6物种×32已暴露DEV窗口，native / BG dinucleotide shuffle / TE shuffle，固定所有 TE 本身或对照扰动；job `12848734`。这是第一阶段机制诊断，不等于 Pro 建议的天然/模拟中心移植全实验。
4. **Matched embedding**：实际相同基座比较。优先 NTv2-500M pretrained 与 D；全状态及 Known，监督 probe 和无监督聚类分开。所有权重的训练暴露单列。最多1 GPU、4 CPU、48GB、2小时，不训练encoder，不解封。
5. **D 外部 screen**：优先利用 frog / bee / beetle 的合格已有同assembly资产，每种预选4个1MiB区域，1GPU每种最多2小时，无目标校准、无模型选择。这些物种在项目中已有历史暴露，只能称任务外物种的回顾性/开发 screen，不称全基因组独立确认；稀疏参考只报告 positive recovery。最多两GPU同时运行，包括embedding。

上述实际执行情况及失败应写入各自实验报告。未完成项不借由提交 Slurm 标为完成。已有seed42足以本轮比较，不为每项补多seed。

## 第二批：有限的模型选择与独立确认

本轮已有 frog/bee/beetle screen 用于回答当前 D 的已知外部缺口，不继续添加十几个“直到成功”的物种。未来真正前瞻性面板最多六个新物种槽位：两个开发、四个确认。Pro 提出的候选是 medaka / silkworm（开发）和 stickleback / turkey / D. simulans / oyster（确认）；**这些只是候选，assembly、数据与暴露资格尚未核实，不是冻结测试集**。物种改动只能由运行前的数据资格决定，不能由分数决定。公开reference-poor身份须用具体库覆盖来源描述，不能由“非模式生物”推定。

资格允许后，在看新确认分数前固定最终材料流程。每物种报告监督未见种/未见类群、预训练暴露未知、参考来源、正类覆盖。无可靠负类就不报告 biological precision/F1；同源/空间隔离依赖具体数据，不能把染色体或物种分开自动当作无同源泄漏。

MoE 只作为条件分支：先 shared D，再一个共享 adapter 和一个容量/训练呈现量可比较的双专家系统；只有专家互补时比较固定平均、taxonomy 路由和学习 gate。逐物种挑测试最高分只能标 oracle，不是部署策略。旧海胆小 head 提高材料指标但有结构及原域保留性问题，不是已完成稀疏 backbone MoE。

Pro 建议的晋级数值（开发macro F1 +0.01、单物种下降不超过0.01、结构下降不超过0.02）仅为尚未采用的草案；不是当前冻结旧门的替代。新训练的确切样本、容量、目标和停止规则应先落成具体协议，再按当前作者授权执行，不把泛泛预算建议当已完成训练设计。

## 两个下游对象与对照

初始提议为一非哺乳脊椎动物、一昆虫；与最终TE确认角色及Tiberius训练暴露一起选定，不能看TE分数后只挑最佳物种。**后续直接核读模型配置发现，当前官方 `vertebrates.yaml` / `insecta.yaml` 均为 `softmasking: False`；有该类群模型不代表它消费softmask输入。**因此下段140 calls只是Pro初始建议，不能直接提交。

来源：[模型输入合同](https://github.com/Gaius-Augustus/Tiberius/blob/main/model_cfg/README.md)、[vertebrates配置](https://raw.githubusercontent.com/Gaius-Augustus/Tiberius/main/model_cfg/vertebrates.yaml)、[insecta配置](https://raw.githubusercontent.com/Gaius-Augustus/Tiberius/main/model_cfg/insecta.yaml)，2026-09-17核读。Apis mellifera还属于current insecta的训练物种；不能称Tiberius未见种。

可行修订：保持D外部TE面板扩展非哺乳；先在现有哺乳softmask接收器上补**D自身**的用途；昆虫可使用 [superseded/insecta_softmasking.yaml](https://raw.githubusercontent.com/Gaius-Augustus/Tiberius/main/model_cfg/superseded/insecta_softmasking.yaml) 的明确旧版固定权重比较mask，再把current unmasked作为实际流程对照。旧版结果不能称改善当前insecta模型。非哺乳脊椎动物的softmask用途暂为接收器缺项，不把软屏蔽无效视为TE模型生物学失败，也不盲目改成hardmask、强行翻转模型输入flag或新训练gene predictor。Pro已明确承认并撤回原140-call方案，支持此修订；可选昆虫机制实验缩为一个物种×4core×4臂，但尚未执行。

当前已写入可执行的新D用途协议：固定鸭嘴兽旧面板全部20core，每core新增D一臂，复用合格U_soft/U_nosm/R_TE/R_all/P3，主比较D−R_TE，流程比较D−U_nosm，全gain/loss和空间bootstrap。它是回顾性扩展，明确不是新的盲法物种确认。见 [实验协议](../../experiments/D-TIBERIUS-PLATYPUS-20260917.md)。

建议每物种10个预定义5Mb core，每个core七臂：官方unmasked模型；同softmask模型输入未mask序列；最终TE模型mask；species-matched RM 的 TE-only mask；RM all-repeat mask；RM2→RM mask；Red mask。固定gene checkpoint比较mask效应；官方unmasked checkpoint作为整套流程对照单列。7臂并非已执行，也不默认每臂都需GPU；按现有Tiberius原生运行环境定资源。

必须报告 exact locus/CDS-chain、exon/junction、全部gain与loss；RNA/protein支持若可用则作独立验证，基因参考注释本身不是独立真理。RM2库若由测试genome生成，应披露其允许的de novo目标输入，不把它称为与无目标数据的知识条件一致。没有合适Tiberius clade权重的物种保留N/A，不新训gene finder凑表。

在材料流程和实际mask接收器冻结前，不启动全套140 calls；可以先准备精确的assembly/GFF、clade模型与mask生产入口。旧P3结果保留，不自动归入D。

## 机制结论的措辞

- hg19 apparent FP 获得后来参考支持：支持**比较注释依赖性**。经过匹配背景、同序列核实仍不能单独证明真TE、发现未来注释或没有记忆。
- human-library RM 的迁移下降：支持**显式参考库覆盖影响检出**。只有相同输入、版本、分母的配对结果才能比较模型与RM；旧不同chr不能直接放同一排名。
- 模拟上P高于R：描述阈值预测的P/R不对称。不能据此证明上下文机制；新的配对干预才直接改变上下文。
- Pretrained embedding 的probe好：表示中存在可由该readout提取的标签相关信息。无监督cluster、supervised contrastive、linear probe三者不互称。
- main4是 SINE/LINE/LTR/DNA 的broad class，不能称细粒度superfamily/family注释。

## 发布到新GitHub与Hugging Face

当前研究仓库继续保存证据和完整历史。最终公开使用仓库应是独立、可安装的最小导出：FASTA→概率/0-based BED/softmasked FASTA；显式model bundle和CAL；CPU/GPU命令；小型notebook；benchmark脚本与版本/数据下载manifest。科学模型尚未最终选定，不先创造一个“通用模型”发布名。

发现一个实际移植问题：旧 `infer_fasta.py` 的校准artifact绑定Baobab绝对路径，并依赖科研目录中的helper。当前D文件同时含X0 `calibration_protocol`与UPSTREAM实验`protocol`；入口优先读取前者，因此**不存在先前准备审计所推测的protocol不兼容**。公开包须明确绑定模型身份和校准数值，用相对路径搬迁，并与既有推理逐碱基对齐。不能仅删除身份检查就宣布可部署。

NTv2-500M上游model card标为 **CC-BY-NC-SA-4.0**（[原始模型卡](https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-500m-multi-species/blob/main/README.md)，2026-09-17核读）。发布时保留上游归属与权重许可信息，不把整个权重包误标为无条件MIT/商业可用。代码和权重许可分开记录。HF上传、全权重包及新仓库尚未完成；本轮先准备可迁移入口，最终权重必须是上述冻结流程。

## 结束条件

一套明确的最终流程；完整、有限的外部面板（包括非哺乳）；实际消费mask的接收器上的同模型下游应用；同模型benchmark行；有限机制检验；可下载和可复现的发布。非哺乳TE外推与非哺乳gene效用分别报告，不能因没有合格mask接收器而混为同一失败或无条件承诺两个非哺乳用途。共享模型、固定类群路由、或收窄适用域的工具都可以成为结束状态。无多seed网格，无新增Gap搜索，无顺手扩大Plant/Fungi首训，无按阴性结果不断换模型或物种。

Gap暂不作为本稿新的研发任务：本稿输出TE材料/类别图，不声称恢复完整生物插入事件。是否值得Nature Communications取决于外部与下游闭合后的新贡献和证据，不由模型数量、可视化美观或期刊愿望决定。

## 本轮已执行部分的终态

GEN三权重配对 `12854214` 与D→Tiberius统一评分 `12853263` 已完成。D在鸭嘴兽100Mb/639参考loci的F1为0.598402；相对固定接收器未mask提升0.040977，染色体bootstrap区间[0.017171,0.068708]；相对RM_TE提升0.006669但区间跨零。GEN类别微调后的条件TE四类5-NN为0.9030、K-means ARI为0.2429，完整八状态readout为0.6857。本轮只完成所列有限实验，没有关闭整个独立外部确认、库薄弱强替代或最终HF发布任务。详细分母和限制见[当前总表](current-results-and-paper-decisions.md)。
