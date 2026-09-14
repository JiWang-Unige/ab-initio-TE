# TE_final Dfam/contrastive 证据恢复（2026-09-14）

## 结论先行

这次 SSH 取证找到了两套容易被混淆的 contrastive embedding 结果，以及当前仓库中的一套独立 Dfam panel：

1. 当前 Baobab `TE_final` 的 M5 表是一个 10,000 fragments、12 classes、13 species 的历史表。它的 GLM contrastive 结果较弱；最强的 class-level 结果反而是 `6-mer + contrastive`（B0，ARI 0.9281）。
2. Baobab `TE_final_archived` 的 Phase 7 报告和历史日志确实记录过一个很强的可训练 GLM contrastive B1：ARI 0.6928、NMI 0.7164、Purity 0.8595；报告将其与 6-mer ARI 0.0425、NMI 0.0729 比较。这是另一套 panel，而且原始 `exp004` comparison 目录没有随 archive 保留；由于 panel 和 raw lineage 没有闭合，目前只能作为内部研究线索/历史自述，不能直接做 supplement quantitative figure。
3. 当前仓库中精确的 Dfam consensus 结果（1,800 fragments、10 family clusters、512 bp）只有本地 `tefm_calib` panel 找到：A1（native GENERanno + family-supervised contrastive）为 ARI 0.2242、NMI 0.3119；C1（basic sequence features + contrastive）为 ARI 0.7083、NMI 0.7135。它支持 A1 相对 A0 的改善，但不支持“GLM embedding 远超 basic features + contrastive”。

因此，当前只能把历史 Phase 7 B1 保留为待恢复的跨物种粗粒度 superfamily embedding 线索；在 raw result、panel 和 split 没有闭合前，不把它写成 supplement quantitative figure，也不能把它与当前 Dfam 1800/10-family 结果合并，更不能据此声称已经完成无监督、未见家族或新物种泛化验证。

## 取证范围与远端位置

- SSH 账户：`jwang@login1.baobab.hpc.unige.ch`。本次只在登录节点进行轻量目录、文本读取和文件复制，没有训练、重评分或解封旧配置。
- 当前目录：`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final`
- 历史 archive：`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final_archived`
- 远程 `TE_final` 中没有找到 `embedding_dfam_consensus.tsv`、`embedding_strict.py`，也没有找到包含当前本地 `.224190` 或 `.708307` 数字的结果表。
- 没有复制 genome FASTA、Dfam 大库、embedding arrays、checkpoint、training state 或凭据。紧凑源码、配置、结果表和必要日志已复制到本报告目录下的 `reports/TE-FINAL-DFAM-RECOVERY-20260914/`。

## 证据 A：当前 `TE_final` 的 M5 表

### Panel 身份

远程文件：

`archive/v1_modules/module5_contrastive/results/summary/embedding_comparison.tsv`

该表和配套日志显示：10,000 fragments，12 classes，13 species；比较 class-level 与 species-level 的 NMI/ARI。M5 代码和日志使用 contrastive projection，但这个 panel 与本地 Dfam consensus 1800/10-family panel 的数据身份不同。

### 数值

| Setting | 描述 | Class NMI | Class ARI | Species NMI | Species ARI |
|---|---|---:|---:|---:|---:|
| A0 | Raw 6-mer frequencies | 0.101456 | 0.031519 | 0.147555 | 0.043361 |
| A1 | Pretrained GENERanno，无 contrastive | 0.056494 | 0.020756 | 0.021119 | 0.006512 |
| A2 | Multi-species finetuned GENERanno，无 contrastive | 0.071412 | 0.018771 | 0.063802 | 0.023421 |
| B0 | 6-mer frequencies + contrastive projection | 0.971285 | 0.928141 | 0.121129 | 0.024522 |
| B1 | Pretrained GENERanno + contrastive | 0.100685 | 0.045053 | 0.030885 | 0.011761 |
| B2 | Finetuned GENERanno + contrastive | 0.077095 | 0.024541 | 0.061517 | 0.022439 |

`docs/EMBEDDING_RESULT_SUMMARY.md` 对此表的解释也是：B0 是强的 k-mer control；A1/A2/B1/B2 的 foundation-model embedding 结果弱，不能据此主张 foundation model 已经形成可靠的 TE-family geometry。B0 的高分不能归因于 GLM。

