# L1候选panel公开元数据核查

2026-09-08；范围：用户授权的鸭嘴兽、紫海胆、C. briggsae公开组装/来源元数据及历史暴露比对。未下载或打开FASTA/标签，未构建Label-A，未训练、校准、推理或读取封存结果。

结论：三者均有可定位的公开组装，但目前没有一个被证明满足独立终端panel资格。以下是待选版本，不声称最新版本或已冻结数据附件。

## 组装事实

| 候选 | 核查版本 | 日期/级别 | Primary Assembly bp | 全部assembly bp |
|---|---|---|---:|---:|
| 鸭嘴兽，TaxID 9258 | GCF_004115215.2 / mOrnAna1.pri.v4 | 2020-11-06 / Chromosome | 1,859,264,908 | 1,859,281,927 |
| 紫海胆，TaxID 7668 | GCF_000002235.5 / Spur_5.0 | 2019-09-06 / Scaffold | 921,840,143 | 921,855,793 |
| C. briggsae，TaxID 6238，AF16 | GCA_000004555.3 / CB4；对应GCF_000004555.2 | 2014-07-02 / Chromosome | 108,384,165 | 108,384,165 |

来源为直接读取的NCBI assembly_stats文本元数据：[鸭嘴兽](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/004/115/215/GCF_004115215.2_mOrnAna1.pri.v4/GCF_004115215.2_mOrnAna1.pri.v4_assembly_stats.txt)、[紫海胆](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/002/235/GCF_000002235.5_Spur_5.0/GCF_000002235.5_Spur_5.0_assembly_stats.txt)、[CB4](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/004/555/GCA_000004555.3_CB4/GCA_000004555.3_CB4_assembly_stats.txt)。

鸭嘴兽RefSeq与GenBank GCA_004115215.4并不相同；紫海胆RefSeq与GCA_000002235.4也不相同，不能混用标签坐标。CB4报告两库版本相同。紫海胆870条核scaffold；网页的一个assembled molecule是线粒体，不是单条核染色体。CB4虽为Chromosome级，但有4,436个spanned gaps、2,965,486bp总gap，不能把级别当作无缺口。

## 暴露与标签资格

本机及Baobab项目文档/脚本/配置的物种名搜索，仅发现C. briggsae在既有T2验证规划中（`docs/23_te_refinement_publication_route.md:243`；本机`docs/11_master_plan.md:208`）。本机再查版本号及ornAna/strPur/cb4别名未发现额外历史使用记录。规划不是实际训练/评分证据；未命中也不是从未使用的证明。未扫描封存科学结果来补齐此项。

NTv2-250M的[发布者模型卡](https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-250m-multi-species)明确预训练于850个NCBI基因组，但本轮未取得逐assembly名单；公开数据集目录请求返回HTTP 401，未绕过权限。三种候选的确切backbone暴露均仍UNKNOWN，P3组件完整来源链也不能由此次名称检索替代。不得声称完全未见DNA。

NCBI基因注释或网页RepeatMasker masking百分比不是本项目冻结Label-A。三者均尚缺同版本assembly配套的本项目RepeatMasker/Dfam版本、family库、P/U/N合同和产物完整性证据。未来构建必须先批准具体来源及执行范围，当前不宣称标签已准备好。C. briggsae曾在验证规划中，因此在实际执行/反馈历史排除前尤其不能称为全新独立测试。

## 成本含义与决策

Primary Assembly合计2,889,489,216bp；按协议草案由已完成作业推得的66.28GPUh/Gb，首轮全域P3/NT计算外推为191.52GPUh（全部assembly口径191.52GPUh）。冻结backbone特征可供六head共享，不乘六。

这是经验外推，不是批准预算或可靠上限；尚缺第二次候选latent forward、六物种TRAIN/CAL/DEV准备、head训练、CPU标签/同源处理、I/O、缓存和失败余量。不得用原24GPUh screen限额授权新实验，也不据预算自行缩小panel。候选缓存约589864bytes/候选，候选数量未知，不能给出虚假总存储上限。

本次元数据准备已完成；完整L1仍NOT_COMPLETED。冻结协议前仍需组件实际监督/评分来源链、标签合同、同源挑战细则及有依据的总资源上限。当前证据不足以让用户直接批准执行；不自动替换候选、不把缺资格当科学NO-GO。

NCBI Datasets skill的脚本因缺requests无法运行，本次采用官方网页及FTP纯元数据回退；未安装依赖，未保存原始响应或生物序列。

