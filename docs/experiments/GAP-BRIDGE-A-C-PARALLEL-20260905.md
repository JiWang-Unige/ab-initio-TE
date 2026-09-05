# GAP-BRIDGE A/C 并行前瞻准备协议

日期：2026-09-05。状态：`PREPARE_AND_BOUNDED_SMOKE_ONLY`。

用户已选择推进 A 与 C。本文件冻结本轮准备与有界 smoke 的设计，不是完整训练
或 confirmatory test 的执行令。所有本轮产物 `scientific_claim=false`。A 尚无
完整 trainer；C 完整九 core 干预的运行规模应以 smoke 实测成本确定。

旧 [Stage 1 closure](GAP-BRIDGE-NEURAL-STAGE1-R1-CLOSURE-20260905.md) 的
`NO_ACTIONABLE_ARM` 保持成立，原 P3 是现有主 mask。chr19–22 的新标签、测试指标
与模型选择仍封存；smoke PASS 不释放 confirmatory test。chr13 是已消费的开发数据。
旧 conditional R1 文件作为历史保留，不能用本轮新设计重新判旧 G/R/H PASS。

机器可读设计清单为 `configs/GAP-BRIDGE-P3-NT-R2.json` 和
`configs/GAP-BRIDGE-DOWNSTREAM-C-R1.json`。它们描述执行契约，不宣称所有脚本均已
实现 config loader；实际 CLI 参数应与清单逐项一致。

## 本轮问题与资源

| 路线 | 独立改变的因素 | 本轮产物 |
|---|---|---|
| A，`GAP-BRIDGE-P3-NT-R2` | 在完整 P3 H 信息上增加冻结 NT 连续信号 | 原生坐标配对、统计量准备、8 候选真实前向 smoke |
| C，`GAP-BRIDGE-DOWNSTREAM-C-R1` | 固定基因预测器，仅改变输入 softmask | M0/MW/MP 输入与完整 CDS-chain 评估准备、有界可执行性 smoke |

A 回答新增模型信息是否值得学习；C 回答已知 comparator-positive gap 材料的
mask 干预是否改变固定预测器的基因结果。两者不是学习率、seed 或调度扫描。
A 的开发不依赖 C 的阳性结果，C 也不使用 A 输出选择干预位点。

所有作业单次不超过 12 h，A+C 本 cohort 合计新增 GPU 消耗不超过 24 GPU-hours，
失败、重跑和 smoke 都计入；不得把 24 小时分别分给两条路线。运行前沿用项目既有
审查与 Slurm 分配规则，不在 login node 计算。先测量 smoke 的时间/内存，再决定
预算内下一步；规划估计不是实测。到达预算边界即保存现状，不自动扩大运行。

## A：配对输入与工程范围

P3 为 immutable anchor。候选只能来自原始 P3 相邻最大正区间之间的 1–512 bp 完整
gap；crop 是 `[left256][complete gap][right256]`，仅右侧 pad 至 1024。动作仍是
完整 gap fill 或 abstain，不删除 P3-positive bp，不新增 NT 候选。

| 项目 | 冻结定义 |
|---|---|
| H0 | 完整原 Stage 1 H 的 143 channels/7 scalars；新增槽标准化后归零 |
| HN | H0 原信息 + 1 NT continuous logit channel + 3 NT seam scalars |
| 配对容量 | 两臂均 144 channels、10 scalars；同读出结构、初始化、训练流 |
| NT channel | `clip(log(p_TE/(1-p_TE)), -12, 12)`；pad 位置归零 |
| 新 scalars | crop 是否跨4096 seam；`log1p` 最近 seam 距离；`sign(midpoint-seam)` |
| 新 scalars 拟合 | 只用 chr3+chr5、`TRAIN`、`comparator_known=1` 的 741,503 原候选 |
| 原 scalars | 读取原 Stage 1 `scalar_stats.json`，七维均不重拟合、不改原符号定义 |
| 原生几何 | P3 8192/8192，NT 4096/4096；均 origin 0；phase shift 0 |
| seam tie | 最近距离相同取左 seam；gap 中点落在 seam 时 direction=0 |
| 末端与未知序列 | 原 tokenizer padding 后裁至真实长度；保留包括 N 在内的基因组坐标 |

新 stats 使用已有 known 资格，不把 target、family、support 或 comparator relation
用作输入；常量新列用 scale=1，中心化后为零。拟合 count 不为741,503时须先解释
源 manifest/资格差异，不能悄悄在 smoke 子集重拟合。推理阶段不访问标签字段；原文件
携带标签字节不等于它们进入模型，不宣称文件层面从未读取这些字节。

原点为0时，每个8192 P3 seam也是4096 NT seam。A增加不同模型的观测，不能宣称增加
跨 seam 上下文。原生 NT token-to-bp 投影复用 `strict_segment_eval.py`；不得压缩
valid mask 或把原始 genome coordinates 换成拼接后的索引。每个真实crop位置必须
有实际NT token-to-bp预测覆盖；若tokenizer截断留下未预测位置，smoke判FAIL，不能将
初始化的0当作该位置的预测概率。

