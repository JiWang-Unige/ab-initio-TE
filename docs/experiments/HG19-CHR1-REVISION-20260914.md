# hg19 单染色体训练与注释修订：固定首轮

2026-09-14。用户已要求按 Pro 收敛方向开始推进完成；本轮采用下列有限实现。
这是新的探索性实验，不更改旧 H0/D/P3 或任何已封存的验收。

- 单一 GLM：原生 NTv2-500M pretrained encoder + seed42 新初始化二分类头；不会加载 H0/D/P3 的 TE 权重。复用的初始化 helper 只读取 H0 config 作结构比较。
- 旧序列/比较注释：现有 hg19 FASTA 和 hg19 UCSC rmsk；精确路径固定在同名 JSON。该文件的真实库/引擎生成版本仍待闭合；不因 hg19 名称就称之为2009年标签。
- TRAIN 只在 chr1；预先从8192 bp无重叠网格按seed42选3000tiles。CAL chr11/256tiles、DEV chr13/256tiles；EVAL chr2/834、chr3/833、chr4/833，约20.48Mb。只用旧序列≤1%非ACGT条件筛选，不按新注释或模型得分选择。
- chr16/18保留现有效用用途；chr19–22及对应版本区域不进入本实验。染色体留出不是同源family/copy留出，也不证明GLM预训练未见该序列。
- 标签P为明确的SINE/LINE/LTR/DNA/RC/Retroposon；Unknown/模糊类与非ACGT为ignore，其余为旧比较注释下的N。N不是经独立实验确认的非TE。ignore优先；训练半窗完全不可评分时停止准备，不偷换窗口或标签。
- 训练复用已有4096 bp半窗、8192 bp pair、每步6tiles的单物种ERM循环；4000更新、400 warmup、AdamW 2e-5、正类权重3，final-step-only。先运行2-update独立工程smoke，输出与正式训练分开；不挑选DEV最优checkpoint、不增加seed。
- CAL-only标定与阈值；新注释不进入训练、CAL或checkpoint选择。先冻结旧预测及表观FP、匹配背景，再检查新版支持；同时计算新增FN及旧阳性删除。没有稳定新旧同引擎库对照时，只能称annotation-revision support，不能写library-only因果效果。

执行：CPU准备→原生encoder初始化/2-update GPU smoke→固定正式训练→CAL/旧注释评估→新旧同assembly审计→跨assembly唯一、双向、序列一致的映射分层。后续阶段必须读取前一步真实结果，模型训练完成不等于FP被新注释证实。

新训练范围与预算在任何模型结果前固定；本文件不宣告训练、推理或跨assembly验证已完成。旧框架goal/claim审批文本不作为自动研究流程恢复。

## 首轮实际执行

CPU准备作业12695213于2分12秒完成。TRAIN chr1的3000tiles含11,876,062 positive bp、12,685,204 comparator-negative bp及14,734 ignore bp；所有训练半窗可计算损失。CAL/DEV各256tiles，EVAL合计2500tiles与预先配置一致。原始序列和labels仅保留Baobab，紧凑[准备报告](../../reports/HG19-CHR1-REVISION-20260914/preparation.json)已归档。尚无新模型效果或新版annotation支持比例。

后续独立来源审计 **12698548 COMPLETED**（2分16秒）：与[UCSC原始hg19输出及版本说明](https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/)在chr1/2/3/4/11/13直接比较，两侧均1,918,650条记录，其中1,610,832条明确TE；TE坐标+strand以及有效P/ignore区间全部一致，TE覆盖513,685,346bp。逐记录的差别仅为`repFamily`空值/继承class的表示，不能称所有原始记录完全相同。官方文件标为RepeatMasker open-3-2-7、`-s`、RepBase20090120；本次可以陈述“有效材料标签匹配2009初始注释”，而非只根据hg19组装名称推断。详见[来源审计](HG19-CHR1-REVISION-20260914-2009-PROVENANCE.md)。此结果没有改动已经固定的训练配置/数据，也不把2026年的预测称为2009年预测。

