# Backbone、窗口与跨物种迁移证据清单

**盘点日期：2026-09-17。** 本文件只整理已存在的本地报告和 baobab 旧项目产物；本轮没有提交新训练或重分析，也没有改写冻结结果。数值只在相同任务、标签来源、分割、训练步数和评估口径内比较。不同项目之间的数值不可直接排名。

## 结论先行

1. GLM/NT 基座比较确实做过，而且分为三条不同证据链：
   - 本地 `PIPE-TEFM-SUPP-20260617` 是单 seed、800 step、human H0、token-proxy 的四基座 × 五窗口 quick screen；
   - baobab `/home/users/j/jwang/TE_final` 的 hg38-only N1/N2/N3 是 3-seed、bp-level binary、正式 chromosome split 的 backbone 主比较；
   - 本地 `PIPE-TEFM-FINAL-20260623` 是 NTv2/NTv3 尺寸 × 窗口迁移矩阵，495 行，包含 6 个 animal 和 5 个 plant 物种的一染色体 `one-chromosome` screen。
2. “人类 hg38 微调后迁移到其他哺乳动物”有真实数值。当前最清楚的证据是 remote v2 的 GENERanno N3 单 seed：牛 0.906、鸡 0.798、斑马鱼 0.740、爪蟾 0.695；植物和 tunicate 明显更弱。它支持“human-only 模型在部分 vertebrate 上可迁移”，不支持泛物种或仅靠遗传距离的置信度公式。
3. “human-only reference library 的 RepeatMasker 对照”也确实存在，但只在 remote **archive/v1** 模块中找到，且不是当前 v2/v5/v6 主证据链。`run_repeatmasker_human_lib.py` 使用 `RepeatMasker -species human`，在七个外部动物 chr1 上完成；最接近的人/猴较高，鼠/大鼠/牛/鸡下降。这一组可以作为 library-bias control 的历史结果或补充材料，不能与当前 N3 或 local matrix 直接合并成一个排名。
4. 当前最稳妥的模型结论是：`GENERanno N3` 是旧 hg38-only 正式 split 的最强 in-distribution backbone；在 local transfer matrix 中，`NTv2-250M @ 4096` 是 6-animal mean 的 screen leader（0.6482），而 `NTv3-100M-pre @ 2048` 是 5-plant mean leader（0.3980）。参数量越大并不保证跨物种迁移更好。
5. 六物种共享模型和 MoE 尚未构成一个可公开的“泛物种模型”：六物种 D 内部 seed42/17 证据显示 *C. elegans* 约 0.78–0.81，D 对其有小幅 bp/AP 改善但 interval/boundary 没有解决；adapter/MoE pilot 是冻结 backbone 的小 head routing 探索，不能被称为 sparse-backbone MoE 或已解决多物种稳定性。

## A. 本地 SUPP quick screen：四个基座 × 五个窗口

来源：

- 训练命令：`configs/pipelines/PIPE-TEFM-SUPP-20260617.train_jobs.tsv`；
- 汇总：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep_current.tsv`、`window_sweep.tsv`、`all_metrics.tsv`；
- 报告：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/FINAL_REPORT.md`。

这里所有单元都使用 human H0 quick panel、seed 42、800 training steps、相同 token-label/TE class weight 设定；指标是 TE-F1 与 TE-AUPRC 的 token-proxy screen。它适合回答“窗口和 backbone 是否有明显差异”，不适合替代三 seed bp-level 主结果。

| 基座（配置中的 identity） | 参数量（记录值） | 512 | 1024 | 2048 | 4096 | 8192 |
|---|---:|---:|---:|---:|---:|---:|
| DNABERT-2 | 117M | 0.7986 | 0.8922 | 0.8999 | 0.9101 | 0.8998 |
| GENERanno | 0.5B | 0.8702 | 0.8783 | 0.9326 | 0.9430 | 0.9340 |
| NTv2-500M | 500M | 0.8118 | 0.9068 | 0.9380 | **0.9458** | 0.9396 |
| HyenaDNA large | 配置未记录可核实参数量 | 0.6800 | 0.6947 | 0.7571 | 0.7930 | 0.7835 |

