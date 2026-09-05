# L1 发布准备：元数据与接口边界

日期：2026-09-05。本文只整理本地协议、物种表、来源说明和接口代码；未读取保留面板的序列、标签或预测文件，未执行推理、训练、下载或发布。它不是模型有效性结论，也不开放任何新实验。

当前可以继续做 sequence-only 接口和发布范围准备；内部 DEV 达标本身不等于对外发布就绪。现行初始化协议明确把最终保留面板开放、公开权重/服务和可见性变更留给用户审阅。

同日后续：初始化扩展已科学NO-GO并完成空间CI归档；无标签FASTA接口
已单独实现，9项合成测试及冻结D的8206bp人工序列CPU smoke通过。
下文“接口差距”保留最初审阅时的事实，后续实现与验证详见
[FASTA接口V1](CROSS-SPECIES-L1-FASTA-INFERENCE-V1.md)。这补上工程入口，
不补上外部泛化、历史暴露、独立效用或公开许可的证据缺口。

## 物种角色：必须保留历史语境

下表比较两个已经存在的**角色声明**，不把旧表中的角色直接当成某个具体 checkpoint 的实际训练证据。

| 物种 / 当前 assembly | 2026-08-11 frozen species 表 | 当前 X0-R2 表 |
|---|---|---|
| human / hs1、mouse / mm39、chicken / galGal6、zebrafish / danRer11、c_elegans / ce11 | train_core / fit_only | train |
| pig / susScr11 | mammal_holdout / primary_test | train |
| fruit_fly / dm6 | train_core / fit_only | primary，显式 chr2L/chr2R/chr3L/chr3R |
| horse / equCab3 | mammal_holdout / primary_test | primary |
| opossum / monDom5 | optional_stress / audit_only | primary |
| cattle / bosTau9 | mammal_holdout / primary_test | replication |

旧表还列出 western_clawed_frog、western_honey_bee、red_flour_beetle、lizard 和 x_laevis；当前 X0-R2 表没有这些行，不应自动把它们纳入当前承诺。当前人类 `primary_regex` 仅列偶数 chr2–chr18；worm 记录 4 个 train chromosomes、1 个 validation chromosome，不在这张表里给出其具体分配。这里没有重新计算染色体分配。

因此，当前的 “held-out” 应限定为当前冻结方案的监督/选择边界，不能仅凭当前角色表宣称“全项目历史未见过”，更不能据此推出 backbone 预训练未见过。尤其 pig 与 dm6 的角色在两个方案中不同。完整的实际 checkpoint、家族和同源暴露审阅仍是现行协议要求的后续证据，不是本文新发现了泄漏。

证据：[当前 species_x0_r2.tsv](../../scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv)；[旧 FROZEN_SPECIES_HOLDOUT_V1.tsv](../../scripts/experiments/SF-DIRECT-BASELINE-SCREEN-20260811-R2/FROZEN_SPECIES_HOLDOUT_V1.tsv)；[material route 的 claim boundary 与 E1/E2/E3 定义](CROSS-SPECIES-L1-MATERIAL-ROUTE-20260903.md)。

## 来源与许可：已有记录和未闭合部分

当前 species 表给出准确 assembly 名、FASTA 路径和 project-owned self-run RepeatMasker Label-A 路径；它没有逐 assembly 的下载来源版本、分发条款或发布包范围。`docs/species_label_source_audit.md` 已说明 Label-A 来自 self-run RepeatMasker+Dfam，UCSC rmsk 只是外部/历史 comparator。**“project-owned” 指本项目生成注释，不自动代表所有上游素材的分发许可。**

已有正面许可记录不应写成“全部未知”：本地 Dfam 3.9 dossier 记录该固定 release 的 CC0 1.0；RepeatModeler2 2.0.9 / RepeatMasker 4.2.4 dossier 记录 Open Software License 2.1，并将 Repbase-derived library 作为单独依赖、排除于该 smoke。后者是指定版本的工具记录，不是对当前历史 Label-A 作业实际工具/库版本的替代证明。

