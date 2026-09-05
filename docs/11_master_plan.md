# Master Plan / TE-FM 总路线合同

> **2026-09-05 用户指定 A/C 并行推进。** 当前 Human gap 新工作为
> `GAP-BRIDGE-P3-NT-R2` 的原生窗口配对准备/有界 smoke，与
> `GAP-BRIDGE-DOWNSTREAM-C-R1` 的固定三种 softmask 下游诊断准备。
> 协议见 `docs/experiments/GAP-BRIDGE-A-C-PARALLEL-20260905.md`。
> 旧 G/R/H Stage 1 的 `NO_ACTIONABLE_ARM` 不变；chr19 保持封存，
> 不启动 full-backbone training，也不把工程 smoke 作为科学通过。

> **Current route override (2026-08-31).** Older selector/structured-decoder
> actions below are historical and must not restart closed experiments. The
> only active route-selection experiment is the zero-GPU, ontology-first
> [`FBTI-EXTANT-LOCUS-PHASE0-R1`](experiments/FBTI-EXTANT-LOCUS-PHASE0-R1-20260831.md).
> Neural relation training, LoRA and full-backbone post-training remain frozen
> until its label, oracle-substrate and evidence-sufficiency gates all pass.

> 由 `$master-plan` 维护。最后更新：2026-08-12（保留 2026-07-01 主线历史，新增 bounded cohort）。
>
> 本文件现在是项目唯一中文主入口：既是导航图，也是 TE foundation model 研究路线合同。`docs/23_te_refinement_publication_route.md` 已并入本文件，之后仅作英文旧版参考，不再作为主路线维护。

## 0. 当前导航

> **2026-08-13 workflow simplification migration**：当前完整控制面已冻结到 `../ab-initio-TE-archive/` 并通过恢复 smoke；本项目转为历史证据仓。精简执行项目已创建于 `../ab-initio-TE-publication-lite/`，不含 Discovery/`$pursue`/编号式 docs 全家桶或项目级 hooks，只推进用户明确指定的少数补充结果。当前等待用户给出结果清单；旧资产未删除或移动。

### 2026-08-11 bounded direct-pilots overlay

- **当前动作**: F 路线已按 DEC-004 关闭。S leaf-adapter Job `11535362` 的六记录 syntactic component PASS 已完成 `2/3 DEGRADED_REVIEW` 与 pivot=`continue-current-route`。当前停在人闸：旧 `ACTIVE_GOAL` 仍是 selector/decoder milestone，会把所有 S 路线有效组件机械判为 failed_run；需先由用户批准最小 `$revise-goal` diff，再允许实现一个新的 representative CPU gate。RepeatMasker、representative/full DATA、homology、GPU direct S0、S1 和 claim 仍未授权。
- **为什么先做**: 五工具的实际版本、数据库和 adapter 是后续 FM-vs-workflow 可比性的地基；F/S 是对旧 fragmentation/open-set limitation 的新机制测试，但只有在 truth/split 闸通过后才有科学意义。
- **与旧决策兼容**: F 的 re-entry 仅限“immutable leaves + typed parent joins + richer/global evidence”，不重启 `DEC-001/002` 已否决的 gap/HMM/CRF/阈值或轻量 post-hoc cousin。S 把 Unknown 视为不确定性/更高 ontology node/abstain，绝不把它当普通生物 superfamily。
- **授权和上限**: 用户已一次性批准本 cohort 的 bounded smoke/screen；每作业 ≤12h，新增总 GPU ≤24 GPU-hours，CPU smoke 0 GPU，最大并行方向 3。禁止 full/scale、部署、数据库迁移、commit/push 和论文主张。
- **恢复指令**: 读 `codex_jobs/handoffs/TEFM-NEW-DIRECTIONS-PILOTS-20260811/UNIGE_DIRECT_CONTINUATION_PROTOCOL_20260811.md` 与三个 `GOAL_*_R2.json`，再对账 Wave-1 三个 R2 exp_id。已有 RUNNING/PENDING 时只做 job reconciliation；否则从 implement/code-review 状态继续。S1 不得在 S0 全门通过前启动。

- **Mode**: Mixed
- **模式组成**: Publication-Validation + Pipeline-Execution + bounded Discovery。
- **为什么切换**: 项目已经不再是“方向模糊地找一个 TE 模型”。当前已确定主张形状：raw-genome foundation model (FM) TE annotator 是主线；refinement-aware metrics、reference-circularity audit、zero-human ladder 是证据防守层。仍需少量 bounded Discovery 来确认 backbone/window/loss，但这些探索必须服务主 claim。
- **当前阶段**: 路线合同重构完成中；`$council` 已裁决新增 TE-LEN-VIZ、SF-TARGET、WIN-MATRIX、P8-MATRIX 等 phase gates，并在 2026-06-15 后续裁决：把 GENERANNO 整合版缺口以“嵌入现有 gate”的方式补入，不新增顶级算力合同；PU-Learning 从主线降级为 negative ablation / gated repair；Label-A 固定为 self-run RepeatMasker+Dfam，Label-B/de novo 作为 U-shield、sensitivity、baseline、candidate evidence，异常低表现物种/类可单独跑 de novo+Dfam 诊断。2026-06-18 根据 `PIPE-TEFM-SUPP-20260617` 和 `PIPE-TEFM-SEG-SF-20260618`，模型/窗口和注释可用性路线收束为 GENERanno 主线：下一步优先使用 4096bp，保留 2048bp 作为 shared anchor，对 segment/boundary 指标采用 overlap center-merge + smoothing/postprocess 候选。2026-06-19 根据 `PIPE-TEFM-REPAIR-20260618` 和 `PIPE-TEFM-LOCK-20260619`，混合动物结论进一步分层，superfamily 收束为 main4+Unknown/reject，fragmentation 使用 overlap/HMM。2026-06-21 根据 `PIPE-TEFM-EXTEND-20260620` 与 `PIPE-TEFM-ANCHOR-20260621`，植物/跨界 PU 不晋升，模型推荐改为 panel/kingdom-specific anchors；embedding claim 降级为 guardrail；decay/anchor selector 只作为 deployable screen，需要 locked panel 验证。2026-06-23 新增最终补充 pipeline `PIPE-TEFM-FINAL-20260623`：以 adaptive staged 方式补 NTv2/NTv3 model-size × window matrix、三重复 error bar、species-specific recovery audit、multi-anchor/decay 选择器和 strict fragmentation/interpretability 证据。
- **当前最终产物目标**: 一个从 raw genome sequence 直接推理的 TE foundation model 注释框架，能够在受控 reference-reproduction benchmark 中超过传统工具，并用 segment/boundary/refinement、zero-human 泛化和 reference-circularity 分析支撑可发表 claim。
- **当前动作**: `PIPE-TEFM-FINAL-20260623` model-size/window matrix 已完成并通过 3/3 `$tri-review` 与 pivot。Track B 证据包已补充 error bar、strict segment、plant QC、multi-anchor/selector、interpretability 与 structured-decoder support screens。`TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC` 已闭合：selector 只作为 conservative top-2/local-probe trust router 使用，leave-clade/new-clade 必须 abstain；structured decoder/fragmentation objective 路线已按 stop rule 停止并记入 `docs/09`，不能继续 threshold/gap/post-hoc 或 survival/retention tweak。`PIPE-TEFM-CAP-FRAGARCH` capability branch 也已闭合：Round 1 frozen interval heads 和 Round 2 fragment graph linker 均工程成功但方法失败，3/3 tri-review/pivot 决定停止并记入 `DEC-002`。当前不再继续 frozen/post-hoc interval reconstruction；fragmentation 只作为 limitation/future work，CE raw 与 overlap/smoothing 保留为固定 comparator。继续禁止把 animal 与 plant 混成一个 headline mean。

```text
路线合同/证据归档
  -> evaluator contract
  -> species/chromosome ladder + split
  -> traditional/FM baseline reproduction
  -> FM main comparison
  -> zero-human decay model
  -> refinement/circularity/evidence audit
  -> figure/table + publication package
```

## 1. 一句话主张

用 raw genome sequence 输入的基因组 foundation model 做 TE 注释，证明它在同一 reference-reproduction 口径下可超过 RepeatModeler2/EDTA/HiTE 等传统工具；同时用 segment-level annotation quality、reference-circularity sensitivity、P/RN/U/hardN label discipline 和 zero-human 泛化阶梯证明这个优势不是 bp-F1 幻觉、不是 RM reference artefact，也不是把未知区误报成 TE。

## 2. Claim hierarchy / 证据层级