对应 AUPRC 也在 `window_sweep_current.tsv` 中；例如 NTv2-500M 为 0.9239/0.9674/0.9846/0.9893/0.9873（从 512 到 8192），GENERanno 为 0.9415/0.9483/0.9793/0.9869/0.9845。训练命令中的 HyenaDNA identity 是 `hyenadna-large-1m-seqlen-hf`，没有把未记录的参数量补猜为某个整数。

**可以写入论文的结论：** 在完全相同的 H0 quick-screen 协议中，较长窗口总体改善 TE detection，GENERanno 和 NTv2-500M 明显高于 HyenaDNA；NTv2-500M/4096 在这个 screen 最高。**不能写入论文的结论：** 这张表证明某个基座在所有物种或下游任务都最好；训练步数、label/source、指标和分割与其他矩阵并不相同。

## B. 当前 NTv2/NTv3 尺寸 × 窗口迁移矩阵

来源：

- `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`（495 rows）；
- `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/current_status.json`；
- `docs/06_results_log.md` 中 `PIPE-TEFM-FINAL-20260623` 和 `PIPE-TEFM-FINAL-EBAR/STRICTSEG/PLANTQC-20260629` 条目。

矩阵含 165 个 NTv2 行和 330 个 NTv3 行；每个 checkpoint/window 同时评估 `animal_fine`（*C. elegans*, chicken, fruit fly, mouse, western clawed frog, zebrafish）和 `plant_fine`（Brachypodium, maize, rice, sorghum, thale cress），每物种 1200 windows。下表是跨物种 TE-F1 的物种均值，仍是单 seed、一染色体迁移 screen；不是 in-domain 主结果。

| checkpoint | 参数量/变体 | animal mean @ best window | best window | plant mean @ best window | best window |
|---|---:|---:|---:|---:|---:|
| NTv2-50M | 50M | 0.5653 | 2048 | 0.2686 | 2048 |
| NTv2-100M | 100M | 0.6206 | 8192 | 0.2530 | 512 |
| **NTv2-250M** | **250M** | **0.6482** | **4096** | 0.2278 | 2048 |
| NTv3-8M-pre | 8M | 0.5229 | 2048 | 0.3083 | 2048 |
| **NTv3-100M-pre** | **100M** | 0.5822 | **2048** | **0.3980** | **2048** |
| NTv3-650M-pre | 650M | 0.4595 | 4096 | 0.2459 | 512 |
| NTv3-8M-pre-8kb | 8M, 8kb pretraining variant | 0.5293 | 1024 | 0.2998 | 1024 |
| NTv3-100M-pre-8kb | 100M, 8kb variant | 0.4595 | 2048 | 0.1955 | 2048 |
| NTv3-650M-pre-8kb | 650M, 8kb variant | 0.5530 | 4096 | 0.2613 | 2048 |

关键细节：

- local human H0 training screen 的最佳 NTv2 row 是 `ntv2_250m_H0_w4096_seed42`，TE-F1 0.93494、macro-F1 0.93627、AUPRC 0.98395；最佳 NTv3 H0 row 是 `ntv3_650m_pre_H0_w4096_seed42`，TE-F1 0.91962、macro-F1 0.92137、AUPRC 0.97752。
- 后续 chromosome-repeat error-bar screen 仍保留 panel-specific 方向：NTv2-250M/4096 animal mean 0.6431（18 chromosome/species rows），NTv3-100M-pre/2048 plant mean 0.3833（15 rows）。
- 8kb NTv3 并没有一致优于非 8kb 变体；因此不能把“更长预训练上下文”写成已验证的普遍改进。
- `species_probe.tsv` 的 22 行是“每个目标物种都单独微调”的 supervised probes，例如 human 0.9285、mouse 0.9525、zebrafish 0.9036、chicken 0.9278、*C. elegans* 0.7667、red flour beetle 0.1494。它不是共享模型的泛化实验，不能用来证明一个 checkpoint 在 22 个物种上都可用。

