# Validation Matrix / 下游任务与可靠性论证矩阵

> 由 `/publication-plan`、`/generalization`、`/sota-randomized` 共同维护。用于回答“模型/流程为什么可靠，哪些下游任务必须做”。

## 1. Main result
| Candidate | Dataset/split | Metric | Value | Comparator | Comparable? | Evidence path |
|---|---|---|---:|---|---|---|

## 2. Downstream / external validation tasks
| Task ID | Task | Purpose for paper claim | Dataset | Metric | Baselines | Required seeds | Status | Output path |
|---|---|---|---|---|---|---:|---|---|
| D1 | Label-A/B concordance + U-shield | Defend Label-A primary reference while preventing Dfam blind spots from becoming false negatives | 6-8 representative species; start with core anchors | interval IoU, boundary shift, Label-B-only bp, hardN overlap, U-shield bp | Label-A self-run RM+Dfam; Label-B de novo+Dfam | 1 deterministic label run | TODO | reports/label_concordance_* |
| D2 | Poor-performance de novo diagnostic | Diagnose species/superfamily where FM performs abnormally poorly under Label-A | Triggered species/chromosome/superfamily | Label-B added support, Label-C support, claim-limited verdict | Label-A result; de novo+Dfam diagnostic | 1 deterministic label run | TRIGGERED_ONLY | reports/diagnostics/de_novo_* |

## 3. Robustness / OOD / sensitivity
| Check ID | Perturbation / OOD split | Expected behavior | Pass criterion | Status | Result |
|---|---|---|---|---|---|
| CT-1 | flank masking: full vs center-only vs flank-only | TE prediction should rely primarily on TE-containing center rather than flanks alone | Long-context or selected anchor model must not derive most positive signal from flank-only inputs; exact threshold fixed after screen calibration | TODO |  |
| CT-2 | flank swap with GC/repeat-density matched cross-species or cross-chromosome flanks | Stable TE-center predictions under matched flank changes | Large prediction delta triggers context-trap warning and limits context-generalization claim | TODO |  |
| CT-3 | matched negative panel: GC/k-mer/repeat-density matched RN/hardN | Precision/RN-FPR should remain acceptable on hard backgrounds | A model that only wins on easy random negatives cannot support C1/C4 claim | TODO |  |
| CT-4 | embedding species leakage on known TE intervals | Embeddings should cluster more by family/superfamily than by species for family/superfamily claims | High `NMI(cluster,species)` relative to family/superfamily is a warning or blocker for representation claims | TODO |  |

## 4. Ablations
| Ablation ID | Removed/changed component | Hypothesis | Metric | Expected delta | Status |
|---|---|---|---|---:|---|
| A1 | PU/ignore-mask/nnPU vs binary CE | Asymmetric weak supervision might help transfer if controlled | transfer TE-F1, segment F1, unknown pred-TE rate | Must approach binary and control U over-call to re-enter | ABANDONED_MAINLINE / FUTURE_REPAIR_GATED |
| A2 | Label-A primary vs Label-B audit/U-shield | Unified RM+Dfam is reproducible primary reference; de novo improves audit/shield but should not become default truth | concordance, U-shield bp, ranking stability | Label-B should expose blind spots without changing main truth by default | TODO |

## 5. Randomized SOTA small-sample retraining
> `init` 列必填：random=随机初始化重训（同预算公平参考，建 screen_anchor）/ pretrained=载入官方权重（仅作上界对照，**不混入随机初始化的 mean**）。split_scheme/metric_impl 必须与我们的 Track A 一致（防泄漏可比）。
| Model | init | sample_fraction | seeds | split_scheme | Metric mean±std | Our comparable run | Verdict | Link |
|---|---|---:|---|---|---|---|---|---|

## 6. Statistical tests
| Comparison | Test | Paired? | n/seeds | p-value/CI | Status |
|---|---|---|---:|---|---|

## 7. P8 transfer / generalization matrix

本节承接 `docs/11 §7.1 P8-MATRIX`。P8 的目的不是堆满全排列，而是把“模型泛化能力”和“数据库/reference bias”拆开，避免审稿人质疑 FM 只是学到了人类或 Dfam/RepeatMasker 的偏差。

### 7.0 Experiment version map

