# BRAKER 完整流程应用验证：执行登记

2026-09-25，按用户新的自主执行指令启动。[固定协议](../../docs/experiments/BRAKER-MASK-UTILITY-20260925.md)、[精确部署输入](../../configs/BRAKER-MASK-UTILITY-20260925.inputs.json)、[作业登记](jobs.jsonl)。

目的为鸡/斑马鱼完整 ETP 的 D、RM2_FULL、RED_FULL 六臂应用比较，不把旧同预算 pilot 的局限抹去。两个物种都是 D 微调物种；RNA/外源蛋白在同物种各臂相同。所有长任务运行于 private CPU，无 GPU。

## 已实际完成

共享 OrthoDB v12 Vertebrata 文件已下载、完整解压过滤，移除鸡 taxid9031 的17,274条与鱼 taxid7955 的25,793条，保留19,350,805条外源蛋白、10,487,364,393个氨基酸字母。原始文件6,188,932,489 bytes。原生状态为 `PROTEINS_READY`，统计见 [proteins-status.json](proteins-status.json)。这仅是输入准备完成，不是基因注释或科学结果。

精确 ENA paired RNA 元数据已保存：鸡4类组织/细胞类型共20,490,058,265压缩bytes，鱼WT24/48hpf共6,055,852,095bytes。原有鱼PRJNA899844每run过大，不纳入本次25GB/物种预算；没有先观察mask效果再选输入。鱼不引入KO，不把胚胎RNA当完整组织覆盖。

## 正在执行与衔接

- `13194294`：真实 ETP bundled sample已完成。最终GTF含1,537条CDS feature，GeneMark/AUGUSTUS中间GTF存在；原生状态ETP_EXAMPLE_COMPLETE。Slurm共811秒，1.8022 allocated CPU-hours；仅工程运行资格，不作准确率结果。见 [smoke-status.json](smoke-status.json)。
- `13194295 / 13194296`：鸡/鱼完整 D、RM2 重建及全基因组 RED；原先参考FASTA的大小写不继承。
- `13194304`：共享蛋白准备完成。
- `13194313 / 13194314`：RNA获取和 HISAT2 比对，分别依赖上述掩码准备完成，生成同物种三臂共用的无注释辅助 BAM。

评价准备脚本在新预测前固定常染色体区域、D TRAIN/CAL排除、旧用途halo排除、完整RefSeq分母与独立长读长结构。正式六臂由 `run.sbatch` 固定为两个物种 × 三种mask，最多两臂并发，每臂16CPU/96GB/72h；只有真实smoke及共同输入、两物种评价域均准备好后才运行。不得把提交或exit0当作科学完成。

独立鱼 processed GTF 只承担转录结构支持。作者参考比较信息保留；`u`不是coding真值，缺少RNA匹配不算FP。鸡暂无可直接使用的 processed IsoSeq坐标，不把现有证据说成两物种均有独立完整CDS真值。

固定比较与失败都保留；不看新分数改区域、模型、阈值、分母或预算。当前是执行状态，尚无新的完整BRAKER科学比较结果。

## 新预测之前的实现核实

GTF scorer已用真实bundled BRAKER格式核对，独立start/stop codon行会并入CDS坐标并去重；预测缺codon标记不会从错误分母消失。鱼长读长文件使用numeric contig，固定映射1–25到chr1–chr25；class_code从transcript行取，transcript span不会被当作exon。正负链、独立codon、跨旧halo排除和numeric-contig小型fixture通过。

评价准备13194346在鱼参考同CDS链多名称歧义处停止，鸡分母已完成且保留。没有读取目标BRAKER分数。鱼主域4组、全域5组坐标相同的参考单位已按exact-CDS连通合并，保留名称/源行明细。恢复13194364完成，未覆盖原失败目录；正式六臂13194349已更新为依赖RNA准备及成功的13194364。原生失败15秒、0.0167 allocated CPU-hours计入。

## 评价准备终态

恢复33秒完成，原失败15秒一并保留，评价准备累计0.0533 allocated CPU-hours。全局状态EVALUATION_READY。鸡主域201,407,137 bp、6,588参考loci；鱼主域769,648,038 bp、14,576参考loci。[准备摘要](evaluation-preparation.json)

鱼独立长读长文件取得48,086个多外显子结构，8,523个与全域完整RefSeq CDS内含子链匹配，主域匹配4,874个。该子集仅增强结构支持，不提供独立CDS起止/蛋白功能真值；其余结构不自动视为非编码。后续须依据preparation.json里的鱼zebrafish-r2路径评分。[长读长资格统计](zebrafish-long-read-summary.json)

正式六臂仍等待两个物种的全基因组mask和共同RNA BAM完成；已排入依赖队列，后续由已恢复的heartbeat自动核实、分析及Git同步。