## C. Remote v2 主比较：hg38-only 三 seed backbone

来源（baobab）：

`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/reconstruct/HUMAN_FINETUNE_AND_COMPARISON_RESULTS_SUMMARY.md`，原始证据列出的文件为：

- `docs/HG38_BACKBONE_FINETUNE_EVAL_METRICS.md`；
- `results/tables/hg38_backbone_finetune_eval_metrics.csv`；
- `results/tables/hg38_backbone_finetune_eval_seed_metrics.csv`；
- `results/tables/fig2_backbone_comparison.csv`。

协议：hg38 train chr1/3/5/7/9，validation chr11/13/15，test chr17/19/20/21/22；bp-level binary TE detection；3 seeds。这个表比 local quick screen 更适合作为正文的 backbone comparison，但仍要在稿件中保留其 hg38-only 范围。

| Run | 基座 | window | TE precision | TE recall | TE-F1 | macro-F1 |
|---|---|---:|---:|---:|---:|---:|
| N3 | GENERanno 0.5B | 1024 | 0.9414 ± 0.0004 | 0.9476 ± 0.0008 | **0.9445 ± 0.0005** | 0.9481 ± 0.0004 |
| N2 | NTv2 250M | 2048 | 0.9324 ± 0.0016 | 0.9466 ± 0.0013 | **0.9394 ± 0.0007** | 0.9433 ± 0.0006 |
| N1 | DNABERT2 117M | 2048 | 0.9062 ± 0.0006 | 0.9511 ± 0.0005 | **0.9281 ± 0.0002** | 0.9333 ± 0.0002 |
| HyenaDNA medium/large | HyenaDNA | — | — | — | — | — |

Remote window note: the same summary reports NTv2 @4096 = 0.9386 and @8192 = 0.9422; neither established stable superiority over the 2048 main row. HyenaDNA appears in the plans/configuration but no completed hg38 fine-tune result was found in the current repository; do not fill that cell from the local quick screen.

### 归档 v1 的 assembly/mixture × window 结果

`archive/v1_modules/module7_deliverables/tables/comprehensive_cross_species_comparison.tsv` 和 `cross_species_2048bp_comparison.tsv` 还保留了早期 2048 bp/8192 bp 的 human-assembly 与 multi-species 行。它们不是同一套 v2 N1/N2/N3 backbone protocol，且远程总结明确将其标成 historical archive，因此只用于追溯“早期也观察到近缘物种较强、multi 对较远物种可能有帮助”的方向：

| assembly/训练行 | 2048 F1（代表物种） |
|---|---:|
| hg38 model → hg38 | 0.9609 |
| hg19 model → hg19 | 0.9513 |
| hg38 model → hs1 | 0.9420 |
| hg38 model → panTro6 | 0.9390 |
| multi → rheMac10 | 0.9287 |
| hg19 model → mm39 | 0.8941 |
| hg19 model → bosTau9 | 0.9240 |
| multi → galGal6 | 0.9415 |
| multi → xenTro10 | 0.9011 |

归档整体均值（混合分母，不能与 current one-chromosome matrix 合并）：hg38_2048 0.6964、hg19_2048 0.6849、multi_2048 0.7298、multi_8192 0.7446；排除旧记录标注的 outliers 后分别为 0.8354、0.8216、0.8799、0.8933。若使用，只能放历史/补充表并注明旧 protocol；正文应优先使用 remote v2 3-seed 表和 local final matrix。

## D. hg38-only 跨物种迁移与 mixture rescue