| Claim | 说法 | 主指标 | Comparator | 必须防守的问题 | 状态 |
|---|---|---|---|---|---|
| C1 FM raw-genome annotator | FM 只吃 FASTA/window sequence，可在受控 benchmark 中超过传统 TE 工具 | bp TE-F1、AUPRC、precision/recall | RepeatModeler2、EDTA、HiTE、RepeatMasker/EarlGrey、one-hot/CNN | tool/library/reference regime 必须一致 | off-machine 结果已由用户确认，待归档 |
| C2 Annotation usability | 高 bp 分数能转化为可用 BED/GFF3 segment | segment IoU F1、boundary F1、fragmentation、overmerge | raw prediction、cheap threshold+min_len+merge_gap、传统工具 segment | bp-F1 不代表 annotation quality | 待 docs/19 锁定 |
| C3 Zero-human generalization | 排除 human+non-human primate 训练后，FM 仍可泛化到 hs1/T2T human anchor | hs1/T2T TE-F1 + segment/boundary；distance-decay residual | 同距离但低完备注释物种、production protocol | human 高分是否只是 annotation completeness 高 | 待 species ladder |
| C4 Reference-circularity defense | 传统工具高分受 RM/library/reference regime 影响，FM 优势需分层解释 | RM-derived vs RM-free delta、library-version sensitivity、evidence support tier | RM-dependent vs RM-free/structural tools | RM-derived GT 不是 biological truth | 旧 TE_final W11/W12 可迁移 |
| C5 Evidence-supported candidates | model-only 高分 U 区只能叫 candidate，不能直接叫 novel TE | independent support rate | Dfam/newer library、structural tools、copy/domain/manual audit | DL-only false positives | P1/P2 |

**硬规则**: 任何结果若没有写清 `tool version + library version + reference regime + metric level + split/chromosome`，不得写成 “FM beats traditional tools”。

## 3. 已确定选择

