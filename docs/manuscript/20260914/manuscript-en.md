# English manuscript — complete first draft

来源：ChatGPT 6 Pro，2026-09-14；送审 Git c6781414794c120e41f67d9b43859a4d28453065。[原对话](https://chatgpt.com/c/6aa7c372-9118-83eb-a6f1-828ffb3ecab9)。本文件从完整回复按章节提取；原文见 pro-full-response.md。

完整叙事初稿；不是可直接投稿版本。保留原稿的 [TO COMPLETE] 和 E/R 证据标识。投稿前须将送审过程描述改为实验方法，按所保留主张补齐实际证据，并完成作者、图表和发布信息。

## Title

**From transposable-element material detection to actionable annotation: a controlled evaluation of genomic language models**

**Authors and affiliations:** [TO COMPLETE]

## Abstract

Genomic language models can identify sequence patterns associated with transposable elements (TEs), but agreement with a base-pair annotation mask does not establish recovery of biological insertions or safe downstream masking. We evaluated these distinctions using a shared multi-species material detector and separate, controlled human annotation experiments. On an internal development panel comprising six training species and 24,541,946 callable bases, the shared model achieved a species-macro base-pair F1 of 0.8888, compared with 0.4459 for comparator-run matching and 0.2044 for IoU-qualified joint-boundary matching. Expanding the independent worm training-coordinate pool improved development performance in two seeds under a matched update budget. In contrast, enabling cross-half attention did not satisfy the frozen context-improvement criterion; worm development F1 remained 0.7942. In a separate gap experiment, adding nucleotide-transformer logits and seam features reduced negative-fraction mean squared error by 8.5905% and increased action average precision from 0.3036 to 0.3872. Nevertheless, none of 60,497 tied-score thresholds satisfied even optimistic necessary conditions for low-risk whole-gap filling. Truth-assisted gap-mask additions also failed to recover additional correct coding-sequence chains in a completed nine-core gene-prediction experiment. These results support an experimentally useful TE-material detector and identify specific coverage and information effects, while separating them from unestablished claims of universal generalization, biological insertion reconstruction, and downstream benefit. Independent-panel qualification, matched contemporary tool comparisons, and release-level reproducibility remain necessary before broader deployment claims. [E04–E11, E15]

## Introduction

Transposable-element annotation involves several related but non-equivalent questions. A base may contain recognizable TE-associated sequence even when the boundaries, ancestry, and integrity of the original insertion cannot be reconstructed. Conversely, two annotated fragments can belong to the same historical insertion while intervening sequence is not wholly attributable to that element. RepeatMasker explicitly accommodates fragmented and nested matches, while RepeatCraft and Earl Grey provide procedures for organizing or defragmenting repeat annotations. These procedures motivate distinguishing material detection from insertion reconstruction rather than treating every discontinuity as an error to fill. [R2–R4] ([repeatmasker.org][1])

Genomic foundation models offer a different source of evidence: representations learned from DNA sequence. The Nucleotide Transformer study establishes a general representation-learning framework for genomic prediction, and the GENERanno project provides an eukaryotic checkpoint used in a separate series of experiments here. Neither a foundation-model designation nor sequence-only inference removes dependence on training labels, pretraining exposure, or task-specific evaluation. [R1, R5] ([Nature][2])

We therefore distinguish three targets. **L1** is a binary mask of TE-associated material relative to a specified computational comparator. **L2** is the topology of contiguous comparator runs, including interval agreement and joint boundary agreement. **L3** is biological insertion identity, which requires evidence beyond adjacency or mask continuity. We additionally distinguish a predictive score from an action: filling a gap changes an annotation and can mask non-TE sequence even when the score contains useful information.

This study asks which of these claims are supported by the available experiments. A shared-model series tests internal multi-species material detection, coordinate coverage, and information exchange between adjacent sequence halves. A separate human series tests boundary supervision, cross-species structural transfer, gap-risk prediction, and gene-prediction utility. Historical backbone, typing, representation, and routing experiments provide secondary evidence but are not assembled into a hypothetical universal model. Our central contribution is an evidence-resolved assessment of the transition from material prediction to actionable annotation, including informative negative results and explicit limits to their interpretation.

## Results

### 1. A shared model detects TE-associated material within a six-species panel, but does not establish universal annotation

The shared D model was evaluated on 500 development tiles from each of six species represented in training. Across 3,000 tiles, the evaluation contained 24,541,946 callable bases, including 7,452,597 comparator-positive bases. Species-macro base-pair F1 was 0.888761. The corresponding macro interval F1 at intersection-over-union (IoU) 0.8 was 0.445884, and IoU-qualified joint-boundary F1 at 5 bp was 0.204361. These metrics answer different questions and should not be interpreted as interchangeable estimates of accuracy. [E04]

| Species      | Callable bp | Positive bp | Base-pair F1 | Run F1, IoU ≥0.8 | Joint-boundary F1, 5 bp |
| ------------ | ----------: | ----------: | -----------: | ---------------: | ----------------------: |
| *C. elegans* |   4,076,828 |     389,795 |     0.797565 |         0.304933 |                0.136771 |
| Chicken      |   4,094,383 |     157,905 |     0.831720 |         0.378378 |                0.150579 |
| Human        |   4,092,984 |   1,921,941 |     0.940310 |         0.544222 |                0.288808 |
| Mouse        |   4,090,361 |   1,598,850 |     0.941998 |         0.566082 |                0.297714 |
| Pig          |   4,095,493 |   1,140,557 |     0.893138 |         0.500507 |                0.215211 |
| Zebrafish    |   4,091,897 |   2,243,549 |     0.927836 |         0.381181 |                0.137085 |

**Table 1.** Internal DEV results for D, seed 42. Counts and F1 were independently checked from the archived confusion counts. Structural matching is performed on tile-level comparator runs, not independently verified biological insertions. All six species contribute to training. Source: E04, `per_species` and `summary`.

Only worm fell below 0.8 in this particular table. This observation does not establish that worm is the only difficult species in general: historical panels include different species, plants, labels, and model recipes. Nor does a near-threshold result change the frozen acceptance decision. The wider L1 programme remained incomplete, and no executed mixture-of-experts (MoE) result was found in the submitted tree. [E02, E06, E15, E20]

### 2. Coordinate coverage provides a replicated benefit, whereas additional cross-half attention does not pass its matched test

The upstream coverage comparison changed the worm training-coordinate pool from 1,500 to 3,000 tiles while retaining the shared-model objective, sampling balance, and 4,000-update budget. Other species retained 1,500 tiles each. Worm SCREEN comprised 512 separated tiles with 4,163,080 callable bases; the reused worm DEV panel comprised 500 tiles with 4,076,828 callable bases. SCREEN contained new coordinates on training chromosomes and was not an unseen-species test. [E05, E21]

| Seed |    SCREEN F1, L → D |       DEV F1, L → D |
| ---- | ------------------: | ------------------: |
| 42   | 0.789994 → 0.802736 | 0.783315 → 0.797565 |
| 17   | 0.794581 → 0.807310 | 0.788782 → 0.807216 |

**Table 2.** Matched coverage comparison. Average precision also improved in both seeds on both panels. These paired directions support a coverage effect at the tested budget; they do not establish stable satisfaction of all release criteria. The existing closure explicitly records that absolute usability remained unstable. [E05]

An archived label-oracle diagnostic obtained worm DEV F1 of 0.994498 under the implemented token-constant output constraint. This is not a learned-model result, but it shows that the six-base output grid alone cannot account for an observed ceiling near 0.8. It does not exclude limitations of input tokenization, optimization, or available context. [E05]

PAIR8 subsequently tested a narrower hypothesis: whether the two original 4,096-bp halves benefit from exchanging information. PAIR8 and BLOCK4 used the same packed encodings, output mapping, supervision, and update budget; only attention connectivity differed. PAIR8 increased worm SCREEN F1 from 0.809500 to 0.812998 but decreased worm DEV F1 from 0.795764 to 0.794154. The DEV difference was −0.001610, and the SCREEN difference of 0.003497 was smaller than the registered 0.005 minimum. PAIR8 macro DEV F1 was 0.892187, but this aggregate did not rescue the failed worm criteria. Seed 17 was not released. [E06]

A separate score diagnostic constrained precision and recall to at least 0.75. For seed-42 worm DEV, the best scalar-threshold oracle F1 was 0.799613, only 0.002048 above the deployed result. Thus, threshold adjustment alone could not meet the 0.8 target on that panel. Replacing the H0 encoder with the native pretrained encoder while using the same fresh classification head also failed its matched test: P0R DEV F1 was 0.791441 versus 0.803254 for H0R. These findings further limit threshold-only and initialization-only explanations; they do not prove that all calibration or pretraining interventions are ineffective. [E24]

These experiments identify coordinate diversity as useful under the tested conditions while providing no accepted benefit for this specific cross-half attention intervention. They do not rule out all longer-context architectures and do not justify automatically adding experts or model capacity.

### 3. Boundary alignment does not explain the human structural improvement, and transfer remains endpoint-dependent

A separate GENERanno-derived human P3 series evaluated whether aligned edge supervision improved structural recovery. The matched P3-R2 experiment compared an aligned boundary target with a jointly permuted boundary target that retained target mass and distribution within each window. Evaluation used the first 1,200 windows of length 8,192 bp on human chromosome 17, containing 14,253 comparator runs. [E07]

Aligned supervision achieved interval F1 of 0.407518, whereas the matched permutation control achieved 0.447522. Joint-boundary F1 at 5 bp was 0.215538 versus 0.250507, respectively. Base-pair F1 was similar, at 0.931778 and 0.932072. Thus, improvements relative to the earlier P3 recipe cannot be attributed specifically to correct boundary alignment in this experiment. This is a mechanism test, not evidence that arbitrary boundary targets are universally preferable. [E07]

Frozen P3-R1 transfer further separated material agreement from topology. On the mouse chromosome-1 diagnostic, base-pair F1 was 0.902004 but interval F1 was 0.096592. On the exact FlyBase r6.68 positive-only panel, P3-R1 interval recall at IoU 0.8 was 0.078037, with 51.557723 predicted fragments overlapping each truth run on average. This later P3 diagnostic was completed and must not be omitted merely because it was absent from the earlier three-cell benchmark. The FlyBase truth set comprised 4,972 flattened positive runs; it did not certify negative genomic sequence and therefore cannot support genome-wide precision or F1. [E07, E16]

The original same-assembly benchmark included HiTE, historical Base-CE, and DAPT-CE. Their positive-base recalls were 0.448982, 0.003408, and 0.018514; interval recalls were 0.216412, 0, and 0.000402. These are results for those particular frozen models and workflows, not a ranking of current shared D against traditional annotation. HiTE is a full TE-detection and annotation approach with its own discovery and boundary procedures, so any contemporary comparison must record the workflow and library resources rather than compare only model labels. [E16; R6] ([Nature][3])

### 4. Additional gap information improves risk prediction without enabling a low-risk filling policy

The HN-O experiment tested whether nucleotide-transformer logits and seam features add information about gaps left by the frozen human prediction. It used 90,081 training candidates and 60,574 DEV candidates, of which 60,569 were fully known under the computational comparator. Known DEV gaps contained 3,449,084 bases. The head predicted the negative-base fraction within a gap; lower predicted risk favoured filling. HN-O was compared with an otherwise matched H0-O control, with three training seeds. [E08]

HN-O reduced length-weighted negative-fraction MSE from 0.06148917 to 0.05620693, a relative reduction of 8.5905%. Action average precision increased from 0.30359897 to 0.38721622, an absolute increase of 0.08361725. The direction of the information improvement was consistent across the three seeds. Because nucleotide-transformer logits and seam features were introduced together, the effect cannot be assigned to the transformer alone. [E08]

Fraction MSE and literal base-level Brier error must also be distinguished. For gap length \(L_g\), observed negative fraction \(r_g\), and a constant gap prediction \(s_g\),

$$
\mathrm{Brier}
=
\frac{\sum_g L_g(s_g-r_g)^2}{\sum_g L_g}
+
\frac{\sum_g L_g r_g(1-r_g)}{\sum_g L_g}.
$$

The second term is irreducible under a constant within-gap score. Accordingly, literal Brier error decreased from 0.10562713 to 0.10034488, or 5.0008%, not 8.5905%. Neither improvement establishes safe masking. [E08]

A subsequent fixed-score feasibility analysis enumerated 60,497 distinct tied-score thresholds, plus abstention. None met the optimistic necessary conditions for whole-gap action. These required at least 1,000 selected candidates, recovery of at least 10% of known positive gap bases and 5% of the designated long-gap positive bases, and strict negative/unknown masking budgets. The optimistic genomic span was 47,185,920 bp, allowing at most 471.8592 known negative bases under the 10-bp-per-Mb budget. [E09]

The largest risk-admissible action selected 822 gaps, recovering 4,449 of 461,733 known positive bases while adding 441 known negative bases. The first threshold satisfying the utility requirements selected 8,414 gaps and recovered 46,251 positive bases, but added 24,747 negative bases—approximately 52.45 times the optimistic negative budget. Since even these necessary conditions failed, no deployment calibration or gene-safety evaluation could rescue this fixed ordering within the tested monotone-threshold policy family. This is a bounded no-go result, not proof that all gap models or all partial-gap actions are impossible. [E09]

### 5. Completed gene-utility results do not establish benefit, and a separate base-mask experiment remains incomplete

The completed C experiment evaluated nine human chromosome-13 cores under three masks, yielding 27 valid cells. The reference contained 243 distinct complete coding-sequence (CDS) chains represented by 330 source rows. M0 was the existing P3 mask—not an unmasked genome. MW added comparator-known all-positive whole gaps; MP added comparator-positive bases within candidate gaps. Both additions were truth-assisted diagnostic interventions rather than deployable predictions. [E10]

M0 and MW each yielded 54 true positives, 37 false positives, and 189 false negatives, corresponding to micro chain F1 of 0.323353. MP yielded 54 true positives, 36 false positives, and 189 false negatives, with F1 of 0.324324. Its increase of 0.000971 reflected a net change in false positives, not recovery of a new correct chain. Neither addition gained or lost a correct reference chain, so the registered gain requirement failed. The result is scientifically negative for these interventions on these cores. [E10]

A distinct P3 base-mask experiment was designed to compare unmasked U, P3-masked P, and reference-repeat-masked R across 20 larger cores, for 60 planned cells and a different gene-locus endpoint. The archived 14 September status records smoke job 12652888 as FAILED, exit 1:0, after 21 min 58 s, with `KeyError: BASE_MASK_OBSERVATION`. There are no complete 60-cell utility results. This engineering failure neither establishes nor refutes the benefit of P3 masking relative to unmasked input. **[NOT YET ESTABLISHED: P3 base-mask benefit for gene annotation.]** No completed independent transcription-regulation utility experiment was found. [E11, E20]

### 6. Auxiliary studies constrain broader annotation claims

Historical backbone/window screens contain substantial exploratory evidence, including 495 rows spanning nine checkpoint/configuration variants, five windows, and eleven species. Each row used 1,200 windows, not an independent training seed. Unequal sequence exposure, coordinate coverage, and historical label/evaluator differences prevent a clean causal ranking of architectures or context lengths. These results are retained as recipe-development evidence in the Supplementary Results. [E02, E03]

Direct classification used BG, SINE, LINE, LTR, DNA, and Unknown. These are coarse output types, not a comprehensive biological superfamily taxonomy. On 4,915,200 labelled positions, the pretrained initialization achieved TE-detection F1 of 0.904104 and four-type macro F1 of 0.864415, but Unknown recall was 0.388597. Binary-H0 initialization retained four-type macro F1 of 0.863267 while Unknown recall fell to 0.042627. The field named `main4_conditional_macro_f1` averages globally computed class F1 values for the four selected types: background/rejection confusions still contribute false positives and false negatives, although BG and Unknown do not receive their own terms in that average. A broadly usable superfamily annotator is therefore not established. [E12, E23]

The Dfam-consensus representation panel contained 1,800 fragments and ten clusters. ARI was 0.079557 for raw GLM embeddings, 0.224190 after family-supervised contrastive learning, 0.142266 for basic sequence features, and 0.708307 for contrastively transformed basic features. These combined train-plus-holdout ARIs must not be mixed with results from other panels. Holdout macro F1 on 450 fragments was 0.238251, 0.413748, 0.338528, and 0.421935, respectively. The contrastive objective used family labels, preprocessing included the pooled feature set, and the split did not establish unseen-family or homology-isolated generalization. Thus, neither wholly unsupervised discovery nor superiority over basic features is supported. [E13, E23]

Finally, genomic-feature performance regression achieved in-sample R² of 0.820308 but leave-species-out RMSE of 0.304043 over 156 species–anchor records. A separate conservative router's selected feature set included the best observed anchor in 19/22 leave-species-out cases, but only 13/22 leave-clade-out cases. Its reported mean shortlist regret of 0.007083 used the best observed F1 within the shortlist and is an oracle shortlist statistic, not a validated label-free local-probe outcome. These experiments do not establish deployable F1 prediction, base-level calibration, or out-of-distribution risk control. [E14]

## Discussion

The strongest supported conclusion is that TE-associated material prediction, structural agreement, and safe annotation action require separate evidence. This does not make base-level detection uninformative. It specifies its meaning: agreement with a computationally defined material mask on the evaluated domain. The shared model's material scores and the replicated coordinate-coverage effect are positive results within that scope. However, calling every predicted run a TE insertion would overstate the available biological evidence.

The experiments also clarify why apparently promising interventions did not yield the intended downstream advance. Matched boundary controls did not support the proposed alignment mechanism. Additional gap features improved prediction of composition but could not separate enough useful whole-gap actions from harmful ones at the frozen risk budgets. Even truth-assisted additions failed to produce new correct CDS chains in the completed C experiment. These are different failure modes; none should be used to substitute for the unfinished unmasked-versus-P3 gene-utility comparison.

Nor should traditional annotation be described as uniformly dependent on an externally supplied reference library. RepeatMasker is a homology-based annotation component, whereas workflows such as Earl Grey and HiTE can include de novo discovery and construction of sequence resources from the target genome. Library availability, construction cost, taxonomy, and fragment handling must therefore be specified at the workflow level. Sequence-only GLM inference avoids a target-time library search in the implemented entry point, but does not imply training independence from RepeatMasker/Dfam labels or freedom from pretraining exposure. [R2, R4, R6] ([repeatmasker.org][1])

Several limitations restrict the manuscript. The principal shared-model panel contains training species and reused development coordinates. Computational labels can be incomplete or taxonomically uneven. The prepared independent candidate panel has not supplied completed independent model results, and its label coverage and exposure require qualification. Historical results were produced under multiple implementation versions, and fixes to coordinate handling, Unknown shielding, or tied-score evaluation do not automatically update archived metrics. Several main results are available as compact summaries but not as the underlying predictions needed to reproduce every frontier or interval. No new statistical significance is inferred from the number of bases, tiles, or workflow cells. [E03, E15]

Within these limits, the work argues against indiscriminate expansion of model complexity. The current context test does not justify MoE, and error diversity between backbones is not sufficient evidence for a useful ensemble. Future work should first establish qualified independent evaluation, matched contemporary workflow comparisons, and claim-specific utility. New biological insertion or historical annotation-recovery studies would require their own truth and exposure designs; they are not results of the present study. **[NOT YET ESTABLISHED: unseen-species generalization, biological insertion recovery, historical prediction followed by later confirmation, and independent regulatory utility.]** [E15, E18, E20]

## Methods

### Evidence provenance and experimental separation

The reviewed ZIP contains 2,882 tracked files and identifies the submitted commit in its archive comment. We inspected source code, protocols, archived tables, and compact JSON results and independently recalculated available confusion-derived metrics and aggregate differences. The snapshot excludes raw genomes, checkpoints, full run outputs, and caches. No new training, inference, HPC query, or raw sealed-panel evaluation was performed. A recorded remote job state is cited as an archived check, not a newly observed scheduler state. [E01, E11]

The shared NTv2 series, human GENERanno/P3 series, historical Base/DAPT benchmark, and auxiliary classification/representation studies retain their own input, split, and evaluation contracts. Cross-table comparisons are descriptive unless the experiments explicitly match the relevant factors. **[TO COMPLETE: release manifests linking every main result to immutable input, checkpoint, calibration, prediction, and evaluator hashes.]**

### Targets, labels, and coordinates

L1 denotes TE-associated base-pair material relative to the stated comparator, rather than experimentally verified TE origin at every base. In the current shared series, labels retain positive/unknown/negative priority. `1` supplies positive mass; `0` and hard-negative `H` supply negative mass; `?` is excluded from supervised mass. The implemented priority may retain positive labels at ambiguous sequence positions, so callable status must be taken from the label contract rather than inferred solely from the DNA alphabet. [E21]

The internal species use hs1, mm39, galGal6, danRer11, ce11, and susScr11 assemblies. The separate human gap/utility series uses its own hg38 chromosome contracts. Prepared external candidates include platypus, sea urchin, and *C. briggsae*, but successful label export is not an independent model evaluation. Actual RepeatMasker/FamDB/Dfam versions and curation coverage are recorded in the panel metadata. **[TO COMPLETE: qualified negative-label scope, pretraining exposure statement, and copy/family/homology isolation appropriate to each intended claim.]** [E15]

### Shared material model and matched interventions

The upstream trainer calls the shared NTv2 task without changing its base-model loader; the implementation points to the NTv2-500M H0 checkpoint. This is distinct from historical NTv2-250M comparisons and the separate NT-logit gap input. Each 8,192-bp tile is represented by two independently encoded 4,096-bp halves. Six-mer tokens retain positive and negative base counts; remaining tail bases have their own tokens. Predictions are projected back without changing genomic coordinates. [E21]

For half \(h\), the weighted binary cross-entropy is

$$
\ell_h=
\frac{
\sum_j\left\{3P_j[-\log p_j]+N_j[-\log(1-p_j)]\right\}
}{
3\sum_jP_j+\sum_jN_j
},
$$

where \(P_j\) and \(N_j\) are callable positive and negative masses for token \(j\). The two half losses are averaged, followed by equal averaging across the six species sampled at each step. Full-parameter training uses AdamW, learning rate \(2\times10^{-5}\), weight decay 0.01, gradient-norm clipping at 1, 4,000 updates, and 400 warmup updates. The final-step checkpoint is used. There are 24,000 tile presentations per arm, not 24,000 independent tiles. [E05, E06, E21]

L and D differ only in the worm coordinate pool under the matched upstream protocol. PAIR8 and BLOCK4 preserve each half's token phase, tail bases, and supervision while changing cross-half attention visibility. Frozen D is a practical reference; PAIR8 versus BLOCK4 is the direct matched information-path contrast. Registered release gates, including the failed seed-42 gate, were not redefined for this manuscript. [E05, E06]

### Calibration and material/topology evaluation

The shared evaluation fits a non-negative-slope Platt transform on the designated six-species CAL data, with species-balanced fitting, and selects one global threshold under the frozen worst-species-first rule. It does not fit a worm-specific deployment threshold. Reusing this procedure does not establish calibration on an unseen species. Base-pair precision, recall, and F1 are computed from pooled callable counts within each species; the macro result averages species values. Average precision uses grouped tied scores in the current implementation. [E21]

Comparator-run matching uses greedy interval matching at IoU at least 0.8 within evaluation tiles. The archived boundary metric additionally requires both boundaries of an already matched pair to lie within the specified tolerance. It is therefore IoU-qualified joint-boundary F1, not an independently scored endpoint metric. Unknown-coordinate holes are retained rather than removed by concatenating valid positions. Legacy experiments require explicit evaluator-version certification before being pooled with newer results. [E03, E21]

### Human boundary and external benchmark experiments

The P3-R2 comparison holds the GENERanno backbone, U-Net trunk, body targets, seed 42, and 800-update budget fixed while replacing aligned boundary targets with a matched within-window permutation. The aligned target is triangular within ±16 bp of each comparator-run edge. The control jointly permutes left/right target pairs over boundary-valid positions, preserving their distributions and mass while breaking coordinate alignment. Training uses the first 3,000 8,192-bp windows on human chromosome 1, validation uses 800 windows on chromosome 11, and evaluation uses 1,200 windows on chromosome 17.

Mouse transfer is an absolute diagnostic, without an assumed matched mouse baseline. FlyBase r6.68 annotations are flattened into non-overlapping positive runs; 5,734 source annotations become 4,972 union runs on the 143,726,002-bp assembly. Positive-only scoring does not label all remaining sequence negative. Full-assembly inference coverage was checked in the archived benchmark. **[TO COMPLETE: reconcile inconsistent narrative job identifiers and archive canonical prediction manifests for the legacy and later P3 cells.]** [E07, E16]

### Gap-information and actionability analyses

Gap-head training uses the registered human training chromosomes; DEV is chromosome 13. HN-O augments the control input with the frozen nucleotide-transformer logit and seam features together. Three seeds are trained under the matched head schedule, and their risk logits are averaged before applying the sigmoid. Targets are negative fractions; the information metric is base-length-weighted MSE on fully known gaps. Action AP evaluates the registered binary action target rather than general base-level calibration. [E08]

The feasibility analysis orders all candidate gaps by increasing frozen risk score, groups exact ties, and evaluates every resulting whole-gap prefix plus abstention. It applies candidate-count, positive-recovery, long-gap-recovery, and negative/unknown budgets. The genomic span used to derive those budgets is deliberately optimistic; it is not the measured callable denominator. Failure of necessary conditions rejects the fixed-score monotone whole-gap family without opening CAL or sealed panels. **[TO COMPLETE: deposit the full threshold frontier and immutable candidate/score ledger; the compact JSON alone does not reproduce all 60,497 threshold rows.]** [E09]

### Gene prediction

The completed C analysis fixes Tiberius 2.0.7, `mammalia_softmasking_v2`, sequence length 400,050, batch size 1, and the native CDS-only exact-chain scoring rule across nine cores. All cores, including those without reference chains, remain in the denominator. Gains and losses are matched reference-chain changes, not inferred from a net F1 difference. Tiberius itself has been evaluated as a gene predictor with repeat-masking input, but that literature does not demonstrate a benefit of the masks studied here. [E10; R7] ([OUP Academic][4])

The newer P3 U/P/R protocol instead specifies 20 cores and a gene-locus endpoint that permits a match to a prelisted complete isoform. Its engineering smoke failed before complete utility scoring. Its planned sample size, reference counts, and acceptance criteria are not treated as observed results and are not pooled with C. [E11]

### Auxiliary analyses and uncertainty

Coarse typing reports detection, globally defined per-class F1, all-six-class macro F1, and Unknown behaviour separately. Representation analysis distinguishes family-supervised contrastive training from subsequent clustering. In the Dfam panel, 1,350 fragments form the training partition and 450 form a stratified holdout; K-means fits training representations, while reported ARI/NMI cover the combined pool. Pooled standardization and the lack of family/homology isolation limit prospective interpretation. Router shortlist regret is recomputed from observed anchor outcomes and is not interpreted as an executed local selection procedure. [E12–E14]

No confidence intervals or significance values are fabricated from summary tables. Seeds, species, spatial blocks, genomic bases, and workflow cells are different units. Registered gates are reported as decisions; they are not statistical significance tests. Where the main claim requires uncertainty not recoverable from the archive, **[TO COMPLETE: paired spatial-block uncertainty from archived predictions under a fixed analysis plan, without new threshold or model selection].**

## Data and Code Availability

The reviewed code is identified by repository `JiWang-Unige/ab-initio-TE` and submitted commit `c6781414794c120e41f67d9b43859a4d28453065`. The review package includes a file inventory, local evidence ledger, source hashes, a read-only numerical audit script, and an audit-results JSON. It does not redistribute genome data, model checkpoints, full prediction caches, or private HPC outputs. **[TO COMPLETE: stable public release/DOI, checkpoint and calibration artifacts, permissible derived evaluation data and prediction manifests, environment/container digests, license and access conditions.]** Availability of a submitted ZIP must not be represented as a verified public release.

## References

| ID     | Verified source                                                                                                                                                                                                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1** | Dalla-Torre, H. et al. *Nucleotide Transformer: building and evaluating robust foundation models for human genomics.* Nature Methods 22, 287–297 (2025). DOI: `10.1038/s41592-024-02523-z`. ([Nature][2])                                                                                                                     |
| **R2** | RepeatMasker. *Web RepeatMasker help*, official documentation, accessed 14 September 2026. ([repeatmasker.org][1])                                                                                                                                                                                                            |
| **R3** | Wong, W. Y. and Simakov, O. *RepeatCraft: a meta-pipeline for repetitive element de-fragmentation and annotation.* Bioinformatics 35, 1051–1052 (2019). DOI: `10.1093/bioinformatics/bty745`. ([OUP Academic][5])                                                                                                             |
| **R4** | Baril, T., Galbraith, J. and Hayward, A. *Earl Grey: A Fully Automated User-Friendly Transposable Element Annotation and Analysis Pipeline.* Molecular Biology and Evolution 41, msae068 (2024). DOI: `10.1093/molbev/msae068`. ([OUP Academic][6])                                                                           |
| **R5** | GenerTeam. *GENERanno-eukaryote-0.5b-base*, official model card. Associated work: Li, Q. et al., *GENERanno: A Genomic Foundation Model for Metagenomic Annotation*, bioRxiv (2025), DOI: `10.1101/2025.06.04.656517`. The model card is the checkpoint source; this is not the separate SegmentNT paper. ([Hugging Face][7]) |
| **R6** | Hu, K. et al. *HiTE: a fast and accurate dynamic boundary adjustment approach for full-length transposable element detection and annotation.* Nature Communications 15, 5573 (2024). DOI: `10.1038/s41467-024-49912-8`. ([Nature][3])                                                                                         |
| **R7** | Gabriel, L., Becker, F., Hoff, K. J. and Stanke, M. *Tiberius: end-to-end deep learning with an HMM for gene prediction.* Bioinformatics 40, btae685 (2024). DOI: `10.1093/bioinformatics/btae685`. ([OUP Academic][4])                                                                                                       |

---

## 主要数字的附件定位

以下路径相对于仓库根目录。本地提取稿保留正文关键数字的直接入口；Pro 生成文件中的完整25项证据附录仍见原对话。本文件从可读取回复保存，并非成功下载的附件。

| 证据                   | 相对路径                                                                                                                 | 字段／评价对象                                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **E02** 历史矩阵         | `reports/tefm_final/PIPE-TEFM-FINAL-20260623/summaries/matrix_eval.tsv`                                              | `model_key, window, species, n_windows, te_f1`；495行的组成                                                                      |
| **E02** 早期窗口         | `reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep_current.tsv`                                       | 各checkpoint/window的早期F1；不得与当前DEV混分母                                                                                         |
| **E03** 历史版本问题       | `docs/experiments/REPOSITORY-SYSTEM-REVIEW-20260906.md`                                                              | Unknown→0、坐标压缩、interval painter、AP ties与训练暴露审计                                                                              |
| **E04** 共享D          | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D/dev_metrics.json`                                      | `per_species.*.{tiles,callable_bp,positive_bp,bp_tp,bp_fp,bp_fn,bp_f1,segment_f1_iou_0_8,boundary_f1_5bp}`；`summary`        |
| **E05** 覆盖比较         | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed{42,17}/{L,D}/{screen,dev}_metrics.json`                    | 八个明确组合文件；worm `bp_f1/bp_average_precision`及相同分母                                                                             |
| **E05** token oracle | `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904.md`                                                             | D0-C exact-ceiling归档段落；.994498不是本轮运行结果                                                                                      |
| **E06** PAIR8        | `reports/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/seed42-decision.json`                                                      | `contrasts`、`absolute_readiness`、`scientific_gate_pass`、`release_seed17`                                                    |
| **E07** P3机制及外部结果    | `docs/experiments/P3-R2-CLOSURE-20260830.md`                                                                         | Human matched table、Mouse段落、Exact FlyBase r6.68 T1表；完整预测未包含在ZIP                                                             |
| **E08** HN信息         | `reports/GAP-A-B1-SCREEN-20260908-R1/result.json`                                                                    | `training_rows/dev_rows/known_dev`；`results.{arm}.known_DEV.{rows,bp,fraction_mse,irreducible,pseudo_base_brier,action_ap}` |
| **E09** HN动作         | `reports/GAP-HN-RANK-FEASIBILITY-20260908-R1/result.json`                                                            | `unique_score_thresholds/feasible_thresholds`及两个decision points；完整frontier不在ZIP                                             |
| **E10** 旧C           | `reports/GAP-BRIDGE-C-UTILITY-20260906-R1/result.json`                                                               | `core_count/completed_cells/reference_distinct_chains/reference_source_rows`；`modes.*.metrics`、`paired_vs_m0`               |
| **E11** 新P3失败        | `docs/experiments/MANUSCRIPT-LIVE-STATUS-20260914.md`                                                                | 12652888终态、exit、elapsed、异常及smoke-only记录                                                                                     |
| **E11** 新效用协议        | `docs/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1.md`                                                              | 20core×3与gene-locus端点；这些是计划，不是完成结果                                                                                          |
| **E12** 粗类型          | `reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/superfamily5.tsv`                                               | `*_support/*_f1/unknown_recall/te_detect_f1/main4_conditional_macro_f1/macro_f1_all6`                                       |
| **E12** 指标定义         | `pipelines/PIPE-TEFM-LOCK-20260619/superfamily5_task.py`                                                             | `compute_metrics`，尤其main4 macro与conditional accuracy的区别                                                                     |
| **E13** Dfam表示       | `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/embedding_dfam_consensus.tsv`                                 | `setting,n,n_clusters,ari,nmi,holdout_macro_f1`                                                                             |
| **E14** F1点预测        | `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/selector_formula_results.json`                                 | `n_rows`、`deployable_random_forest`的in-sample R²及LOSO RMSE                                                                  |
| **E14** 路由器          | `reports/tefm_final/PIPE-TEFM-PURSUE-SELECTOR-20260630/conservative_router/selector_conservative_router_summary.tsv` | 固定 `feature_set=baseline_plus_kmer` 后比较split、contains-best及regret                                                           |
| **E15** 独立panel      | `docs/experiments/CROSS-SPECIES-L1-PANEL-METADATA-20260908.md`                                                       | assembly accession、修复后标签产物、库覆盖及暴露资格                                                                                         |
| **E16** 传统benchmark  | `docs/experiments/LEMMI-TE-BENCH-20260824-R1.md`                                                                     | assembly/truth flattening、三个有效T1 cell与运行台账                                                                                  |
| **E21** 当前训练/评分      | `scripts/experiments/CROSS-SPECIES-L1-20260903/cross_species_token_task.py`；同目录 `calibrate_evaluate_x0.py`           | 模型loader、token质量权重、CAL-only Platt、阈值规则和结构端点                                                                                 |
| **E24** J0/初始化       | `docs/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1.md`                                                               | J0阈值oracle表、P0R/H0R/D结果、停止决定及归档空间区间                                                                                         |
| **E25** gap路线状态      | `docs/experiments/GAP-ROUTE-TERMINAL-AUDIT-20260908.md`                                                              | 已完成、未执行、缺生物真值路线的分类；不是“所有方案均失败”                                                                                              |

---

[1]: https://www.repeatmasker.org/webrepeatmaskerhelp.html "https://www.repeatmasker.org/webrepeatmaskerhelp.html"
[2]: https://www.nature.com/articles/s41592-024-02523-z?error=cookies_not_supported "https://www.nature.com/articles/s41592-024-02523-z?error=cookies_not_supported"
[3]: https://www.nature.com/articles/s41467-024-49912-8?error=cookies_not_supported "https://www.nature.com/articles/s41467-024-49912-8?error=cookies_not_supported"
[4]: https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281 "https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281"
[5]: https://academic.oup.com/bioinformatics/article/35/6/1051/5079332 "https://academic.oup.com/bioinformatics/article/35/6/1051/5079332"
[6]: https://academic.oup.com/mbe/article/41/4/msae068/7635926 "https://academic.oup.com/mbe/article/41/4/msae068/7635926"
[7]: https://huggingface.co/GenerTeam/GENERanno-eukaryote-0.5b-base "https://huggingface.co/GenerTeam/GENERanno-eukaryote-0.5b-base"
[8]: https://docs.sylabs.io/guides/latest/user-guide/environment_and_metadata.html "https://docs.sylabs.io/guides/latest/user-guide/environment_and_metadata.html"
[9]: https://docs.omnibenchmark.org/latest/tutorial/ "https://docs.omnibenchmark.org/latest/tutorial/"
[10]: https://docs.omnibenchmark.org/latest/reference/ "https://docs.omnibenchmark.org/latest/reference/"
[11]: https://docs.omnibenchmark.org/latest/howto/ "https://docs.omnibenchmark.org/latest/howto/"