## 08:30 UTC heartbeat：辅助结构评分就绪

核对Slurm和原生日志：两个RED作业在持续写出掩码、无报错，RNA和六臂按依赖等待，不重复提交或重启原作业。正式BRAKER尚未产生目标预测。

已补完独立长读长的正证据评分，并由private作业13194397在8秒固定可评价分母：主域27,862条完整内含子链（参考CDS相容4,874条），全常染色体域48,068条（相容8,523条）。原48,086是整个源文件的多外显子结构数，不能直接用于主域。原始RefSeq gene-locus分母保持6,588/14,576。[冻结分母摘要](long-read-denominators-summary.json)

评分保留所有源类别、逐染色体恢复量以及相对D的gross gains/losses；不从RNA缺失定义FP。UTR-off预测CDS链不能自动代表完整转录本重建。正负链、跨旧halo、部分预测FP、exact intron链和primary/full输出隔离的合成fixture已通过。具体定义写入固定协议。

脚本输出改为score-primary.json/score-full.json避免互相覆盖；鱼需要指向已保留的zebrafish-r2目录。正式六臂的依赖与原生输入检查已包含该冻结清单，仍需等待两份RNA BAM。此次只有评价准备完成，没有新的模型准确率结果。

## 09:12 UTC heartbeat：鸡完整掩码准备完成

鸡作业13194295原生状态MASKS_READY，464条序列、共1,065,365,425 bp，RED输出与源序列逐记录大写碱基一致。D、RM2_FULL、RED_FULL实际小写ACGT分别40,685,285、152,009,313、333,937,733 bp；覆盖不同是固定方法输出，不能从覆盖量推断基因注释效果。原生RED记录保留，掩码准备共5,198秒、11.5511 allocated CPU-hours。[完成摘要](chicken-masks-summary.json)

共同RNA作业13194313已按依赖自动启动，正在获取预定鸡RNA；未产出最终BAM，尚不能称RNA_READY。鱼13194296仍在写出RED掩码，无原生报错；鱼RNA和六臂ETP仍依赖等待。本轮无新提交、无修改模型/阈值/评价分母，无新的基因注释准确率结果。

## 10:47 UTC heartbeat：两物种掩码与鸡 RNA 终态核实

鱼全基因组掩码作业13194296已完成：1,923条序列、1,679,203,469 bp；D / RM2_FULL / RED_FULL小写ACGT分别894,533,834 / 1,001,834,539 / 858,140,069 bp。RED原生repeat-span统计比实际小写ACGT多842 bp，两者不作为同一统计口径；实际掩码按协议仅保留小写ACGT，未改变掩码规则。源序列顺序与大写碱基逐记录一致。耗时11,009秒，24.4644 allocated CPU-hours。[鱼掩码摘要](zebrafish-masks-summary.json)

鸡共享RNA作业13194313已完成，原生状态RNA_READY。八个FASTQ与冻结字节数一致，共158,050,764个read pairs；四份BAM及索引存在，quickcheck通过，flagstat中的primary reads逐样本恰为输入pairs的两倍。各臂继续共用全部四份BAM，不因比对率差异筛选样本。耗时5,527秒，24.5644 allocated CPU-hours。[RNA原生日志与摘要](chicken-rna-summary.json)

| 鸡 RNA run | 预定组织/细胞 | Read pairs | HISAT2 overall alignment |
|---|---|---:|---:|
| SRR13642599 | Ileum | 46,331,004 | 91.54% |
| SRR13642601 | Lung macrophage | 33,641,559 | 68.97% |
| SRR13642607 | Ovary | 45,648,092 | 86.36% |
| SRR13642613 | Thymus | 32,430,109 | 63.82% |

比对率描述部署证据的异质性，不代表基因预测准确率，也不证明完整组织覆盖。鱼RNA作业13194314已自动启动、仍在准备；六臂13194349等待其完成。本轮没有新的基因注释结果、没有重复提交或变更科学参数。

## 11:20 UTC heartbeat：共同输入完成，正式 ETP 开始

鱼RNA作业13194314已到RNA_READY：四个FASTQ与冻结字节数一致，两份BAM/索引、quickcheck和flagstat通过，primary reads逐样本恰为输入pairs的两倍。SRR31188006（24 hpf）22,399,208 pairs、overall alignment 95.04%；SRR31188005（48 hpf）22,904,743 pairs、92.36%。24 hpf样本有48.46%的read pairs多位置concordant比对，故overall alignment不能当作唯一定位率。两个固定样本均保留。耗时2,582秒、11.4756 allocated CPU-hours。[鱼RNA原生摘要](zebrafish-rna-summary.json)