| ID | Date | 选择 | 理由 | 影响哪些后续步骤 | 可重开条件 |
|---|---|---|---|---|---|
| D-001 | 2026-06-14 | `docs/11_master_plan.md` 升级为唯一中文总路线合同 | 用户要求一份完备路线图；`docs/23` 与 `docs/11` 双维护会漂移 | 所有新会话先读 docs/11 | 若后续拆成正式 publication/pipeline 子文档 |
| D-002 | 2026-06-14 | `docs/23_te_refinement_publication_route.md` 并入 docs/11 后归档 | docs/23 是英文旧草案，且 refinement-first 与当前主线不完全一致 | docs/23 不再作为主入口 | 若需要保留英文投稿路线，再另建 docs/12/稿件文档 |
| D-003 | 2026-06-14 | 主线是 raw-genome FM TE annotator，不是 RM-region postprocessor | FM 推理阶段只吃 FASTA/window sequence，才能公平比较 RepeatModeler2 等传统工具 | 模型输入、pipeline、claim wording | 若另开 secondary refinement tool |
| D-004 | 2026-06-14 | 采用“FM 主线 + refinement/circularity 防守” | 用户确认 FM 超传统工具是主线；refinement metrics 用来证明注释可用性 | docs/19、docs/14、figure plan | 若 off-machine 结果归档后不成立 |
| D-005 | 2026-06-14 | 训练协议双层分明：production/matched-label + zero-human | production 证明工具性能；zero-human 证明泛化，不把整篇成败压在最难协议上 | baseline、result-log、figure table | 若目标期刊要求只讲 zero-shot/zero-human |
| D-006 | 2026-06-14 | zero-human human anchor 的理由是 human 注释最完备 | hs1/T2T 作为高可信 reference anchor；同距离低完备注释物种用于区分模型失败 vs 注释不完备 | generalization decay model | 若出现更完备非人类 reference |
| D-007 | 2026-06-14 | 泛化公式用每物种一条合适常染色体建 ladder，再用另一条常染色体做稳定性检查 | 长染色体提供足够 block/window 内不确定性；第二染色体验证 chromosome-choice 稳定性 | species manifest、split、eval scripts | 若第一阶段显示染色体内异质性过大 |
| D-008 | 2026-06-14 | 泛化公式变量包含 evolutionary distance + annotation completeness/library coverage + TE composition | 需要解释 performance decay 是否来自距离、注释缺失或 TE landscape | docs/19、docs/14、analysis scripts | 若数据不足，先退化成距离+TE fraction |
| D-009 | 2026-05-29/2026-06-14 | RepeatMasker full-parse 口径保留，`U` 不当 negative | hardN/RN 需要 simple/low-complexity/satellite 等 other repeat 信息；未注释不等于真负类 | label harmonization、check_data | 若外部 gold negative panel 可用 |
| D-010 | 2026-06-14 | HMM/CRF、long-context 16-32kb、backbone zoo、family/open-set、model-only novel discovery 均降级 | 这些都不能挡 MVP；必须先证明 FM 主比较和 annotation usability | experiment priority | 若 C1/C2 已经稳过 gate |
| D-011 | 2026-06-15 | `$council` 裁决采用“强关卡，弱参数；主干导航，分布执行” | TE 长度、superfamily、窗口和 P8 迁移矩阵会决定后续结果是否可比；但不能把 docs/11 写成全排列算力合同 | docs/13/14/19、refs/dossiers、P2-P8 执行表 | 若 EDA 显示当前 gate 阈值不适合某 kingdom 或目标物种面板大改 |
| D-012 | 2026-06-15 | Cross-kingdom 不删除，但默认降为 Enhanced/sentinel；same-kingdom holdout 与 human/non-human audit 进入 Core | 跨界泛化有论文价值但解释复杂，过早全量执行会导致 P8 组合爆炸 | docs/14 P8 matrix、figure plan | 若主 claim 明确改为 universal cross-kingdom FM |
| D-013 | 2026-06-15 | Rare/single-species superfamily 默认不进入主 macro-F1 | 小众类会放大噪声和 species-label leakage，扭曲主评分 | docs/19 metric masks、refs/dossiers/sf_target_set.md | 若该 rare superfamily 成为单独 biological case study |
| D-014 | 2026-06-15 | GENERANNO 整合版缺口分层落盘：`SPECIES-PANEL`/`SAMPLING-BATCH` 立即进入 Core data/split contract；`CONTEXT-TRAP` 进入 pre-claim/screen diagnostic；`UHC-EVIDENCE-CARD` 进入 C5 guardrail；`FAMILY-EMBEDDING` 和 `CLI-RELEASE` 保持 Enhanced/Parked | 三方 council 认为 1-4 是可比性/防守合同，但不能新增一串独立大工程；5-6 会改变论文边界并拖慢 C1/C2 主比较 | docs/13/14/19、docs/15 | 若论文标题/摘要级主张转向 family/novel discovery 或 software release |
| D-015 | 2026-06-15 | PU-Learning 退出主线；当前 ignore-mask/nnPU 记为 `SCREEN_NEGATIVE / ABANDONED_MAINLINE`，仅保留 negative ablation 与 gated repair | M2 sampled transfer 中 PU 明显弱于 binary，threshold-only repair 不能救回；但 `unannotated != reliable negative` 这个科学问题不被否定 | docs/14 ablation、后续 training objective 选择、算力分配 | 训练级 PU repair 在 sampled multi-target gate 通过：接近 binary TE-F1、unknown pred-TE rate 受控、segment F1 不崩 |
| D-016 | 2026-06-15 | Label-A = self-run RepeatMasker+Dfam 是唯一 claim-bearing primary reference；Label-B = de novo+Dfam 不升全局主标签，用作 U-shield/sensitivity/baseline/candidate evidence；若模型在某物种或 superfamily 表现异常差，可单独跑 de novo+Dfam 诊断 | Council 认为统一 Label-A 最可复现、可比；de novo 作为主标签会引入 pipeline bias 和跨物种不可比；但 Dfam 漏标需用 Label-B 主动屏蔽和诊断 | docs/13 label-source protocol、docs/19 evaluator mask、P2/P3 gates | 若 Label-A/B concordance 与 U-QUALITY 显示某物种 Label-A 严重不足，默认限缩 claim 或 audit-only；是否升级 label source 需新 council，不自动切换 |
| D-017 | 2026-06-16 | 物种策略升级为“少量核心训练 + 宽评估 + production/generalization 分离”：H0 human-only；A0/A1 小 ablation；A2 六个非人动物作为主 no-human animal；B 加 human 做 production；C 独立 PlantTE；D animal+plant shared/kingdom-head；E fungi 后置 | 宽物种池直接进训练会变量过多、解释弱；当前节点代表性设计更适合主线，但旧物种池保留为 held-out/stress/reserve。若 backbone 预训练见过 human，只能写 no human supervised TE labels during fine-tuning | docs/species.md; docs/13 SPECIES-PANEL; docs/14 P8; software_outputs/repeatmasker_dfam/experiment_views | 若主 claim 改为 universal cross-kingdom 或新物种 Label-A/QC 证据改变训练池 |
| D-018 | 2026-06-18 | 后续注释可用性实验固定 `GENERanno` 作为基模，窗口只跑 2048bp 和 4096bp，单 seed=42 | 前一轮 screen 显示 GENERanno 在 2048 transfer、mouse-only 和可运行性上最适合进入下一阶段；4096 是 H0/paired transfer 强窗口，2048 是共享 anchor | `PIPE-TEFM-SEG-SF-20260618` overlap/segment/superfamily/embedding 管线 | 若 bp-level full evaluator 证明 4096/2048 都不稳定，或 NTv2 在 claim-calibrated full run 显著超过 |
| D-019 | 2026-06-18 | embedding clustering 作为 Enhanced/screen 证据，不直接等同 superfamily classifier claim | contrastive 与 clustering容易受标签泄漏、species composition 和 k-mer 背景影响；本轮已修 holdout 泄漏，但仍需看 B vs D panel 和 kmer baseline | `reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/embedding_cluster` | 若 model embedding 稳定超过 kmer baseline 且跨 panel/length 一致，再升级为 family representation claim |
| D-020 | 2026-06-19 | A2 mixed-animal 低均值不得解释为动物模型整体失败 | `invert_boost_animal_4096` 在 B-panel mean TE-F1 0.9351、A1 close vertebrate mean 0.8985；A2 mean 0.5750 主要由 honeybee/beetle 和远缘 stress species 拖低 | 下一轮 claim/eval 表必须分 primary close/training-domain panel 与 stress/label-source appendix | 若 label-concordance 修复后 stress species 仍低且 close/training-domain 也退化 |
| D-021 | 2026-06-19 | binary TE fine-tuning 后的 embedding 不作为 superfamily clustering 负结论 | C1 length512 ARI 0.9208、holdout macro-F1 0.8784、pair AUC 0.9856；A1 pretrained GENERanno length512 holdout macro-F1 0.8495；B1 binary fine-tuned length512 holdout macro-F1 0.5561，说明目标函数改变了 representation geometry | embedding 后续必须包含 C1/A1、pairwise similarity、linear probe、leak-free supervised contrastive 或 metric-learning 版本 | 若 leak-free contrastive 后 model embedding 仍稳定低于 C1 |
| D-022 | 2026-06-20 | `PIPE-TEFM-EXTEND-20260620` 可并行执行，但只作为分支隔离的 screen | Council 认为批次回应的是前序具体缺口，但假设轴多，必须按 embedding/SF5/plant transfer/PU/cross-kingdom/stress anchor/decay 分支单独解释 | 当前 sbatch 依赖链、result summary、后续 tri-review | 若任一分支基础设施失败或只能以 aggregate mean 解释，则该分支 inconclusive |
| D-023 | 2026-06-20 | Plant/PU 训练不使用 unannotated background 作为可靠 negative | 植物与低质量注释物种的 U 区可能含真实 TE；把 U 当负例会失去 PU-learning 的科学意义 | `prepare_pu_windows.py`、`pu_token_task.py`、plant/cross-kingdom 结果解释 | 若后续建立 RN/hardN 高置信负例 panel，可新增 RN/hardN 对照训练 |
| D-024 | 2026-06-21 | `PIPE-TEFM-EXTEND-20260620` 后不晋升 plant/cross-kingdom PU | plant/cross PU 主要表现为高召回低精度，non-TV 分支大量 overcall；TV+HMM 有改善但仍低于 `invert_boost_animal_4096` | 下一轮主模型继续使用 `invert_boost_animal_4096`; PU 只保留 negative ablation / future methodology | 若建立高置信 RN/hardN 负例或 PU objective 能同时控制 U-overcall 与 segment-F1 |
| D-025 | 2026-06-21 | main4+Unknown 使用 base-pretrained 初始化 | EXTEND SF5 复核 main4 conditional macro-F1 0.8547、Unknown recall 0.3957；与 LOCK 的 base-pretrained 优势一致 | superfamily/open-set 分支、docs/19 metric masks、future SF5 runs | 若新 objective 在 Unknown recall 和 main4 false-unknown rate 上同时显著更好 |
| D-026 | 2026-06-21 | strict embedding 不作为 FM superiority claim，C1 是必需 baseline | family-level dynamic internal/boundary fragments 中，A1 model+contrastive 有提升但 C1 basic sequence features + contrastive 最强；Dfam consensus 缺 FASTA 只能标 pending | embedding/contrastive 只作为 guardrail/secondary analysis | 若配置 Dfam consensus FASTA 后，model embedding 在 consensus/genomic internal/boundary 三来源均稳定超过 C1 |
| D-027 | 2026-06-21 | decay formula 只作为带 label/source covariates 的探索模型 | distance-only R2 0.1870；加入 label_jaccard/source variables 后 R2 最高 0.5249 | 泛化公式写法、figure/table 防守、source-concordance audit | 若后续全 panel/多染色体验证显示 distance-only 或 phylogenetic model 稳定解释主要方差 |
| D-028 | 2026-06-22 | 对外推荐采用 panel/kingdom-specific anchors + deployable selector under evaluation，而不是单一万能模型 | `PIPE-TEFM-ANCHOR-20260621` 显示 `insect_primary_4096` 可把 honeybee TE-F1 恢复到 0.9465，但 beetle 仍近零；BG-inclusive embedding 仍由 C1 胜出；deployable selector leave-species-out error 仍高 | Track B panel design、anchor recommendation、figure/table wording、stress appendix | 若 locked Track B 显示单一 branch 在所有 primary panels 上稳定优于 panel-specific routing，或 selector 在 held-out species 上不能超过 best-single baseline |
| D-029 | 2026-06-23 | 最终补充 pipeline 采用 adaptive staged execution，而不是盲目全矩阵 waterfall | Council 认为 45 个 model-window 训练、495 个 eval、三重复和 species audit 必须由 adapter smoke、strict metric lock、sentinel/full matrix 结果逐步触发；NTv2-500M species probe 只能作为 soft label/source audit，不能单独决定剔除物种 | `PIPE-TEFM-FINAL-20260623` download/prep/smoke/strict-segment、后续 train/eval/error-bar/multi-anchor/decay formula | 若 smoke 全部通过且 sentinel matrix 显示新增模型族存在明确信息增益，可升级完整矩阵和三重复；若 adapter 或数据失败，先修 runtime/data gate，不解释为性能证据 |
| D-030 | 2026-06-29 | `PIPE-TEFM-FINAL-20260623` 晋升到 Track B，但采用 panel-specific minimal promotion set | 3/3 tri-review 均建议 `scale-to-track-b`。Human/animal leader 是 `ntv2_250m@4096`，plant challenger 是 `ntv3_100m_pre@2048`；模型参数量和 8kb 预训练不呈简单单调优势 | `PIPE-TEFM-FINAL-EBAR-20260629` error bars、strict segment/boundary、plant label QC、multi-anchor selector | 若染色体重复 error bar 显示 leader 不稳定，或 strict segment 指标与 bp-F1 方向相反，则重开候选集或引入 `ntv2_250m@2048`/其他 fallback |
| D-031 | 2026-06-30 | `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC` 闭合：selector 冻结为 conservative router，structured decoder 路线停止为 future work | Selector 两轮后仍只能防守为 in-panel top-2/local-probe router，leave-clade/new-clade abstain；decoder final retention-constrained attempt 工程成功但方法失败，segment/boundary 低于 CE 且 true-backed deletion 仍高于 0.15 | publication wording、docs/09 决策日志、后续不再跑同类 decoder tweak | 只有出现新机制并同时把 segment-F1、boundary-F1、missed_true_rate 和 deleted_true_backed_fraction 四个 strict gate 全部预注册为 primary，才可重开 |
| D-032 | 2026-07-01 | Fragmentation capability Round 1 决策为 `replace-component`，停止 frozen-lightweight interval heads | `PIPE-TEFM-CAP-FRAGARCH-20260701` 测试 `boundary_proposal` 与 `anchor_free_interval`，均未同时超过 CE 和 CRF-style smoothing，且 true-backed deletion 很高；3/3 tri-review 认为当前 heads 不能 scale/tune | `docs/24_sprint_pursue_ledger.md`、下一轮 capability-pursue 设计、publication future-work wording | 只允许一个 genuinely new mechanism 的 bounded Round 2，例如 fragment graph linker 或 boundary-conditioned span refinement；不得重启 threshold/gap/HMM/CRF/survival/retention tweak |
| D-033 | 2026-07-01 | Fragmentation capability Round 2 后停止当前 interval reconstruction capability | `PIPE-TEFM-CAP-FRAGGRAPH-20260701` 的 preservation-first graph linker 等同 CE raw，learned keep/drop 虽提升 human strict segment/boundary 但 deleted_true_backed_fraction=0.8632 且 mouse 不过 smoothing；3/3 tri-review 和 pivot 均建议 abandon-route | `docs/09 DEC-002`、publication limitation/future-work wording、后续 TODO 清理 | 只有 end-to-end/global interval detector 或更强生物先验模型在至少两个染色体/物种上同时超过 CE 与 smoothing，并满足 missed_true_rate 与 true-backed deletion guardrail，才可重开 |
| D-034 | 2026-08-11 | 正式并行推进 B/S/F；S 必须先验证 direct-superfamily baseline，再研究 hierarchical/open-set error correction | 用户明确要求继续推进并规定 superfamily 顺序；直接基线不过时，abstention 可能只是隐藏错误 | continuation protocol、docs/03/19、Wave-1 exp IDs、Wave-2 G/E 顺序 | 若 S0 leakage-safe 直接基线全门通过，则开放 S1；否则只修 annotation/split/head identity |
| D-035 | 2026-08-12 | S0 保留 direct superfamily 标签，sequence homology 仅定义 leakage-safe split components；excluded identifiers 保持 U/ignore，`X13_LINE` 保持 ambiguity/audit-only | 用户授权继续 direct-superfamily-first；该选择避免用同源聚类改写预测标签，同时用 component-level zero-overlap 防止家族泄漏 | S0 identity resolution、homology graph、data materialization、direct-head evaluator | 若 partition-3 metadata 解析仍无法恢复缺失身份，则将未解析项保留为明示 coverage blocker，不得随机/前缀猜测或用 copy-derived proxy 静默替代 |
| D-036 | 2026-08-12 | 关闭旧 Dfam 3.9 post-hoc identity 路线，转为 annotation-time accession-preserving 的新 benchmark version；先 6-family CPU round-trip smoke，再真实窗口 representative concordance，后 full DATA/homology，最后才 direct S0 | Job `11528267` 证明旧 identifier 的权威 exact relation 只能唯一覆盖 50/279、26.595% occurrence mass；用户要求继续解决研究问题且坚持 direct-SF 先行 | 新 benchmark 合同、accession-retention/concordance ledger、CPU DATA gate、direct-S0 evaluator | 工具链 smoke 不冒充代表性证据；不改旧结果、不缩分母、不用 fuzzy/current API/copy proxy；CPU identity/concordance/leakage 任一失败即停止，GPU/S1 不授权 |

