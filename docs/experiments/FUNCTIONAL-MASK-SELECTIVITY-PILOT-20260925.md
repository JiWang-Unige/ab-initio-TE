# FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925

状态：**两物种十个core、四个新臂及评分13192933/13192934全部完成并核对；已达可解释停点。不是独立确认测试。**

[两物种结果及下一阶段建议](../../reports/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/CLOSURE-20260925.md)：鱼原始D较完整RM2的F1差为+0.015632，但同预算D较RM2随机/可信度筛选分别为−0.000817/−0.000970，区间跨零。鸡的同预算位置选择信号未在鱼重现；保留应用价值，不升级为跨物种功能选择性已确认。

本 pilot 只复用已经暴露的鸡和斑马鱼 10×5 Mb core + 100 kb halo 用途面板、固定六物种 NTv2-500M binary D 输出以及同 assembly 的全基因组 RM2 输出。它不训练模型，不增加物种、seed 或 D 阈值，也不按 AUGUSTUS 分数更换区域。两个物种原来的 `D`、U、R_TE、RED 结果仍保留；新增结果只用于判断现有收益能否由 mask 覆盖量解释。

## 要检验的问题

原 D 与完整 native RM2 的掩码量和片段长度分布不同。pilot 检验两个互相竞争的解释：

1. 下游差异主要是 mask 多少造成的；
2. 在相同可比较的 mask 预算下，D 或 native RM2 的具体位置选择仍造成不同的基因结构结果。

因此，原 D 与完整 RM2 是原始用途臂；共同预算臂是人为干预，不能被写成新的固定 D 性能。

## 固定输入和评估边界

每个物种沿用 `NONMAMMAL-GENE-UTILITY-20260918` 的十条染色体、每个 5,000,000 bp core、左右各 100,000 bp halo。所有 mask 都在完整 5,200,000 bp AUGUSTUS 输入上生成和计数；core 只用于原有 gene-locus 评分。halo 参与 AUGUSTUS 输入并完整保留，但其 masked bp 只作为报告项，不在看到下游分数后重新调预算。

RM2 输入为 `WHOLE-GENOME-BENCHMARK-20260918/native/{species}/RM2-mask-recovery-v2/masked.fa`，不是重新发现或重新运行的库。`annotation.out` 只提供 native alignment 的置信度排序。每个 RM2 lower-case run 与同 assembly U 序列逐碱基大写一致，否则 preparation 失败。D 输入直接复用既有每 core FASTA 和已完成 GFF。

gene reference、locus 单位、core ownership、AUGUSTUS 3.5.0、同物种参数和 `--softmasking=1 --UTR=off --stopCodonExcludedFromCDS=false --alternatives-from-evidence=false --alternatives-from-sampling=false` 与原用途实验完全相同。reference 只在 score 阶段读入，不能指导 mask 构造。

## 五个掩码臂

| 臂 | 定义 | 是否为原始性能 |
| --- | --- | --- |
| `D_FIXED` | 原用途实验已经生成的固定 D mask/GFF | 是；保留原始 D 结果 |
| `RM2_FULL` | 完整 native RM2 masked FASTA 的同区域提取 | 是该输入层的原始 native RM2 臂 |
| `D_COMMON_RANDOM` | D mask 按长度层和固定坐标 hash 随机下采样到共同预算 | 否；干预臂 |
| `RM2_COMMON_RANDOM` | RM2 mask 按同一规则随机下采样到共同预算 | 否；干预臂 |
| `RM2_COMMON_CONF` | RM2 mask 在相同长度层预算内按 native 比对可信度排序保留 | 否；干预臂 |

U 和 `D_FIXED` 的既有 AUGUSTUS GFF 直接复用。其余四个输入臂中，`RM2_FULL`、`D_COMMON_RANDOM`、`RM2_COMMON_RANDOM`、`RM2_COMMON_CONF` 重新运行原生 AUGUSTUS；不重复计算已经完成的 U/D/R_TE/RED。

## 共同预算和片段长度规则

合并后的每个 lower-case A/C/G/T run 按完整长度落入固定层：`[1,16)`, `[16,64)`, `[64,256)`, `[256,1024)`, `[1024,4096)`, `[4096,16384)`, `[16384,65536)`, `[65536,∞)` bp。对每个 core 独立计算：

\[
q_b=\min(\mathrm{bp}_{D,b},\mathrm{bp}_{RM2,b}),
\qquad B_{common}=\sum_b q_b.
\]

所以共同预算是每个长度层的交集，而不是简单把较小一方补到较大一方。每个长度层分别决定哪一方需要下采样；当斑马鱼 D 的总 mask 大于 RM2 时，D 不会被补齐，RM2 也不会获得任何没有 native mask 证据的填充碱基。完整 D/RM2 原始臂始终保留。若某一长度层没有共同覆盖，该层贡献为零并原样报告。

