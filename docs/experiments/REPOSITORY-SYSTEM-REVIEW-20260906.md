# 全仓实验设计审阅与执行裁决

## 来源和范围

- 用户要求：先推送最新 Git 状态，使用内置浏览器 ChatGPT Pro 全仓审阅；待完整报告返回后制定并执行下一步计划。
- 送审提交：`b6b2c08b436c9fe5ce49b2af67f46690fdaa9350`，已推送并核对 origin/main。
- 附件为该提交完整 `git archive` 工作树，2,983 个文件、81,667,520 bytes（未压缩），不是精选摘要；无原始数据、权重和运行缓存。
- 完整原报告：[ChatGPT Pro 全仓实验设计审阅](https://chatgpt.com/c/6a9ca31f-0610-83eb-b663-a3e26a020c7c)。页面显示 `6 Pro`、思考47m41s及完整回复操作，已结束生成。本文是决策摘要，不是逐字转录。
- Pro 自报完成全树索引，331个Python AST、1,343个JSON、406个Markdown和441个表格的结构检查；按路线追踪 pipelines/scripts/configs/docs/reports/refs 等关键入口、配置与结果。全树索引不等于逐行语义审阅全部文件。
- Pro 没有访问HPC、原始数据、权重或完整Git历史。其100个测试入口中存在失败和缺依赖，不能称全测试通过；声称的复现仍需针对实际决策核实。浏览器附件下载/正文导出未取得本地文件，不能宣称证据包已下载。
- Pro 是独立顾问，不是实验数据或新授权。与本次并行的 [A/C专项审阅](GAP-BRIDGE-A-C-PRO-REVIEW-20260906.md) 是另一份材料和对话，不能算成同一数据实验的独立重复。

## 总体判断

保留 INIT 的 `STOP_INIT_HISTORY_SCIENTIFIC_NO_GO` 和旧 G/R/H 的 `NO_ACTIONABLE_ARM`；不释放 INIT seed17，不重开旧CONF、chr19科学评价或外部保留物种。当前未完成统一动物模型的绝对性能目标。Human gap的C效用实验不能替代L1主线交付。

最近的停止不是“没跑完所以没试过”，但也没有否定全部序列信息、全部初始化或全部TE冗余机制。主要瓶颈是material信号、结构恢复、可执行低风险行动和实际下游效用之间尚未连通。继续同面板初始化/阈值扫描不受支持。

## 具体发现与裁决

| 发现 | 证据入口 | 裁决与验证边界 |
|---|---|---|
| 三个旧painter对起点排序后的原始ends二分，嵌套区间可漏标 | SUPP `prepare_ucsc_windows.py`、EXTEND `prepare_pu_windows.py`、SEG-SF `prepare_superfamily_windows.py` | 修查询索引，保留多类别原覆盖顺序；检查仍影响活跃checkpoint的实际输入。不能未看原BED就宣布旧模型污染比例 |
| 旧strict evaluator用`[valid]`压缩坐标 | FINAL `strict_segment_eval.py` | 不跨未覆盖区域平滑/合并/匹配；保留基因组坐标和原有行粒度。只隔离受影响历史比较，不改P3或当前L1冻结分数 |
| 旧AP并列分数顺序敏感 | SUPP `te_token_task.py:average_precision_binary` | 改为分数组AP；不把此问题外推到固定阈值F1。当前L1实现已正确 |
| 历史骨干呈现量与窗口评估范围不匹配 | SUPP实际train TSV、前1200窗口评估 | 旧矩阵仅支持各完整recipe的观察值，不能纯归因骨干/context；不自动重跑GPU矩阵 |
| 历史embedding预处理和ARI/NMI包含训练样本，身份隔离不足 | `embedding_cluster.py`、`embedding_strict.py` | 限制为既有标签结构描述，不宣称未见家族发现；没有当前选模/主张依赖则不追加计算 |
| 当前L1 topology按tile且callable-censored | `calibrate_evaluate_x0.py:evaluate_species_tiles` | 这是既定评价对象，不是把Unknown当负例的理由；不能等同无标签FASTA原始run的融合率/实例数 |
| A有真实NT截断风险，8crop不代表全母体 | `prepare_pair.py:native_nt_window`及smoke记录 | 完整获准TRAIN/DEV候选的CPU投影覆盖检查，分别统计gap/crop；缺失不得零填或删候选 |
| A同时增加NT logit和3个seam scalar | A/C协议及配对实现 | 原准备比较只能解释组合信息。若未来要隔离NT预测增量，须两臂共享几何；不回写旧smoke，不在本轮改冻结训练流 |
| C真实非空exporter及stop-codon未闭合 | `evaluate_chains.py`、runtime产物 | 先完成非空技术输入/端点约定，再考虑9core科学干预。243 distinct chains不是243独立基因组或330条独立链 |
| 中央目标/历史dossier状态冲突 | `ACTIVE_GOAL.json`、TEtrimmer dossier | 更正明确过期表述、加入当前导航；不擅自改中央机器目标或重建控制框架 |

### 送审后的更正

Pro说C r2没有成功证据，是对送审时间点的判断。协作者已归档`12409697` COMPLETED0:0、113秒、1RTX3090，固定三种mask均完成但均0转录本；smoke没有完整包含的参考CDS链。该结果补上runtime，不补上非空exporter、stop-codon或效用证据。不能按旧报告重复提交相同空样本。

## 下一步执行计划

本次执行范围为有限实现修复、只读/CPU覆盖审计及C评分准备；不是新训练或完整科学试验授权。

1. **修复真实实现错误。** 修改上述三个painter、旧AP、旧strict坐标路径，增加对应最小反例和无缺口回归；不改变历史产物。对活跃H0所用旧数据链只查实际可达影响，差异为零即关闭，非零则报告并隔离解释，不自动重训。
2. **A完整母体覆盖。** 本轮核对现有chr3/chr5 TRAIN及chr13 DEV候选，冻结tokenizer/4096窗口/origin0；CPU检查真实token cap投影。分别统计完整gap和head crop缺失，包含donor筛选前母体，不做CAL/test评分或sealed访问。运行采用下述另一路已获用户授权的覆盖审计，不重复提交；其额外CAL输入coverage仅作已授权技术诊断，不能据此拟合/评分/选择。报告决定是否需要修适配器或另立几何协议；不重复8crop smoke替代此项。
3. **C非空/端点评分准备。** 基于当前固定runtime及已授权DEV输入，先核实真实exporter源码与RefSeq stop-codon规则；拟议首个gene-bearing技术输入为原core6完整core/halo，只跑M0，不依据预测收益选样，不科学评分。必要的新计算须经过项目提交前审查和Slurm资源核对；不因原空样本PASS就宣布端点已验证。
4. **更正状态与解释。** 保存本审阅裁决、测试/覆盖结果；更正TEtrimmer内部矛盾，当前导航指向本计划，保留历史和并行协作者的改动。
5. **在完整C科学评分前提交明确人闸。** 固定9core×3mask、微汇总完整CDS链F1、gain/loss/unmatched/boundary-incomplete及基因风险；建议探索性条件为F1增加、至少一条新增正确链、零丢失M0正确链。该条件不是既定事实或公认阈值，须用户决定是否采用和是否需更高最小gain。共同上限仍为A+C合计24 GPUh，含失败/smoke，单作业≤12h；不各给24h。
6. **依结果决定后续。** MW有益可支持whole-gap在本DEV的效用；仅MP有益不支持whole-gap A；都不支持则停止以gene utility为理由扩张A。A完整训练须独立前瞻协议、配对几何、预算及行动门；下一轮L1新机制、独立确认和公开发布分别另行决定。

当前不执行第5–6步中的完整科学运行、训练或解封。可执行准备完成后明确交付实际结果和剩余选择，不用“计划已写”冒充实验完成。

## 执行记录

### 2026-09-06：历史修复与A审计代码就绪

- 三个旧painter、AP与strict坐标错误均用原函数复现。修复后7项测试PASS；独立只读reviewer也执行7项测试并补查无缺口五种transform等价、missing/unknown不进入bp分母，裁决PASS。测试加载纯函数/固定预测，不加载训练依赖或checkpoint。
- painter采用prefix-max end索引，保留原interval列表（PU采样仍用它）及多类别排序覆盖优先级。strict在原坐标零覆盖分隔下算结构指标，后处理只作用于连续覆盖段；旧结果不覆盖。AP保持空/无正例NaN，只修分数组处理。
- 曾准备一份shape-only CPU审计草稿，3项坐标测试及独立审查PASS；但提交前squeue发现另一路已提交同问题审计`12416056`。本轮没有提交该草稿，已移除未提交的重复脚本/测试/sbatch，不保留第二套审计实现。实际NTv2-250M metadata为auto_token/nt_kmer/4096，源码EsmForTokenClassification仅对原token轴dropout+classifier。
- 当前复用[另一路用户授权的A/C readiness计划](GAP-BRIDGE-A-C-FOLLOWUP-20260906.md)。A作业`12416056`于2026-09-06 09:15:55集群时间启动，2CPU/12G/2h/0GPU；包括TRAIN/DEV及获另行授权的CAL输入coverage，但不做CAL评分。C正准备native-CDS-only端点适配与M0 core6（预定空输出回退core10）。本轮不与其重复运行，不混淆工程与科学授权。

### H0实际输入核对：完成，未见本次painter漏标影响

独立只读reviewer批准`audit_h0_labels.py`后，在本机临时输入副本执行；原BED/JSONL、checkpoint和冻结分数均不修改。旧paint来自送审commit，修复paint来自当前源码。只读取TRAIN/VAL缓存，BED仅纳入这些split的染色体；无TEST缓存、模型推理、再训练或GPU作业。输入是历史hs1，而非当前hg38。窗口数按实际training_meta的n_train/n_val固定。

| 祖先recipe/split | 实际窗口 | 缓存与旧paint不一致bp | 旧paint与修复paint差异bp |
|---|---:|---:|---:|
| NTv2-250M H0 TRAIN | 3000 | 0 | 0 |
| NTv2-250M H0 VAL | 1200 | 0 | 0 |
| NTv2-500M H0 TRAIN | 3000 | 1667（13窗口） | 0 |
| NTv2-500M H0 VAL | 800 | 92（1窗口） | 0 |

250M四千二百窗口来源核对完全一致，因此关闭这条活跃donor输入上的painter污染疑点。500M不能声称与当前重画流程完全一致：进一步逐行对齐两套缓存的chr/start/end/sequence，3800窗口全部一致；差异完全是250M的`-100`在500M缓存中为`0`，将Unknown转0后标签逐bp一致。说明这里有历史Unknown口径差异，而非这次prefix-max修复造成的差异；现有证据不定位旧生成命令，也不证明模型受影响幅度。保留H0祖先recipe限制，不据此重训或推翻当前L1/INIT评估。此审计不代表全部历史数据无误，也没有验证token训练target或性能因果影响。

可复现命令：`python scripts/experiments/REPOSITORY-SYSTEM-REVIEW-20260906/audit_h0_labels.py --input-root <原相对目录结构的只读输入副本>`。本次独立审查PASS，运行exit0；32,768,000个窗口bp比较计数含两recipe的重复坐标，不是32.8Mb独立样本。

### C非空端点：复用协作结果，工程完成

实际核对`12416061`：COMPLETED0:0，207秒，1GPU；`outputs/GAP-BRIDGE-C-ENDPOINT-20260906-R1/run-r1/STATUS=COMPLETED`、`READINESS=NONEMPTY_ENDPOINT_READY`。core6 M0产生303 CDS行、20条distinct chains；GTF/GFF3 native CDS一致。20条均ATG起始、末端stop、长度mod3=0，无内部in-frame stop；未审phase progression。真实exporter参考往返覆盖243distinct chains/330source rows。core6已非空，未触发core10预测。

这关闭本次非空/端点准备问题，不证明完整9core效用、MW/MP收益或A值得完整训练；`claim_eligible=false`、`scientific_scoring_enabled=false`。描述性truth match不是工程通过条件。A/C共享累计GPU为既有193秒加本次207秒，即400秒（0.111111GPUh），其余预算不是自动授权完整实验。

交付时A作业`12416056`仍在运行；已处理chr3的394678候选/44590原生窗口，但全母体summary尚未完成，不能报完整coverage PASS。此作业由并行A/C任务管理，本轮不重复提交或接管。下一项科学运行仍须先固定9core×3mask效用门与授权；建议最低探索门为chain F1增加、至少一条新增正确链且零丢失M0正确链。不得自动进入A训练、旧CONF或chr19评分。
