# 本轮补实验执行与结果收敛

2026-09-15。用户明确要求完成前三项补实验、补充 Tiberius 与公平长输入 benchmark，允许既定范围内训练、结果处理、Git 提交和推送。本文件是持续跟进入口；作业启动不等于实验完成。

## 冻结范围

见 [本轮范围](PAPER-CLOSURE-20260915.md) 及五项独立协议。保持 seed42，不增加 seed；不以追求阳性为理由改模型、阈值、训练预算或评价集。Gap 暂停新增解决方案。保留人类 Tiberius 1% loss gate 失败及旧阴性结果。

共享 D 的 dm6、cattle、horse、opossum 和原协议指定的 worm 留出染色体继续封存；人类 chr19–22 不开放。新的 cow **P3/Tiberius** 实验单独获准，不授权共享 D cattle 评价。NTv2 的新 EVAL 需要排除先前读过的 query 及其同源/近邻记录；不能把旧结果重新命名为独立验证。

本机 `/Users/jiwang/Desktop/TE/ab-initio-TE`；远程 `/home/users/j/jwang/ab-initio-TE`。使用 `ssh baobab`；连接可用性以最近实际连接为准。重计算只用 Slurm；login 只读小型状态、日志、调度与传输。

## 当前执行图

**最新连接/作业更新，2026-09-16 16:18 UTC记录：** 用户告知Baobab恢复后，首次成功查询显示三物种固定D重放12743579 COMPLETED（5m13s、exit0），依赖评分12743581 COMPLETED（2m53s、exit0）；六个注释cell此前均已完成。随后取回`replay/complete.json`和`score/result.json`时SSH再次Connection refused，普通连接及IPv4连接均未成功。尚未取得或审阅新科学计数，不能据此声称重放验证或库敏感性结论已通过。下一步只取回既有compact结果并复核，不重复提交或训练。下文等待GPU等状态是历史快照。

**最近核实，2026-09-16 09:56 UTC：** 外部Tiberius完整40core/200cell已合格完成，替代score12740044 COMPLETED（35s），正式result.json及资格元数据已取回。两物种P相对无mask流程和同checkpoint无mask均有正向F1效应；P−R_TE的区间均跨0，未建立RM优势；所有对照的原正确locus损失比例均超过1%。[完整结果](../../reports/P3-TIBERIUS-EXTERNAL-20260915/full-r1-score-12740044/RESULTS.md)。原人类1%门失败保留。

前三项、长输入benchmark和外部Tiberius的本轮冻结执行与评分均已结束。benchmark为13合格完成+1项CB4 EDTA原生失败，新Omni完成；不追求所有实验为阳性。

用户09-16新增讨论是斑马鱼高F1是否来自注释完整度，以及Plant/Fungi是否应扩展。已完成原六物种D DEV汇总计数的回顾性诊断，未改变原结果；[诊断入口](../../reports/SPECIES-ANNOTATION-DIAGNOSTIC-20260916/RESULTS.md)。只读Dfam元数据作业12743207已完成，历史三物种probe也明确curated-only。内置浏览器Pro已完成固定e3df4e2的聚焦讨论，见第五次审阅归档。新三物种库诊断独立获本轮用户请求授权：准备12743578已完成（3m58），原D推理重放12743579等GPU，六个注释cell12743580前三项运行，其余按最多3项并行排队；score12743581依赖afterok两者。新协议见SPECIES-LIBRARY-CONTROL-20260916.md。只用已观察三物种DEV，0新训练、原校准/阈值不变，原汇总必须精确复现。剩余为该有限诊断收束、稿件/图表整合，不扩大Gap或Plant/Fungi。