Remote `v2_eval/C2_generanno_n3_xspec/*_N3_gpu_results.json`、`results/tables/te_compare_precision_recall.csv`、`docs/paper_draft/results.md` R.5.4 记录了 GENERanno N3 hg38-only binary 的 single-seed 外部迁移：

| 物种/assembly | clade | N3 TE-F1 | precision | recall |
|---|---|---:|---:|---:|
| bosTau9 chr25 | vertebrate | **0.906** | 0.892 | 0.921 |
| galGal6 chr24 | vertebrate | 0.798 | 0.780 | 0.817 |
| danRer11 chr25 | vertebrate | 0.740 | 0.849 | 0.656 |
| xenTro10 chr1 | vertebrate | 0.695 | 0.799 | 0.615 |
| ci3 chr1 | tunicate/OOD | 0.353 | 0.739 | 0.232 |
| arabidopsis chr1 | plant | 0.195 | 0.856 | 0.110 |
| glycine_max chr1 | plant | 0.504 | 0.846 | 0.359 |
| physcomitrium chr1 | plant | 0.587 | 0.950 | 0.425 |

这组数值支持“human-only binary 模型在一部分 vertebrate 上具有可用的 sequence transfer，远离 vertebrate 后主要表现为 recall 下降”。它不支持按遗传距离直接给置信度，也不支持无脊椎动物或植物的普适结论。

同一 remote summary 的 mixture control：

| 训练混合 | hg38 test TE-F1 | 状态 |
|---|---:|---|
| NTv2 hg38-only N2 | 0.9394 ± 0.0007 | 3-seed 主结果 |
| NTv2 animal-only N28 | 0.9369 ± 0.0008 | 3-seed 主结果 |
| NTv2 three-kingdom N13 | 0.9218 ± 0.0004 | 3-seed 主结果 |
| GENERanno three-kingdom N3K | hg38 约 0.942 | preliminary single seed |

N3K 同 backbone 的 external rescue 在 arabidopsis（0.195 → 0.846）和 Physcomitrium（0.587 → 0.752）最明显，但 N3K 是 preliminary single-seed，不能替代 N3 的 3-seed主结果。它更适合作为“训练物种组成决定 cross-kingdom recall”的机制性补充。

## E. Human-only RepeatMasker library 对照：已完成但属于 archive/v1

初始本地盘点没有在当前 local reports 找到这项结果；进一步在 baobab 的 `TE_final` 中定位到：

- 脚本：`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/archive/v1_modules/module2_repeatmasker/scripts/run_repeatmasker_human_lib.py`；
- 主结果：`/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/archive/v1_modules/module2_repeatmasker/results/full/repeatmasker_comparison.tsv`；
- 单物种 `metrics.json`：同一 `results/full/{panTro6,rheMac10,mm39,rn7,canFam6,bosTau9,galGal6}/` 目录；
- 运行设计：目标物种 chr1，`RepeatMasker -species human -pa 16 -xsmall -gff`，对照各物种 `rmsk_te.bed.gz`。

真实结果：

| 目标物种 | F1 | precision | recall | 解释边界 |
|---|---:|---:|---:|---|
| panTro6 | 0.9612 | 0.9779 | 0.9451 | 近缘灵长类，human library 仍覆盖较好 |
| rheMac10 | 0.9629 | 0.9766 | 0.9495 | 近缘灵长类，覆盖较好 |
| mm39 | 0.5117 | 0.9599 | 0.3489 | precision 高，recall 明显缺失 |
| rn7 | 0.5296 | 0.9564 | 0.3662 | precision 高，recall 明显缺失 |
| canFam6 | 0.8000 | 0.9598 | 0.6858 | 中等覆盖 |
| bosTau9 | 0.5733 | 0.9464 | 0.4111 | 目标库不足以覆盖全量 |
| galGal6 | 0.7552 | 0.9344 | 0.6337 | 跨哺乳类至鸟类下降 |

