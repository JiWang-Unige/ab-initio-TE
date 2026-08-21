# Pipeline Blueprint / 流程化研究推进图

> 由 `/pipeline-blueprint` 维护。用于“已有既定思路、raw data 或分析流程，需要把 pipeline 建稳并产出可投稿证据”的阶段。它不是 blind iteration，而是 DAG 化推进。

## 0. Pipeline identity
- Pipeline name:
- Purpose:
- Input raw data:
- Final outputs:
- Claim supported:

## 1. DAG overview

```text
raw_data → QC → preprocessing → feature/model/statistical analysis → validation → figures/tables
```

| Stage | Purpose | Input | Output | Script/software | Parameters/config | QC gate | Status |
|---|---|---|---|---|---|---|---|
| S1 |  |  |  |  |  |  | TODO |

## 2. IO contracts

| Artifact | Path pattern | Producer | Consumer | Required metadata/hash | Retention policy |
|---|---|---|---|---|---|
| raw data | `data/raw/...` |  |  |  | keep |
| processed data | `data/processed/...` |  |  |  | keep |
| external software output | `software_outputs/<tool>/<run_id>/...` |  |  |  | keep summary + logs |

## 3. External software calls

| Tool | Version/container/env | Command template | Output dir | Log file | Failure handling |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 4. Validation and sensitivity plan

| Check | Why | Method | Pass criterion | Status |
|---|---|---|---|---|
|  |  |  |  | TODO |

## 5. Pipeline execution ledger

| Run ID | Date | Stage(s) | Input hash | Config | Output | Status | Notes |
|---|---|---|---|---|---|---|---|

## 6. Handoff
- Next stage to execute:
- Blocking input needed:
- User decision needed:

## 7. TE-FM phase-gate execution protocol

本节承接 `docs/11 §7.1`。这里写具体执行协议；`docs/11` 只保留导航和准入/阻断条件。所有 gate 的输出都必须带输入路径、软件版本、物种/染色体清单、日期和 hash/manifest；否则只能作为探索笔记，不能支撑 claim。

### 7.0 LABEL-SOURCE

目的：冻结 claim-bearing 标签来源层级，避免在模型表现不佳后临时切换真值，也避免 de novo pipeline bias 混入主 benchmark。

Label layers:
- `Label-A` = self-run RepeatMasker + Dfam, fixed RepeatMasker/Dfam/RMBlast versions, species parameters, run ID, genome/library hashes. It is the primary reference for main training, main evaluation, and cross-species generalization matrices.
- `Label-B` = RepeatModeler2 / EDTA / HiTE + Dfam + RepeatMasker. It is used for sensitivity, U-shield, traditional de novo baseline, and candidate validation.
- `Label-C` = structure/copy/consensus/domain/cross-assembly/manual evidence. It is used for UHC evidence cards and case studies, never as genome-wide primary labels.

Required outputs:
- `label_source_manifest.tsv`: species, genome hash, Label-A run ID, RepeatMasker/Dfam versions, Label-B tool versions if present, Label-C evidence sources.
- `label_source_policy.json`: explicit mapping from Label-A/B/C intervals to `P`, `RN`, `U`, `hardN`, `audit_only`, `candidate`.
- `u_shield_intervals.bed.gz`: Label-B TE-like intervals not present in Label-A and not rejected as hardN/blacklist; these are masked from loss and primary FP calculations.

Gate rule:
- Label-A is the only default claim-bearing primary label source.
- `Label-B-only` TE-like intervals must not be promoted to `P` by default; they enter `U` / candidate evidence unless a new user-approved route decision explicitly changes label source status.
- If a model performs unexpectedly poorly on a species, chromosome, or superfamily, run a bounded de novo+Dfam diagnostic for that unit. The diagnostic may trigger claim narrowing, audit-only demotion, or U-shield expansion; it does not automatically replace Label-A.
- A species or superfamily with severe Label-A/B conflict is label-source-limited until `LABEL-CONCORDANCE`, `U-QUALITY`, and any available Label-C evidence explain the conflict.

### 7.1 CHROM-LADDER