| 工作 | 作业/输出 | 后续验收 |
|---|---|---|
| 库控制 | 原注释12732075两份完成；评分恢复12735616已COMPLETED（46s），旧TIMEOUT保留 | 同输入/引擎库配置敏感性已完成；差异含taxon/curation/RepBase混杂，不是单纯版本效应，见该方向RESULTS.md |
| source-only 匹配/蛋白 | 12732331完成；no-reuse12735617已COMPLETED（52s）；旧阻塞12732397已取消 | 5540唯一配对；>=50%/80%TE支持差在两库均为正，但不能直接FP rescue；强蛋白matched支持仍0/5540 |
| NTv2 label-free | 12732191完成41分33秒；权重核查12733074完成；旧尝试保留 | 六臂已完整评价：适配transductive ARI小幅增，但NMI和inductive ARI较冻结NTv2下降，不能称稳定提升；本项闭合，见独立RESULTS.md |
| SF5 ontology | train/eval及legacy12731987已COMPLETED（3h55m09s），结果本地收回 | 5400/1440/2160完整六物种；TEST材料F1=0.884305，main4 macro=0.833687；状态/物种差异明显，无稳定整体提升，见RESULTS.md |
| Tiberius 数据 | acquire12731819、prep12732000完成 | cow470参考loci（220含NM转录本）；platypus639（0含NM），均是注释相对效用 |
| Tiberius 参考修复 | 12732214_0 cow及_1 platypus均COMPLETED（39m52s/2h34m01s） | cow完整Dfam3.9库1718条/219080 repeat rows；platypus已核实1139条/387011 repeat rows，manifest PREPARED_WITH_NATIVE_RM |
| Tiberius smoke | 原12732021失败保留；12735505_0和_20均COMPLETED（36m38s/34m46s） | 两物种五arm均合格；checkpoint bind修复实际通过 |
| Tiberius full | 40/40core、200/200cell合格完成；实际模型调用和输入不变量通过 | 完整产物已由score统一评分，无partial推断 |
| Tiberius score | 12740044 COMPLETED，35s；旧12732548取消记录保留 | 正式result.json已取回，计数/gain-loss复核通过；两物种未建立P优于R_TE |
| 长输入模拟 | model/smoke12731809、sim10012731886完成 | 100,000,000bp，163602片段，插入材料55000087bp，坐标/大小写材料mismatch0；L3/strand未资格化 |
| 长输入真实 | prepare12731942完成 | CB4全基因组108384165bp，367序列，真实只报reference-positive recall |
| native方法 | fixed RM/HiTE/RM2、模拟EDTA及两EarlGrey恢复均合格完成；CB4 EDTA原生失败 | EarlGrey exact strained+lineage检查通过，全部原生cell终态；旧输出/累计耗时保留，EDTA不再恢复 |
| 固定D | 两GPU完成；CPU CB4 12731959 COMPLETED（Slurm 7h15m16s；实测26112.05s）；sim CPU12731960 COMPLETED（Slurm 6h37m45s；实测23861.16s） | CB4全部108384165bp/367序列；CPU E5-2630v4、16线程；GPU硬件不同，完整分母齐前不排名 |
| 长输入评分 | 12739923 COMPLETED；对应Omni 4/4 workflow jobs完成 | 全14cell保留：13合格完成+1失败；旧12738470及其Omni回放保留为含不合格EarlGrey的历史记录 |
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

### 20:44 UTC 新终态：EDTA恢复补丁错误

12738345_[0,1]分别在3m41s/3m47s FAILED：本次是生成的 `get_fasta_sequence.py` overlay 第12行缩进错误，属于本项目恢复补丁引入的问题，不能归因于原EDTA或生物学输入。原源码接口诊断保持成立，但此前验证只保证driver语法与文本替换，未充分验证实际生成模块，相关报告正在更正。下一步先编译并在容器中导入实际overlay，对真实helper运行坐标样例，再继续同预算恢复；不使用 `--force` 绕过生物学候选检查。

评分12732389已按协议afterany完成（25s）：`ALL_CELLS_TERMINAL_WITH_FAILURES`，两输入各6/7个可评分方法，保留完整14cell分母。此文件保留为本次失败快照，不覆盖；修复EDTA后提交新的score作业，并更新本入口及automation指向。未以该评分的准确性决定修复或选择方法。Tiberius恢复至少index15已实际运行。