## 4. 模型、输入与输出定义

### 主模型输入

- `data/raw/<species>/genome.fa`
- `genome.fa.fai`
- `chrom.sizes`
- window/chunk manifest，例如 4 kb core window、2 kb stride。

主模型推理阶段禁止使用：

- RepeatMasker/UCSC/RepeatModeler2/EDTA/HiTE/EarlGrey 的 interval 作为输入特征；
- 已有 TE-like regions 作为唯一候选区域；
- 任何目标物种 test chromosome 的 annotation evidence。

这些外部注释只能用于：

- 构建训练 label；
- 构建 reference benchmark；
- 作为 traditional baseline；
- 做 circularity/evidence audit。

### 主输出

- `p_TE.bigWig`
- `p_order_or_superfamily.bigWig`（若分类 claim 启用）
- `boundary_start.bigWig`
- `boundary_end.bigWig`
- `segments.filtered.bed`
- `segments.superfamily.gff3`
- `evaluation_summary.tsv/json`
- `label_qc.html` / `prediction_qc.html`

## 5. 数据、标签与 split

### Label states

| State | 含义 | 训练用途 | 评估用途 |
|---|---|---|---|
| `P` | high/medium confidence TE positive | positive loss | TE reference / support tier |
| `RN` | reliable negative，扣除 TE/repeat/uncertain/problematic 区域 | negative loss | specificity / RN-FPR |
| `U` | unannotated or uncertain region | ignore | candidate evidence only |
| `hardN` | simple repeat、low complexity、satellite、tandem、other non-TE repeat-like | hard negative | hardN-FPR |

规则：

- `U` 不能当 negative。
- family-level classification 只在 high-confidence segment subset 上做，不能作为第一阶段 headline。
- unresolved nested、conflict、near-boundary ambiguity 默认 ignore 或 low-weight，不进普通 negative loss。

### Label source hierarchy

| Layer | Source | Role | Claim status |
|---|---|---|---|
| `Label-A` | self-run RepeatMasker + Dfam, fixed version/library/species parameters | 主训练、主评估、cross-species matrix 的 primary reference | claim-bearing primary |
| `Label-B` | RepeatModeler2 / EDTA / HiTE + Dfam + RepeatMasker | Label-A/B sensitivity、U-shield、traditional de novo baseline、UHC candidate validation | audit / shield / baseline；不自动升主标签 |
| `Label-C` | structure/copy/consensus/domain/cross-assembly/manual evidence | UHC evidence cards 和 case study 支撑 | candidate/discovery support only |

规则：

- `Label-B-only` TE-like interval 不等于 primary positive；默认进入 `U` 或 candidate evidence，训练 loss 与主 FP 计算中屏蔽。
- 若某物种、染色体或 superfamily 上主模型表现异常差，允许单独跑 de novo+Dfam 诊断；该结果用于判断 Dfam 覆盖盲区、label-source-limited claim 或 audit-only 降级，不自动改写全局 Label-A。
- 任何把 Label-B 升为 primary/co-primary 的动作都视为路线变更，必须有 Label-A/B concordance、U-QUALITY、Label-C 支撑和用户确认；不得在一次模型失败后临时切换真值。

### 物种与 split 角色

| Tier | 角色 | 物种/候选 | 用途 |
|---|---|---|---|
| Production / matched-label | 工具性能主比较 | human/hs1 或当前 reference-rich species + matched non-human panel | FM vs RepeatModeler2/EDTA/HiTE/RepeatMasker |
| T1 train no-human | A2 no-human supervised-label 训练 | mouse, zebrafish, chicken, Xenopus tropicalis, fruit_fly, c_elegans | 排除 human + non-human primate supervised TE labels；若 backbone 预训练见过 human DNA，claim wording 必须限定为 fine-tuning labels |
| T2 validation ladder | 距离/注释完备度验证 | cow, opossum, anole, D. pseudoobscura, C. briggsae | threshold/model selection 不碰 human |
| T3 held-out anchor | high-confidence 泛化 anchor | hs1 / T2T-CHM13 | zero-human 泛化主评估 |
| T4 evidence/audit | 独立证据 | Dfam/newer library, structural tools, copy/domain/manual panels | circularity 和 model-only candidate audit |

### 常染色体策略

- 每个物种先选一条足够长、TE bp 足够多、annotation/provenance 清楚的常染色体建 ladder。
- 每个关键 clade 再选另一条常染色体做公式稳定性检查。
- sex chromosome、microchromosome、极端 TE-poor/TE-rich contig 不作为第一版公式主点。
- 染色体内 block/window 波动用于 confidence interval，不当作独立 species-level 样本。

## 6. 指标合同草案

| Claim | Primary metrics | Secondary / guardrail | 不能做的事 |
|---|---|---|---|
| FM vs traditional | bp TE-F1, AUPRC, precision/recall | MCC, calibration, runtime | 不能跨 reference/library/split 混比 |
| Annotation usability | segment_iou_f1@0.5, boundary_f1@50/100bp | median/P90 boundary error, fragmentation reduction | 不能用 bp F1 代替 annotation quality |
| Overmerge control | overmerge rate, cross-family overmerge | false bridge FPR | 不能靠无限 merge 提高 segment IoU |
| Incomplete-label specificity | RN-FPR, hardN-FPR | U high-score candidate support rate | 不能把 U 当 negative，也不能把 model-only U 叫 novel TE |
| Generalization decay | species/chromosome-level F1 residual vs distance/completeness/composition | worst-species floor, block bootstrap CI | 不能把 overlapping windows 当独立泛化样本 |
| Circularity sensitivity | RM-derived vs RM-free delta, library-version delta | evidence tier support | 不能把 RM-derived score 当 biological truth |

`docs/19_evaluator_contract.md` 必须把 segment matching、boundary matching、overmerge、fragmentation、RN/hardN FPR、calibration 和 statistical test rules 写成可执行合同后，才能开始 claim-bearing runs。

## 7. 执行路线图

| Step | 名称 | 为什么先做 | 完成证据 | 状态 |
|---:|---|---|---|---|
| 1 | 归档路线与 off-machine 结果 | 先把主 claim 和证据来源固定，避免继续在聊天里漂移 | docs/11 更新；off-machine FM>RepeatModeler2 结果进入 docs/15/refs 或明确 pending | now |
| 2 | Evaluator contract v0.1 | 没有指标合同，任何 “beats traditional” 都不可复现 | docs/19 填好 metric、reference regime、统计规则 | todo |
| 3 | Species/chromosome ladder + manifest | zero-human decay 和 production comparison 都依赖固定 panel | species_manifest + chromosome choice + provenance | todo |
| 4 | Label harmonization + QC | P/RN/U/hardN 是训练与防守核心 | label_harmonization_rules + training_ready gate | todo |
| 5 | Traditional baseline reproduction | 必须本地复现 RepeatModeler2/EDTA/HiTE/RepeatMasker 口径 | docs/20 + reports for baseline | todo |
| 6 | FM main comparison | 主 claim 证据：raw-genome FM vs traditional | comparable result-log + validate_goal | todo |
| 7 | Refinement/usability evaluation | 证明高 F1 转化成可用 annotation | segment/boundary/overmerge/RN-hardN tables | todo |
| 8 | Zero-human decay + circularity audit + publication package | 证明泛化与 reference robustness，并把结果组织成 figure/table/reviewer defense | decay model + RM-free/library/evidence audit + docs/12/14 figure plan | todo |

### 7.1 Council phase gates / 2026-06-15 补充执行表

本表来自 `$council` 裁决，原则是“强关卡，弱参数；主干导航，分布执行”。`docs/11` 只记录必须产出的判定材料和进入下一阶段的条件；完整协议落到 `docs/13`、`docs/14`、`docs/19` 与 `refs/dossiers/`。