两物种掩码、共享蛋白、各物种RNA以及冻结评价域全部就绪。正式数组13194349已在11:18:55 UTC自动启动D两臂：13194349_0鸡（Slurm内部ID13195479）、13194349_1鱼（13195480）。原生日志明确进入ETP模式，BRAKER 3.0.8；实际命令无skipOptimize/gm_max_intergenic样例参数。资源为private、每臂16CPU/96GB/72h、无GPU，数组并发2；其余四臂等待JobArrayTaskLimit。[正式启动记录](etp-initial-start.json)

当前仅为正式流程启动，尚无最终GTF和新准确率。继续按冻结主域、完整常染色体及长读长辅助定义完成全部固定臂分析；不因先启动D或任何中途表现调整其余臂。

## 16:12 UTC：原生 GeneMark 警告核实

鸡D进入GeneMark模型构建与原生masking-penalty优化。`build_mod.pl`第50/56行出现两条`uninitialized value`警告；读取固定容器源码后，定位为未定义的`Parameters.gcode`与1/6比较，而非模型训练退出。实际生成的`GeneMark-ETP/proteins.fa/model/output.mod`与`ref.mod`均为`$TAA_ON 1`、`$TAG_ON 1`、`$TGA_ON 1`，标准终止密码子开关保留。未修改容器、模型或参数，原生日志继续保存；若后续出现实际失败再按终态处理。

此处GeneMark自动选择masking penalty属于预先允许的各臂原生自训练，不是重调D阈值或使用评价标签。两臂仍在运行，最终GTF尚未产生；以上只解释工程警告，不是科学结果。

## 2026-09-27 08:55 UTC：鸡 D 原生终态及单臂评分

鸡 D（13194349_0）于06:22:51 UTC完成完整ETP；原生日志有BRAKER RUN FINISHED，最终braker.gtf为71,871,974 bytes，已解析255,067条CDS feature、23,961条transcript feature和18,318条gene feature。这些是原生文件行数，不是主评价域的基因分母。Slurm耗时155,036秒（43小时03分56秒），689.0489 allocated CPU-hours；batch MaxRSS为23,738,768 KB。GNU time原生过程的峰值内存单列，不与Slurm采样峰值混用。[原生终态摘要](chicken-D-prediction-summary.json)

已用private CPU作业13233773评分这一个完成臂，11秒、0.0122 allocated CPU-hours。单臂文件为score-D-primary.json和score-D-full.json，完整矩阵仍使用预定score-primary.json/score-full.json；不覆盖冻结准备或提前生成比较结论。[评分摘要及逐染色体计数](chicken-D-score-summary.json)

| 鸡 D 评价域 | 参考 gene-loci | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 冻结主域 | 6,588 | 4,480 | 3,451 | 2,108 | 0.564872 | 0.680024 | 0.617122 |
| 完整常染色体 | 16,262 | 11,601 | 8,246 | 4,661 | 0.584522 | 0.713381 | 0.642554 |

逐染色体TP/FP/FN之和与总体一致，TP+FN与冻结参考分母一致。主域8,670条唯一预测CDS链中5,219条匹配参考，折叠为4,480个参考loci的TP；同一locus的多个正确isoform不增加TP或FP，其余3,451条不匹配链记FP。16条缺完整codon feature的预测仍保留在评价中。完整常染色体包含D监督暴露区域，不能当作独立验证。以上均为RefSeq一致性，尚不能判定掩码用途改善、优于RM2/RED或未见物种泛化。

鸡RM2_FULL（13194349_2，内部13233079）已于06:22:52 UTC自动接续，鱼D正在全基因组AUGUSTUS预测；其余三臂依次排队。仍为每臂16CPU/96GB/72h、无GPU、最多两臂ETP并发。全部输入、其他臂和评价规则保持冻结，不根据这个单臂分数改变实验。

## 2026-09-28：鱼 D 原生终态核实，评分已排队

本次恢复连接后按集群UTC时间核实：鱼D（13194349_1）已于2026-09-27 12:30:46 UTC完成完整ETP，原生日志有BRAKER RUN FINISHED，状态PREDICTION_READY。最终braker.gtf为107,307,642 bytes，原生解析得到369,505条CDS feature、35,484条transcript feature和28,084条gene feature。Slurm耗时177,111秒（49小时11分51秒），787.1600 allocated CPU-hours；batch MaxRSS为22,954,200 KB。两个D臂ETP累计1,476.2089 allocated CPU-hours，预处理和评分成本另列。[鱼D原生摘要](zebrafish-D-prediction-summary.json)

鱼D的冻结CDS及长读长结构评分已提交private CPU作业13246903（4CPU/16GB/2h，无GPU）。截至核实时仍在排队，尚未产生score-D-primary.json/score-D-full.json；不能用提交状态代替指标。沿用zebrafish-r2的14,576个主域参考loci与27,862条长读长结构，不改变分母或把无RNA匹配定义为FP。