### 当前继续入口（20:52 UTC）

实际生成的三个overlay现已编译并在EDTA容器中导入；真实helper的dotted accession、普通分段、overlap分段及已规范ID样例通过，见已更正EDTA报告。新恢复为12738464_[0,1]，输入为上一失败12738345的复制工作目录，累计原耗时31318.23/14840.21秒继续从84600秒扣除；不覆盖任何原目录。当前CB4运行、sim100等资源，未形成EDTA完整输出。原CB4空LTR是独立未决条件，不自动加force绕过。

attempts已同步到新恢复。新score12738470已提交并核实afterany12738464；旧score12732389不可覆盖，其状态摘要保存在 `reports/TE-LONG-BENCH-20260915/score-12732389-status.json`。未来Omni回放应使用最新完整终态bundle，不误用旧失败快照。

## 2026-09-16 结果核实与剩余任务

- EDTA：12738464_1模拟完成123471行GFF转换；_0 CB4（raw job12738465）运行22m22后FAILED，Slurm exit1:0、native EDTA exit255。LTR.raw.fa有13记录，但LTR.intact.raw.fa为空；TIR与Helitron已完成。属于默认候选门不通过，不是新接口错误，不加force、不增加预算。
- score12738470原生终态bundle及其Omni干净GitHub回放均收回。Omni固定commit4edaeb16…、4job成功，只证明按block统计重现指标，不证明上游产物满足全部知识条件。
- EarlGrey输出路径和adapter正确，但实际sim组合库只有1405bytes，与strained库一致；起始lineage库3.63MB未加入。RepSub变量只在续跑跳过的初始函数赋值，导致final RM漏库。两输入均须有界恢复，不能用该低分声称方法天然保守或D胜出。原12738271/12738272及评分12738470保留；具体修复/新jobs由本入口后续更新。
- 固定D在100Mb模拟上precision0.887689、recall0.301975、F1 0.450648，低于已合格fixed RM/RM2/HiTE/EDTA；不因该阴性重训、调阈值或换输入。两CPU流程也不显示速度优势。
- CB4源Label-A原生表明确仅23个SINE条目、1571bp严格TE阳性，不能用于真实全基因组准确性排名。fixed RM与来源近似同库同引擎，100%来源召回非独立敏感度；D检出972bp、漏599bp，覆盖缺口与漏检并存。不在看过结果后偷偷更换参考。

结果入口：[benchmark解释](../../reports/TE-LONG-BENCH-20260915/RESULTS.md)、[参考资格](../../reports/TE-LONG-BENCH-20260915/reference-qualification/RESULTS.md)、[EDTA终态](../../reports/TE-LONG-BENCH-20260915/edta-recovery/FINAL-STATUS.md)、[EarlGrey资格](../../reports/TE-LONG-BENCH-20260915/earlgrey-recovery/OUTPUT-QUALIFICATION.md)、[当时回放（历史）](../../reports/TE-LONG-BENCH-20260915/omni-12738470/README.md)。

### 01:22 UTC：EarlGrey恢复与新评分依赖

`12739911_0`/`_1`已分别在cpu238/cpu239启动，16CPU/80GB/E5-2630V4，输出`native-12739911/{c_briggsae,sim100}-earlgrey`。恢复仅复制旧工作目录，保留初始mask、RepeatModeler和TEstrainer；恢复`RepSub`后重建最终RM/merge/summary。两cell原耗时8725.850726/9014.238390秒继续计入原84600秒预算。只有新status记录`final_library.exact_concatenation=true`并完成输出/坐标检查，才可将EarlGrey重新纳入合格比较。

`attempts.json`已更新并同步远程；新评分`12739923`已核实`afterany:12739911_*`依赖，输出应为`score-12739923/result.json`。它允许EDTA的真实失败保留在完整分母中；不得用旧不合格EarlGrey结果填补新cell。原12738470及其Omni回放保留为历史快照。Tiberius另按原200cell完整性门处理，不与benchmark混合。