目的：锁定 species/chromosome ladder，防止随机 split、旁系同源片段或近重复片段泄漏。

Required outputs:
- `species_manifest.tsv`: species、kingdom/clade、genome build、annotation source、Dfam/library coverage、chosen primary chromosome、stability-check chromosome。
- `chromosome_ladder.tsv`: 每条候选染色体长度、TE bp、TE fraction、assembly status、是否 sex chromosome/microchromosome、选择/排除理由。
- `split_leakage_report.tsv`: train/validation/test 之间的同源/近重复检查结果。
- `sampling_manifest.tsv`: 每个 species/chromosome 的 TE-internal、TE-boundary、hardN、RN、random、U-calibration pool 数量和 bp 覆盖。

Gate rule:
- sex chromosome、microchromosome、极端 TE-poor/TE-rich contig 默认不作为第一版主点。
- 若 train/test 之间存在无法解释的同源片段或高相似重复片段，进入模型训练前必须 BLOCKED。
- baseline reproduction 和 screen 训练都必须引用同一个 species/chromosome role manifest；不得先跑 baseline 再补 split 解释。

Embedded `SPECIES-PANEL` contract:

| Layer | Species / TaxID candidates | Default role | Notes |
|---|---|---|---|
| Human anchor | Homo sapiens / 9606; hs1/T2T-CHM13 plus hg38/hg19 where needed | H0 source; A-series held-out; B production anchor; assembly-version audit | Human is not allowed in A0/A1/A2 no-human supervised TE-label training. If backbone pretraining used human DNA, claim wording must be "no human supervised TE labels during fine-tuning", not "never saw human DNA". |
| A2 no-human animal train | Mus musculus / 10090; Danio rerio / 7955; Gallus gallus / 9031; Xenopus tropicalis / 8364; Drosophila melanogaster / 7227; Caenorhabditis elegans / 6239 | main no-human animal training anchor set | This is the P0 no-human animal set. Rat/dog are not A2 core; they are QC/reserve unless a later production extension explicitly promotes them. |
| Animal held-out / stress | Sus scrofa / 9823; Bos taurus / 9913; Equus caballus / 9796; Apis mellifera / 7460; Tribolium castaneum / 7070; optional Monodelphis, Anolis, Xenopus laevis | held-out/stress/reserve pool | Used to test transfer curve, distance, clade, label quality, and TE landscape. Do not mix a held-out species into train and still use it as transfer evidence. |
| PlantTE core | Oryza sativa / 4530; Zea mays / 4577; Sorghum bicolor; Brachypodium distachyon; Setaria italica or interim Setaria viridis; Arabidopsis thaliana / 3702; optional Solanum lycopersicum / 4081 | separate PlantTE model family | PlantTE is a core C-track model, not just sentinel. Missing sorghum/Brachypodium/Setaria italica must be annotated before first full C run, or clearly waived/proxied. |
| Plant held-out / reserve | Oryza longistaminata; Zea diploperennis; Arabidopsis lyrata; Vitis vinifera / 29760; Solanum lycopersicum / Glycine max depending on train choice | plant stress / reserve / held-out | Used for PlantTE generalization and crop/dicot stress; grape is reserve/held-out, not current core train. |
| Fungi future | Saccharomyces cerevisiae, Schizosaccharomyces pombe, Neurospora crassa, Aspergillus nidulans, Magnaporthe oryzae, Fusarium graminearum, Cryptococcus neoformans | E-stage fungi, after QC | Fungi must not block H0/A2/B/C. Add only after fungi Label-A/B/QC passes; use confidence-aware loss and kingdom-specific heads. |

Experiment-oriented annotation views live under `software_outputs/repeatmasker_dfam/experiment_views/`. Each view has `species_manifest.tsv` and `annotations/` symlinks to available Label-A outputs.

Embedded `SAMPLING-BATCH` contract:

