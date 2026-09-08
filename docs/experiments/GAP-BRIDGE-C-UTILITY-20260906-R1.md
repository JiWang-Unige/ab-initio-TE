# C fixed nine-core mask utility experiment

> 2026-09-08 closure: 12416179 COMPLETED 0:0 / 2972s; 27/27 cells verified.
> MW/MP both fail the frozen utility gate (gained=0 in both). Gene-utility
> expansion closed by the user's automatic rule; see
> [full result](GAP-BRIDGE-C-UTILITY-20260906-R1-RESULT.md). Execution-start notes below are historical.

## Authorization and frozen question

2026-09-06 用户明确回复“批准”，批准完整 **9 core × 3 mask** 实验，并采用
“链F1增加、至少新增1条正确链、零丢失M0正确链”为探索性继续门。
本协议在任何完整三臂结果之前锁定；不把工程readiness中已查看的core6 M0
描述性结果当作新独立证据。实验ID `GAP-BRIDGE-C-UTILITY-20260906-R1`。

问题仅限：固定chr13 DEV候选上的mask干预，是否改善固定Tiberius的完整CDS链？
它不是TE模型训练、真实插入重建、独立确认、SOTA比较或统一动物L1交付。
旧INIT/G-R-H NO-GO、P3、chr19–22/旧CONF/外部保留物种封存不变。
不是DEC-001/002的decoder/threshold重调；干预发生于固定基因预测器的softmask输入。

## Inputs and controls

- 原 `masks-20260905-r2` 的全部DEV core：0,1,2,6,10,14,15,18,20；原core及100kb halo。
  前三个零候选、零参考core也完整执行并计入FP；不得按结果删core。
- M0原P3；MW只加原候选中known全P的whole gap；MP加原候选中的comparator-positive bp。
  不改FASTA字母、mask、candidate、Unknown或halo；不重建mask。
- 所有27单元在新目录重新运行，同一Tiberius2.0.7源码
  `4d657012a3ed4e923f5d0ac5cef65fecae8109bd`、已验证SIF及其固定权重配置
  `mammalia_softmasking_v2.yaml`，seq_len400050/batch1；顺序core升序，每core M0/MW/MP。
  不换seed、参数或checkpoint，不搜索模型。重复core6 M0计入预算，不算独立重复。
- 参考仍为hg38 `ncbiRefSeqCurated-20250813.txt.gz`，原eligibility、owner及完整链规则：
  最小genomic CDS start属于core，整链在owner halo内，仅owner record；330来源行去重为243链。
- 端点复用 `GAP-BRIDGE-C-ENDPOINT-20260906-R1/endpoint.py` 的native CDS-only解析。
  CDS已含stop，不并辅助start/stop_codon、不改phase或端点。真实exporter及非空
  core6 M0作业12416061已验证；不重写旧provisional evaluator。

## Locked evaluator and decisions

主指标为所有九core **micro complete-CDS-chain F1**：2ΣTP/(2ΣTP+ΣFP+ΣFN)，
精确匹配strand和每个CDS半开区间。保留每core TP/FP/FN、P/R/F1；无分母的局部值为null。
每个MW/MP相对M0分别报告delta F1、gained/lost正确链明细、新增unmatched链、
全部解析排除计数及明细（含boundary_incomplete/nonowner/outside）、halo端点接触数。
评价器不因预测不以ATG/stop结尾、不满足mod3或不匹配参考而过滤；序列/phase局限须保留。
固定Tiberius自身既有的最短CDS200bp及in-frame stop后处理仍保留，并非新增评价器过滤。

每臂继续门同时要求：`delta_micro_f1 > 0`、`gained_correct_chains >= 1`、
`lost_correct_chains == 0`。不使用四舍五入后的F1判门，不复活旧.005/.001草案。
新增unmatched和被排除预测完整报告，不能隐藏边界假阳性；无新增任意风险阈值。
另对所有chr13参考转录本（含不进入243链主分母者）的CDS/exon/intronic splice
dinucleotide计算新增mask重叠bp和受影响gene；是风险描述，不筛预测或事后修改门。
splice区间固定为每个真实内含子两端各2bp；重叠bp按每类union去重，gene清单去重。

- MW过门：本DEV支持whole-gap utility，才可进一步提案A；不是自动启动A。
- 仅MP过门：支持局部material干预，不为whole-gap A背书。
- 两臂都不过：停止以该预测器/面板gene utility为由扩张A；不调门再跑。
- 输出/坐标/输入/预算失败或27单元未齐：工程未完成，不作科学NO-GO。
- 结果限反复使用的chr13 DEV探索面板，243链不视为243独立基因组；无显著性/泛化主张。

## Runtime, tests and stop

一个private allocation，1RTX3090/4CPU/48GiB/2h，27单元顺序运行，预计约1h。
依据core6实测97秒模型推断、207秒整项readiness，2h留启动/完整预检余量；无自动重试。
A/C共享24GPUh，已有400GPU秒（含失败），本作业最坏再2GPUh仍在界内；单作业≤12h。
任何失败保留新目录/日志、停止后续单元，禁止覆盖已完成readiness和冻结输出。

实现仅在新exp目录，复用旧reference读取/native端点/实际one_hot观察器。
确定性单元测试覆盖micro而非macro、零参考core FP、gain/loss身份、单bp/strand、
重复记录、缺单元、GTF/GFF3不一致、mask新增CDS/exon/splice风险；独立code-review-gate
PASS后才提交。无需训练split或loss检查：无训练/拟合，模型与reference不相互写回；
几何必须等于原9DEV core，真实预检确认243分母、全部27输入字母和softmask。
`STATUS=COMPLETED`仅在27单元及最终配对汇总成功后写入；工程完成与科学门分别存储。

## A readiness update (not a C selection variable)

A12416056完成902.5秒CPU审计：926253候选，89个crop非完整（27部分/62无覆盖），
84个gap非完整；24/106760原生窗口存在缺失。没有删候选、填0概率或改窗口。
原全候选A输入契约被阻断，不启动训练；C仍使用之前固定mask，与此次coverage结果独立。

## Execution record

- 8项新定向测试及bash语法通过，独立只读Codex审阅PASS；代码与现行metric合同逐行核对。
- 既有pre_submit_gate对7个reviewed code/config文件在本机和HPC均PASS；并非新增指纹框架。
- 原生全N core也会按真实长度进入固定库的分组、one_hot、预测和export；没有特殊删除路径。
- 2026-09-06 CEST，作业`12416179`已启动于gpu034；1RTX3090/4CPU/48GiB/2h。
  运行目录`outputs/GAP-BRIDGE-C-UTILITY-20260906-R1/run-r1`；日志`logs/gap-c-utility_12416179.{out,err}`。
  本行只记录执行开始，最终工程/科学状态待27单元及配对汇总完成。
- 分配内8/8测试通过；真实exporter参考往返、27份FASTA/六通道及mask-gene风险预检完成，
  已进入`core0 M0`实际预测。并非27个预测单元已完成。