配套 B1 日志记录了 10,000 sequences、base embedding shape `(10000, 1280)`、50 contrastive epochs、temperature 0.07、hidden 256、projection 128，并记录了一个与汇总表略有差异的最终 NMI 0.0925、ARI 0.0421。这说明日志与汇总表不是同一版本/同一输出的完全一致副本；论文应以可重放的固定 artifact 为准，不混用这两行数字。

## 证据 B：`TE_final_archived` 的 Phase 7 历史 B1

### 报告中的 panel 与结果

远程文件：

- `results_summary/06_unsupervised_clustering.md`
- `history/cluster7.txt`
- `te_foundation/phase7_embedding/configs/experiments/exp004_B1_warm_trainable.yaml`

`06_unsupervised_clustering.md` 描述的 panel 是 hg38 test set、n=5,000 sequences、5 个粗粒度类别：LINE、SINE、LTR、DNA、Background。报告表给出：

| Model | ARI | NMI | Purity |
|---|---:|---:|---:|
| K-mer | 0.0425 | 0.0729 | 0.3237 |
| A2 random frozen | 0.0172 | 0.0312 | 0.2027 |
| A1 pretrained frozen | 0.0897 | 0.1197 | 0.3946 |
| B2 pretrained + head | 0.0685 | 0.0984 | 0.3541 |
| **B1 pretrained trainable** | **0.6928** | **0.7164** | **0.8595** |

`cluster7.txt` 中同一历史讨论再次记录 B1 的 ARI 0.6928、NMI 0.7164、Silhouette 0.595、Purity 0.859，并另行记录过 A1 0.532/0.642/0.524/0.777 和 k-mer 6-mer ARI 0.0330、NMI 0.0905。A1 和 k-mer 的这些不同数字表明历史记录包含不同阶段、不同筛选或修复后的输出；B1 数字虽然在报告和日志中重复出现，但不应与本地 Dfam panel 直接拼接。

历史聊天记录称该设计使用六个物种（hg38、mm39、galGal6、danRer11、dm6、ce11）和七个 coarse labels（LINE、SINE、LTR、DNA、RC、Unknown、Background）。这与 `06_unsupervised_clustering.md` 的 hg38、五类叙述不完全一致，必须视作 panel/阶段身份未完全闭合的限制。记录还显示 A1/A2 曾因 Slurm 超时缺少完整 comparison 阶段，随后提交过补充作业；archive 中没有保留这些 `exp004` 的完整 raw comparison JSON。

## 证据 B2：`exp002_consensus_100bp` 只有计划和代码，没有完成的 consensus metrics

这条分支是本次针对“Dfam consensus contrastive”记忆的重点核查。远程可找到：

- `te_foundation/phase7_embedding/configs/experiments/exp002_consensus_100bp.yaml`
- `te_foundation/phase7_embedding/slurm/prepare_consensus_data.sbatch`
- `te_foundation/phase7_embedding/slurm/train_exp002_consensus.sbatch`
- `te_foundation/phase7_embedding/slurm/evaluate_exp002_consensus.sbatch`
- `te_foundation/phase7_embedding/NEXT_STEPS.md`
- `history/cluster2.txt` 中关于创建 consensus evaluation pipeline 的记录

配置把数据源写为 Dfam38 consensus，fragment size 100–300 bp、10,000 train pairs、1,000 validation pairs、5 epochs。可是 `NEXT_STEPS.md` 仍把 Consensus 列为 MVP 成功后的 Phase 7.2，并把 Real Genome/Consensus 的 ARI、NMI、Silhouette 都写成 `?`。`cluster2.txt` 也只显示了脚本和 pipeline 的准备/修改，没有提交完成和结果数值。

受限 `find` 检查在当前 `TE_final` 和 `TE_final_archived` 都没有发现 `exp002_consensus_100bp` 的 data、embeddings、clustering、metrics、comparison 或日志目录。archive 中存在的 `exp002_real_extended` 是另一项 `source: real_genome`、hg38 chr1 的 50,000-pair 实验；它有 checkpoint 目录，但其 `embeddings/`、`clustering/`、`family_analysis/` 目录为空，且不是 Dfam consensus 结果。因而不能用 `exp002_real_extended` 或 Phase 7 B1 的 coarse-label 表替代用户记忆中的 consensus metrics。

这个结论的边界是“在本次访问的两个明确远端目录中没有找到闭合产物”，不等价于证明该作业从未在其他路径运行；如果后续提供具体 job ID、log 路径或其他 archive 位置，应沿该身份继续核查。

