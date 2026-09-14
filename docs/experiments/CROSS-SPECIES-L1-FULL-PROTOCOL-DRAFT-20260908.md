# 完整 L1 protocol 草案：尚不可冻结或执行

2026-09-08。状态：**DESIGN_DIRECTION_APPROVED / EXECUTION_NOT_AUTHORIZED**。
用户随后明确回复“批准”，同意以冻结P3主体、HN-O whole-gap增补、六物种
匹配重训为协议设计方向。此批准只覆盖协议完善，不包含训练、校准或解封。
下方历史待决定文字由文末设计细化替代；最终panel资格与总预算尚未闭合。
用户另已授权三种候选的公开元数据检索及历史暴露比对；该项已完成，见
[panel元数据核查](CROSS-SPECIES-L1-PANEL-METADATA-20260908.md)。下方元数据授权请求为历史记录，不需重复批准；未扩展为序列、标签或模型执行授权。
这不是完整已冻结协议，不授权训练、校准、封存数据读取或最终声明。
Label-A准备进度：12522308的CB4任务及同语义修复数组12664906的鸭嘴兽、紫海胆任务
均已完成来源、无Matrix错误、非空产物和坐标工程核验；12522308中有矩阵错误的两套原始
产物保留但不得消费。详情与失败证据见[panel元数据核查](CROSS-SPECIES-L1-PANEL-METADATA-20260908.md)。
这不改变本草案的`EXECUTION_NOT_AUTHORIZED`状态，也不允许以工程完成替代独立资格或科学门。
授权更新：用户在完成三组装准备后明确回复“全部批准”，批准继续所述L1准备与后续流程。
不再将已说明事项重复作为许可缺口；但尚未定义的数据资格、同源参数和资源上限不是
已冻结事实。全规模执行仍须满足目标第6项的协议/资格/门/预算完整性条件。
资源授权更新：用户明确“不设上限，完成任务为首要目标”。新阶段不设用户总GPUh、
CPUh或存储硬上限；旧20GB仅对应已完成的下载准备。保留用量估计、实际记账、
集群单作业限制及工程/科学停止规则，不再将缺少数值上限作为授权阻塞。
[A/B1结果](GAP-A-B1-SCREEN-20260908-R1-RESULT.md)已完成；HN-O机制GO，
H0-S机制NO-GO。终端L1仍NOT_COMPLETED。

## 目标、已知事实和不可跳过的设计决定

目标仅为相对于项目RepeatMasker+Dfam Label-A的跨物种TE-material bp mask。
不涉及insertion identity、生物学完整真值、gene utility或universal model。

HN-O是Human hg38 gap候选的negative-fraction风险head，不是逐碱基分割模型。
当前训练数据仅chr3/5的90081候选，DEV仅chr13；冻结P3和NT特征，三seed
17/42/20260902。预测代码只输出候选logits，没有本轮CAL或完整mask决策。
因此不能将其risk直接叫作全基因组TE概率，也不能用本次DEV拟合action阈值。
既有L1 FASTA接口接收NTv2 token-classification checkpoint，并不接收该gap head。

建议下一项待批准的模型设计是：**冻结P3主体mask，HN-O仅为满足原候选几何的
whole-gap增加材料**；保留H0-O作为同容量对照、未修饰P3作为实际基线。
这是新mask决策协议，不是已获批screen的默认部署步骤。其限制是不能删除
P3假阳性，不能恢复没有合格gap候选的漏检，不能由Human排序收益推断跨物种收益。
不自动换成D、PAIR8或LOSS-MASS候选，也不执行额外训练来绕过该设计决定。

批准该方向后仍须在任何新科学评分前明确：是否仅冻结现有Human head作transfer，
还是使用六物种TRAIN重训匹配heads；后者需要新的跨物种候选清单、stats和覆盖可行性。
这两者科学问题和成本不同，不能将其混写成同一已冻结实验。

## 数据资格：目前未有已证明合格的独立终端panel

现有六物种训练资产声明为human hs1、mouse mm39、chicken galGal6、zebrafish
danRer11、pig susScr11和c_elegans ce11；注意Human hs1并非本screen的hg38。
不得把hg38候选坐标直接应用于hs1。若采用跨物种重训，需新注册准确assembly、
TRAIN/CAL/DEV坐标及候选构建合同；保留既有标签、未知/歧义及缺失输入限制，
不能静默删掉难预测物种或不完整候选来保证可运行。