| Version | Role in validation | Train / fine-tune set | Evaluation set | Layer |
|---|---|---|---|---|
| H0 | Human-only upper-bound | human | human held-out chromosomes; hs1/hg38/hg19 assembly audit | Core |
| A0 | Mouse-only no-human ablation | mouse | human T2T; pig/cow/horse | Small ablation |
| A1 | Vertebrate no-human ablation | mouse, zebrafish, chicken, Xenopus tropicalis | human T2T; optional vertebrate stress | P1 |
| A2 | Main no-human animal model | mouse, zebrafish, chicken, Xenopus tropicalis, fly, worm | human T2T; pig/cow/horse; Apis/Tribolium | Core/P0 |
| B | Animal production model | human + A2 six species | human + animal held-outs | Core/P0 |
| C | PlantTE model | rice, maize, sorghum, Brachypodium, Setaria, Arabidopsis +/- tomato | wild rice, teosinte, Arabidopsis lyrata, tomato/soybean/grape | Core for plant track |
| D-shared | Animal + plant universal baseline | A2 animals + C plants | animal + plant held-outs | Enhanced/P1 |
| D-kingdom-head | Animal + plant kingdom-aware model | A2 animals + C plants | animal + plant held-outs | Enhanced/P1 recommended |
| E | Animal + plant + fungi | A2 animals + C plants + fungi core | kingdom held-outs | P2 after fungi QC |

Current output manifests for these versions are indexed in `software_outputs/repeatmasker_dfam/experiment_views/*/species_manifest.tsv`.

### 7.1 Row definitions

| Row | Name | Definition | Purpose | Layer |
|---|---|---|---|---|
| R0 | Best/current FM | 当前主候选或最终 FM，按 production protocol 训练 | 主性能比较 | Core |
| R1 | Human-only FM | 只用 human Label-A 训练/微调 FM，再推断非人类目标物种 | 测量人类知识对非人类的迁移价值 | Core |
| R2 | No-human FM | 训练集中排除 human 与 non-human primate，再测试 hs1/T2T human anchor 和非人类目标 | zero-human 泛化与 de novo 学习能力 | Core |
| R3 | Dfam-human-only RepeatMasker | RepeatMasker 只使用 human Dfam/library，例如 `-species Homo sapiens`，不训练 FM | database-bias audit；传统人类库迁移下限 | Core |
| R4 | Target/clade Dfam RepeatMasker | RepeatMasker 使用目标物种或目标 clade library | 传统 reference-aware baseline | Core |
| R5 | RepeatModeler2 / de novo baseline | 目标基因组上运行 de novo repeat discovery baseline | de novo traditional comparator | Core |
| R6 | Kingdom-specific FM | 每个 kingdom/clade 独立训练或从 P7 主模型继承 | 检查 kingdom-specific 是否比 universal 更现实 | Enhanced unless main model uses it |
| R7 | Universal FM | 一个模型覆盖所有物种/kingdom | 若 early evidence 支持，再作为 universal claim | Enhanced |
| R8 | Dfam species-specific RM | 目标物种专用 Dfam/library | 仅当库可用且不破坏公平性 | Parked |

### 7.2 Column definitions

| Column | Test set | Purpose | Layer |
|---|---|---|---|
| C0 | Human hs1/T2T anchor | 高完备注释 anchor；zero-human 主测试点 | Core |
| C1 | Non-human animal holdout | human-only FM 与非人类动物泛化 | Core |
| C2 | Same-kingdom holdout | 同 kingdom 内留出 species/clade | Core |
| C3 | Per-target species panel | 每个主要目标物种独立结果 | Core |
| C4 | Animal -> plant/fungi | 极限 OOD；检验跨界序列语法迁移 | Enhanced/sentinel |
| C5 | Plant -> animal/fungi | 极限 OOD；检验跨界序列语法迁移 | Enhanced/sentinel |
| C6 | Kingdom pooled holdout | 聚合 kingdom 层结果，辅助 figure/table | Enhanced |

### 7.3 Required comparisons

| Comparison | Question answered | Minimum layer |
|---|---|---|
| Human-only FM vs Dfam-human-only RM | FM 是否超越“人类库同源迁移”，还是只是复制人类 reference bias | Core |
| No-human FM vs target/clade Dfam RM | 排除人类后，FM 是否仍有 de novo/generalization value | Core |
| Best/current FM vs RepeatModeler2/de novo | 主工具是否超过传统 de novo baseline | Core |
| Best/current FM vs target/clade Dfam RM | FM 是否超过 reference-aware traditional baseline | Core |
| Kingdom-specific FM vs Universal FM | 大一统模型是否值得作为主 claim | Enhanced |
| Same-kingdom vs cross-kingdom decay | 泛化失败来自进化距离、TE landscape 还是注释完备度 | Enhanced |

### 7.4 Metrics per cell

每个可比较 cell 至少报告：
- bp-level TE-F1、precision、recall、AUPRC。
- segment IoU F1 and boundary F1 if segment output exists。
- per-superfamily macro-F1 under `docs/19` masks。
- kingdom-masked macro-F1 when per-kingdom label space differs。
- RN-FPR、hardN-FPR、U high-score candidate rate。
- species/chromosome/block bootstrap confidence interval。