| Gate | Phase | 层级 | 必须产出 | 阻断/警告条件 | 详细落位 | 状态 |
|---|---|---|---|---|---|---|
| `CHROM-LADDER` | P2 | Core | species/chromosome ladder、train/validation/test chromosome roles、TaxID/assembly provenance、同源/近重复泄漏检查 | 若 train/test 同源片段或可疑近重复无法排除，BLOCKED | `docs/13 §7.1`; `docs/19 §3` | todo |
| `TE-LEN-VIZ` | P2/P3 | Core | per-species/per-superfamily TE 长度直方图、累积 TE bp、短/长片段比例、fragment density、Label-A/B 长度对比 | 候选 window 覆盖不足、碎片化严重或 Label-A/B 长度分布冲突，WARNING；严重时阻断 window 决策 | `docs/13 §7.2` | todo |
| `LABEL-CONCORDANCE` | P3 | Core | Label-A vs Label-B interval IoU、boundary shift、class-level concordance | 一致性过低时不得冻结 superfamily set 或 TEPost 参数 | `docs/13 §7.3` | todo |
| `U-QUALITY` | P3 | Core | U/RN/hardN 污染检查，尤其 U 中潜在 TE bp 比例；UHC evidence-card schema | U 明显含 TE 时，不得把 U 当 negative；无 evidence tier 时不得 claim novel/underannotated TE | `docs/13 §7.4`; `docs/14 §8`; `docs/19` | todo |
| `SF-TARGET` | P3->P4 | Core | provisional frozen superfamily set、global/per-kingdom bp%、species coverage、rare/Other_TE 合并记录 | 类别过多、Other_TE 过大、单类样本不足、单物种特异类进入主评分时 WARNING | `docs/13 §7.5`; `docs/19`; `refs/dossiers/sf_target_set.md` | todo |
| `WIN-MATRIX` | P4 | Core + Enhanced | 2048bp shared anchor、每 backbone native/recommended window、2048 覆盖率表；context-trap sentinel 设计；最终 backbone 才做 512-8192 sweep | 禁止全模型 x 全窗口 x 全物种穷举；2048 覆盖不足时升级一个长窗口评估；claim 前需有 flank/matched-negative 防守或明确 waive | `docs/13 §7.6`; `docs/14 §3`; `docs/19 §6.5`; `refs/dossiers/window_matrix.md` | todo |
| `P8-MATRIX` | P8 | Core + Enhanced | human-only FM、no-human FM、best/current FM、Dfam-human-only RM、target/clade Dfam RM、RepeatModeler2/de novo baseline 的分层矩阵 | 缺 human-only FM vs Dfam-human-only RM 时不得 claim 人类知识泛化；缺 no-human vs target Dfam 时不得 claim de novo/generalization | `docs/14 §7` | todo |
| `SPECIES-WEIGHT` | P7 | Enhanced | 多物种采样权重方案与消融计划 | 物种数量/TE bp 严重不均衡时必须至少登记风险 | `docs/13 §7.7` | parked until P7 |
| `TEPOST-PARAMS` | P7 | Enhanced | 基于 TE-LEN-VIZ 的 min_len/merge_gap/smoothing 参数表 | 不得盲用默认参数支持 annotation usability claim | `docs/13 §7.8` | parked until P7 |
| `FIGURE-TABLE-PLAN` | P6 后 | Enhanced | Fig/Table 与 required evidence/run ID 对照表 | 缺 run ID/version/hash 的图表不得进入 claim | `docs/12`; `docs/14` | todo |

## 8. 实验优先级

| Priority | 实验 | 目的 | 成功标准 | 失败时动作 |
|---|---|---|---|---|
| P0 | off-machine FM>RepeatModeler2 结果归档 | 固化主 claim 的已有事实 | 有路径、表格、物种、metric、protocol | 不能 headline “beats RepeatModeler2” |
| P0 | raw RM / RepeatModeler2 / EDTA / HiTE reproduction | 建公平传统 baseline | 同 split/reference/metric 可复现 | 修 baseline，不改模型 |
| P0 | one-hot/CNN 或 light U-Net | 证明 FM 不是普通 CNN 就能替代 | FM 明显优于 non-pretrained baseline 或解释差异 | 降级 FM novelty |
| P0 | GENERanno 4 kb raw-genome FM | 主模型回路 | 超传统或至少接近且在防守指标更好 | 调整 head/loss/window，不扩 zoo |
| P0 | segment/boundary/overmerge metric | annotation usability | 比 raw prediction 和 cheap baseline 更好 | 降级为 detector + postprocess |
| P0 | zero-human hs1 anchor + ladder | 泛化核心证据 | hs1 高可信 anchor + distance/completeness model | 重新解释为 production tool |
| P1 | window ladder 1/2/4/8 kb | 找 context sweet spot | 提升且 OOD 不崩 | 避免 16-32kb context trap |
| P1 | context-trap sentinel | 验证模型是否依赖 flanking/species background shortcut | flank masking/swap、matched negative、embedding species leakage 至少完成最小诊断或有明确 waive | 若长 context 依赖 flank 背景，降级长窗口 claim |
| P1 | RM-free / library sensitivity | circularity defense | 传统和 FM 的 reference delta 可解释 | 收窄 claim wording |
| P1 | HMM/CRF/learned decoder | 结构化后处理 | 必须超过 cheap threshold+min_len+merge_gap | 继续 parked |
| P2 | family/open-set module | 生物解释和 candidate support | high-confidence segment 上有效 | future work |
| Park | model-only novel discovery | 潜在高风险 claim | 需独立 homology/structure/copy/domain/manual support | 不作为主线 |

## 9. 泛化下降公式设计

目标不是只画 heatmap，而是建立一个可解释的 performance decay model：

```text
performance(species, chromosome)
  ~ evolutionary_distance_to_training_anchor
  + annotation_completeness_or_library_coverage
  + TE_composition
  + genome/TE landscape covariates
```

第一版变量：

- evolutionary distance：TimeTree 或文献来源，记录版本。
- annotation completeness / library coverage：RM-self baseline、Dfam/library coverage proxy、reference TE bp fraction、known annotation source richness。
- TE composition：LTR/LINE/SINE/DNA/UNKNOWN_TE fraction、TE bp fraction、repeat landscape entropy。
- uncertainty：chromosome block bootstrap；第二常染色体 stability check。

解释目标：

- 若 hs1 高、相近非人类低，且低分物种 annotation completeness 低，则不能直接判为模型泛化失败。
- 若同距离、同完备度物种仍低，才更像模型无法跨该 TE landscape。
- 若长 window in-domain 高但 OOD 低，标记为 context trap。

## 10. 投稿故事与图表

| Fig/Table | Message | Required evidence | 状态 |
|---|---|---|---|
| Fig.1 | raw genome -> FM -> TE probability/boundary -> segment BED/GFF3 -> evidence audit | pipeline schema + artifact examples | todo |
| Fig.2 | FM 在受控 reference-reproduction benchmark 中超过传统工具 | FM vs RepeatModeler2/EDTA/HiTE/RepeatMasker comparable table | off-machine pending archive |
| Fig.3 | 高 bp F1 转化为 annotation usability | segment IoU, boundary F1, overmerge, fragmentation | todo |
| Fig.4 | zero-human 泛化与 annotation completeness/TE composition 共同解释性能下降 | hs1 anchor + species ladder + decay model | todo |
| Fig.5 | 结果不是 RM circularity 或 model-only novel overclaim | RM-free/library sensitivity + evidence tiers | todo |
| Fig.6 optional | case studies | IGV/UCSC panels for boundary/gap/overmerge/hardN | todo |

Reviewer 预案：

| 攻击点 | 防守证据 |
|---|---|
| 只是学 RepeatMasker reference | RM-free / library sensitivity；evidence tiers |
| bp F1 不代表 annotation quality | segment/boundary/overmerge 主表 |
| 传统工具比较不公平 | tool/library/reference/split/metric 合同 + local reproduction |
| human zero-human 高分只是 human 注释更好 | completeness confounding model + matched distance controls |
| model-only positives 是 false positives | U candidate 只做 evidence-supported candidate，不叫 novel TE |
| backbone novelty不够 | contribution 是 raw-genome FM annotator + label/evaluator/evidence framework |

## 11. 开放问题