旧external角色为horse/equCab3、opossum/monDom5、fruit_fly/dm6，cattle/bosTau9
作replication。但发布准备记录指出这些物种有历史角色/实验暴露，尤其dm6曾为
train_core。角色表不是实际checkpoint暴露证明，不能断言已发生某个checkpoint泄漏，
也不能据其sealed名称证明独立性。

独立资格必须逐一记录：所有候选组成模型的监督数据、head拟合、模型选择、
阈值选择、历史项目评分反馈及backbone预训练暴露的已知/未知范围。
未能排除用于适应性选择的历史评分时，只能作旧panel复评，不能承担本目标的
真正独立终端结论。需要新panel时，须先批准具体外部物种/assembly/来源，
不能自动替换或借用旧CONF、chr19–22、保留worm染色体。

当前只查阅本地代码和来源/角色记录，未打开这些封存序列、标签或科学结果。

## 评价合同草案（最终候选及panel明确后一起批准）

- 三seed均保留，不替换、不挑最佳seed。建议沿用17/42/20260902；每seed独立
  校准和完整mask评估，主报告为每物种三seed算术均值，不把logit ensemble当重复性。
  已完成screen的ensemble门保持原定义，不被此新合同追溯修改。
- TRAIN只拟合模型；CAL只拟合该系统的全局校准及一个共享决策阈值。
  DEV只作预注册诊断，不调阈值。阈值搜索空间、损失、tie-break及whole-gap
  与原P3概率如何组成一个可用于AP的全域分数，必须在实现前补齐，禁止事后决定。
- 全部panel按自然prevalence评价，P>U>N及hard-N定义保持Label-A合同。
  无标签推理不能读取truth/callable来保留预测；评价的未知mask单独应用。
- 终端全assembly门建议沿用原material-route的严格标准：每物种三seed平均F1≥.80，
  F1的95%空间区间下界≥.80，无seed/species F1<.78；平均P/R均≥.75且区间
  下界≥.73；macro F1下界≥.82，worst-species F1下界≥.80。
- 1Mb空间块、1000次配对bootstrap；CAL参数固定，所有seed及候选/对照共享抽样。
  不以空间CI声称seed总体CI，不删除undefined draw。RNG与跨物种汇总细则待精确定义。
- 报告每seed/物种的F1/P/R、raw-score AP和macro AP、六长度层、未知及有效质量。
  建议候选对实际基线每物种AP不下降；该新增门须随新协议批准，不能从screen AP代替。
- segment F1@IoU.8及原joint boundary5对实际基线下降≤.05；fragments/truth和split
  ≤1.25倍基线；missed-rate增加≤.03；macro hard-N FP率增加≤.005。
  boundary25、fusion、短预测率同时报告；连通材料段不是生物学插入实例。
- homology控制需明确具体比对/聚类单位与阈值、隔离到哪个split和结果分母。
  当前binary JSONL不保留完整family/copy身份，不能据此声称family-clean。
  保留natural完整分母及预注册同源挑战，不据测试效果重采样；family新颖性不作主张。

## 预算、执行停止及证据

A/B1实际23736GPU秒=6.593333h，已结清；旧24h预算不是新完整实验的自动授权。
完整阶段尚无可靠GPU估算：Human head训练27:29包括预测，不能外推六物种
全assembly P3/NT特征成本。批准设计后先以已授权TRAIN有界吞吐和实际assembly
长度计算三seed训练、CAL及全域预测上界，再提出具体GPUh/CPUh/存储硬上限。
上界未明确并获批前不提交全规模作业；不以缩数据、减seed或改窗口补预算。

工程/覆盖/数据资格/资源失败保留原产物及失败证据，记NOT_COMPLETED/BLOCKED；
修复只限明确原因且合同不变。科学门失败只在完整有效的已批准协议执行后才记
该终端候选L1-NO-GO；不得改门救援。全部门通过才记L1-GO，公开声明另需批准。

## 当前需要的具体决定

请先批准是否将后续候选限定为“冻结P3主体 + HN-O whole-gap材料增补”，
并明确采用现有Human heads的跨物种transfer，还是六物种匹配重训。
建议采用六物种匹配重训的协议设计，与完整跨物种模型目标对齐；现有Human heads
至多作冻结的归因对照，不能用更小的transfer试验替代完整终端方案。
这一决定只确定新协议对象，**不授权校准、封存评估或训练**。
随后提交具体独立panel资格/访问和资源请求；未通过资格者不能用旧panel静默替代。

依据：screen.py及stage1_model.py的候选输出定义；
CROSS-SPECIES-L1-RELEASE-READINESS-20260905.md的暴露记录；
species_x0_r2.tsv的assembly角色；CROSS-SPECIES-L1-MATERIAL-ROUTE-20260903.md
的全assembly评价合同。未读取CAL指标或重新计算封存数据。