固定 donor 是原 P3 的所有合法 gap 中每一个 bp 都有 `p_NT>=0.5` 的集合，gap上限512。
一次性全部执行这些完整 gap；超预算就报告该固定点不可行，不能按标签截断、选子集或
调整阈值。NT 单模型0.5是描述性 comparator，部署安全的主要基准为原 P3。

当前只准备 stats 与首次 chr3 smoke：按原候选 `(gap_start,candidate_id)` 排序取前8，
不按标签、风险或 seam 挑选。真实 forward 仅验证坐标、finite、两臂原槽相同及 H0
新增槽为零；不训练 readout、不计算科学收益、不运行 CAL-FIT/CAL-GATE/test。
未来完整训练若单独锁定，仍沿用原 loss、length weights、两次完整 block-stream
passes、seeds 17/42/20260902，不能将训练顺序实验一起混入 A。

下列内容尚不是本轮科学 PASS 标准：旧 `0.9*min(P3,NT)` topology gate、改写后的
Brier/fraction-MSE门槛、边界/segment容忍值、任何预算匹配 donor 优越性阈值。
完整 A 前须另行锁定可执行 gate；报告原 known/unknown-bp、基因风险与 strict
topology 负结果，不能通过隐式继承旧草案得到 PASS。

## A：已核实 ancestry 与资格边界

远端 project root：`/home/users/j/jwang/ab-initio-TE`。

| 资产/阶段 | 已核实事实 |
|---|---|
| P3 checkpoint | `outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet`；metadata是原四状态P3-R1，不是后来的decoupled P3-R2 |
| P3 初始化 | 直接 `.backup/pretrained_models/GENERanno-eukaryote-0.5b-base`；不经过H0、DAPT或P2 |
| P3 任务监督 | 3,000 chr1-prefix ×8192窗口，800 steps；800 chr11-prefix验证窗口；代码最终保存而非best-checkpoint选择 |
| P3 历史测试 | 1,200 chr17窗口，现有eval仅`chr17:0–9,830,400` |
| NT checkpoint | `software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42`；`best_model/pytorch_model.bin`实存 |
| NT 任务监督 | metadata为3000 train窗口×4096、1200 steps；生成顺序与历史H0记录支持chr1-prefix |
| NT 选择 | 1200 validation窗口，生成顺序支持chr11-prefix；远端`checkpoint-1200/trainer_state.json`明确best step=1000，以validation TE F1选择 |
| NT 历史测试 | 代码test同样取前1200；同一源文件与窗口数的已出ensemble报告只有`chr17:0–4,915,200` |
| 基础预训练 | GENERanno模型卡386B eukaryotic bp、config为MaskedLM；NT模型卡850 genomes/MLM；精确Human坐标暴露均未排除 |

以上支持这两条特定任务监督链，不是全项目未污染证明。生成器 metadata 的 `chroms`
是允许列表，不能作为实际使用chr3/5/13/19–22的记录；精确NT train/val坐标未在已有
小型metadata中列出，不能把窗口bp总量当作连续基因组区间。通用预训练记录
`pretraining_overlap_unknown`，不阻止chr3/5/13工程准备，也不支持未见基因组/未见
同源家族宣称。confirmatory release仍需核对相关监督、calibration、model-selection
和历史reported-test暴露；不以更换assembly名称证明独立。

## C：固定 softmask 干预

C 使用全 chr13 上原 split 的全部9个 DEV cores，每个core左右100,000 bp halo，
分区来自原 `stage0_oracle.json` 的 `chr13_split`，不能从候选表的 distinct block
推导：真实候选仅覆盖其中6个block，另外3个empty core仍保留、三种输入相同。
在染色体端点裁切。一个core一条输入记录，三种mask具有相同核苷酸、长度、分区、
方向和上下文。每条记录只有本core内的原DEV候选允许改变；所有halo始终保持M0，
包括halo与另一DEV core重叠时。不得把其他core的新增mask带入本记录halo。

| mask | 定义 |
|---|---|
| M0 | 原 P3 mask；uppercase参考序列中只将原P3正区间转lowercase |
| MW | M0 + 本core内所有known且全positive的完整原候选gap |
| MP | M0 + 本core内所有原候选gap中的comparator-positive bp；unknown保持原样 |

MW/MP 是不可部署的 label-assisted oracle 干预。更多softmask并非数学上的基因效用
上界；MP−MW同时改变材料覆盖和动作分辨率，不能归因于分辨率单因素。基因注释不用于
选core、候选、halo或编辑位置。保留全部DEV候选，不筛原G/R/H低错误尾部。

固定预测器为 Tiberius **2.0.7**，源码commit
`4d657012a3ed4e923f5d0ac5cef65fecae8109bd`，模型配置
`mammalia_softmasking_v2`，`softmask=True`。代码版本、配置与实际权重资产身份在运行
记录中明确；不能只以container标签替代配置和softmask通道核对。首次准备时尚无已验证
成功的本项目Tiberius运行，不把依赖/容器构建成功当作gene inference成功。

