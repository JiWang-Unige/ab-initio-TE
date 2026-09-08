# GAP-A-B1-SCREEN-20260908-R1：新预算内配对筛选协议

运行前锁定：2026-09-08。用户本轮持续授权包括新实验、首训、实现/seed/预算及前瞻指标
选择；无外部评阅或机器goal要求。本协议不修改旧A、G/R/H或C的冻结协议与结论。

## 为什么不执行原全量A

原Stage1作业12156002实际47:30:23/1GPU，仅旧全量两遍就超过本轮剩余23.0633GPUh。
这是全量直接复现的资源证据，不是A科学失败。新实验独立编号，缩为有界机制筛选；
两条新对照使用同一子集/特征，不能报告成原全量A或原全量B1的实验结果。

## 数据和前瞻抽样

- 只用原hg38 chr3/5 TRAIN以及chr13原9-core DEV候选及原所需窗口上下文。
  不拟合CAL，不读取CAL结果，不读chr19–22/旧CONF/保留物种；P3主mask不变。
- 原候选清单中按crop右端所归属的8192窗口索引，每64窗口形成一个524288bp训练块。
  先从所有TRAIN候选的几何确定非空块，不看target、family、seam或风险。
  每chr独立从排序块列表无放回选择ceil(块数/8)个块：NumPy default_rng(20260908)，
  顺序chr3、chr5；随后恢复坐标顺序。所选块实际ID与候选ID在首次prepare中落盘。
- 两臂配对训练使用所选块的known候选，剔除原coverage清单里crop不完整者。
  原74个TRAIN缺失不一定全在此次子集中；逐一记录实际排除者，不填0概率、不移NT网格。
  不完整候选仍保留在原母体。DEV全60574候选预测，known分母60569；不因结果删样本。
- 固定原P3七维stats和已完成NT三维seam stats，不重拟合。训练权重在实际所选完整
  known训练集上按原六长度层等总权重、层内长度加权并归一至均值1；缺长度层即不可实施。
- 原DEV homology purge只作挑战诊断，复用原全TRAIN建立的purge清单，是保守的筛除，
  不按本轮抽样重定义homology，不宣称新的独立泛化。

## 三个arms与训练

H0-O：完整143个P3通道/7 scalars，补成144/10后新增槽归零，坐标有序块。
HN-O：同容量，加入原生NT logit及三seam scalars，块流与H0-O完全相同。
H0-S：与H0-O输入相同，仅每遍训练块顺序按seed+pass确定性置换，块内仍按原坐标顺序。
缓存先正确拼接相邻窗口，因此置换块不改变任何crop内容或上下文。

- P3和NT冻结eval；8192/4096网格origin0，NT截断保持原定义，真实forward覆盖必须完整。
- head沿原Conv143→32结构扩为144→32、MLP202→64→1；其余层/dropout0.1不变。
- seeds17/42/20260902，三臂同seed初始化相同；两遍所选训练块，AdamW lr3e-4、
  weight_decay1e-4、betas0.9/0.999、clip1。无早停或best-seed选择。
- effective batch512，块末不足512也做一次更新；microbatch128累积得到同一加权均值。
  所有臂每遍每候选一次、相同更新数。H0-O/HN-O同seed/update/micro的dropout随机源相同。
  H0-S使用同一随机源规则但样本块顺序不同；不混入其他优化变量。
- 只缓存一次float32配对输入（HN完整槽，H0执行时归零），重用两遍及各臂。
  不写整染色体latent；缓存计划上限180GiB，原始数据/冻结checkpoint不修改。

## 前瞻结果门和解释

每臂先平均三个seed的风险logits，再sigmoid。主分母原全部known DEV。
主指标是bp-weighted fraction-MSE：sum(length*(p_neg-negative/length)^2)/sum(length)。
同时报告literal pseudo-base Brier、不可约项、原精确tie-group action AP、每seed、
六长度层、原homology-purged DEV，以及未知候选数。分解须满足Brier=MSE+不可约项。