本次恢复结论是：远端 `TE_final` 中没有找到一套可核验的 `exp002_consensus_100bp` 完成结果；当前可核验的 Dfam consensus 数字仍是本地 `tefm_calib` 的 A0/A1/C0/C1 panel（见证据 C）。

### 配置能确认什么

`exp004_B1_warm_trainable.yaml` 明确写出：

- backbone 是 GENERanno-TE-Finetuned，`freeze_backbone: false`；
- sequence length 512，InfoNCE，temperature 0.07；
- positive strategy 是 `same_class_any_species`，并使用 hard-negative ratio 0.3；
- clustering 使用 k-means（7 clusters）和 HDBSCAN；
- 六物种路径和每一类的抽样目标在配置中给出。

这些信息支持“这是按跨物种、可训练 backbone 设计的 contrastive screen”，但配置本身不能证明实际运行时没有同源序列泄漏、不能证明物种留出，也不能替代保存的 raw split manifest 和 embeddings。

## 证据 C：当前本地 Dfam consensus panel

### Panel 身份与执行代码

本地匹配 artifact：

- `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`
- `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/embedding_strict/Dfam_consensus/family_len512/{A0,A1,C0,C1}/metrics.json`
- `pipelines/PIPE-TEFM-SEG-SF-20260618/embedding_cluster.py`

该 panel 有 1,800 条 512 bp fragments、10 个 family labels。代码对标签做 stratified 75/25 split（holdout 约 450 条），并在 contrastive 分支调用 `supervised_contrastive_project`，使用 family label 构造正负关系。因此这里的“无监督聚类”是指 k-means 评价阶段；表示学习本身使用了 family supervision，也没有建立 unseen-family 或 homology-isolated holdout。

### 数值

| Setting | 说明 | ARI | NMI | Holdout macro-F1 | Silhouette |
|---|---|---:|---:|---:|---:|
| A0 | Native GENERanno | 0.079557 | 0.141071 | 0.238251 | 0.192695 |
| A1 | Native GENERanno + family-supervised contrastive | 0.224190 | 0.311891 | 0.413748 | 0.173721 |
| C0 | Basic sequence features | 0.142266 | 0.238580 | 0.338528 | 0.074476 |
| **C1** | **Basic sequence features + contrastive** | **0.708307** | **0.713472** | **0.421935** | **0.387822** |

A1 相对 A0 有清楚改善（ARI 0.0796→0.2242，NMI 0.1411→0.3119），说明 contrastive objective 对该 panel 有效；但 C1 的 ARI/NMI 明显最高，且 holdout macro-F1 也略高。因此当前本地 Dfam 结果不能支持“GLM + contrastive 远超 basic features + contrastive”。这也是目前最直接、可追踪的 Dfam 结论。

## 身份分离与论文使用边界

| 结果 | 是否可与本地 Dfam panel 合并 | 推荐论文位置 | 可支持的表述 |
|---|---|---|---|
| 当前 M5 B0/B1/B2 | 否 | supplement 或 negative diagnostic | 该历史 M5 panel 中 GLM embedding 较弱，k-mer contrastive 是强 control |
| Phase 7 B1 0.6928/0.7164 | 否 | 暂不入图；仅内部研究线索 | 历史记录中，一个 coarse-label screen 的可训练 contrastive GLM 曾取得强聚类结果；raw/panel/split 闭合后再评估是否可用于论文 |
| 本地 Dfam A0/A1/C0/C1 | 可作为本地独立 panel | supplement；若补齐拆分可进入正文 | A1 比 A0 好，但 C1 是当前最强对照，GLM superiority 未证实 |

如果 raw run identity 后续闭合，Phase 7 B1 的设计可以回答“在一个跨物种、粗粒度类别、允许 backbone 更新的 screen 中，contrastive adaptation 是否能显著重塑 embedding geometry”。现有报告和日志只提供这一方向的历史自述，当前不能把它当作已闭合的论文证据。它不能回答：

- 新 family 或未见 family 的 zero-shot 识别；
- 物种留出后的泛化；
- 真实 TE insertion 的 instance recovery；
- GLM 相对于强 sequence baseline 在 Dfam family panel 上的普遍优势。