## 批准后的设计细化（拟纳入最终执行协议，不追溯修改screen）

### 1. 模型、mask与排名是三个不同对象

固定screen使用的P3 checkpoint及NTv2-250M checkpoint，不换成500M D模型。
2026-09-08直接读取Baobab实际training_meta.json确认：P3为GENERanno-eukaryote-0.5b-base
经human_h0_w8192监督训练所得（seed42、max_steps800）；NT为NTv2-250M经
human_h0_w4096监督训练所得（seed42、3000 train/1200 val windows、max_steps1200）。
因此两者均不是仅有无监督预训练的组件；外部资格必须覆盖Human监督与模型选择来源。
原始元数据路径分别为screen.py指定P3目录下training_meta.json及NT目录下training_meta.json。
P3/NT均eval且不更新；只从同seed相同初始权重训练六个新head：
H0-O和HN-O各seeds17/42/20260902。H0-S已停止，不在新阶段重训。
模型维度144通道/10 scalars及head结构、两遍、AdamW3e-4、wd1e-4、
betas(.9,.999)、dropout.1、clip1、effective512/micro128沿用screen。
全部最终epoch2 checkpoint保留，不作DEV选模或seed替换。

P3主体集合B仍由原8192窗口、stride8192、origin0和阈值.5产生。
候选仍为相邻最大P3阳性runs之间1–512bp完整gap、左右各256bp真实ACGT上下文；
非合格候选按原label-blind规则abstain。NT4096网格和原截断语义不变。
在此规则下本应合格但实际NT/P3覆盖不完整者触发数据资格失败；不得零填、
移动网格或在外部评价时删掉受影响区域。其处理必须在新执行授权前明确，
不能把screen中既有coverage排除表移植到其他assembly。

每seed/arm校准后风险为r_i。最终mask为
`M = B union {entire eligible gap_i : r_i <= rho}`；仅fill或abstain，
不能删B、部分填充、改P3阈值、挑gap子集或加其他后处理。
运行时不读Label-A决定候选资格或保留预测；truth仅供评价分母。

全域排序分数明确为：B内2，合格gap内1-r_i，其余位置-1。
这是material priority score，不是全域校准概率；所有ties完整分组。
P3实际基线同样按B内2、其余-1计算AP；H0/HN使用同一种排序定义。
另报P3原始连续概率AP，但不拿它与上述不同分数定义混作机制AP门。
mask F1/P/R与这个无阈值排序AP分别报告。输出包含原P3轨、gap风险表和最终mask，
不宣称一个gap常数代表其中每个碱基的生物学置信度。

### 2. 六物种训练、采样及数据签署前提

拟复用D的既有TRAIN坐标：worm3000个8192bp tile，其余五物种各1500；
保留原六物种CAL/DEV各500tile和Human H0暴露排除，不引入SCREEN/CONF监督。
不把旧Human hg38 head或坐标改名成hs1；新候选必须按准确assembly重新构建。
候选归属由gap中点所在固定tile唯一决定；标签损失仅来自所属TRAIN候选，
必要原窗口上下文用于冻结特征。不能把tile截断的P3 run当作真实最大run计算长度：
需先生成所属染色体的冻结P3轻量mask，随后获取所需latent/NT窗口。
这会增加计算，必须计入预算，不默认已有全域P3缓存。

数据准备必须记录gap完整监督区间及上下文坐标。TRAIN监督与CAL/DEV监督不得重叠；
TRAIN与CAL/DEV输入上下文的实际重叠须在评分前处理并登记，不以旧tile不重叠替代。
既有CAL与DEV为开发数据而非独立测试；最终外部panel仍须与整个拟合/选择过程隔离。
若既有池不能满足拟定合同，不擅自重划分；停止准备并修订待批准数据附件。

为避免species候选数量决定梯度权重，拟采用每species每长度层等总质量、
层内按gap长度加权：w_i正比L_i / sum(L_j in same species,length stratum)，
再全TRAIN归一为均值1。任一species缺少一个必需层则不可实施，不补零或合并层。
这是六物种扩展的新权重定义，须与最终协议一起批准，不称为原Human实验复现。
两遍所有候选各见一次，species按human/mouse/chicken/zebrafish/pig/c_elegans，
各species按原坐标块有序流；H0/HN同seed/update/micro共享dropout随机源。
每块尾批保留；精确候选ID、权重、更新数由评分前的数据附件冻结。
P3七scalar和NT三seam scalar均拟使用本轮六物种TRAIN统计一次，H0新增槽归零；
零方差或覆盖不完整是准备失败，不事后启用兼容策略。