### Pro审阅已发送（01:27 UTC）

提交`34bb71c7f7697671710d6c06d6b4353086211c58`已成功推送到GitHub main。已在内置浏览器的原[科研梳理与论文初稿对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)使用6 Pro发送新的固定提交审阅请求，页面显示“Pro思考中”。入口为`PAPER-CLOSURE-REVIEW-20260916.md`，要求实际读取GitHub并区分已完成前三项与pending Tiberius/EarlGrey，形成中文收敛表、英文结果/讨论修订和现实投稿定位。回复尚未完成，不能把已发请求写成审阅完成；后续读取此同一对话、归档并核实建议，不重复发送请求，不自动执行越出当前冻结范围的新实验。

### 第四轮Pro完成后的收敛（2026-09-16）

已实际读取完整可见回复和生成文档预览，Pro报告固定GitHub34bb71c、21分16秒完成；它未查询后来的HPC状态。新归档位于`docs/manuscript/20260916/`，为Agent依据页面整理的审阅/编辑稿，非成功下载的原附件。前三项无需为阳性重训；模拟D召回不足进入正文，SF5/聚类放补充；明确D、P3及各任务模型身份。库控制匹配差值与全FP字段分母不同、容量控制只匹配head两项已核对源码并加注，原指标未变。随后已取回EarlGrey→新score→新Omni的合格完成结果；剩余为Tiberius完整200cell→固定评分→稿件/图表整合。Pro建议不自动授权额外实验，不重复发送同一审阅请求。

## 2026-09-16 10:25 UTC 新诊断执行入口

三物种库准备已合格：500原DEV中心/物种均与原材料序列一致；斑马鱼1966→1966且序列完全相同，猪784→3831，鸡218→395；curated原序列均是combined不变子集。TRAIN正类材料暴露分别6,590,012、3,266,685、450,199 bp，说明相同窗口数不是相同TE监督量。以上不等于已验证完整度因果。运行输出在outputs/SPECIES-LIBRARY-CONTROL-20260916/run-r1。重放无原逐位置缓存可比，只能先复现原混淆计数；失败则不评分或改模型。全部六cell完成且原计数复现后读score/result.json，保留完整四格转移、新FN、原阳性损失、class缺支持。候选独立证据另判断，不自动把扩库支持称TP。

当前完整英文工作稿在docs/manuscript/20260916/manuscript-en.md；已有摘要/引言/结果/讨论/方法/可用性与图表安排。新诊断仍标pending，正式图组、发布材料仍未完成。

10:32 UTC更新：三物种注释0/1/2/4/5已COMPLETED并有complete.json，只有猪combined/index3仍运行；原D重放12743579继续等GPU，score12743581等依赖。三张已完成数据图（物种计数、模拟benchmark、外部Tiberius）已生成PDF/SVG/PNG；无待运行结果被画成已完成。

11:16 UTC已读Slurm：12743580六个原生注释cell全部COMPLETED/exit0，猪combined用时9m41s；原D重放12743579仍PENDING资源，12743581仍依赖等待。后续读取六cell compact输入资格时SSH connection refused，未得到资格包，不将Slurm完成冒充统一评分。未重复提交；下次恢复后继续原作业。

12:27 UTC：一次SSH核实仍connection refused，未读到新的Slurm状态，沿用11:16的最后已知状态，不密集重试。利用本地已合格证据补齐Figure1研究结构图（PDF/SVG/PNG），清楚区分六条实验与L1/L2/L3；不新增科学结果或实验。

16:04 UTC：本轮一次SSH仍立即返回connection refused；距11:16首次中断近5小时。当前阻塞是无法核实/收回结果，不是已知的作业失败。六项原生注释的COMPLETED来自11:16证据，模型重放/评分最后已知为排队，当前状态未知。首次就持续连接阻塞提醒用户；后续相同拒绝保持静默，不重复提交、改路由或降低SSH安全设置，连接恢复再接续。