如果将 B1 放入论文，图表必须同时给出 panel、类别粒度、sequence length、species split、family/homology isolation 状态和 raw artifact 状态，并标为 exploratory/historical，避免把 `.6928` 直接引用成当前 Dfam `.7083` 的来源。

## 建议的后续闭环

1. 固定一个可复现的 Dfam consensus panel：保存 release、family IDs、fragment sampling、deduplication 和 split manifest；把 train/holdout family identity 与序列同源隔离状态写入结果表。
2. 在同一 panel、同一 split、同一 clustering protocol 下记录 `A0/A1/C0/C1`；本轮按用户要求保留现有 single-seed screen，不自动扩展为 multiseed，也不把它包装成 claim-grade 证据。本恢复任务没有启动新训练。
3. 另做 family-held-out 与 species-held-out 评价，把“表征能否聚类已知标签”和“能否泛化到未知 family/species”分开。
4. 对 historical Phase 7 B1，仅在能找回 raw embeddings、真实 label manifest、split 和完整 comparison JSON 后，再考虑是否升级为论文图表；在此之前只保留为内部线索/历史自述。
5. 不把 M5 的 B0 高分写成 GLM 成功；它更适合作为 sequence-only contrastive control，也应检查是否存在标签泄漏或过于直接的 composition signal。

## 已复制 artifact 清单

以下文件均为小型文本/配置/结果文件；目录结构相对路径按远端保留。`remote/...` 文件的来源是 Baobab，`local_current/...` 文件的来源是本地当前仓库，二者没有被合并成一套结果。

### Baobab 当前 `TE_final`

- `remote/TE_final/docs/EMBEDDING_RESULT_SUMMARY.md`
- `remote/TE_final/archive/v1_modules/module5_contrastive/results/summary/embedding_comparison.tsv`
- `remote/TE_final/archive/v1_modules/module7_deliverables/tables/clustering_comparison.tsv`
- `remote/TE_final/archive/v1_modules/module5_contrastive/scripts/compute_embeddings.py`
- `remote/TE_final/archive/v1_modules/module5_contrastive/scripts/train_contrastive.py`
- `remote/TE_final/logs/m5_B1_embed_20260216_002258.{out,err}`
- `remote/TE_final/logs/m5_embed_6792443_{0,1,3}.{out,err}`
- `remote/TE_final/logs/m5_embed_6793718_{2,5}.{out,err}`

### Baobab `TE_final_archived`

- `remote/TE_final_archived/results_summary/06_unsupervised_clustering.md`
- `remote/TE_final_archived/history/cluster7.txt`
- `remote/TE_final_archived/history/cluster6.txt`
- `remote/TE_final_archived/history/cluster2.txt`
- `remote/TE_final_archived/te_foundation/phase7_embedding/NEXT_STEPS.md`
- `remote/TE_final_archived/te_foundation/phase7_embedding/extract_metrics.py`
- `remote/TE_final_archived/te_foundation/phase7_embedding/configs/base.yaml`
- `remote/TE_final_archived/te_foundation/phase7_embedding/configs/experiments/exp002_consensus_100bp.yaml`
- `remote/TE_final_archived/te_foundation/phase7_embedding/configs/experiments/exp002_real_extended.yaml`
- `remote/TE_final_archived/te_foundation/phase7_embedding/configs/experiments/exp004_{A2_cold_frozen,B1_warm_trainable,B2_warm_frozen,cross_species}.yaml`
- `remote/TE_final_archived/te_foundation/phase7_embedding/data_sources/consensus.py`
- `remote/TE_final_archived/te_foundation/phase7_embedding/slurm/{prepare_consensus_data,train_exp002_consensus,evaluate_exp002_consensus}.sbatch`
- `remote/TE_final_archived/te_foundation/phase7_embedding/scripts/run_experiment.py`

### 本地当前 Dfam panel

- `local_current/summaries/embedding_dfam_consensus.tsv`
- `local_current/metrics/Dfam_consensus/family_len512/{A0,A1,C0,C1}/metrics.json`
- `local_current/source/embedding_cluster.py`
- `local_current/FINAL_REPORT.md`

## 验证记录

- 已通过显式 SSH 路径读取远端文件并逐项复制；复制后检查了文件存在、大小和关键 TSV/Markdown/JSON 内容。
- 本任务没有运行训练、推理、重评分、解密、Slurm 作业或大资产传输。
- 本任务没有提交 Git；父任务可在检查本报告和复制清单后统一提交。