对HN-O/H0-O和H0-S/H0-O分别判定：fraction-MSE相对降低≥5%，且action AP不下降。
这是新探索性资源决策门，不是旧Stage1门，不代表显著性、可部署或gene utility。
H0分母为0或无正bp时结果不可判；不得记PASS。不得依据DEV结果改门、增seed或重采样。

- 过门：该有界信息增量/顺序机制筛选阳性，保留为有证据的探索性成功；不自动部署、
  解封或推翻旧G/R/H。若需后续阶段，须在任何新阶段评分前另记协议和剩余预算。
- 未过门：该有界候选实现的预定投资门失败，停止这一screen，不做lr/seed/样本比例扫描。
  不由缩样本筛选失败推导全量模型或整类NT/顺序方法被证伪。
- 工程失败/资源不足/数据缺失：如实记录未完成或不可实施，不记科学失败。
- C已结清，不复跑。Gate L缺独立truth/专家材料仍未实施，不用FlyBase packets冒充。

## 有界执行和预算

现有A/C累计3372GPU秒，24GPUh总上限不重置。CPU准备/测试经Slurm进行。
1. 单3090≤20分钟smoke：前两个已抽中TRAIN块，实际NT/P3提取及全部九head的有界训练；
   不计算DEV科学指标。特征可复用，smoke权重不进入最终训练。
2. 按smoke吞吐分别外推剩余特征与两遍全head训练/DEV推理，保守乘1.5；只有分别可在
   8h提取、8h训练+推理的限额内完成时才提交完整阶段。剩余预算不足同样停止。
3. 完整提取≤8h/1GPU，训练+DEV推理≤8h/1GPU；各job≤12h。单GPU/8CPU/96GiB，
   private-teodoro-gpu，既有te_benchmark环境。评价汇总CPU-only，不占登录节点计算。
4. 以上最坏新增16h20m，加旧消耗仍<24h。工程修复最多两次，累计额外GPU上限4h，
   且任何时候实际已用+所有待执行作业最坏时长必须≤24h；不因失败重置预算。
   不重跑完成的提取块/阶段；只有确切不完整产物隔离后才能修复。

代码与适度定向测试由当前Agent审阅；不调用第三方评阅。结果收集、解释和记录完成
才结清本实验。此前恢复文档的全量A提案被本独立screen替代，旧协议仍保留。

## 执行记录

- 2026-09-08：当前Agent源代码审阅、Python语法和sbatch语法检查完成；提交CPU
  准备/4项定向测试作业12497152，4CPU/16GiB/10分钟/0GPU，尚非科学实验结果。
- CPU12497152 COMPLETED0:0/39s，4/4定向测试通过；几何抽样固定90个TRAIN块、60个
  DEV块，90132个所选known TRAIN中51个原coverage缺失，最终90081 TRAIN；完整60574 DEV。
  缓存估计88,865,960,920bytes，9485个P3窗口forward（块内必要carry含在其中）。
- GPU smoke12497161 COMPLETED0:0/323s。两块2132行、124P3/248NT窗口，实际P3特征
  231.996s、NT10.064s；全部九head各5次更新、训练22.343s，finite且配对初始化一致。
  无DEV收益。按预定公式含1.5余量估计提取27410.32s、训练/推理3784.38s，成本门通过。
  累计GPU已用3695s=1.0264GPUh，旧消耗未重置。
- 提交完整提取12497294（1GPU≤8h）及成功依赖训练/DEV推理12497296（1GPU≤8h）。
  即使两者均耗满，当前累计也不超过17.0264GPUh；smoke特征复用，正式权重重新初始化。
- 全部阶段已完成：提取12497294/18392s、训练预测12497296/1649s、CPU评价12497303/9s、
  独立复算12498578/105s均COMPLETED 0:0。HN-O SCREEN_POSITIVE，H0-S SCREEN_GATE_FAIL。
  详见[结果和解释](GAP-A-B1-SCREEN-20260908-R1-RESULT.md)。累计6.593333GPUh，未重试。