- Sampling must be stratified by segment type, not random genome windows only.
- Required strata: TE-internal, TE-boundary, hard negative, RN, random background, U-calibration/ignored.
- Initial screen defaults may start near `30% TE-internal / 25% TE-boundary / 20% hard negative / 15% random/RN / 10% U-calibration`, but these are v0 defaults, not immutable route constants.
- Every run must report the realized sampling mix by species, chromosome, superfamily, and stratum.
- Hard negatives include near-TE flanks, GC/k-mer/repeat-density matched non-TE, and non-TE repeat classes such as simple/satellite/tandem/low-complexity; they must stay distinguishable from RN.
- Species balance is two-stage: sample species/clade first, then segment within species. Large genomes or high-TE species must not dominate by raw bp alone.
- Superfamily balance should use capped inverse-frequency or capped inverse-sqrt weights; rare/single-species classes may be oversampled for learning but remain excluded from headline macro-F1 until `SF-TARGET` freezes masks.
- Validation split must be chromosome-level where possible; otherwise large-block holdout is required. Adjacent random segment split is not acceptable for claim-bearing runs.

### 7.2 TE-LEN-VIZ

目的：在选择窗口、TEPost 参数和 superfamily set 前，先知道每个目标物种与 superfamily 的 TE 长度分布。

Required outputs:
- per-species TE length histogram，建议 log-scale。
- per-superfamily TE length histogram。
- cumulative TE bp covered by length bins: `<100`, `100-500`, `500-1000`, `1000-2048`, `2048-4096`, `4096-8192`, `>8192` bp。
- short-fragment fraction、long-tail fraction、RepeatMasker fragment count per Mb。
- Label-A vs Label-B length overlay。

Use:
- 指导 `WIN-MATRIX`：若 `2048bp` 对某 Core superfamily 的 bp 覆盖明显不足，必须增加一个长窗口评估。
- 指导 `TEPOST-PARAMS`：`min_len`、`merge_gap`、smoothing 不能盲用默认值。
- 指导 `SF-TARGET`：极端碎片化或长度分布异常的类先标风险，不直接进入主评分。

### 7.3 LABEL-CONCORDANCE

目的：确认不同标签来源或不同 label level 的边界、长度和 superfamily assignment 是否足够一致。

Required outputs:
- Label-A vs Label-B interval IoU distribution。
- boundary shift distribution: start/end absolute error。
- per-superfamily concordance table。
- conflict examples for manual inspection。
- poor-performance diagnostic report when triggered: failed species/superfamily, Label-A coverage, Label-B added bp, overlap with hardN/blacklist, and whether the failure is likely model weakness or label-source limitation。

Gate rule:
- 若 Label-A/B concordance 太低，不得冻结最终 `SF-TARGET` 或 `TEPOST-PARAMS`。
- 低 concordance 的 superfamily 只能进入 low-confidence 或 audit-only 层，不能进入主 macro-F1。
- concordance 低默认触发 scope narrowing / U-shield / audit-only，而不是把 de novo 自动升为主标签。

### 7.4 U-QUALITY

目的：确认 `U`、`RN`、`hardN` 的语义边界，避免把未注释区域当真负类。

Required outputs:
- U 中被 RepeatMasker/Dfam/structural evidence 标为 TE-like 的 bp fraction。
- Label-B-only TE-like bp fraction and corresponding `u_shield_intervals.bed.gz` coverage。
- RN/hardN 与 TE/repeat evidence 的重叠率。
- 清洗建议：keep / mask / ignore / reassign。
- UHC evidence-card schema: `candidate_id`, species, chromosome, interval, model score, predicted superfamily, length, blacklist overlap, annotation overlap, independent support, evidence tier, claim wording。

Gate rule:
- `U` 不能当 negative。
- Label-B-only TE-like intervals are protected as U/candidate evidence unless explicitly rejected as hardN/blacklist; they do not provide positive loss by default。
- U 高分只能作为 candidate evidence，不得直接叫 novel TE。
- 若 RN 或 hardN 污染明显，需重做 label harmonization，不能调模型掩盖问题。
- 没有 evidence tier 的 UHC 只能作为 internal diagnostic；不得写成 novel/underannotated TE claim。
- `Tier 0` = model-only hit, candidate only; `Tier 1` = repeated non-blacklisted cluster; `Tier 2` = consensus/copy support and boundary consistency; `Tier 3` = structural/domain/de novo support; `Tier 4` = cross-assembly or related-species support. Claim wording must not exceed tier strength.