两步GPU工程smoke **12695949 COMPLETED**（1分48秒）。初始化报告确认441个encoder tensors逐项与原生来源相等、classification head新初始化、没有未知缺失/多余权重；human是唯一训练物种，3000 chr1 tiles是唯一任务训练来源，12个半窗损失/step均为有限值。记录归档在[smoke目录](../../reports/HG19-CHR1-REVISION-20260914/smoke-12695949)。这不构成检测效果结果。

正式训练 **12696116** 已在同一数据和固定配置下提交，资源上限为单RTX3090、8CPU、64GB、48小时。4000步完成后使用最终checkpoint，不按DEV选择模型。

2026-09-14正式训练已 **COMPLETED**，耗时1:14:25，恰好4000步、seed42。实际曝光为chr1的3000个唯一tile、24,000次呈现；其他任务训练物种曝光为0。[完成记录与来源](../../reports/HG19-CHR1-REVISION-20260914/full-12696116/completion.json)已复制，权重保留Baobab。正式评估12696405已自动启动；训练完成本身不构成跨染色体性能或新版注释支持结果。

`evaluate.py`在任何评价前检查准备配置、训练来源、固定步数、染色体/角色、半窗配对和数量；逐染色体推理并合并为human，避免复用旧多物种接口时覆盖同物种的多个染色体。chr11 CAL拟合非负斜率Platt，再按最大CAL bp-F1确定阈值（并列时更接近0.5，再取较高阈值）。随后只应用至chr13 DEV、chr2/3/4 EVAL，同时保留原始margin与精确坐标。旧注释bp指标是comparator agreement；tile截断的segment指标仅为材料拓扑辅助，不能解释为完整insertion恢复。新增数据/配对校验共5项测试通过。

随后加入EVAL全分母冻结导出：`old_confusion_intervals.bed`为BED6+tile_id，分别保留TP/FP/FN/TN的原坐标连续区间，ignore孔洞不压缩；`old_prediction_manifest.json`记录四种bp总量，并与既有评分逐项核对。TN对照池完整保留，匹配背景抽样尚未完成。导出不读取后续版本的标签，FP区间是旧比较注释下的材料片段，不能计为生物insertion。针对新导出的坐标孔洞、全部分母和截短输入又增加2项测试，目前本地共7项通过。37秒接口smoke运行早于该导出增补，正式EVAL将使用增补后的版本。

推理接口smoke **12696213 COMPLETED**（37秒），只使用每条染色体预先选定的前2tiles和两步smoke checkpoint，完成CAL→DEV→EVAL全接口；[紧凑输出](../../reports/HG19-CHR1-REVISION-20260914/eval-smoke-12696213/completion.json)明确标注 `ENGINEERING_INTERFACE_ONLY`，不参与正式阈值或checkpoint选择。正式评估 **12696405** 以 `afterok:12696116` 提交，必须等待4000步完成并满足脚本检查后才执行。

## 正式跨染色体结果

12696405 已完成，耗时6分22秒。最终checkpoint、chr11 CAL阈值和预定EVAL区域保持不变；原始margin及全量区间留在Baobab，紧凑[结果](../../reports/HG19-CHR1-REVISION-20260914/eval-full-12696405/eval_metrics.json)已归档。

| EVAL | bp precision | bp recall | bp F1 | segment F1@IoU.8 |
|---|---:|---:|---:|---:|
| chr2 | .947465 | .931836 | .939585 | .556785 |
| chr3 | .953107 | .936692 | .944829 | .573484 |
| chr4 | .953645 | .942591 | .948086 | .570620 |
| pooled | .951502 | .937179 | .944286 | .566925 |

全量2,500 tiles，20,464,212 callable bp；TP=9,275,413bp，FP=472,770bp，FN=621,748bp。四种旧状态连续区间均已导出并与bp分母核对。这里的“FP”仅相对于旧比较注释；segment仍是tile-clipped材料结构，未赋予插入实例含义。

接续12705502映射资格也已完成，97,242区间中的93,116通过唯一双向等长度资格，覆盖源17,120,893bp；旧FP为21,235/21,402个通过。完整失败类别保留，详见[映射附录](HG19-CHR1-REVISION-20260914-mapping-qualification.md)。尚未由此建立内部逐bp双射、独立TE确认或新版F1。