| ID | 问题 | 当前候选/倾向 | 证据缺口 | 下一步如何关闭 | Owner |
|---|---|---|---|---|---|
| Q-001 | off-machine FM>RepeatModeler2 结果在哪里 | 用户确认存在，当前机器不可见 | 路径/表格/metric/protocol 未归档 | 用户提供后走 `$note-gate`/`$note-add` 归档到 docs/15 + refs | user+agent |
| Q-002 | production/matched-label protocol 具体物种 | human-rich + non-human panel | 需确认已有数据和传统工具输出 | species_manifest | agent |
| Q-003 | zero-human ladder 具体常染色体 | 每物种一条常染色体 + 第二常染色体稳定性检查 | 需按长度、TE bp、annotation provenance 选 | pipeline-blueprint / benchmark-roadmap | agent+user |
| Q-004 | primary success gate 数值 | 分 claim metrics | 需 evaluator contract 和 baseline distribution | docs/19 + docs/20 | agent |
| Q-005 | GENERanno 是否唯一 P0 FM | 当前倾向 GENERanno 4kb P0 | 需 smoke/screen 和工程可用性 | bounded Track A | agent |
| Q-006 | fungi/plants 是否进入第一主线 | 当前先 animal/human ladder；plants/fungi P1 | 数据质量和 claim 负担未定 | label QC 后决定 | user |
| Q-007 | Superfamily 阈值采用 global 还是 per-kingdom | 当前倾向 per-kingdom 主规则 + global sensitivity check | 需要 TE bp% 和 species coverage EDA | 跑 `SF-TARGET` Step 1 后用户确认 | user+agent |
| Q-008 | Universal FM 是否作为主 claim | 当前倾向 kingdom/clade-aware 强模型优先，universal 为 Enhanced | 需要 P4/P7 early model evidence | P8 前重审 | user |
| Q-009 | Cross-kingdom 是否升级为 Core | 当前为 Enhanced/sentinel | 若论文主张改为 universal cross-kingdom FM，则需升级 | P8-MATRIX 设计时裁决 | user |
| Q-010 | `2048bp` anchor 是否足够 | 当前作为 Core shared anchor；不支持者允许 `2048eq` 标记 | 需要 TE-LEN-VIZ 覆盖率与 backbone context smoke | WIN-MATRIX gate | agent |
| Q-011 | GENERANNO 整合版缺口是否全部升主线 | 已裁决：1-4 嵌入现有 gate，5-6 Enhanced/Parked | 需要落地最小合同并避免扩成全排列算力合同 | 本轮已落 docs/13/14/19；后续按结果重审 | user+agent |
| Q-012 | Superfamily 是否改成 5 类开放集 | 当前倾向 SINE/LINE/LTR/DNA + Unknown/reject；主指标只报 main4 conditional macro-F1，Unknown 单独报 reject recall/false-unknown rate | 需要确定 Unknown 的训练构成、阈值校准和是否按 bp/segment smoothing 后评估 | 下一轮 superfamily head 改 label policy 并在 docs/19 固定 metric | user+agent |
| Q-013 | fragmentation 是否需要 learned decoder | 当前 HMM 已把 segment-F1 从 raw 0.4846 提到 0.7339，但 boundary-F1 仍约 0.6181 | 需要判断剩余 gap 来自边界学习不足、标签噪声还是 postprocess 过合并/欠合并 | 在 overlap+HMM baseline 上加 boundary/start-end head、semi-Markov/CRF 或 segment proposal refiner | agent |
| Q-014 | embedding 旧高分与当前低分如何对齐 | 当前解释为 objective/metric 不同：旧 high signal 更接近 pairwise/contrastive/linear-probe；binary token fine-tune 不保 superfamily geometry | 需要 leak-free split、balanced species/class sampling、C1 baseline、A1 pretrained、B1 fine-tuned 的同一协议对照 | 写入 embedding protocol，避免把 transductive/upper-bound 当 holdout claim | agent |

## 12. 停止/推进闸门

| Gate | 通过条件 | 失败动作 |
|---|---|---|
| G0 路线与证据归档 | docs/11 作为唯一主路线；docs/23 归档；off-machine 结果有 pending/archived 状态 | 不进入 claim-bearing run |
| G1 Evaluator | docs/19 有可执行 metric/reference/split/stat test 合同，并含 species panel、sampling audit、context perturbation 和 UHC claim rules | 先写 evaluator，不跑 claim-bearing 模型 |
| G2 Label QC | P/RN/U/hardN mutually exclusive；RN/hardN 没有明显污染；human/primate leakage 检查通过 | 修 harmonization，不调模型 |
| G3 Traditional baseline | RepeatModeler2/EDTA/HiTE/RepeatMasker 结果可复现且口径清楚 | 修 baseline/provenance |
| G4 FM value | FM 在 C1 或 C2 至少一个主 claim 上超过强 baseline，且 guardrail 不恶化 | 若只赢 bp F1 不赢 usability，收窄 claim |
| G5 Zero-human | hs1 anchor + ladder 支持泛化解释，且 completeness confounding 可解释 | 若失败，降级为 production tool |
| G6 Publication | figure/table 全部有 run IDs、versions、hashes、evidence paths | 不进入 manuscript claim |

## 13. 现在该做什么

2026-06-30 更新：`PIPE-TEFM-FINAL-EBAR-20260629`、`PIPE-TEFM-FINAL-PLANTQC-20260629` 和 `PIPE-TEFM-FINAL-STRICTSEG-20260629` 已完成。当前最终候选仍然是 panel-specific，而不是单一万能模型：动物/人类迁移使用 `ntv2_250m@4096`，植物诊断使用 `ntv3_100m_pre@2048`。error-bar 结果支持这个结论：animal_fine 均值分别为 0.6431 vs 0.5300，plant_fine 均值分别为 0.1733 vs 0.3833。plant Label-A/UCSC Jaccard 均值只有 0.0784，因此植物低绝对分数必须和 label/source completeness 一起解释。strict segment 结果显示 bp-F1 不能直接等同于完整注释：IoU 0.8、boundary 5 bp 下，animal `ntv2_250m@4096` + CRF-style smoothing 的 segment-F1 为 0.2557、boundary-F1 0.0989；plant `ntv3_100m_pre@2048` + gap100/min100 的 segment-F1 为 0.0305。下一步应进入 multi-anchor selector / deployable decay formula 和最终 pipeline packaging；segment/boundary 需作为独立 usability limitation + postprocess module 报告，不应包装成已完全解决。

2026-06-30 更新 2：`PIPE-TEFM-FINAL-SELECTOR-20260630` 已把 multi-anchor 和 deployable selector 推进到 screen-complete。结果支持 panel-specific anchors：observed best-anchor-per-species mean TE-F1 为 0.7787，而当前 best broad single model (`cross_supervised_4096`, 至少 5 rows) mean TE-F1 为 0.5432。NTv2-500M species-probe 作为软注释质量审计显示 red_flour_beetle 仍是 hard failure（target fine-tune 后 TE-F1 0.1494），thale_cress 也低（0.4168），soybean/C. elegans 为 partial/caution。deployable RF selector 的 leave-species-out RMSE 仍有 0.3040，所以只能作为 triage/recommendation 工具；annotation-aware 公式可解释 label/source 影响，但不能用于新物种部署。下一步不要再扩大 selector screen，而应转向 claim-grade panel lock + tri-review，或继续短高置信 TE 片段与模型可解释性分支。

2026-06-30 更新 3：`PIPE-TEFM-FINAL-INTERPRET-20260630` 已完成短片段解释性初筛，并通过 3/3 independent tri-review。结果不支持把 binary high-score strict-background spike 直接包装成 hidden TE：9 个 high-score strict-BG 片段的 mean binary TE probability 为 0.8893，但 mean SF5 BG fraction 为 0.9974；reviewer 还指出这些片段集中在 western_honey_bee `GroupUn`，存在明显来源/低复杂度混杂。更有价值的是 Unknown annotation audit：260 个 Unknown 片段 mean best-main4 SF5 fraction 为 0.4706，说明部分 Unknown 可能有主流 superfamily-like 信号，但只能作为再审计候选，不能自动重标。当前解释性分支下一步是 matched strict-BG controls、matched human known-main4 controls、saliency/occlusion/k-mer motif enrichment；三篇参考 PDF 已存在但本地缺 PDF 文本抽取工具，方法对齐仍 pending。

2026-06-30 更新 4：解释性分支已补 matched-control / k-mer / PDF extraction screen。high-score strict-BG 的 9 个候选已在同物种同染色体 honeybee `GroupUn` 内完成匹配，质量为 `ACCEPTABLE_COMPOSITION_SCREEN`，但仍只能用于 false-positive trigger 诊断，不能用于 hidden TE prevalence。Unknown-main4-like 32 个高置信候选虽然完成了 human known-main4 匹配，但质量为 `POOR_GC_MATCH`：case mean GC 0.6638，matched control mean GC 0.3920，mean abs GC delta 0.2723；富集 k-mer 也以 GC-rich motifs 为主。因此 Unknown 分支当前应从“可能重标 main4”收窄为“高 GC/SVA-like/model-bias annotation audit”。`pypdf` 已可抽取三篇 PDF 的前 8 页，1703.01365v2 与 2009.07896v1 明确覆盖 attribution/saliency/occlusion 关键词；下一步若继续解释性 claim，应走小规模 Slurm model-level saliency/occlusion，而不是登录节点前台跑。

2026-06-30 更新 5：解释性分支已完成 bounded model-level occlusion smoke（job `9853298`，34 fragments，612 detail rows）。结果进一步收窄 claim：strict-BG 候选在 512 bp fragment context 下 binary 原始均值只有 0.0205，SF5 main4 为 0，说明早先 high-score 更像 full-window/flanking context trigger，不能说 512 bp 内有 hidden TE motif。Unknown-main4-like 片段保留强 SF5 局部敏感性（mean delta 0.3028，max 0.7285），但由于前一步 GC 对照失败，只能作为 high-GC/SVA-like/model-bias annotation audit。当前解释性分支 screen 已足够支持“不要过度声称”的结论；除非要做 figure-level 机制 claim，否则不再扩大该分支。