## 下一阶段具体授权请求：仅来源锁定与序列准备

拟请求允许从NCBI下载上述三个准确版本的genomic FASTA及assembly report到Baobab独立新目录；不替换既有资产。限定GCF_004115215.2、GCF_000002235.5、GCA_000004555.3，不切换配对版本，不自动更新或更换物种。准备检查只确认文件可读、序列ID/长度与对应assembly report一致，并记录核/非核范围及缺口；不根据TE预测或标签筛选序列。总新增磁盘上限20GB，达到上限停止，不提交Slurm/GPU作业。

该请求不包括下载TE标签、生成RepeatMasker结果、同源比对计算、特征提取、模型训练、CAL、DEV/held-out评分、旧封存数据访问或发布。序列检查不能证明独立性，组件来源链仍需单独闭合；失败或暴露不明不能自动换panel，也不能报告终端科学NO-GO。

这只是待批准的准备范围，不是用户授权记录。完整执行仍须另行提交并批准冻结协议、标签/同源合同和资源预算。

## 序列准备执行记录（用户随后明确回复“批准”）

批准仅覆盖上一节来源锁定、下载及基础核查；不扩展到标签、计算作业或模型执行。
三份原始压缩FASTA和三份assembly report已下载至Baobab独立目录：
`/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/software_outputs/L1-PANEL-PREP-20260908-kqZrej`。
原始文件保留，未覆盖旧资产；下载命令退出0，目录实占886681431bytes，低于20GB上限。
下载逐文件上限3GB，六文件总上界18GB；实际未触及。未保存解压副本。

基础核查脚本为`scripts/experiments/check_l1_panel_fasta.py`（本机运行，通过SSH只读压缩流）。
首次执行报`ValueError: Assembly report/FASTA ID mismatch`，原因是配对报告含GenBank独有
线粒体CM016609.2（RefSeq列为na）；检查脚本误将na作为预期RefSeq ID。
最小修复为仅采用所选数据库有accession的报告行，不更改FASTA或生物学筛选条件。
该失败记录保留，不把首次解析失败称作组装损坏。

修复后完整执行退出0，三者均PASS：压缩流可完整解码、ID集合完全匹配且无重复、
每条序列长度与所选数据库报告一致。原样stdout保存在[L1-PANEL-PREP-20260908-QC.jsonl](L1-PANEL-PREP-20260908-QC.jsonl)。
鸭嘴兽/紫海胆/CB4分别322/871/367条序列，N碱基15,158,118/337,500/2,967,626；
均无ACGTN之外字符。N碱基数不等于assembly_stats的组装gap长度：鸭嘴兽多16bp、
CB4多2140bp；两种统计不能混用，此处不改变或填补N。

本次已批准的下载与基础核查完成；未生成标签、未提交Slurm作业或调用模型。
完整L1仍NOT_COMPLETED：文件一致性并不证明任务监督/适应性选择独立，亦未补齐
Label-A、同源挑战与总资源预算。任何后续科学执行须按完整协议另行批准。

## “全部批准”后的来源核对

用户随后明确批准继续完整流程。已说明事项不再重复索取许可，尚未定义的资源数量和
科学参数仍需具体化，不能把未知值称作已冻结参数。未因此打开旧封存评分或修改科学门。

直接读取实际checkpoint training_meta.json：P3源于GENERanno-eukaryote-0.5b-base，
监督数据为human_h0_w8192；NT源于NTv2-250M，监督数据为human_h0_w4096。
这补齐了组件的直接监督来源，不等于其全部上游来源或历史反馈独立性已证明。

从实际历史Label-A的
`software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617/c_elegans/chunks/c_elegans_chunk_00002_bundle/RUN_METADATA.txt`
核实：`RepeatMasker version 4.2.2`；语义参数`-xsmall -gff -species Caenorhabditis elegans; no -a`，
线程`-pa 4`，source_libdir为该run的rm_lib_overlay。
对应提交脚本使用CONS-Dfam_3.9，并允许部分manifest行的custom library；必须逐训练物种
核实是否实际用了custom library，不能以脚本默认值替代消费记录。
工具许可文档中的4.2.4不能代替这条实际4.2.2来源证据，当前不升级或重跑标签。