### 3. CAL-only拟合和全局action阈值

每seed/arm分别拟合单调Platt：r=sigmoid(a*z+b)，a>=0。
目标为候选negative fraction；使用自然gap bp质量且各species总权重相等的BCE，
不加class weight或正则。校准只读新合同允许的CAL，不读取DEV目标拟合参数。

同一CAL枚举全部完整风险tie-group加no-fill端点，直接计算六物种完整mask指标。
先最大化minimum-species F1，保留距最大值<=.001者，再最大化macro F1；
数值相同在1e-12内时选择更少added bp，再选择更小rho；no-fill作为独立端点保留。
阈值不得超出枚举集合，不按species单设，不用DEV或external改变此选择。
所得a/b/rho与模型路径冻结后，DEV和批准的独立panel各只评价一次。

### 4. 科学门与独立性

沿用上文拟定全assembly绝对F1/P/R/CI门及拓扑/hard-N门；新增AP门明确比较
相同全域priority-score定义下的候选和P3/H0，而不是旧screen的gap action AP。
建议对两个对照均要求每species三seed均值AP不下降，且拓扑门逐seed/物种通过；
所有这些拟定门需在任何新评分前与执行协议一起批准。
空间抽样拟固定numpy default_rng(20260908)，每物种独立抽其占用1,000,000bp块，
共享draw用于所有seed/arms；每draw先算每seed/物种pooled指标，再取seed均值及
species macro/minimum。1000draw、线性2.5/97.5分位数，不重拟合CAL、不抽seed。
有undefined draw则报告并判完整性不可用，不通过删draw制造区间。

独立性最低要求是外部物种及其组装不参与本系统任一组件的任务监督、head拟合、
CAL、DEV选择或本轮适应性设计反馈。Backbone预训练暴露单列，不声称完全未见DNA。
已知历史项目评分影响方案者只能旧panel复评。当前旧external四物种不能自动填入
独立终端栏；仅“尚未解封”不够。需要获准的来源/assembly和组件暴露附件才能冻结。

family exposure按相同Dfam release的family accession/name记录TRAIN出现与外部出现，
不以binary mask推断family身份；对同源区间的比对工具/阈值及结果分母仍需明确，
未定义前不宣称homology-clean。天然TE同源不等于split泄漏：分别报告监督坐标重叠、
近重复序列暴露与共享family，不能用family删除把目标换成unseen-family任务。

### 5. 由实际吞吐约束的预算，而非自动增加预算

来自已完成extract.json：P3 17544.4608秒/9361窗口（8192bp），
NT 753.6322秒/18722窗口（4096bp）。折算约P3 63.55GPUh/Gb、NT 2.73GPUh/Gb，
合计约66.28GPUh/Gb（1Gb=10^9bp）。这是当前3090实现的经验外推，不是承诺上界；
尚未包含fullmask构建后额外latent读取、I/O、head训练、CAL和失败余量。
全域P3/NT共享于六heads，不能误乘六；必要重复forward也不能漏记。

最终预算公式须使用实际去重窗口数：1.5×(P3窗口数×1.87421秒
+NT窗口数×.040254秒+实测head/数据处理时间)，加已消费的新阶段工程时间。
第一次全染色体P3 mask pass与第二次候选latent pass分开计数，不能双向漏算。
float32候选特征约589864bytes/候选；缓存上限必须据冻结候选总数明确，
超出时不得未经预算批准改为反复推理。原screen6.593333GPUh独立记账且不重置。
在实际panel大小、候选/窗口数与来源资格未知时，不提供虚假的总GPUh或完工日期。

## 下一项授权请求（不包含模型执行）

候选设计已获批，不再重复询问。仍需授权独立panel准备范围：建议先允许公开
assembly与来源元数据检索及历史暴露比对，候选范围为鸭嘴兽、紫海胆和
Caenorhabditis briggsae，分别提供哺乳类、非脊椎后口动物及线虫层次。
这些是待核实候选，不声称本地已有合格数据或从未被backbone预训练见过；
先取得准确accession、来源、可用注释/Label-A构建路径、长度与暴露证据再提交选择。
本项拟授权仅公开元数据，不下载/打开FASTA或标签、不构建Label-A、不推理、不训练，
不打开旧CONF、chr19–22或旧sealed面板。若任一候选不合格，报告而不自行替换。
完成该准备后才可能提交带准确数据附件、同源控制和总预算的完整冻结协议。
