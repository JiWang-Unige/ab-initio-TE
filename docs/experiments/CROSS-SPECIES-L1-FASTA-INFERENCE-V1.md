# L1 sequence-only FASTA 接口 V1

2026-09-05：初始化训练扩展科学NO-GO后的已授权有界工程。
不训练、不改变冻结校准/阈值/原评估器、不释放任何保留面板。
实现与有界验证已完成：9项合成测试和一次冻结D模型CPU smoke通过。
不将接口工程就绪等同模型有效性或公开发布。

## 输入与输出契约

- 输入：plain/gzip FASTA、已存在的NTv2 token-classification final model、
  tokenizer/model-code目录和该模型原有的六物种共享CAL校准JSON。
- 不接收labels、RepeatMasker注释或Label-A Unknown/callable mask。
- 每个contig从0开始按4096bp无重叠分窗，短尾使用实际序列长度；复用
  `calibrate_evaluate_x0.py` 的6-mer/单碱基尾部投影与冻结Platt变换。
- 概率轨覆盖全部输入碱基；BED只使用校准文件内阈值的`>=`规则，
  跨相邻窗口/批次合并连续阳性，不跨contig，不补gap、不筛长度。
- 单独输出非ACGT输入的ambiguity QC BED。歧义输入由已有tokenizer
  规则映射，QC轨不能作为删掉预测的标签替代物。
- 输出为material概率及connected-run BED，不是生物学插入实例ID，
  没有family/superfamily预测。坐标为0-based half-open。
- 分批推理、流式写概率/片段，避免累积全染色体浮点预测数组；FASTA
  读取可保留一条contig序列。输出目录是独立运行产物，不写checkpoint。

## 验证边界

首先用合成margin provider验证坐标、短尾、批次边界、跨窗连通、
多contig、gzip和ambiguity不删预测；校准源不匹配必须在推理前拒绝。
随后仅对合成FASTA使用冻结D seed42完成一次小型真实模型工程smoke，
沿用项目Slurm运行环境。可将相同合成序列直接送入已有推理helper，
比对完整概率与冻结阈值结果；这是接口一致性，不是新的科学测试。
不读取CONF、reserved worm、horse/opossum/dm6/cattle资产。

现有历史 `pipelines/PIPE-TEFM-FINAL-20260623/infer_fasta_to_bed.py`
是8192bp、single_nt_nospecial、固定0.5的CE桥，不适配本NTv2 6-mer
加Platt模型；不改它的冻结语义。新接口独立位于
`scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/`。

## 效用与发布范围

工程通过最多支持“可对无标签FASTA生成完整坐标概率/材料片段”的声明。
不能由此声称跨物种泛化、碎片重建、插入边界恢复或独立下游效用。
后续实用比较应冻结模型/校准、真实使用单位、资源成本和决策终点，
把material coverage与严格topology负面对照同时保留；不放宽gap或指标。
独立utility数据、最终保留面板、同源/家族/历史暴露和多seed确认仍需
单独协议与用户审阅。公开代码/权重/服务、改变可见性与随包素材的选择
不由本接口自动授权。来源与许可现有记录及缺口仍见
`CROSS-SPECIES-L1-RELEASE-READINESS-20260905.md`，本次不作法律结论。

## 工程实施与审查

`infer_fasta.py` 和9项合成单测已完成。覆盖4096/8192窗口边界及1–5bp
终端窗口、跨批次连通、阈值相等、plain/gzip多contig、大小写/IUPAC、
完整概率roundtrip、校准身份及失败无成功summary。原推理helper未修改。
独立只读subagent审查PASS，主代理自审未发现未解决问题。
已修正第一条contig在迭代其余序列时被额外保留的引用；无需迁移层。
这里只是合成接口验证，不能代替真实模型smoke。

命令入口接受 `--fasta --model-dir --tokenizer-dir --model-code-dir
--calibration-json --output-dir`，可选 `--batch-size`（默认12）及`--cpu`。
不提供标签、阈值、gap或长度过滤参数。成功目录包含
`material_probability.bedGraph.gz`、`material_runs.bed`、`ambiguity_qc.bed`
及最终`summary.json`。已有同名产物拒绝覆盖；失败可能留下部分轨道，
应使用新的输出目录，并以可解析、状态COMPLETED的summary判定完成。

真实smoke脚本 `smoke_fasta.py` 仅构造8206bp合成序列：两个contig，
实际窗口长度4096/4096/9/5，使用冻结D seed42及其原CAL。
捕获同一次helper推理的margin来比对输出，不再执行第二遍模型推理。
`sbatch/CROSS-SPECIES-L1-FASTA-INFERENCE-V1.sbatch` 使用CPU-only
private分区、4CPU/16GB/30min、显式te_benchmark环境与srun。
没有labels或split数据读取、训练、checkpoint写入或GPU请求。

smoke脚本与sbatch另经独立只读审查PASS。`smart-sbatch` Phase1：
3个现有任务+1=4/8、至多3个方向、单任务；CPU-only显存/排除项不适用；
30min小于12h/168h、214TB可用、无维护、独立job-ID日志和输出。
源码 `8ad7ba7` 双端同步后提交CPU smoke `12402018`。
产物目录 `outputs/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/12402018/`，
日志 `logs/te_l1_fasta_smoke_12402018.{out,err}`；真实smoke结果待验。

## 工程闭合与使用

`12402018` COMPLETED0:0，用时45秒，`smoke_report.json` 为PASS，
推理summary为COMPLETED/device=cpu/total_bp=8206。四窗口
4096/4096/9/5均完成；全部概率逐值等于捕获的原helper输出，BED与冻结
阈值匹配，QC仅对应输入4个歧义碱基。人工序列没有阈值阳性；这不能验证
真实阳性检测效果，跨窗阳性合并的功能证据来自合成margin单测。
本次无标签、真实基因组面板或GPU读取/请求；模型权重本身为原冻结D。
完整紧凑报告与summary归档在本文同名目录。GPU总账仍为3.081944h。

接口在已获授权的FASTA上、项目Slurm分配内调用，例如：

```bash
python3 scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py \
  --fasta /path/to/authorized-input.fa.gz \
  --model-dir /path/to/frozen/final_model \
  --tokenizer-dir /path/to/frozen/final_model \
  --model-code-dir /path/to/native/ntv2-code \
  --calibration-json /path/to/that-model/calibration.json \
  --output-dir /path/to/new-run-output \
  --batch-size 12
```

路径必须与现有CAL身份一致，不能把另一个模型的校准套用过来；CPU运行
加`--cpu`。Baobab不可在登录节点直接运行此命令，须在既有`srun`分配内
或经`smart-sbatch`提交。示例只是接口用法，不授权开放额外数据。
复现本次人工输入工程验证可查看对应sbatch，但已完成者不需再提交。

有界接口、来源历史/许可缺口说明和效用范围准备现已交付。本轮不自动
追加TRAIN/全染色体/保留面板推理，不发布权重或服务，不新开训练路线。
本轮heartbeat在归档同步后关闭，后续科学或发布选择留给用户审阅。
