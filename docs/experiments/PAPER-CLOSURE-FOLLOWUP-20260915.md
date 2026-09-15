# 本轮补实验执行与结果收敛

2026-09-15。用户明确要求完成前三项补实验、补充 Tiberius 与公平长输入 benchmark，允许既定范围内训练、结果处理、Git 提交和推送。本文件是持续跟进入口；作业启动不等于实验完成。

## 冻结范围

见 [本轮范围](PAPER-CLOSURE-20260915.md) 及五项独立协议。保持 seed42，不增加 seed；不以追求阳性为理由改模型、阈值、训练预算或评价集。Gap 暂停新增解决方案。保留人类 Tiberius 1% loss gate 失败及旧阴性结果。

共享 D 的 dm6、cattle、horse、opossum 和原协议指定的 worm 留出染色体继续封存；人类 chr19–22 不开放。新的 cow **P3/Tiberius** 实验单独获准，不授权共享 D cattle 评价。NTv2 的新 EVAL 需要排除先前读过的 query 及其同源/近邻记录；不能把旧结果重新命名为独立验证。

本机 `/Users/jiwang/Desktop/TE/ab-initio-TE`；远程 `/home/users/j/jwang/ab-initio-TE`。使用 `ssh baobab`；连接可用性以最近实际连接为准。重计算只用 Slurm；login 只读小型状态、日志、调度与传输。

## 当前执行图

**最近核实，2026-09-15 20:39 UTC：** SSH恢复且实际连接正常，使用任务专用控制连接 `/tmp/te-closure-baobab.sock`。前三项补实验已收敛，不重复训练或评分。Tiberius两物种smoke的五臂均完成；full完成cow c00–c14后被UID 0取消，保留结果并只恢复24个缺失core。EarlGrey两输入已完成最终输出资格化，两项CPU推理也已完成。EDTA已定位真实运行错误并提交12738345_[0,1]，均运行中；最终比较尚未完成。

| 工作 | 作业/输出 | 后续验收 |
|---|---|---|
| 库控制 | 原注释12732075两份完成；评分恢复12735616已COMPLETED（46s），旧TIMEOUT保留 | 同输入/引擎库配置敏感性已完成；差异含taxon/curation/RepBase混杂，不是单纯版本效应，见该方向RESULTS.md |
| source-only 匹配/蛋白 | 12732331完成；no-reuse12735617已COMPLETED（52s）；旧阻塞12732397已取消 | 5540唯一配对；>=50%/80%TE支持差在两库均为正，但不能直接FP rescue；强蛋白matched支持仍0/5540 |
| NTv2 label-free | 12732191完成41分33秒；权重核查12733074完成；旧尝试保留 | 六臂已完整评价：适配transductive ARI小幅增，但NMI和inductive ARI较冻结NTv2下降，不能称稳定提升；本项闭合，见独立RESULTS.md |
| SF5 ontology | train/eval及legacy12731987已COMPLETED（3h55m09s），结果本地收回 | 5400/1440/2160完整六物种；TEST材料F1=0.884305，main4 macro=0.833687；状态/物种差异明显，无稳定整体提升，见RESULTS.md |
| Tiberius 数据 | acquire12731819、prep12732000完成 | cow470参考loci（220含NM转录本）；platypus639（0含NM），均是注释相对效用 |
| Tiberius 参考修复 | 12732214_0 cow及_1 platypus均COMPLETED（39m52s/2h34m01s） | cow完整Dfam3.9库1718条/219080 repeat rows；platypus已核实1139条/387011 repeat rows，manifest PREPARED_WITH_NATIVE_RM |
| Tiberius smoke | 原12732021失败保留；12735505_0和_20均COMPLETED（36m38s/34m46s） | 两物种五arm均合格；checkpoint bind修复实际通过 |
| Tiberius full | 原12732547完成cow c00–c14；复用platypus c00后合计16core/80cell；缺失24core恢复12738295_[15–19,21–39%2]等资源 | UID 0取消原因未公开，无模型失败证据；部分输出保留，未重跑完整core |
| Tiberius score | 12732548，afterok12738295 | 200cell全部完成后生成 `outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1/result.json` |
| 长输入模拟 | model/smoke12731809、sim10012731886完成 | 100,000,000bp，163602片段，插入材料55000087bp，坐标/大小写材料mismatch0；L3/strand未资格化 |
| 长输入真实 | prepare12731942完成 | CB4全基因组108384165bp，367序列，真实只报reference-positive recall |
| native方法 | 两输入固定RM/HiTE/RM2已完成；EarlGrey12738271_4/12738272_4均COMPLETED；EDTA原两项FAILED保留，恢复12738345_[0,1]均RUNNING | EarlGrey修复Perl路径/模块后合格，累计耗时8725.85s/9014.24s包括失败及续跑；EDTA恢复见下文 |
| 固定D | 两GPU完成；CPU CB4 12731959 COMPLETED（Slurm 7h15m16s；实测26112.05s）；sim CPU12731960 COMPLETED（Slurm 6h37m45s；实测23861.16s） | CB4全部108384165bp/367序列；CPU E5-2630v4、16线程；GPU硬件不同，完整分母齐前不排名 |
| 长输入评分 | 12732389已解除hold，afterany12738345；其余选定12cell已核实全部COMPLETED | `outputs/TE-LONG-BENCH-20260915/score-12732389/result.json`；失败进入完整分母，不提前选完成方法评分 |
| 模拟库条目覆盖 | 已收回12733209结果；本地计数核对通过 | 366/366生成条目名称被实际固定RM库覆盖；包含非TE条目，不用于声称新家族发现 |