随后遍历六训练物种全部128条chunk的RUN_METADATA：worm3、chicken18、human24、
mouse28、pig22、zebrafish33；无缺失记录，所有记录均4.2.2，均为各自物种的
`-pa 4 -xsmall -gff -species <scientific name>; no -a`，没有`-lib`消费参数。
因此这六物种的实际工具版本/命令一致性已闭合；Dfam实际库来源仍需单独核实。
元数据解析首次遇到`_csv.Error: field larger than field limit (131072)`，按已有脚本方式
设置csv.field_size_limit(sys.maxsize)后完成，未修改原manifest或任何标签。

## 资源放行后的实际进展

用户明确资源不设上限、完成任务优先；不再索取数值预算上限。实际消耗仍记录，
保留集群单作业时限和失败停止规则。读取FamDB root属性确认db_name=Dfam、
db_version=3.9、famdb_version=2.0.0、db_date=2025-03-10；当前RepeatMasker -v仍为4.2.2。

已提交Label-A准备数组12522308（0鸭嘴兽、1紫海胆、2CB4），4CPU/64GB/7天每task，
不申请GPU。脚本`scripts/experiments/submit_l1_panel_labela.sbatch`沿用`-xsmall -gff
-species`、no-a和同一Dfam来源，为每task建立独立可写library cache及产物目录。
只生成比较标签，不消费模型输出、CAL/DEV/测试指标或根据标签挑选panel。
最近观察为PENDING/Priority；未重复提交或改资源。提交不等于生成成功或科学PASS。

六物种坐标附件核对：X0-R2/12175761/tiles.tsv的TRAIN/CAL/DEV，加
UPSTREAM/materialization/12306000/manifest.tsv的worm TRAIN3000（不读取CONF）。
总TRAIN10500，CAL/DEV各3000；TRAIN与CAL/DEV在每物种均为不同染色体。
原tile跨split无重叠，但不能据此声称增广候选上下文不重叠。
CAL/DEV最短tile间距：worm0、zebrafish8192，其余human/mouse/chicken16384、pig40960bp。
间距<16384的跨角色相邻tile对为worm3、zebrafish2。完整gap/feature窗口所有权
可能跨tile边界，仍须在候选准备阶段逐项核实，不自动改split或移除困难输入。

已为本次完整结果处理安排每小时回查（应用任务ID `l1-label-a-preparation-follow-up`），
仅对12522308及其后续已授权的准备工作行动；无变化时静默，处理完毕或需要用户决定时暂停。
最近调度估计首task于2026-09-09 06:27:26集群时间开始，估计可能变化，不作为完工承诺。
本记录不是L1终端结论，亦不授权重复提交已存在作业。

### 2026-09-09首次完成子任务

23:37 UTC回查：12522308_2（CB4）COMPLETED 0:0，耗时00:12:24；
_0鸭嘴兽与_1紫海胆仍RUNNING（分别gpu035/gpu034）。未重提、取消或改资源。
CB4运行元数据与指定组装、4.2.2、Dfam3.9及物种命令一致；out、gff、tbl、masked均存在，
ProcessRepeats输出done。尚待标签坐标完整性核查，不把作业退出0代替最终数据资格。
stderr有`gzip: stdout: Broken pipe`，原日志保留，来源尚未定位；不据此重跑已完成任务。
实际库选择日志报告仅curated families：16个祖先分类群family、0个物种lineage-specific family。
这是当前Label-A的覆盖局限，不是模型结果；不得自行纳入uncurated库或换物种改善表现。

00:37 UTC回查：_0/_1仍RUNNING，_2仍COMPLETED 0:0。完成CB4 `.out`全部32,903条
记录的坐标核查：query ID均属于准确GenBank assembly report，1-based inclusive区间均
合法，`end + remaining query length`均等于对应序列长度；invalid_records=0。
本项不计算模型指标或据标签分布作选择。gzip警告来源仍未确证；源码存在ProcessRepeats
读取gunzip子进程的管道，但没有证据把该警告唯一归因于此，因此保留未决标记。

01:38 UTC：_1紫海胆COMPLETED 0:0（02:29:58），_0鸭嘴兽仍RUNNING。
两者stderr均出现`Matrix::parseFromFile: Could not open .../Matrices/crossmatch/simple1.matrix`。
该矩阵用于RepeatMasker的TRF结果处理（源代码2737附近），可能影响hard-N标签，
故即使退出0且out/gff/tbl/masked存在，也不能宣布这两份标签有效。
紫海胆来源元数据正确，实际库选择14个祖先curated families、0个lineage-specific family。
登录节点当前源矩阵存在可读；尚不能确定计算节点当时读取失败的底层原因。