鱼RM2_FULL（13194349_3，内部13234648）于2026-09-27 12:30:46 UTC自动接续。两物种RM2目前均在原生AUGUSTUS优化阶段，两个RED臂等待数组并发名额；ETP仍最多两臂并行。未新增训练、输入或阈值，也未因中途分数修改对照。当前仍无D对RM2/RED的完整比较结论。


## 2026-09-29 15:33 UTC：鸡 D–RM2 固定比较与鱼 D 评分

按恢复连接后的集群实际时间核实，鸡RM2_FULL（13194349_2）已于03:07:03 UTC完成完整ETP。原生日志有BRAKER RUN FINISHED，最终GTF为68,517,021 bytes，含244,770条CDS、21,416条transcript、15,984条gene feature。Slurm耗时161,051秒（44小时44分11秒），715.7822 allocated CPU-hours，batch MaxRSS 24,109,488 KB。三个已完成ETP臂合计2,191.9911 allocated CPU-hours，未完成臂与预处理另列。[原生终态](chicken-RM2_FULL-prediction-summary.json)

鸡D与RM2的预定比较由private评分作业13290194完成：25秒、0.0278 allocated CPU-hours。沿用原评分实现、冻结区域、分母、seed42和10,000次染色体bootstrap，仅让现有提交脚本接受多个已完成臂。独立保存score-D-RM2_FULL-primary/full.json，不覆盖旧单臂或最终三臂文件。逐染色体计数与总体一致，D的重放指标及逐染色体计数与旧单臂逐项相同。[完整比较摘要、逐染色体和gross gains/losses](chicken-D-RM2_FULL-score-summary.json)

| 鸡评价域 | Arm | 参考loci | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 冻结主域 | D | 6,588 | 4,480 | 3,451 | 2,108 | 0.564872 | 0.680024 | 0.617122 |
| 冻结主域 | RM2_FULL | 6,588 | 4,278 | 2,651 | 2,310 | 0.617405 | 0.649362 | 0.632981 |
| 完整常染色体 | D | 16,262 | 11,601 | 8,246 | 4,661 | 0.584522 | 0.713381 | 0.642554 |
| 完整常染色体 | RM2_FULL | 16,262 | 11,364 | 6,808 | 4,898 | 0.625358 | 0.698807 | 0.660045 |

主域D−RM2的F1差为−0.015858，固定染色体bootstrap的95%区域敏感性区间为[−0.035426, +0.002503]。D增加260个匹配参考loci、失去58个，净增加202个；同时未匹配参考的预测链增加800条。完整常染色体F1差−0.017491，区间[−0.026804, −0.008513]，gross gains/losses为385/148。主域区间跨零不证明等效或非劣；全域含D监督暴露区域，不能作为独立验证。当前结果体现召回与precision的权衡，不支持D改善整体RefSeq一致性，更不能将未匹配链直接断言为生物学错误。每臂独立自训练，不能归因成固定预测器的纯mask效应。

鱼D评分13246903已于10:07:25 UTC完成：24秒、0.0267 allocated CPU-hours，batch MaxRSS 621,244 KB。冻结参考及长读长分母、逐染色体总数均相符。[鱼D CDS和结构分层摘要](zebrafish-D-score-summary.json)

| 鱼D评价域 | 参考loci | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 冻结主域 | 14,576 | 10,078 | 4,721 | 4,498 | 0.680992 | 0.691411 | 0.686162 |
| 完整常染色体 | 25,526 | 17,422 | 8,959 | 8,104 | 0.660400 | 0.682520 | 0.671277 |

| 鱼D长读长内含子链层 | 主域 recovered / observed | 主域恢复率 | 完整常染色体 recovered / observed | 全域恢复率 |
|---|---:|---:|---:|---:|
| 全部观测结构 | 4,146 / 27,862 | 14.8805% | 7,243 / 48,068 | 15.0682% |
| 参考CDS相容子集 | 3,897 / 4,874 | 79.9549% | 6,819 / 8,523 | 80.0070% |

参考CDS相容子集属于参考辅助层，不能将约80%的恢复率说成全部长读长恢复或独立完整CDS正确率。UTR-off预测的CDS内含子链与源转录本结构比较，源结构可能包含非编码转录本和UTR内含子；未匹配不定义FP。主域class=u恢复27/700、全域44/1,555，仅为源类别描述，不证明这些结构编码。全部源类别与逐染色体计数保留在摘要中。

鸡RED_FULL（13194349_4）已于10:07:01 UTC自动启动，原生日志处于ETP/GeneMark阶段；鱼RM2正在全基因组AUGUSTUS预测，鱼RED仍等待数组并发名额。六臂已有三个完成，完整比较仍未完成；继续固定两物种、原预算、输入和评价，保留当前负面结果，不增加搜索或改阈值。