## 真实失败与修正

- Dfam4 缺少 uncurated 分区时 FamDB 可能 exit0 且输出部分库。CB4 初次 fixed RM 和 EarlGrey 初始 mask 尝试不能代表完整库。选用完整分区 Dfam3.9 的同一 lineage library 用于 fixed RM/EarlGrey；原引擎4.2.4固定，所有尝试见 `configs/TE-LONG-BENCH-20260915-attempts.json`。
- EarlGrey 使用 `/usr/local/share/RepeatMasker/Libraries/famdb`，需要其真实路径挂载；仅设置 FAMDB_DIR 无效。支持的 `-l` 显式传相同初始库。
- 新 Tiberius 12732197 缺少 RepeatMasker 启动所需 FamDB 挂载，已在12732214修正；旧注释/日志保留，未将错误库的 mask 用于正式推理。
- native EDTA 在 CB4 LTR 阶段出现空候选文件警告但继续执行；最终必须结合完整输出检查它是无候选还是实际未完成，不能只凭进程exit0认可科学输出。
- 库控制旧评分循环重复为chr级旧注释union构建starts数组，并重复计算同一overlap。已缓存该索引并复用单次结果，独立逐碱基集合oracle验证半开区间语义不变；12732075仅在评分阶段超时，修复后仅对现有结果重评分。

上述库评分修复已部署并完成；新旧legacy区间表逐字一致，两份native注释未重跑。Tiberius失败保留于 `run-r1-failed-12732021`，恢复细节见该方向 `SMOKE-RECOVERY-12735505.md`。EarlGrey原失败工作目录未覆盖，新目录复制后续跑；`native.py --resume-from`用于已确认的EarlGrey兼容性中断。第二次修复仅涉及Perl解释器和模块路径，现两输入均完成；全部失败及续跑耗时计入相同预算，完整14分母不变。

SF5报告修正了一个解释问题：三个status的one-vs-rest TP之和不是合并Unknown的精确TP，状态间错分在合并后会成为TP。目前JSON可给出status精确标签micro F1及二值合并F1下界，不能假造未保存的联合混淆矩阵。未新增训练、模型选择或测试集调优。

## 完成动作

1. 读取各作业实时Slurm终态、日志和实际产物；修复明确接口错误时保留原尝试，按相同输入、模型、阈值、预算重试并更新映射和依赖。不得为达到好分数换配置。
2. Tiberius只有200cell全部合格才运行固定科学评分；比较P–R_TE、P–U_nosm及其他两对照，按染色体paired bootstrap，保留loss loci。原人类结论不覆盖。
3. benchmark聚合每方法/物种的实际输入、失败、墙钟、资源、知识条件。模拟真值F1和真实阳性召回分开，CPU/GPU同硬件类别解释，不能把Omni回放时间当native时间。
   模拟生成family与实际固定库的name/accession重叠核实由 `library_exposure.py` 和 `reports/TE-LONG-BENCH-20260915/library-exposure/` 记录；只做协议已要求的库暴露披露，不改变调用或分数。
4. `benchmarks/te_omnibenchmark/long_panel.yaml` 已固定到代码commit `4edaeb16e735be4c25fdbace12822f026604f649`（配置提交ef6cecf已推送）；用本机现成 Omni runtime、真实 compact block bundle 运行图。Omni的范围是从Slurm已验证block充分统计量重算指标，不伪称重跑native工具。
5. 将compact结果、限制、正文/补充材料定位与用户五项问题的结论写入研究文档；原始序列、概率数组、权重留远程。提交并推送到既有GitHub。没有完整结果时保持RUNNING/PARTIAL，不写“论文已闭合”。

若计算跨本次交互，沿用已有TE跟进任务，正常运行或状态未变时静默，仅对完成、真实失败、结论变化或用户决策通知。全部已授权结果处理和推送完成后暂停跟进。

## 本次恢复补充

Tiberius full的UID 0取消记录没有披露管理员/控制器的具体原因，不推断为模型失败或用户取消。cow c15/c16部分输出完整保留到 `run-r1-cancelled-12732547`。先前恢复12738275包含已完成index20，所有任务均在执行前取消，改为精确缺失集合12738295；见 [full恢复报告](../../reports/P3-TIBERIUS-EXTERNAL-20260915/FULL-RECOVERY-12738275.md)。

EarlGrey在最终RepeatMasker后遇到缺失 `/usr/bin/perl` 及RepeatMasker Perl模块目录问题，已在复制的工作目录中修复并完成。原始失败输出、阶段计时及最终状态均保留，见 [EarlGrey报告](../../reports/TE-LONG-BENCH-20260915/earlgrey-recovery/RECOVERY.md)。CB4完整CPU计时与节点硬件证据见 [CPU报告](../../reports/TE-LONG-BENCH-20260915/cpu-completed/RESULTS.md)。

EDTA原CB4在TIR-Learner的分段ID/坐标还原处失败，sim100因pandas 3的Series索引语义失败。三处源码兼容补丁在原镜像源码上验证，并做分段坐标oracle；恢复12738345_[0,1]使用同E5-2630V4、16CPU/80GB，复制原工作目录并以overwrite0复用已完成阶段，原耗时31097.63s/14614.03s从84600s预算扣除。原失败和具体修复见 [EDTA诊断](../../reports/TE-LONG-BENCH-20260915/edta-recovery/DIAGNOSIS.md)。attempts已同步远程；12732389已解除hold，等待剩余两项EDTA终态后按完整14cell固定评分。
