# L1 closure：当前执行边界与结果账本

更新：2026-09-08。以用户本轮 L1 closure 指令为准；本文不批准新科学协议。

## 当前判定

**L1 NOT_COMPLETED；HN-O mechanism GO，H0-S mechanism NO-GO。**
A/B1四阶段已完成且数值审计PASS，详见
[完整机制结果](GAP-A-B1-SCREEN-20260908-R1-RESULT.md)。
完整L1独立协议的[草案及设计缺口](CROSS-SPECIES-L1-FULL-PROTOCOL-DRAFT-20260908.md)
已记录；候选mask映射、独立panel资格和完整预算尚未确定，不能称为已冻结可执行协议。
用户随后批准了“冻结P3主体＋HN-O whole-gap增补、六物种匹配重训”的设计方向。
草案现已补充mask/全域排名、训练权重、CAL-only选择和按实测吞吐计算预算的规则；
仍待独立panel公开元数据准备范围授权及数据/预算附件，不启动模型执行。
旧 B0、初始化和 PAIR8 的有界科学阴性保持有效，
但这些结果以及当前 A/B1 的任何阴性都不能代替完整独立协议的终端 L1-NO-GO。

已读取本轮指定的 A/B1 screen、material route、upstream、init-history、
pair-context 和 gap terminal audit 六份协议/报告。继续按
[A/B1 冻结协议](GAP-A-B1-SCREEN-20260908-R1.md)处理现有运行，
不执行另存的 LOSS-MASS 提案，不恢复已关闭的模型分支。

## 现有执行链

Slurm 实时核对：提取12497294在gpu034运行，核对时已用4:58:08；
其余作业均PENDING/Dependency，未重复提交、取消或改变资源。

| 作业 | 已注册动作 | 成功依赖 |
|---|---|---|
| 12497294 | 冻结NT/P3特征提取，1GPU，最多8h | 已完成准备及smoke |
| 12497296 | 三臂、三seed训练与DEV预测，1GPU，最多8h | afterok:12497294 |
| 12497303 | 冻结指标和门判定，CPU，最多10min | afterok:12497296 |
| 12498578 | 独立算术实现与分母/训练消耗核对，CPU，最多10min | afterok:12497303 |

输出根目录为`outputs/GAP-A-B1-SCREEN-20260908-R1/`。收尾需要完整
`extract.json`、`training/summary.json`、`predictions/complete.json`、
`result.json`和`numerical_audit.json`，并核实上述作业终态。
原始cache、逐块预测、权重和失败证据保留在原位置，不加入Git。
现有8h+8h上限连同既有3695GPU秒，最坏合计17.0264GPUh，仍属原24h预算；
实际消耗待终态账本，不把这个上界当实际用量。

## 科学分母及判定

### 提取完成、训练已启动

12497294已COMPLETED0:0，用时18392秒（5:06:32）。`extract.json`已收集：
新写148523行，复用smoke的2132行，合计150655=90081 TRAIN+60574 DEV；
本阶段9361个P3窗口加smoke124个，合计9485，与冻结计划一致。
实际GPU累计3695+18392=22087秒（6.1353GPUh）；训练若耗满8h，
累计上界14.1353GPUh，未增加或转移预算。
依赖训练12497296已在gpu034启动；CPU结果汇总和审计仍等待原成功依赖。
这仅证明提取工程阶段完成，不代表九head训练、预测完整性或科学门通过。

- H0-O、HN-O、H0-S；seeds17/42/20260902全部保留。
- 仅Human hg38 chr3/5 TRAIN与chr13 DEV：90081训练候选，60574预测候选，
  60569 known DEV及5 unknown。无跨物种screen分层可报告；其他物种为未评估，
  不以历史跨物种分数补充本轮分母。
- 主比较先平均三seed风险logits再sigmoid；HN-O及H0-S分别相对H0-O要求
  bp-weighted fraction-MSE相对下降至少5%，且exact-tie action AP不下降。
- 保留每seed、六长度层、原全TRAIN homology-purged DEV挑战和Brier分解。
  挑战分母不是新独立held-out。已读现有评价与数值核对代码，尚无完整真实结果。
- 完整有效且过门：对应mechanism GO；完整有效且不过门：对应mechanism NO-GO；
  缺产物、工程/资源失败或不可判分母：NOT_COMPLETED，不作科学阴性。

## 终端目标与下一个人类批准点

若机制过门，准备新的完整L1协议，但不自动执行。必须在训练/独立评估前明确
训练数据、真正独立held-out资格、三seed、CAL-only校准、固定阈值、每物种
F1/P/R、macro F1、AP、segment/boundary和hard-N门、homology/family暴露控制、
预算及失败停止规则，并取得新科学协议及必要数据访问授权。
历史material-route列出的external panel有历史项目暴露，不能仅凭“sealed”
名称认定首次独立盲测；须在不读取封存科学结果的范围内核实其资格。

当前不读取CAL科学结果、旧CONF、chr19–22、保留染色体或封存物种；
不改标签、split、窗口、缺失策略、阈值或科学门。完整独立协议尚未执行，
所以目前既不能给L1-GO，也不能给终端L1-NO-GO。

最终主张仅限相对于项目RepeatMasker+Dfam Label-A的跨物种TE-material
base-pair mask计算模型；不外推insertion identity、完整生物学真值、
gene utility或universal model。最终公开声明仍须用户批准。