首次 runtime smoke：按原 DEV 候选 `(gap_start,candidate_id)` 排序取第一个，
以其 gap 中点为中心，在所属记录 halo 内裁取固定 400,050 bp（端点仅平移以保持长度）。
对同一片段的 M0/MW/MP 各运行一次，`seq_len=400050, batch_size=1`，
不按基因注释或模型结果选择。GPU 可见性不成立则不运行；最多 1 GPU ×2 h。
这是运行时与 softmask 输入检查，片段边缘/上下文不同于完整 DEV 方案，不用于科学评分。

RefSeq来源固定 `data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz`。
保留strand、CDS起止、CDS外显子链、`cdsStartStat/cdsEndStat` 和 `exonFrames`。
primary endpoint为完整CDS-chain micro-F1：先汇总九core的TP/FP/FN，再计算
`2TP/(2TP+FP+FN)`，不能平均各core F1。无有效分母时记undefined，不报告PASS。
相同坐标及strand的完整CDS链去重；匹配保留所有CDS边界，不能用exon overlap代替。
预测先由record相对坐标转换回genomic coordinates。每条distinct完整链按其最小
genomic CDS start所在DEV core唯一归属，truth与prediction用相同规则；不按覆盖bp
打分或另选tie规则。整条CDS链须包含于该owner record的halo，否则标
`boundary-incomplete`、单独报告并从primary分母排除。CDS最小start不在DEV core者
不进入primary；halo重复只保留owner record中的链，再按链身份去重。
stop-codon convention仍须在evaluator实现时对齐RefSeq与Tiberius并冻结，目前不作
科学评分；不能把该未完成项掩盖成已经可用的链级结果。

同时报告chain precision/recall、相对M0 gained/lost正确链及gene映射、新增unmatched
predictions、全部新增mask落在CDS/exon/splice的bp，包括comparator-positive bp。
TE comparator-positive不自动等于gene-safe。现有gene-safety evaluator只报告区间风险，
不能代替该链级评估。

旧讨论的`F1 gain>=0.005`、`lost correct genes<=0.1%`仅为待决投资草案，不是本轮PASS
阈值；分母、离散允许损失数与完整科学评分须先冻结。准备/smoke的PASS只证明输入、
softmask通道、推理可用性及坐标转换，不支持partial-fill学习成功、独立生物学实例恢复
或gene annotation方法优越性。

## 停止与下一阶段

源资产/坐标/配对失败按真实工程原因停止对应smoke；不转为科学NO-GO，不放宽参数。
不触碰已关闭Stage1输出、旧conditional历史或`ACTIVE_GOAL.json`。A未实现完整trainer
以及C未完成完整链归属/运行成本验证时，保留准备状态；禁止自动晋升full/scale。
成功smoke之后只在用户授权及共享预算范围内决定下一步，confirmatory gate单独保持封存。

## 本轮执行记录

- C reference-only `12399185` COMPLETED0:0 in1s；7/7 allocated testsPASS。
  1764chr13转录本中595noncoding、830outsideDEV、9boundary-incomplete；
  330eligible transcript rows去重为243条完整CDS链（重复87）。逐core分母
  `0:0,1:0,2:0,6:79,10:19,14:42,15:9,18:74,20:20`。
  M0-correct分母尚未产生且最多243，故旧草案0.1%允许损失在本panel只能为0条；
  不将其转成既定门槛。输出 `reference-20260905-r1/reference_chains.json`。
  paired GTF分支仍provisional且未执行；真实exporter/stop-codon convention待runtime输出验证。

- C 全9core修复重跑 `12398970`；先运行4项定向测试，再构建
  `outputs/GAP-BRIDGE-DOWNSTREAM-C-R1/masks-20260905-r2`。
  positive-projection改为排序区间单游标求交，不为每个候选重扫整chr13。
  实际COMPLETED0:0，用时26秒，4/4测试PASS；全部9core、60574候选，
  MW新增143476bp（17660全P gap），MP新增461752bp；475 unknown bp不新增mask。
- C runtime `12398977`，依赖`afterok:12398482:12398970`，1GPU×2h上限。
  首次400050bp技术smoke三mask，不是全9core科学评价。

- C 容器准备 `12398482`，0 GPU，官方2.0.7镜像与专用`te_gap_tiberius_c`环境。
- C 首次 mask 作业 `12398578`：12秒后 FAILED，候选表只有6个有候选DEV block，
  尚未创建FASTA输出。修复只恢复冻结split的全部9core，不缩小范围。
- A `12398722`：COMPLETED 0:0，62秒；8候选真实smoke PASS，1个P3窗口、
  2个NT窗口，stats拟合741503条。8个crop全覆盖、finite、共享槽相等、H0新增槽为零。
  实际一个NT上下文仅覆盖686/4096bp（其余3410bp被截断），但本次crop均落在另一个
  完整覆盖的窗口；这不是全量候选覆盖证明。JSON总运行48.0秒，其中NT/P3推理
  0.291/4.545秒。无readout训练、收益评分或sealed test访问。