2026-06-30 更新 6：`PIPE-TEFM-FINAL-GENOMEDECAY-20260630` 完成了 deployable selector 的 genome-derived 补充原型和 fragment council。bounded k-mer shift to anchor prototypes 将 leave-species-out RMSE 从 0.3042 降到 0.2666，支持把 genome-wide k-mer/Mash/sourmash distance 纳入最终 anchor selector；assembly stats 单独反而恶化到 0.3441，因此 N50/genome size 只能作为弱辅助变量，不能作为当前公式主 claim。`mash`/`sourmash` 当前不可用，所以本轮仍是 screen-grade，不是 claim-grade selector。碎片化方向的 3/3 council 结论是：继续调 threshold/gap/HMM/CRF 已无主要意义，下一步应做 frozen bp model + interval refiner，其次 boundary-aware head；双链预测只做 forward/RC mean/max/consensus 的低成本 sanity check，若不能提升 strict segment/boundary 且不恶化 missed_true_rate 就停止。

2026-06-30 更新 7：`PIPE-TEFM-FINAL-FRAGSANITY-20260630` 已把双链/上限从建议推进到 bounded screen。mouse chr1 前 120 个窗口上，forward raw 的 segment-F1@IoU0.8/boundary5 为 0.3062，forward CRF 为 0.3569；最好的非 oracle 结果是 `consensus_min + crf_style_penalty4`，segment-F1 0.4149、boundary-F1 0.1267、missed_true_rate 0.0929。`max_prob`/union 风格反而更差，说明双链不能简单取 OR。truth-aware oracle fill supported true intervals 达到 segment-F1/boundary-F1 0.9711，说明 bp 模型常常已触及真 TE，主要缺的是可部署的 interval refiner 去学习保留、合并和修边界。下一步 fragment 主线应做 lightweight frozen interval refiner；若要全染色体 RC/oracle，需要先优化 prototype metric loop，full mouse chr1 job `9856510` 已因指标循环过慢而取消，不能作为 evidence。

2026-06-30 更新 8：`PIPE-TEFM-FINAL-INTERVALREFINER-20260630` 已完成 lightweight frozen-bp interval-refiner smoke。40-window mouse chr1 结果显示该 deployable 后处理原型不优于 consensus+CRF：`consensus_min_crf` segment-F1@IoU0.8/boundary5 为 0.4685，而最佳 refiner `refiner_keep_drop_gap_merge` 为 0.4667，boundary-F1 也更低。truth-aware oracle 仍达到 segment-F1/boundary-F1 0.9919，所以“可修复空间”很大，但不是当前局部特征 + keep/drop/gap-merge 后处理能解决。fragment 主线现在应从“继续调 threshold/gap/HMM/CRF 或轻量后处理”重定向为结构性组件：segment-aware decoder、boundary-aware head、richer interval proposal/refiner 或 semi-Markov/duration-aware decoder；若不做这些，文章里应把 strict interval/boundary 作为明确 limitation 和 future work。

2026-06-30 更新 9：`PIPE-TEFM-NEXT-DECAY-FRAG-20260630` 对泛化衰减公式和 trainable fragmentation component 做了下一轮 tri-review/council + bounded smoke。结论是：精确的 new-species confidence formula 仍不可用，best point selector (`baseline_plus_kmer / leave_species_out`) RMSE 0.2642、top-1 anchor accuracy 0.4545，leave-clade-out RMSE 仍约 0.40-0.42；不能用它告诉用户“这个物种上模型可信度是多少”。当前唯一可防守的 selector 形态是保守 top-2 anchor shortlist + local chromosome probe：true best/top2 覆盖 0.8636、mean regret 0.0071，但 high-confidence single-anchor coverage 为 0。碎片化方向上，冻结 bp 概率后的 trainable boundary CNN / duration prior / linear CRF 全部不如 post-hoc CRF（segment-F1@IoU0.8/boundary5 分别为 0.2778 / 0.2366 / 0.1798 vs CRF 0.4685），说明弱概率轨道 decoder 不值得扩跑。下一步如果继续做可用 annotation claim，应转为 near-backbone boundary-aware head、embedding-level/richer interval proposal scorer、或改良 emissions 后再接 trainable CRF/semi-Markov；如果继续 selector claim，则必须加入 public taxonomy 与 genome-wide MinHash/Mash/sourmash 距离，并以 leave-clade-out + abstention/top-k regret 作为硬闸。

2026-06-30 更新 10：`PIPE-TEFM-STRUCTDEC-20260630` 回答了“CRF/HMM/半马尔可夫作为 backbone 后端一起训练是否还没试”的问题：之前确实没试过，已用 seed=42 做了 bounded smoke。该实验把 HMM/CRF/semi-Markov-style loss 接在 GENERanno token logits 上进行 fine-tune，不是 post-hoc smoothing；retry job `9860193` 成功完成。结果有正信号：test segment-F1@IoU0.8/boundary5 从 CE baseline 0.3069 提升到 HMM 0.3836、CRF 0.3631、semi-Markov proxy 0.4258，boundary-F1 最高也由 0.1414 提到 0.2105。但还不能宣告解决：HMM 和 semi-Markov proxy 的 missed_true_rate 升到 0.3033；CRF 的 missed_true_rate 较好 0.1721，但 boundary-F1 只有 0.0921。当前路线应修正为：post-hoc/frozen-probability decoder 方向已失败或很弱；joint structured backend 方向保留为 promising，需要下一轮加 explicit boundary loss + true-retention/missed-true penalty，并在 mouse strict segment panel 上复测后再决定是否扩大。

2026-06-30 更新 11：`PIPE-TEFM-PURSUE-DECAY-STRUCT-20260630` 完成了用户要求的 bounded `$pursue` 迭代。泛化衰减公式不能升级为精确可信度公式，但可以升级为保守 trust router：in-panel/leave-species 使用 `baseline_plus_kmer` top-2 anchor shortlist + local chromosome probe，contains-best 0.8636、mean regret 0.0071、single-anchor high-confidence coverage 0；leave-clade/new clade 不给 confident anchor，规则是全部 abstain 并要求 local probe 或新 anchor。这满足“避免 confidently wrong”的保守路由目标，但仍不能告诉用户某新物种的精确 F1。碎片化方向上，boundary/true-retention joint training 进一步确认有结构信号，`semimarkov_retention` 把 segment-F1 从 CE 0.3069 提到 0.4439、boundary-F1 从 0.1414 提到 0.2290；但 missed_true_rate 升到 0.3525，并且 deleted CE fragments 中约一半 true-backed，因此未过 promotion gate。当前 decoder 路线不能扩大训练；若继续，只能换成更强 interval-level true-retention/segment-aware objective，否则作为 future work/limitation。

2026-06-30 更新 12：已把当前 `$pursue` 入口从旧 draft 模板改为 active milestone goal：`ACTIVE_GOAL.json` 的 `goal_id` 为 `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC`，scope 为 `milestone`，明确这是 publication-validation support，不是 terminal SOTA claim。该 pursue 的两条并行方向被限定为：1) selector 继续补 genome-wide MinHash/Mash/sourmash 或等价 k-mer distance，但输出只能是 conservative top-2/local-probe router，并且 leave-clade/new clade 默认 abstain；2) fragmentation 只能换 objective/loss 到 interval-level true-retention、fragment-survival 或 segment-aware decoder，不能继续 threshold/gap/post-hoc HMM/CRF 调参作为主路线。机器 gate 要求 selector top2 contains-best >=0.85、mean regret <=0.03、leave-clade abstention >=0.95；decoder 必须同时提升 segment-F1 和 boundary-F1，且 missed_true_rate 相对 CE 不得超过 +0.03。若 selector 连续两轮仍只能 triage、或 decoder 连续两轮不能通过 true-retention gate，则停止对应方向并写成 limitation/future work。

2026-06-30 更新 13：`TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC` 已完成闭合。Selector 方向加入 deterministic bottom-k MinHash-equivalent genome distance 后，leave-clade diagnostics 有改善但仍不能形成 deployable point formula；最终对外只保留 conservative trust router：known/in-panel top-2 shortlist + local chromosome probe，leave-clade/new-clade abstain。Decoder 方向完成 final retention-constrained screen：工程成功并可在 24GB 3090 上运行，但方法失败，segment-F1/boundary-F1 低于 CE，deleted_true_backed_fraction 仍高于 0.15。3/3 tri-review 与 pivot 已决定 abandon structured decoder fragmentation objective route，并在 `docs/09_decisions_log.md` 记录 `DEC-001`，后续不再重复 survival/retention/threshold/gap/HMM-CRF tweak。

2026-07-01 更新：用户追问 threshold 是否过严、短片段是否不应被 HMM/CRF 固有地剔除后，已执行 `PIPE-TEFM-CAP-POSTPROC-20260701` 作为诊断补充。结果支持“展示多阈值 tradeoff curve”而不是“选一个最优阈值”：human strict-safe best 为 `raw_t0.20`，segment-F1/boundary-F1 `0.2422`/`0.1143`；mouse strict-safe best 为 `gap25_min40_t0.50`，`0.4589`/`0.1575`，deleted_true_backed_fraction `0.1042`。但最佳 observed HMM/length-adaptive 行普遍删除太多 true-backed fragments，human 最强 length-adaptive 行 deleted_true_backed_fraction `0.8583`。review-board 和 council 均裁决这只能作为 sensitivity/comparator evidence，不重启 post-hoc threshold/gap/HMM/CRF 路线。文章中可把该结果用于说明：TE 本身和 UCSC/RepeatMasker 注释都存在真实碎片化，简单“减少碎片数”会误删真实片段；完整 interval reconstruction 仍是 limitation/future work。