### 7.5 SF-TARGET

目的：冻结 provisional superfamily target set，避免小众类别、单物种类别和 label-space 漂移扭曲主评分。

Step 1 data report:
- global superfamily TE bp%。
- per-kingdom superfamily TE bp%。
- species coverage matrix: superfamily x species。
- interval count and bp count by species/superfamily。
- rare/single-species candidates list。

Step 2 decision:
- 默认采用 per-kingdom 主规则 + global sensitivity check。
- 低频、单物种、样本量不足或 concordance 低的 superfamily 默认进入 `Other_TE`、`SPECIES_SPECIFIC_RARE` 或 audit-only。
- exact thresholds 在 Step 1 数据后由用户确认；不得在 EDA 前把阈值写死。

Required dossier:
- `refs/dossiers/sf_target_set.md`: 最终类别、合并理由、可重审条件、对 evaluator mask 的影响。

### 7.6 WIN-MATRIX

目的：在公平比较和模型 native context 之间建立有界折中。

Core:
- 所有可支持 backbone 跑 `2048bp` shared anchor。
- 不支持 `2048bp` 的模型可用最接近且不超过 2048 的 native window，标记为 `2048eq:<actual_bp>`，不得与真 2048 结果混称完全公平。
- 每个 backbone 最多增加 1-2 个 native/recommended windows。
- `512/1024` 可作为短窗口/fragmentation trap 对照。

Enhanced:
- 只对最终 anchor backbone 做完整 sweep: `512/1024/2048/4096/8192`。
- `4096/8192` 对支持长上下文的模型可作为 upper-bound，不作为默认公平比较。

Required dossier:
- `refs/dossiers/window_matrix.md`: backbone、tokenizer/context limit、实际 bp window、是否 Core/Enhanced、比较规则。

Embedded `CONTEXT-TRAP` sentinel:

- Purpose: test whether apparent context gains are TE-internal signal or flanking/species-background shortcut.
- Minimal diagnostics before any strong context/generalization claim:
  - flank masking: compare full segment, center-only, and flank-only inputs on the same labeled intervals.
  - flank swap: replace flanks with GC/repeat-density matched flanks from another species or chromosome.
  - matched negatives: evaluate GC/k-mer/repeat-density matched RN/hardN, not only easy random negatives.
  - embedding species leakage: on known TE intervals, report whether embeddings cluster by family/superfamily more than by species.
- These diagnostics do not block the first screen training loop, but they are required before claiming that a longer context or a specific context length reflects biological TE generalization.
- If long-context models improve in-domain F1 but show high flank dependence or species leakage, the result must be labeled context-trap risk and cannot be used as the default fair comparison anchor without qualification.

### 7.7 SPECIES-WEIGHT

目的：避免多物种训练被大基因组、高 TE bp 或高完备注释物种支配。

默认状态：Enhanced，P7 前重审。若 species panel 严重不均衡，至少登记风险并定义采样权重候选。

### 7.8 TEPOST-PARAMS

目的：把 raw probability map 转成可用 BED/GFF3 segment 时，参数来自 `TE-LEN-VIZ` 和 validation，不靠默认值。

Required outputs:
- min_len、merge_gap、smoothing、threshold 的候选表。
- 每个参数关联的长度分布依据。
- 若不做参数消融，必须登记为 claim 风险。

## 8. PIPE-TEFM-SUPP-20260617 · UCSC strict-TE supplement screen

Purpose: 执行用户要求的补充实验：本地预训练模型在 UCSC strict RepeatMasker TE 注释上的快速微调、窗口大小对比、跨物种泛化、mouse-only 与 A2 no-human mixture 泛化，以及后续碎片化/边缘效应分析。

### 8.1 DAG

```text
ready-by-design manifest + UCSC comparator_strict
  -> prepare_ucsc_windows.py
  -> te_token_task.py train
  -> one-chrom species eval
  -> collect_results.py
  -> tri-review + note-add
  -> mouse-only / A2 mixture dependent runs
  -> decay formula + fragmentation/postprocess analysis
```