这一组对照很适合支撑：library composition 会把传统方案的 recall/F1 变成一个 database-transfer 问题，不能把“传统工具分数低”单独解释为算法差。它不能直接证明模型的 FP 都是真 TE，也不能与 current W11/W12 RM-free/RM-self 的 9-species结果混成同一 ground-truth regime。archive/v1 使用的 assembly、RepeatMasker/Dfam 版本和 current v2/v6 不应默认相同；若用于正文，建议放补充材料和方法注释，正文只解释其作用。

W11/W12 是另一条已完成的 library-coupling control，不是 human-only library：

- `docs/W11_RM_FREE_TRADITIONAL_EVAL.md`：在 7 个可靠 panel-B 物种上，RM-dependent tools 在 RM-free structural reference 下通常下降 0.13–0.67 F1；
- `docs/W12_RM_SELF_BASELINE.md`：Dfam 3.3-only RepeatMasker 的 self-vs-UCSC F1 在 dm6 0.9647、danRer11 0.8943、galGal6 0.8436，但 Arabidopsis 0.0274、Glycine 0.0550、Xenopus 0.1784，显示没有一个跨 kingdom 的 RM-self floor。

安全写法是“library/reference provenance materially changes F1 and the apparent traditional baseline”，而不是“library 解释了所有 DL 漏检或所有低分”。

## F. 六物种共享模型与 MoE/adapter 状态

来源：

- `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904.md` 及其 `seed42/`、`seed17/`、`conf/` 目录；
- `docs/experiments/D-ADAPTER-MOE-PILOT-20260914.md`；
- `reports/D-ADAPTER-MOE-PILOT-20260914/`。

共享 D 的 seed42 DEV bp-F1（按 D arm 的 `dev_metrics.json`）：human **0.940310**、mouse **0.941998**、chicken **0.831720**、zebrafish **0.927836**、pig **0.893138**、*C. elegans* **0.797565**；seed17 D DEV：human **0.941099**、mouse **0.940104**、chicken **0.836385**、zebrafish **0.929588**、pig **0.894193**、*C. elegans* **0.807216**。这些数值是 D 的六物种 DEV，不是 L arm，也不是 worm SCREEN。D 增加 *C. elegans* 训练覆盖后，seed42/17 worm SCREEN 分别从 **0.789994/0.794581**（L）提高到 **0.802736/0.807310**（D），但对应 segment/boundary 并未同步改善。报告明确将其定义为 internal-coordinate coverage pilot，未释放为 external species 或 universal model claim。

MoE pilot 的实际对象是 frozen D hidden features 上的预测 head：dense residual adapter、two-expert soft-gated residual adapter、constant-average experts；它没有 route 500M backbone，也没有在六个物种之间证明稳定的 sparse expert activation。Sea EVAL 中 historical D bp-F1 0.5589，dense/soft-gate/constant heads 约 0.7344/0.7333/0.7376，但 segment-F1@IoU0.8 只有 0.1193/0.1109/0.1059，仍是 bounded, single-seed exploratory result。论文中只能写“adapter/MoE-like head pilot was explored”; 不能把它写成已经完成的多物种 MoE 方案。

## G. 已有的积极结果与应避免的过度解读

以下结果是本项目中真实完成、可作为候选补充材料的阳性/有用诊断：