2026-06-19 更新：`PIPE-TEFM-REPAIR-20260618` 与本轮 reframe/council 复核后，当前路线不应被 A2 stress mean 或 `Other` F1=0 否定。混合动物模型在 close/training-domain animals 上是强的，失败集中在远缘/标签风险 stress species；embedding 旧高分与当前低分的主要差别是 objective 和评估协议；fragmentation 已由 HMM 大幅改善但 boundary 仍是主要 gap；superfamily 不应强迫 heterogeneous `Other` 成为一个生物一致类别。下一步应先修 comparability contract，然后生成非 claim Track B validation：主评估用 GENERanno 4096 + `invert_boost_animal_4096` + overlap/HMM；superfamily 改为 main4 + Unknown/reject；embedding 做 leak-free C1/A1/contrastive 对照。

2026-06-19 更新 2：`PIPE-TEFM-LOCK-20260619` 已完成上述非 claim validation screen。当前 publication-facing 口径应固定为：primary panel 与 stress panel 预注册分开，绝不混成一个 headline mean；stress panel 必须同时报告 Label-A/B concordance、TE coverage/library completeness、以及少量 target/species-specific fine-tune 是否恢复性能。结果支持该口径：lizard、X. laevis、honeybee 在同一 stress split 上经少量物种内微调恢复到 TE-F1 0.858-0.952，说明主要是 domain/label shift；red flour beetle 仍然 0.071，作为 hard stress failure/label-library risk。Superfamily 主线采用 main4+Unknown/reject，且优先 base-pretrained 初始化；fragmentation 主线保留 overlap/HMM，但下一步需要 boundary/segment proposal，因为 multi-species primary screen 的 HMM segment-F1 仍只有 0.5516。

2026-06-20 更新：按用户新增补充实验要求，进入 `PIPE-TEFM-EXTEND-20260620`。本轮只做单 seed=42、GENERanno 4096bp 的补充 screen：1) embedding 改成 family-level、dynamic internal/boundary fragments，并预留 consensus/genomic internal/genomic boundary source 对照；2) SF5 复核 base-pretrained 初始化；3) 把 `invert_boost_animal_4096` 迁移到 PlantTE fine-tune/eval 物种，并与植物 PU 微调、cross-kingdom PU 对照；4) 训练 stress clade anchors 评估 beetle/honeybee/lizard/X. laevis；5) 增强 decay formula；6) 测 PU + U-penalty/TV smoothing 是否缓解 U 区过报和碎片化。Council 裁决为可并行执行，但必须分支报告、不许把 screen 结果包装成正式 claim。

2026-06-21 更新：`PIPE-TEFM-EXTEND-20260620` 已完成并归档。结果支持继续 GENERanno 4096 + `invert_boost_animal_4096`，因为它比 plant/cross PU 更稳，且对 teosinte、maize、rice、sorghum 等植物有可用表现；但 PlantTE 与 stress panel 仍需用 label concordance/completeness 解释。PU/positive-only 的主要问题是高召回低精度过报，HMM/CRF smoothing 能减少碎片但不能替代可靠负例。Embedding family-level 结果仍要求把 C1 作为强 baseline；Dfam consensus source 缺失，不能 claim consensus-vs-genomic 差异。下一步回到 claim-prep：修 `docs/19`、ACTIVE_GOAL/docs20 或显式 waive，锁 primary/stress panel、RN/hardN 策略和 Dfam consensus 输入，再做 claim-grade Track B validation。

2026-06-21 更新 2：`PIPE-TEFM-CALIB-20260621` 已完成并归档，补齐了用户指出的关键缺口。标准监督 plant/cross 微调不能再和 PU 混为一谈：`cross_supervised_4096` 的 plant-fine mean TE-F1 为 0.8568，广义均值为 0.5786；PU/positive-only 继续降级为 negative ablation / future gated repair。当前不应选一个混合均值作为唯一结论：`cross_supervised_4096` 是 plant/cross calibration 的强分支，`invert_boost_animal_4096` 仍是 animal/vertebrate 和 stress reference 分支，二者应进入锁定面板后的 Track B 候选。`insect_no_beetle_4096` 只支持 honeybee 可校准（TE-F1 0.7983），不能拯救 beetle（0.0059）。Dfam consensus embedding 已补齐，但 C1 仍显著强于 A1，不能 claim FM embedding superiority。泛化衰减公式只有加入 label/source/TE composition/train-clade/stress 等变量才有解释力，distance-only 不可作为主公式。

2026-06-21 更新 3：`PIPE-TEFM-ANCHOR-20260621` 已完成并归档。结果支持把对外推荐从“单一万能模型”改为“kingdom/panel-specific anchors + deployable anchor selector under evaluation”，但 selector 仍不能作为稳定部署 claim。`insect_primary_4096` 显著恢复 honeybee（TE-F1 0.9465），但 beetle 仍近零，说明 insect panel 应排除 beetle 并把它作为 label/library/domain audit。Unknown 注释中有明显 main4-like 信号，可作为 annotation-audit/candidate relabel 入口；严格 high-score unannotated 候选则几乎全被 SF5 判为 BG，不能主张 hidden TE discovery。BG-inclusive embedding 仍由 C1 basic+kmer contrastive 胜出，FM embedding superiority 不成立。下一步应进入 panel-specific Track B planning：动物/脊椎、植物/跨界、insect-primary 分开报告，并把 deployable 公式作为粗筛工具而非主 claim。

2026-06-18 更新：`PIPE-TEFM-SEG-SF-20260618` 已完成。该 screen 固定了下一步工程默认值：GENERanno 4096 bp、overlap center-merge、HMM/small-gap smoothing 作为 interval postprocess 候选；superfamily head 也优先 4096。embedding clustering 结果显示 C1（基础序列特征 + contrastive projection）是必须纳入的强 baseline，当前 GENERanno embedding variants 不能直接作为 representation claim。下一步不要继续扩大模型 zoo，应把这些结果写进 `docs/19_evaluator_contract.md` 和后续 claim-bearing segment/superfamily evaluation 的 pipeline contract。

我们刚确定：主线不是“RM 后处理 refinement tool”，而是 raw-genome FM TE annotator；refinement 和 circularity 是让这个 claim 站得住的防守层。`$council` 进一步确认，训练前还必须把 TE 长度、superfamily 目标集、window/context 和 P8 transfer matrix 钉成 phase gates；二次 council 又确认 GENERANNO 整合版缺口只按“嵌入现有 gate”的方式落盘：species panel 与 sampling batch 进入数据合同，context-trap 进入 claim 前防守，UHC evidence card 进入 C5 护栏，family embedding/CLI release 不提前升主线。现在的问题是证据还没闭环：off-machine FM>RepeatModeler2 结果还没归档，species/chromosome ladder 也没锁。若直接跑 claim-bearing 模型，之后很可能因为 metric/reference/split/window/label space 不清楚而无法 claim。下一步应先执行 P2/P3 gate：TE-LEN-VIZ、SF-TARGET Step 1、LABEL-CONCORDANCE、U-QUALITY 和 CHROM-LADDER。

**下一步触发条件**:

1. off-machine FM>RepeatModeler2 结果至少记录为 pending evidence，最好归档到 `refs/dossiers/` 或 `docs/15`。
2. `docs/19_evaluator_contract.md` v0.1 写清 C1-C5 指标、rare class 处理、kingdom-masked macro-F1、species panel、sampling audit、context-trap diagnostic 和 UHC evidence tier。
3. species/chromosome manifest 草案完成。
4. `TE-LEN-VIZ`、`SF-TARGET` Step 1、`LABEL-CONCORDANCE`、`U-QUALITY` 产出第一版报告。

**恢复指令**:

新会话先读本文件，然后按任务读 `docs/13_pipeline_blueprint.md`、`docs/14_validation_matrix.md`、`docs/19_evaluator_contract.md`、`docs/20_baseline_reproduction.md`、`docs/15_evidence_register.md`。不要从 `docs/23` 继续主线，它已经是旧英文参考。
- **2026-08-12 curated-source result**: Job `11527999` completed the independently reviewed Dfam 3.9 curated EMBL audit. It uniquely resolved 50/279 identifiers, left 2 ambiguous and 227 missing while conserving all 6,432,583 occurrences. Three-way review accepts a valid-negative and closes curated-only recovery. The sole next action is one separately reviewed all-family raw-DR support-only CPU audit; all homology/DATA/GPU/S1 gates remain closed, and raw support cannot overwrite direct labels or curated identities.
- **2026-08-12 final S0 identity decision**: Grammar-repair Job `11528267` closed the official Dfam 3.9 relation search. The final result remains 50 unique / 2 ambiguous / 227 missing, with zero raw-DR support and 73.229% occurrence mass unresolved. Three reviewers accept a final valid-negative and close the current annotation-dataset S0 route. The user has approved continued direct-superfamily-first work, including a new annotation-time accession-preserving benchmark version. Authorization is deliberately narrow: CPU accession-retention/concordance preflight only. Until those and subsequent CPU leakage gates pass, homology, full DATA, GPU S0 and S1 remain prohibited.
