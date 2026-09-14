# Embedding 结果汇总

日期：2026-05-20


## 范围

本文档汇总当前仓库中可追踪的 embedding-clustering artifact。目前能定位到的唯一数值聚类表是历史 M5 表：`archive/v1_modules/module7_deliverables/tables/clustering_comparison.tsv`。我没有找到当前 v5/v6 的 embedding arrays、UMAP 坐标，或覆盖 best-generalization 与 weak-generalization 模型的 matched-species 系统 embedding benchmark。


生成产物：

- `results/tables/embedding_clustering_summary.csv`

- `results/figures/embedding_clustering_metrics.png` / `.pdf`

- `results/figures/embedding_clustering_heatmap.png` / `.pdf`


## 当前数值表

| setting   | description                                                  |   embedding_dim |   class_nmi |   class_ari |   species_nmi |   species_ari | claim_status                                            |
|:----------|:-------------------------------------------------------------|----------------:|------------:|------------:|--------------:|--------------:|:--------------------------------------------------------|
| A0        | Raw 6-mer frequencies                                        |            4096 |       0.101 |       0.032 |         0.148 |         0.043 | historical_control                                      |
| A1        | Pretrained GENERanno, no contrastive fine-tune               |            1280 |       0.056 |       0.021 |         0.021 |         0.007 | historical_control                                      |
| A2        | Multi-species fine-tuned GENERanno, no contrastive objective |            1280 |       0.071 |       0.019 |         0.064 |         0.023 | historical_control                                      |
| B0        | 6-mer frequencies + contrastive projection                   |             128 |       0.971 |       0.928 |         0.121 |         0.025 | likely_label_leakage_or_trivial_kmer_separation_control |
| B1        | Pretrained GENERanno + contrastive objective                 |             128 |       0.101 |       0.045 |         0.031 |         0.012 | historical_exploratory                                  |
| B2        | Fine-tuned GENERanno + contrastive objective                 |             128 |       0.077 |       0.025 |         0.062 |         0.022 | historical_exploratory                                  |



## 解读

历史结果**不支持**一个强论文主张，即当前最佳 TE annotation 模型已经学到了可靠的无监督 TE-family embedding。class-level 聚类分数最高的是 B0（`class_nmi=0.971`, `class_ari=0.928`），但 B0 是 6-mer frequency + contrastive projection，而不是 foundation-model embedding 本身的结果。真正 foundation-model 相关的 A1/A2/B1/B2 都较弱：class NMI 只有 0.056 到 0.101，class ARI 只有 0.019 到 0.045。species clustering 也较弱（`species_nmi <= 0.148`, `species_ari <= 0.043`）。

因此，汇报时可以把这部分作为 **negative/diagnostic result**：binary TE fine-tuning 并不会自动产生清晰的 family-level embedding geometry。论文主张层面，在没有新系统 embedding audit 前，建议只作为 future work 或 limitation。


## 若要形成论文级 embedding claim，仍缺少

- 固定模型集合：包括当前最佳泛化模型（`N3K`/`N13`/`N28`）与 weak-transfer comparators。

- 跨模型 matched species windows 与 matched TE classes。

- 实际 embedding arrays，并保存 UMAP/PCA 坐标、seed、layer metadata。

- 同一 clustering protocol 下的 ARI/NMI/purity/silhouette。

- 负对照：shuffled labels、non-TE windows、以及没有 contrastive leakage 的 k-mer-only baseline。

- embedding geometry 与 downstream generalization F1 的显式关联比较。