| Stage | Purpose | Input | Output | Script/software | QC gate | Status |
|---|---|---|---|---|---|---|
| S1 | 构建 human H0 quick windows | `H0_human_only_upper_bound/SPLIT_MANIFEST.tsv`, UCSC `comparator_strict` | `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w*_quick` | `prepare_ucsc_windows.py human` | non-random chromosome split; strict BED exists | DONE |
| S2 | 模型加载 smoke | 六个本地 checkpoint | `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/smoke_te_benchmark/*.json` | `te_token_task.py smoke` | model/tokenizer loads in `te_benchmark` | DONE_WITH_BLOCKERS |
| S3 | window/model quick fine-tune | H0 quick windows, seed=42 | `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_*` | Slurm arrays `9060945`, `9060949` | code-review gate PASS_WITH_WARNINGS | RUNNING/PENDING |
| S4 | B/C fine_tune species one-chrom transfer | best compatible checkpoints from S3 | per-species JSON metrics | `prepare_ucsc_windows.py eval`, `te_token_task.py eval` | skip missing comparator_strict; one chromosome recorded | TODO_AFTER_S3 |
| S5 | mouse-only transfer | best model/window from S3/S4, A1 mouse | human hg38, cattle, horse, pig one-chrom metrics | same scripts | same number of train chromosomes as H0 quick protocol | TODO_AFTER_S4 |
| S6 | A2 mixed no-human training | A2 fine_tune with fixed proportions | A2 eval_only one-chrom metrics | `prepare_ucsc_windows.py mixed`, `te_token_task.py train/eval` | train/val use different chromosomes when available | TODO_AFTER_S4 |
| S7 | decay + fragmentation analysis | S3-S6 metrics/predictions | summary report and route decision | `collect_results.py` plus follow-up analysis scripts | stop if poor fit; no endless formula search | TODO |

### 8.2 Current compatibility verdict

| Model | Local path | Status | Reason |
|---|---|---|---|
| DNABERT-2-117M | `.backup/pretrained_models/DNABERT-2-117M` | runnable | loads in `te_benchmark` with wrapper_auto |
| NTv3_650M_pre | `.backup/pretrained_models/NTv3_650M_pre` | BLOCKED | local snapshot lacks `InstaDeepAI/ntv3_base_model` remote-code files required by `auto_map` |
| nucleotide-transformer-v2-500m-multi-species | `.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species` | runnable | loads as `EsmForTokenClassification` in `te_benchmark` |
| GENERanno-eukaryote-0.5b-base | `.backup/pretrained_models/GENERanno-eukaryote-0.5b-base` | runnable | loads as `GenerannoForTokenClassification` in `te_benchmark` |
| hyenadna-large-1m-seqlen-hf | `.backup/pretrained_models/hyenadna-large-1m-seqlen-hf` | runnable | loads with wrapper_auto; wrapper drops unsupported `attention_mask` |
| evo2_7b_base | `.backup/pretrained_models/evo2_7b_base` | BLOCKED | no HF-recognized `model_type`/tokenizer adapter in local snapshot |

### 8.3 Execution ledger

| Run ID | Date | Stage(s) | Config | Output | Status | Notes |
|---|---|---|---|---|---|---|
| PIPE-TEFM-SUPP-20260617-S1 | 2026-06-17 | S1 | `configs/pipelines/PIPE-TEFM-SUPP-20260617.yaml` | `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w*_quick` | DONE | 512/1024/2048/4096/8192 each has 3000 train/val/test windows. |
| 9060945 | 2026-06-17 | S3 heavy A100 subset | `configs/pipelines/PIPE-TEFM-SUPP-20260617.train_jobs.tsv` | `software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_*` | PENDING | Kept tasks 5-15: DNABERT-8192, NT-v2 all windows, GENERAnno all windows. |
| 9060949 | 2026-06-17 | S3 3090 subset | `configs/pipelines/PIPE-TEFM-SUPP-20260617.train_jobs_3090.tsv` | same run root | RUNNING | DNABERT 512-4096 and HyenaDNA 512-8192. |