已仅修改本机后续提交脚本：恢复历史作业的矩阵实体复制方式（cp -RL），并检查
simple1.matrix与18p35g.matrix可读。未修改已提交副本、运行目录或既有作业，未重提。
本次原始错误和产物保留；待_0结束后汇总有效性，再决定修复尝试，不能将错误当科学NO-GO。

### 2026-09-12 Label-A结果处理与最小修复

数组12522308三个task均已结束且Slurm为`COMPLETED 0:0`：CB4（_2）00:12:24、
紫海胆（_1）02:29:58、鸭嘴兽（_0）16:03:48。三者的`RUN_METADATA.txt`都与指定
assembly、`RepeatMasker version 4.2.2`、`Dfam=3.9`及`-pa 4 -xsmall -gff -species`
（无`-a`）一致，且out/tbl/gff非空。CB4无矩阵错误；其32,903条`.out`记录此前已逐条
核对为准确assembly ID和合法1-based inclusive坐标。

不过_0和_1的stderr都记录
`Matrix::Matrix::parseFromFile: Could not open .../Matrices/crossmatch/simple1.matrix`。
RepeatMasker仍以0退出，但该错误会跳过TRF处理，不能把两套产物当作有效的Label-A；
原始运行目录、日志和产物均保留为失败证据。共同原因是初始脚本没有实体化矩阵目标；
这不是组装、物种、Dfam或Label-A语义问题。

仅为恢复这两个无效task，已用同一输入、物种、RepeatMasker/Dfam和资源提交修复数组
12664906（task0鸭嘴兽、task1紫海胆；2026-09-12 14:17 UTC开始时均RUNNING）。修复仅将
`Matrices`改为`cp -RL`实体复制，并把已观察到的Matrix解析字符串设为明确失败条件，
防止“0退出但TRF缺失”再次写成完成；不覆盖12522308产物、不重跑CB4、不改变标签语义。
修复task仍须完成来源、无Matrix错误和坐标/产物完整性核验。无论工程结果如何，Label-A
准备都不是独立资格、完整协议或L1科学PASS；未启动训练、CAL、独立评估或任何封存读取。

16:50 UTC：修复数组的紫海胆task（12664906_1）`COMPLETED 0:0`，耗时02:32:39。
其STATUS仍明确为`LABEL_GENERATION_COMPLETED_NOT_SCIENTIFIC_PASS`；运行元数据与准确
GCF_000002235.5组装、RepeatMasker 4.2.2、Dfam 3.9及指定物种命令一致。`.out`/`.gff`/
`.tbl`非空（分别752,980/753,672/58行），专用日志无Matrix解析错误并以ProcessRepeats `done`
结束。逐条流式核查752,977个`.out`记录：871个assembly report ID均已识别，所有区间合法且
`end + remaining query length`等于报告序列长度，invalid_records=0。`gzip: stdout: Broken pipe`
仍记录在日志中，但与初始任务相同且没有将其作为成功或失败的唯一解释。鸭嘴兽修复task仍在运行；
尚不宣布两项修复完成或把本工程核查替代L1科学结论。

2026-09-13 06:07 UTC：修复数组的鸭嘴兽task（12664906_0）也`COMPLETED 0:0`，
耗时15:50:00。其STATUS、准确GCF_004115215.2来源、RepeatMasker 4.2.2、Dfam 3.9和
指定物种命令均与合同一致；`.out`/`.gff`/`.tbl`非空（4,973,010/4,973,324/52行），
专用日志无Matrix解析错误并以ProcessRepeats `done`结束。逐条流式核查4,973,007个`.out`
记录：322个assembly report ID均已识别，全部坐标合法且与报告序列长度一致，
invalid_records=0。与其余任务一样，保留但不单独解释`gzip: stdout: Broken pipe`。

至此CB4的原task与鸭嘴兽、紫海胆的修复task都已完成工程核验；12522308中有Matrix错误的
两套原产物仍保留且明确排除。三份可用的Label-A工程产物分别是
`labela-12522308-2`（CB4）、`labela-12664906-1`（紫海胆）和
`labela-12664906-0`（鸭嘴兽）。这只闭合准确assembly上的比较标签生成和基本坐标完整性，
**不是**候选外部独立性、同源控制、完整冻结协议、训练/校准许可或L1科学PASS；未运行这些
后续步骤，且不将工程成功解释为终端评价结论。