| 结果 | 数值/方向 | 可用定位 | 论文边界 |
|---|---|---|---|
| 主四类 superfamily head | TE-detect F1 0.9405；main4 class macro-F1 0.8927；all6 macro-F1 0.7519 | `reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries/superfamily.tsv` | `Other` F1=0，正文只适合 main4；不能宣称全类群 universal class annotation |
| interval smoothing | HMM penalty2 4096 bp F1 0.9385，segment-F1@0.5 0.7339，boundary-F1@100 0.6181 | 同上 `segment_threshold.tsv` | 解决部分 fragmentation；不等于 Gap/linking 已解决 |
| embedding diagnostic | C1 basic+contrastive ARI 0.9208、holdout macro-F1 0.8784、pair AUC 0.9856；A1 pretrained GENERanno ARI 0.8000；binary fine-tuned ARI 0.2822 | `reports/tefm_repair/.../embedding_diagnostic.tsv` | C1 sequence-feature baseline 强于 fine-tuned embedding；不能说 FM embedding 已胜出 |
| Dfam consensus embedding | A1 contrastive ARI 0.2242 vs A0 0.0796；C1 ARI 0.7083/NMI 0.7135 | `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv` | 可写“对比学习改善表示”，不能写成 foundation embedding superiority |
| plant supervised rescue | plant held-out mean: cross-supervised 0.8568、plant-supervised 0.8431；animal invert-boost 0.6254 | `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/binary_eval.tsv` | 是 target-panel supervised correction，不是 zero-shot plant generalization |
| source-aware decay | distance-only R² 0.0396；加入 label/source/composition/GC/clade/stress/kingdom/insect R² 0.7407 | `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/decay_formula_extended/formula_fits_extended.json` | 说明遗传距离单变量不足；复杂公式是 source-aware screen，不能当已验证置信度校准 |
| bounded k-mer selector | leave-species-out RMSE 0.2666 vs baseline 0.3042 | `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630` | exploratory selector；没有 full retraining 或 deployment validation |

两项必须留在限制或补充中的结果：

- hg19→hg38/T2T “future annotation recovery”是负向 protocol check（observed 0.1348/0.1613，corrected conditional null 0.4090），不能包装为模型发现未来 TE；
- current TE_compare best-by-species 是 DL 2/8、traditional 6/8，且传统结果受 RM-derived GT/library coupling 影响。不能只展示 DL 赢的两个物种。

## H. 给论文结构的直接建议

如果文章仍以“通用 TE map/跨物种模型”为主线，正文可放：

1. remote hg38-only N1/N2/N3 三 seed backbone table；
2. local NTv2/NTv3 model-size × window matrix 的 animal/plant 分面；
3. N3 hg38-only vertebrate transfer + N3K plant rescue（明确 single-seed preliminary）；
4. superfamily main4 与 embedding 的解释性结果；
5. W11/W12 和 human-library archive/v1 作为 library provenance/公平比较补充。

正文不应声称“six-species shared model 已完成 universal generalization”或“MoE 已经解决 species stability”。这些应写成当前证据边界或后续版本。

此前 Pro review 中的 **P3 → Tiberius gene-annotation utility** 是保留的历史 proposal，不是本轮最终收束决定。当前主线按作者最新决定回到 **multispecies TE map + downstream utility**：D/NTv2/NTv3 的跨物种 TE map、binary/superfamily 分层、library provenance 和 Tiberius 等下游效用需要在同一多物种证据架构中组织；不能把 D 的 transfer/superfamily/MoE 数字转嫁给 P3，也不应为了凑成一篇更大的论文选择性隐藏 P3 的真实损失门。P3 proposal 与其旧正文/补充分工仍保留在 `docs/manuscript/20260917/pro-review-and-decision.md`，供后续取舍时追溯。

## I. 证据状态标签

| 标签 | 本文件中的实例 |
|---|---|
| **claim-grade within protocol** | remote hg38 N1/N2/N3 3-seed binary table；local matrix 的完整工程产物但 transfer 仍是 screen |
| **screen / exploratory** | local SUPP quick sweep；NTv2/NTv3 one-chromosome matrix；N3K single-seed rescue；k-mer selector；MoE head pilot |
| **historical archive** | archive/v1 human-library RepeatMasker comparison；24-species v1 table |
| **negative or limitation** | cross-kingdom multiclass collapse；hg19 time-travel；Unknown/FN/library attribution unresolved；Gap/fragment linking未解决 |

任何正文数值都应同时报告任务、split、label/reference source、window、seed 和 denominator；不能从这张 inventory 表中跨标签来源或跨 protocol 选一个最高 F1 作为“最佳模型”。