### 7.5 Execution policy

- P8 矩阵结构现在固定；实际执行按 Core / Enhanced / Parked 分层。
- Cross-kingdom 不删除，但默认不作为第一批 Core 全量任务。
- 缺少 R1 vs R3 时，不得 claim “human knowledge generalizes beyond database bias”。
- 缺少 R2 vs R4 时，不得 claim “no-human/de novo FM 超越 target reference-aware baseline”。

## 8. UHC evidence-card guardrail

本节承接 `docs/11 C5` 和 `docs/13 §7.4 U-QUALITY`。UHC 是 unannotated high-confidence model hit；它可以支持 candidate/evidence/audit claim，但不能单凭模型分数写成 novel TE。

| Tier | Required evidence | Allowed wording | Status |
|---|---|---|---|
| 0 | model-only high score in U, no independent support | model candidate / diagnostic only | TODO |
| 1 | repeated non-blacklisted intervals; stable under RC/threshold perturbation; not simple/satellite/tandem/low-complexity | repeat-like candidate | TODO |
| 2 | copy/consensus support and boundary consistency; reasonable class-specific length | credible underannotated repeat candidate | TODO |
| 3 | structural/domain/de novo tool support such as TIR/TSD/LTR/polyA/ORF/domain or RepeatModeler2/EDTA/HiTE overlap | credible TE family candidate | TODO |
| 4 | cross-assembly, related-species, pangenome, or future-annotation recovery support | high-confidence underannotated/novel TE candidate, subject to manual review | TODO |

Required evidence card fields:
- `candidate_id`, species, assembly, chromosome, start, end, strand, length.
- model score, predicted class/superfamily, threshold/config, RC stability.
- overlap with Label-A/Label-B, RN/hardN/blacklist overlap, U status.
- copy number, consensus length, boundary consistency, structural/domain/de novo support.
- cross-assembly/cross-species support, final tier, allowed claim wording, reviewer notes.

Policy:
- C5 claims are disabled until this schema is populated for any reported candidate.
- `FAMILY-EMBEDDING` remains Enhanced/Parked unless the manuscript scope explicitly moves novel-family discovery into title/abstract-level claims.

## 9. PIPE-TEFM-SUPP-20260617 validation tasks

| Task ID | Task | Purpose for paper claim | Dataset | Metric | Required seeds | Status | Output path |
|---|---|---|---|---|---:|---|---|
| SUPP-1 | 2048bp model transfer screen | Pick compatible pretrained backbone and quantify immediate transfer decay | H0 human quick fine-tune; B animal + C plant fine_tune one chromosome/species | token-proxy TE-F1/AUPRC first, bp/segment follow-up required | 1 | RUNNING/PENDING | `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_*_w2048_seed42` |
| SUPP-2 | Window sweep 512/1024/2048/4096/8192 | Test context-length effect and support fragmentation/context-trap analysis | H0 human quick fine-tune | TE-F1/AUPRC by window; edge-vs-center diagnostic after predictions | 1 | RUNNING/PENDING | same run root |
| SUPP-3 | Mouse-only supervised transfer | Compare mouse -> human vs mouse -> cattle/horse/pig under similar vertebrate distance | A1 mouse fine_tune; hg38/cattle/horse/pig eval_only one chromosome | TE-F1/AUPRC plus decay ratios | 1 | TODO_AFTER_SUPP-1/2 | TBD |
| SUPP-4 | A2 no-human animal mixture | Test whether mixed non-human animals improve human/animal transfer | A2 fine_tune with fixed proportions; A2 eval_only one chromosome/species | TE-F1/AUPRC; if poor then tri-review only | 1 | TODO_AFTER_SUPP-1/2 | TBD |
| SUPP-5 | Generalization decay formula | Summarize performance vs training source/window/model and rough phylogenetic/kingdom grouping | SUPP-1/3/4 metrics | simple regression/correlation; abandon if unstable | 1 | TODO_AFTER_SUPP-4 | TBD |
| SUPP-6 | Fragmentation and edge effect | Decide whether non-overlap prediction hurts window edges and whether smoothing/overlap helps | SUPP-2 predictions | edge-center F1 delta; segment continuity | 1 | TODO_AFTER_SUPP-2 | TBD |

Current caveat: SUPP-1/2 first-pass metrics from `te_token_task.py` are token-label proxy metrics for non-single-nucleotide tokenizers. They may rank quick screens, but final claim-bearing rows in §7.4 still require bp-level and segment-level evaluators.