随机臂在各层内按固定 seed `20260925` 对 `(species, core_id, arm, run_start, run_end)` 做 SHA-256 稳定排序，依次保留 run；最后一个超出配额的 run 只保留其居中的精确剩余长度。因而每一层的**来源长度层** bp 配额精确；最后截断片段可能落入更短的实际长度层，所以不声称输出片段长度分布完全相同。完整输入 bp、core bp、左右 halo bp、来源和实际长度层配额、run 数和残余差异全部写入 `mask_manifest.json`。

## Native 可信度臂

`RM2_COMMON_CONF` 不使用任意 divergence/score 阈值，也不看 gene score。每个 RM2_FULL run 接收与其重叠的 native RepeatMasker alignment 中最优的一条记录，按以下预先固定的字典序排序：

1. percent divergence 升序；
2. SW score / query alignment length 降序；
3. query alignment length 降序；
4. query begin 升序；
5. query end 升序；
6. native alignment ID 升序；
7. run 坐标作为最终稳定 tie-break。

然后在每个长度层按该顺序选到同一个 `q_b`。没有可映射 native record 的 run 留在 `RM2_FULL` 审计中，并排在可信度臂的最后；不被静默删除。该排序只使用 RM2 原生 alignment 字段，因此是一个可复现的“保守化”干预，而不是以 reference CDS 构造的 oracle。

## 评分和停止

所有臂使用原有 exact-assembly complete protein-coding CDS-chain locus reference、同一 core ownership 和同一 parser。主要诊断是共同预算下 `D_COMMON_RANDOM` 对 `RM2_COMMON_RANDOM` 以及 `RM2_COMMON_CONF` 对 `RM2_COMMON_RANDOM`；同时报告原始 `D_FIXED` 对 `RM2_FULL` 和预算效应 `D_FIXED` 对 `D_COMMON_RANDOM`。每物种按原协议做 10,000 次、seed 42 的固定染色体 bootstrap；这是区域敏感性区间，不是生物学重复不确定性。

无论方向都完成两物种十个既定 core 和全部新增 AUGUSTUS 预测。结果不能把 pilot 开发诊断升级成独立外部测试，也不能因 pilot 失败而改区域、阈值、长度层、seed 或加入第三物种。等覆盖干预如果追平 D，中心主张应退回“收益主要由覆盖量/保守程度解释”；若 D 在共同预算下仍优且 RM2 可信度臂不能复现，则才有理由继续冻结更强的独立证据确认包。

执行配置见 [`configs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925.json`](../../configs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925.json)，入口见 [`scripts/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/pilot.py`](../../scripts/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/pilot.py)。

## 执行审计（2026-09-25）

两物种 preparation 已以 exit 0 完成（chicken `13192925`，zebrafish `13192926`）。两个物种各十个 core 的 U/D/RM2 大写序列一致性均通过，且所有 RM2 lower-case runs 都能映射到 native `annotation.out`（`rm2_runs_without_native_alignment=0`）。共同预算按长度层、完整 5.2 Mb 输入、core 和左右 halo 的 bp 统计写入物种和 cell manifest；不得把 full-input 的预算相等解读为 core-only 相等。

规则审计先发现原 materialized preparation 不是全体都能由“旧 raw-SW”或“修订后的 SW/aligned-length”重建。保存的前修复 JSON 记录了三种状态：原 materialized（mixed/prepared）、旧 raw-SW reconstruction、修订后的 confidence reconstruction。修订后的重建与 zebrafish 十个 core、chicken 九个 core 逐区间一致；唯一例外是 chicken/c01，因此只保留该 core 的原 mask、GFF、command 和 manifest 为 `*-bugged-pre-repair`，重新物化并重跑该 core 的 `RM2_COMMON_CONF`。之后的 post-repair audit（job `13193129`）显示 chicken/zebrafish 共 20 个 core 全部与修订规则逐区间一致，旧 raw-SW 规则仍全部不一致。该修复没有重跑 `RM2_FULL`、`D_COMMON_RANDOM` 或 `RM2_COMMON_RANDOM`。

有效作业链为 chicken prediction array `13192930`、zebrafish prediction array `13192931`，以及 chicken c01 confidence-only repair `13193088`；两项 score 分别为 `13192933` 和 `13192934`，依赖对应 prediction array，且 chicken score 额外依赖 repair。所有人工 hold 已解除；prediction 任务按每物种 `%2` 并发运行。分数必须等全部新 arm 的 `status=COMPLETED`、command exit 0 和 GFF 检查通过后读取。

终态：以上全部预测和评分完成；80个新增GFF、原生命令及逐core计数通过核对，旧U/D指标逐项不变。终态审计另修复一个描述字段错误：原`source_length_strata`复制了截断后的实际长度分组，现由保留的selection records汇总真实来源层，60个共同预算臂全部满足原配额。原紧凑摘要另存，原生manifest、FASTA、GFF和分数不改；未重新运行预测。`terminal_audit.py`记录可重做的导出与计数核对。
