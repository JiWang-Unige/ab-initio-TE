# 本轮补实验执行与结果收敛

2026-09-15。用户明确要求完成前三项补实验、补充 Tiberius 与公平长输入 benchmark，允许既定范围内训练、结果处理、Git 提交和推送。本文件是持续跟进入口；作业启动不等于实验完成。

## 冻结范围

见 [本轮范围](PAPER-CLOSURE-20260915.md) 及五项独立协议。保持 seed42，不增加 seed；不以追求阳性为理由改模型、阈值、训练预算或评价集。Gap 暂停新增解决方案。保留人类 Tiberius 1% loss gate 失败及旧阴性结果。

共享 D 的 dm6、cattle、horse、opossum 和原协议指定的 worm 留出染色体继续封存；人类 chr19–22 不开放。新的 cow **P3/Tiberius** 实验单独获准，不授权共享 D cattle 评价。NTv2 的新 EVAL 需要排除先前读过的 query 及其同源/近邻记录；不能把旧结果重新命名为独立验证。

本机 `/Users/jiwang/Desktop/TE/ab-initio-TE`；远程 `/home/users/j/jwang/ab-initio-TE`。当前直接 `ssh baobab` 可用，旧 Bamboo 跳转不是必需路径。重计算只用 Slurm；login 只读小型状态、日志、调度与传输。

## 当前执行图

| 工作 | 作业/输出 | 后续验收 |
|---|---|---|
| 库控制 | selected12732075；12732016为重复的顺序版本已取消，输入panel.tsv逐字一致 | 同引擎/同 hg19 输入；区分全库与人 lineage 的内容混杂；旧重复尝试保留，不用于速度比较 |
| source-only 匹配/蛋白 | 12732331已完成；12732397在新库注释完成后计算no-reuse库支持 | 5540个唯一配对；15695 FP未匹配；强蛋白命中仅4/21235且matched为0/5540，不能支持广泛FP rescue |
| NTv2 label-free | 12732191完成41分33秒；权重核查12733074完成；旧尝试保留 | 六臂已完整评价：适配transductive ARI小幅增，但NMI和inductive ARI较冻结NTv2下降，不能称稳定提升；本项闭合，见独立RESULTS.md |
| SF5 ontology | prep12731940完成；train/eval12731987 | 5400 TRAIN、1440 VAL、2160 TEST，完整六物种、八类本体；按物种报分母 |
| Tiberius 数据 | acquire12731819、prep12732000完成 | cow470参考loci（220含NM转录本）；platypus639（0含NM），均是注释相对效用 |
| Tiberius 参考修复 | 12732214_0 cow已完成；_1 platypus继续运行 | cow完整Dfam3.9库1718条、219080 repeat rows；两物种均合格后继续smoke |
| Tiberius smoke | 12732021_[0,20]，依赖12732214 | 两物种各一 core × 五arm，实际模型5/6通道、相同大写序列、GTF/GFF3坐标一致 |
| Tiberius full | 12732547_[0–39%2]，afterok12732021 | 两物种smoke五arm全部完成才可开始，runner另检查两份资格状态；已完成smoke复用，其余core新运行 |
| Tiberius score | 12732548，afterok12732547 | 200cell全部完成后生成 `outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1/result.json` |
| 长输入模拟 | model/smoke12731809、sim10012731886完成 | 100,000,000bp，163602片段，插入材料55000087bp，坐标/大小写材料mismatch0；L3/strand未资格化 |
| 长输入真实 | prepare12731942完成 | CB4全基因组108384165bp，367序列，真实只报reference-positive recall |
| native方法 | CB4: selected12732198_0/4、12731966_1、12731946_2/3；sim:12731947_[0–4] | 五软件 × 两输入，16CPU/80GB/24h，每个完整管线；保留TIMEOUT和失败 |
| 固定D | 两项GPU已完成：CB4 3952.27s/P100、sim 3029.51s/TITAN X；CPU12731959运行/12731960等待 | 全部108384165/100000000bp实际处理；GPU硬件不同，CPU/native未齐前不形成速度排名 |
| 长输入评分 | 12732389，afterany所有上述native和D作业 | `outputs/TE-LONG-BENCH-20260915/score-12732389/result.json`；Slurm终态进入完整14cell分母 |

## 真实失败与修正

- Dfam4 缺少 uncurated 分区时 FamDB 可能 exit0 且输出部分库。CB4 初次 fixed RM 和 EarlGrey 初始 mask 尝试不能代表完整库。选用完整分区 Dfam3.9 的同一 lineage library 用于 fixed RM/EarlGrey；原引擎4.2.4固定，所有尝试见 `configs/TE-LONG-BENCH-20260915-attempts.json`。
- EarlGrey 使用 `/usr/local/share/RepeatMasker/Libraries/famdb`，需要其真实路径挂载；仅设置 FAMDB_DIR 无效。支持的 `-l` 显式传相同初始库。
- 新 Tiberius 12732197 缺少 RepeatMasker 启动所需 FamDB 挂载，已在12732214修正；旧注释/日志保留，未将错误库的 mask 用于正式推理。
- native EDTA 在 CB4 LTR 阶段出现空候选文件警告但继续执行；最终必须结合完整输出检查它是无候选还是实际未完成，不能只凭进程exit0认可科学输出。

## 完成动作

1. 读取各作业实时Slurm终态、日志和实际产物；修复明确接口错误时保留原尝试，按相同输入、模型、阈值、预算重试并更新映射和依赖。不得为达到好分数换配置。
2. Tiberius只有200cell全部合格才运行固定科学评分；比较P–R_TE、P–U_nosm及其他两对照，按染色体paired bootstrap，保留loss loci。原人类结论不覆盖。
3. benchmark聚合每方法/物种的实际输入、失败、墙钟、资源、知识条件。模拟真值F1和真实阳性召回分开，CPU/GPU同硬件类别解释，不能把Omni回放时间当native时间。
   模拟生成family与实际固定库的name/accession重叠核实由 `library_exposure.py` 和 `reports/TE-LONG-BENCH-20260915/library-exposure/` 记录；只做协议已要求的库暴露披露，不改变调用或分数。
4. `benchmarks/te_omnibenchmark/long_panel.yaml` 已固定到代码commit `4edaeb16e735be4c25fdbace12822f026604f649`（配置提交ef6cecf已推送）；用本机现成 Omni runtime、真实 compact block bundle 运行图。Omni的范围是从Slurm已验证block充分统计量重算指标，不伪称重跑native工具。
5. 将compact结果、限制、正文/补充材料定位与用户五项问题的结论写入研究文档；原始序列、概率数组、权重留远程。提交并推送到既有GitHub。没有完整结果时保持RUNNING/PARTIAL，不写“论文已闭合”。

若计算跨本次交互，沿用已有TE跟进任务，正常运行或状态未变时静默，仅对完成、真实失败、结论变化或用户决策通知。全部已授权结果处理和推送完成后暂停跟进。