初始化协议记录 native NTv2-500M 下载来源为 `InstaDeepAI/nucleotide-transformer-v2-500m-multi-species`、日期 2026-05-21，H0 metadata 指向同一个本地目录。协议的最新 J0 补记已从既有 source cache metadata 识别 native config 与 PyTorch weights 的 revision `06615c1660c892fc199840c18123f8385b3542a8`；这补上 native source revision，不独立证明历史 H0 的不可变 ancestry。本次查阅的现行协议与上述来源记录未附该 revision 实际下载 checkpoint 对应的许可证/模型卡副本、衍生权重与服务的适用条款说明。该缺口不是“禁止使用”的判断；在决定具体发布什么之前，仍需把实际权重/代码/素材与其来源条款对应起来，不能从工具或 Dfam 的许可外推模型权重许可。

证据：[初始化来源记录](CROSS-SPECIES-L1-INIT-HISTORY-V1.md)；[Label-A source audit](../species_label_source_audit.md)；[Dfam 3.9 source/license dossier](../../refs/dossiers/dfam39-authoritative-alias.md)；[RepeatModeler2 / RepeatMasker source/license dossier](../../refs/dossiers/repeatmodeler2_repeatmasker.md)。本文只引用已有归档记录，未在线重审条款，也不作法律许可结论。

## 现有接口与 sequence-only FASTA 的差距

当前 L1 评估入口 `calibrate_evaluate_x0.py apply` 接收 `--data SPECIES=JSONL.GZ`，不是原始 FASTA。`infer_half_margins` 本身只消费 sequence，已有 tokenizer、4096-bp 分半和 6-mer/tail 投影可以复用；但外层 `assemble_tiles` 要读取 `labels`，`evaluate_species_tiles` 将阈值预测与来自 Label-A 的 `callable` 相交。这是既定评估口径，不是评估 bug，却不能原样当作无标签 FASTA 的预测保留规则。

可用 FASTA 入口仍需把 sequence-to-margin 与 label-aware evaluation 分开：只凭 FASTA、冻结 model/tokenizer/calibrator 保留预测，明确 contig 坐标和短尾处理，另行导出输入 ambiguity 的 QC 轨道。输出应是 TE-material probability 和可选 connected-run BED；BED 连通片段不是 insertion ID。该工程观察限定于本次读取的现有 L1 入口，不声称仓库中所有历史脚本都没有 FASTA 功能。

证据：[现有 L1 evaluator/inference helpers](../../scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py)；[初始化协议的 sequence-only 后续边界](CROSS-SPECIES-L1-INIT-HISTORY-V1.md)。本文没有实现或运行新接口；当前授权的 smoke 范围仍是 synthetic 和已有 TRAIN sequence，不是最终保留资产。

## 留给最终用户审阅的决定

下一次人闸应在最终保留 worm chromosome、horse/opossum/dm6/cattle 开放前，确定冻结模型、推理/校准方案及它们能支持的具体 claim；历史 CONF 已用于闭合，当前初始化协议禁止新推理、诊断或据此选择，不能当作新的确认集重开。家族/同源暴露、物种/全 assembly 泛化和独立 utility 的证据边界需一起呈现，但本文不替它们给出结果。

公开前还需用户决定发布对象是代码、衍生权重还是服务、哪些数据随包，以及公开可见性；据所选范围完成对应来源/许可审阅，附可复现的无标签推理入口和限制说明。内部自动训练条件或 `FREEZE_READY` 不替代这些决定，也不自动授权扩大资源规模或更改核心科学目标。

证据：[continuing authorization 与 release boundary](CROSS-SPECIES-L1-UPSTREAM-20260904.md)；[当前初始化协议](CROSS-SPECIES-L1-INIT-HISTORY-V1.md)。
