# Active Goal

> /research-interview 写到这里。此后整个工作流的"研究意图源头"——/research-synthesize 和后续 skill 都会回读。

## current_route_2026-09-01_gap_bridge_data_only

- Gate L 因缺少可执行的独立 TE-locus 专家投入而退役，状态为
  `RETIRED_UNEXECUTED_RESOURCE_INFEASIBLE`；它没有 PASS，也不是生物学
  NO-GO。
- 当前目标改为 **comparator-consistent repeat-mask continuity**：冻结
  P3-R1，只判断 prediction-defined internal gap 中哪些 bases 可以在高
  added-bp precision 下加入第二层 softmask。不声称恢复 biological
  insertion、nested topology 或 ancestral boundary。
- 唯一下一步是
  `docs/experiments/GAP-BRIDGE-DATA-ONLY-RESTART-20260901.md` 中冻结的
  `GAP-BRIDGE-PHASE0-R1`：先做 chr17 bit-exact logit-export engineering
  regression 和 chr3/chr5 各 50 Mb 的双染色体 preflight，再用完整 chr3/5
  train、完整 chr13 validation、完整 chr19 one-use test 做 feature-only
  discriminability screen；chr20-22 保留。
- 历史 FRAGGRAPH 已证明旧 CE + 小样本 learned linker 无效，因此本轮是
  一次 re-entry falsification。Phase 0 FAIL 时关闭新 neural gap model 和
  continual learning；library-free sequence signal 在 chr19 与
  homology-purged challenge 上成立时，至多允许一个后续小 CNN 比较；持续
  学习还必须等 chr20-22 复现和 unchanged Mouse direction-of-effect 后才能
  重新提案。
- Mouse 仅在人类 gate 后做一次 unchanged transfer；Fly 不进入这条
  comparator-continuity 路线的常规开发。
- E0 已工程 PASS：chr17 identity job `12126691` 精确一致，chr3/chr5
  各 50 Mb 均完成 6,104 windows、四状态/P_TE/canonical export 和三类
  comparator candidate census。BeeGFS exit-120 失败按真实工程失败保留，
  不进入科学分母。按实测吞吐量，完整 chr3/5/13/19 约需 35.5 GPU-hours，
  超出当前 cohort 的 24 GPU-hour 上限，因此 full Phase 0 状态为
  `PENDING_RESOURCE_REBASE`；当前仍无新科学结果。

## last_result_summary
- exp_id: FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1
- date: 2026-08-12 CEST
- track: F Rice T1 positive-only consensus-collinearity information-sufficiency audit
- primary_metric: information_sufficiency_gate_pass=0; terminal=`VALID_NEGATIVE_INFORMATION_INSUFFICIENT`
- SOTA: n/a; CPU audit, claim-ineligible
- gap: candidate exact-group recovery `0.1389` versus best positive-only comparator `0.3717`; paired bootstrap candidate-minus-comparator mean `-0.2322` with 95% interval `[-0.2801,-0.1734]`
- semantic_success: pass as a route-local valid negative; Job `11531090` completed `0:0` and all audited manifests verify. The old ACTIVE_GOAL validator returns `failed_run` only because it expects obsolete selector metrics; that stop signal is retained without changing the route-local verdict.
- tri_review_status: completed, `2/3 DEGRADED_REVIEW`; Claude and Codex both chose `abandon-route`, Antigravity failed three CLI retries
- pivot_status: completed: abandon the standalone consensus-collinearity parent assembler; preserve broader fragmentation only under DEC-004 re-entry criteria
- recommended_next: no F compute. Continue only the separately reviewed S leaf exact-access probe; do not tune thresholds, add Fly/H0, or reopen DEC-001/002/004 cousins

## 当前研究方向
<一句话>

## 任务边界
- 输入:
- 输出:
- 算这个任务:
- 不算这个任务:
- 应用场景:

## 候选数据集
- 

## 评估指标
- Primary 候选:
- Secondary 候选:

## 既有 SOTA(用户感知,待 /sota-inventory 验证)
- 

## 差异化假设
- 用户觉得现有 SOTA 的薄弱点:
- 我们打算如何不同:

## 资源约束
- GPU 量级:
- 时间预算:
- 风险偏好:

## Handoff to /research-synthesize

- 用户的核心 motivation:
- 隐含假设(用户没明说但贯穿对话的):
- 期望 deep research 回答的问题:
  1. 
  2. 
  3. 
- 用户**不**关心的方向(防止 synthesize 跑偏):

## direction_clarified_2026-08-11_tefm_new_directions_pilots

- 想法最强形态（Phase 1 steelman，已由用户 handoff 确认）：不是把旧 Pro 包搬到 Unige，而是从现有远端资产和官方 source identity 独立重建一组可证伪、claim-ineligible 的 bounded pilots；每条路线先证明合同、数据和 runtime 身份，再让负结果真正具有排除价值。
- 共创浮现的更有趣角度：
  - 五工具 benchmark 的第一贡献是“可复现 denominator + adapter”，不是提前制造一个排名。
  - fragmentation 只有在 immutable leaves + typed parent joins 下才是 DEC-001/002 之外的新机制；简单减少碎片数本身不是成功。
  - superfamily 的合理输出是 deepest-supported ontology node 或 abstain；Unknown 不是一个生物一致的普通 superfamily。
  - transfer 与 embedding 必须先通过 provenance/binding kill-gate，缺资产本身就是可复现的 foundational result。
- 核心架构赌注：F 用 preservation-constrained parent interval lattice 替代删片段式 postprocess；S 用 hierarchical prototypes/calibration + abstention 替代 flat closed-set leaf prediction。
- 已钉死的技术决策（均由 `UNIGE_DIRECT_PILOTS_PROTOCOL_20260811.md` 明确授权，证据评分 5/5）：
  - 顺序固定为 Stage-A repair → B five-workflow smoke → F/S；G/E 仅在资产 gate 通过时运行。
  - 每 job ≤12h、cohort 新增 GPU 总量 ≤24 GPU-hours、CPU smoke 为 0 GPU、最大并行方向 3。
  - smoke/screen 永不 claim；失败、typed block 和 negative result 均保留。
  - B 冻结 RM2 2.0.9/RM 4.2.4、EDTA 2.3.0、Earl Grey 7.3.0；HiTE 3.3.3/TEtrimmer 1.7.4 必须先形成 exact runtime identity，禁止结果后换版本。
  - F 原始阳性 leaves 不可删除；S 的 family/homology split、threshold calibration、clade holdout 在 test 前冻结。
- 仍开放、需实证的问题：
  - F 的现有 truth 主要是 T1/T2 partial truth，能否支持 per-genome false-fusion 与 nested audit；不能时不得报 whole-genome T0 precision。
  - S snapshot 是否能从现有 family identifiers 构造无泄漏 homology components；不能时 route typed-block。
  - HiTE exact SIF、Earl Grey Dfam 4.0 partitions、TEtrimmer 1.7.4 source-overlay 是否能完成完全离线最小启动。
  - G 五个 anchor 缺 run provenance；E 缺 2,200 fragment family/copy/species/component bindings 与 frozen weights。
- 被劝退/降级的子方向：万能 transfer 标量公式、UMAP-only embedding 结论、阈值/gap/HMM/CRF postprocess 重跑、把 TEtrimmer 1.7.2 冒充 1.7.4、把 MCHelper 静默加进 denominator。
- 最强反方论证：F 可能只在 partial truth 上把宽松 join 误当 recovery，S 可能靠 abstention 隐藏错误；因此 false fusion、nested preservation、risk-coverage、unknown recall、false-unknown 和 minimum usable coverage 都是硬 stop rules。若资产身份/分组不闭合，应停为 typed block，而不是用便利输入制造正结果。

## reframe_2026-08-12_accession_preserving_s0

- 用户已明确要求继续推进 direct-superfamily-first：先验证直接 superfamily 注释是否达到预注册门槛，只有通过后才研究错误分类或 hierarchical/open-set S1。
- Job `11528267` 已穷尽并关闭 Dfam 3.9 post-hoc exact-name / curated alias / all-family relation 恢复路线。该结果只否定“从旧 annotation identifier 事后补 accession”的可行性，不否定 direct-superfamily 科学问题。
- 新主张不是覆盖旧 benchmark，而是建立一个明确版本化的 annotation-time accession-preserving benchmark：用冻结的官方 Dfam release、RepeatMasker、species/genome inputs 和命令重新生成 Label-A；每个 P-state hit 必须原生保留 `accession.version`、official consensus SHA256 和 RepeatMasker raw class。
- 标签与 split 严格解耦：`BG/SINE/LINE/LTR/DNA/Unknown` 只由 raw RepeatMasker class 决定；official consensus 只构造 label-blind homology component，绝不改写标签。U/ignore 与 `X13_LINE` audit-only 合同保持不变。
- 先做 CPU-only 6-family accession-retention round-trip smoke；它只验证工具链，不能代表物种或旧 benchmark。通过后再做冻结真实窗口的 representative concordance gate，并最终完整对账旧 6,432,583 occurrence mass。不得缩分母、只取 resolved 50、使用 current API、prefix/casefold/fuzzy alias、copy-derived consensus 或 majority relabeling。
- 在 identity uniqueness、concordance、homology zero-overlap、CPU DATA gate 全部通过前，GPU direct S0、S1 及新机制训练均禁止。现有 `ACTIVE_GOAL.json` 仍是旧 selector/decoder milestone，本次不静默改写其数值；CPU preflight 使用 route-local 合同，GPU 前另走人闸 goal revision/comparability review。

### 2026-08-12 leaf exact-access failed-run checkpoint

- Job `11533175` 在 exact 1CPU/4GiB/10m/0GPU allocation 上通过机器 gate 和 23/23 tests，但在唯一内存 72-call probe 返回后的 read-mode cleanup 阶段错误调用写 finalizer，因 `FamDBLeaf.added` 不存在而失败。
- 72 个观察未落盘，故 exact-access 科学结论仍未知；不得从调用位置推断 PASS 或 typed block。
- one-shot 授权已消耗。当前必须完成 result-log→tri-review→pivot；在该链明确重开前，不得修复重提，也不得进入 RepeatMasker、representative/full DATA、homology、GPU direct S0 或 S1。
- Post-result chain 已闭合为 `2/3 DEGRADED_REVIEW`；两位有效 reviewer 一致允许一个新的 close-only lifecycle component replacement。科学 72-call probe不可改变，fresh review 后至多一次最终 CPU attempt；任何再次失败或 typed block 永久关闭路线。

## reframe_2026-06-18

- 新阶段序列：从“backbone/window 粗筛”收束为“GENERanno 2048/4096 注释可用性证据包”。
- TRANSFER：`PIPE-TEFM-SUPP-20260617` 的 GENERanno 2048/4096 权重、edge-effect 发现、H0 split、UCSC strict-TE label source。
- PARK：NTv2 paired follow-up、NTv3/Evo2 adapter 修复、universal cross-kingdom animal/plant claim。
- 本轮实验：`PIPE-TEFM-SEG-SF-20260618`，包含 overlap center-merge、segment/boundary/fragmentation、postprocess smoothing、superfamily head、pretrained/fine-tuned embedding clustering。

## council_2026-06-18

- 辩题：固定 `GENERanno` + 2048/4096 后，下一步是否应优先做 overlap/segment/fragmentation/superfamily/embedding 证据包。
- 已夯实：该路线直接检验 bp-F1 是否能转化为可用 TE interval 注释，并验证 edge degradation 是否能由 overlap center-merge 缓解。
- 原始 blockers：contrastive holdout 标签泄漏、segment smoothing 跨染色体、stride 覆盖坐标不一致、array sbatch 易误跑、conda fallback 到 base。
- 用户裁决/执行：blockers 已在代码审查后修复；本轮以 screen 运行，阈值固定 0.5 和顺序截断作为 warning，不作为 claim。

## reframe_council_2026-06-19

- 辩题：`PIPE-TEFM-REPAIR-20260618` 后，是否应把下一阶段收束为 `GENERanno 4096 + invert_boost_animal_4096`，并把 close/training-domain animals 与 stress/label-source species 分层评估。
- Quorum：3/3 subagent council。Proponent 支持收束；Opponent 反对把 screen 候选包装成 claim，并警告事后选择 panel；Referee 给出有条件支持，限定为 non-claim comparability-lock validation。
- 已夯实：
  - A2 mixed-animal low mean 不是全动物失败；`invert_boost_animal_4096` 的 B-panel mean TE-F1 为 0.9351，A1 close vertebrate mean 为 0.8985，A2 mean 0.5750 主要由 honeybee/beetle 和远缘 stress species 拖低。
  - embedding 旧高分和当前低分主要来自 objective/metric/protocol 差异：C1/A1 在 pairwise/linear-probe/holdout diagnostics 下强，B1 binary token fine-tuned embedding 不适合作为 superfamily clustering 表征。
  - fragmentation 已被 overlap/HMM 大幅改善，但 boundary-F1 仍约 0.62，下一步 learned decoder 必须超过 HMM，并报告 overmerge/cross-family bridge。
  - `Other` 不是生物一致类别；superfamily 下一步应采用 SINE/LINE/LTR/DNA + Unknown/reject，并把 Unknown 作为拒识/开放集指标，而不是等权 primary macro-F1。
- 仍争议：
  - close/training-domain panel 必须预注册，不能事后只报成功集合。
  - honeybee/beetle/X. laevis 等低分要通过 Label-A/B concordance、completeness、U/RN contamination audit 判断是标签源问题还是模型泛化边界。
  - 当前仍是 screen-only；ACTIVE_GOAL、docs/19、docs/20 未 claim-ready。
- 主裁决：收束“下一轮验证路线”，不收束“论文 claim”。下一步先冻结 comparability contract，再做 non-claim Track B validation。

## reframe_council_2026-06-20

- 辩题：是否现在执行 `PIPE-TEFM-EXTEND-20260620` 这一批补充实验，而不是先收窄到单个子问题。
- Quorum：degraded council。Claude/Antigravity 正常返回，Codex reviewer 的只读 shell 受 `bwrap: Creating new namespace failed: No space left on device` 影响无法读盘，但仍基于传入 context 给出 Opponent 立场；因此本轮为 `DEGRADED_QUORUM`，只能作为 screen-level 决策依据。
- 已夯实：
  - 本批次不是无界探索，而是回应前序具体缺口：family-level embedding 需要动态片段与 source 对照；SF5 需要 base-pretrained 初始化；动物强模型尚需植物迁移测试；植物/cross-kingdom 需要不把 unannotated background 当可靠负例的 PU 训练；stress species 需要更近 clade anchor。
  - 批次可并行执行，但必须保持分支隔离、单 seed、screen-only、不写成 SOTA/claim。
  - PU/plant/cross-kingdom 的 evaluator 语义必须明确：U 区不能当作可靠 negative，报告时应把 positive-only/PU 训练和 strict comparator eval 分开解释。
- 主要风险：
  - 假设轴多，若只看 aggregate mean 会无法归因。
  - Plant PU 和 cross-kingdom PU 可能把 label incompleteness 误读为模型泛化失败或成功。
  - Dfam consensus 路径当前未固定，consensus embedding 只能标记为 skipped/pending，不能影响结论。
- 主裁决：执行 `PIPE-TEFM-EXTEND-20260620`，但它是 bounded publication-validation screen。结果必须按分支报告：embedding geometry、SF5 main4+Unknown、animal-to-plant transfer、plant PU、cross-kingdom PU、stress anchors、decay formula 和 PU/smoothing，不允许混成一个 headline 指标。

## result_synthesis_2026-06-21

- `PIPE-TEFM-EXTEND-20260620` 已完成，语义成功；最终报告在 `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/FINAL_REPORT.md`。
- TRANSFER：继续采用 GENERanno 4096 + `invert_boost_animal_4096` + overlap/HMM 作为 claim-facing 主线；base-pretrained SF5 作为 main4+Unknown 路线；C1 作为 embedding 必须对照。
- PARK：plant/cross-kingdom PU 作为 negative ablation / future PU-methodology，不进入主模型；stress anchor 只作诊断；strict embedding 不支持模型 embedding superiority claim。
- CAVEAT：Dfam consensus embedding 分支因缺本地 configured consensus FASTA 未完成；外部 tri-review/council quorum 不足，本轮只能作为 screen/advisory evidence。

## council_2026-06-21_anchor_selector

- 辩题：对外推荐是否应采用 kingdom/panel 分层 + deployable anchor selector，而不是单一万能 TE-FM；Unknown/high-score unannotated 候选是否可用 SF5/main4 + embedding 作为可解释 TE candidate audit。
- Quorum：3/3 subagent council。Proponent 支持分层 anchor selector；Opponent 支持工程分层但反对现在包装成稳定可部署主张；Referee 要求 selector vs best-single/oracle、deployable-only vs annotation-aware 公式、Unknown/high-score 多证据审计分开报告。
- 已夯实：
  - 当前证据支持 panel-specific reporting：`cross_supervised_4096` 更适合 plant/cross calibration，`invert_boost_animal_4096` 更适合 animal/vertebrate，`insect_no_beetle_4096` 只支持 honeybee 可校准而不能拯救 beetle。
  - deployable anchor selector 可以作为下一步证据目标，但不能偷用目标物种 TE 注释才能得到的变量；annotation-aware 公式只能作为解释模型。
  - Unknown 是 strict open-set/ambiguous bucket，不是普通闭集类；Unknown/high-score unannotated 只能称为 candidate audit，需 SF5 main4 posterior、embedding/C1-kmer baseline、一致外部 evidence 支持后才能升级。
- 仍争议：
  - selector 是否真优于 best single branch，必须由 `PIPE-TEFM-ANCHOR-20260621` 的 held-out species/panel 结果判定。
  - 如果 BG+main4 embedding 仍由 C1/kmer 明显胜出，则 embedding 分支只能支持 label/source audit，不能支持 FM representation superiority。
  - beetle 不应进入 headline success mean；应继续作为 source/library/domain failure stress case。
- 主裁决：执行 `PIPE-TEFM-ANCHOR-20260621`，但它是 screen-only reframe evidence。对外措辞暂定为“kingdom/panel-specific anchors with a deployable selector under evaluation”，而不是“universal model”或“novel TE finder”。

## result_synthesis_2026-06-22_anchor_selector

- `PIPE-TEFM-ANCHOR-20260621` 已完成，语义成功；最终报告在 `reports/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/FINAL_REPORT.md`。
- TRANSFER：采用 panel/kingdom-specific anchor recommendation 作为下一步 Track B 设计框架。动物/脊椎保留 `invert_boost_animal_4096`，植物/跨界保留 `cross_supervised_4096` 或 plant-supervised 候选，honeybee-like insect 保留 `insect_primary_4096`。
- PARK：deployable selector 只作为 screen/triage 工具，等待 locked held-out panel 验证；Unknown/high-score unannotated 只进入 annotation-audit queue，不作为自动重标或 novel TE discovery。
- ABSTAIN_FROM_CLAIM：BG-inclusive embedding 仍由 C1 basic+kmer contrastive 胜出，不能 claim FM embedding superiority；beetle 仍为 hard stress/label-library/domain failure，不能进入 headline success mean。
- CAVEAT：实验后 tri-review/pivot 为 degraded host/council synthesis，不能替代 claim 前独立审查。

## council_2026-06-30_decay_fragment_next

- 辩题：下一轮是否应把泛化衰减公式升级为可用的 genome-derived trust selector，并把碎片化从 post-hoc HMM/CRF 平滑替换为 trainable boundary/interval decoder。
- Quorum：3/3 tri-review + 3/3 council round 1/2。
- 已夯实：
  - 当前 selector 点估计不可用：best deployable point row `baseline_plus_kmer / leave_species_out` RMSE `0.2642`，anchor top-1 `0.4545`，top-2 `0.6818`，leave-clade-out RMSE 约 `0.40-0.42`。
  - 当前可用雏形是保守 action policy：top-2 anchor shortlist + local chromosome probe warning，在已评估物种上 true-best/top2 覆盖率 `0.8636`，mean regret `0.0071`，但 single-anchor 高置信覆盖为 `0.0`。
  - frozen-logit trainable decoder smoke 没有超过 post-hoc CRF：`consensus_min_crf_posthoc` segment-F1 `0.4685`，trainable boundary CNN `0.2778`，trainable linear CRF `0.1798`，duration prior `0.2366`。
- 用户裁决落实：不再把 post-hoc HMM/CRF 视为结构性解决方案；下一步若继续 fragment claim，必须做更接近 backbone embedding 的 boundary-aware head / richer interval proposal-scorer / trainable CRF with better emissions，并保持 missed_true_rate、pred_true_backed_rate、short_true_backed_rate、true-backed deletion 审计。
- 最强反方论证：selector 的 genome-derived signal 可能受 22 species panel 稀疏性限制，leave-clade-out 很差；decoder 的弱原型失败说明不能简单在 probability tracks 后面接小模型，复杂结构也可能拟合注释碎片化偏差。因此下一步必须是 MVP + 严格审计，而不是全量大工程。

## council_2026-07-01_postprocess_fragmentation

- 辩题：阈值是否设得太严、是否应展示多个阈值，并尝试短片段保留 + 长片段 HMM/gap smoothing 或传统 postprocess 方案来缓解 TE fragmentation。
- Quorum：review-board 3/3；council 3/3，两轮均有效。
- 已执行：`PIPE-TEFM-CAP-POSTPROC-20260701` 用 seed `42` 在小 human/mouse panel 上跑 raw threshold、gap/min-length、HMM-style smoothing、short-fragment rescue、length-adaptive short-raw/long-HMM。
- 已夯实：
  - 阈值确实影响 strict interval metrics；human 在严格保留 guardrail 下从 `raw_t0.50` 改到 `raw_t0.20` 可把 segment-F1/boundary-F1 从 `0.1542`/`0.0763` 提到 `0.2422`/`0.1143`。
  - mouse 上有一个 panel-specific guarded heuristic：`gap25_min40_t0.50` 达到 segment-F1 `0.4589`、boundary-F1 `0.1575`、deleted_true_backed_fraction `0.1042`。
  - 但是 HMM/length-adaptive 的最佳观察行大多通过删除真实支持片段获得表面改善；human 最佳 length-adaptive 行 deleted_true_backed_fraction 达 `0.8583`。
- 主裁决：这轮结果只作为 threshold sensitivity / tradeoff audit 和传统后处理 comparator，不作为“最优阈值”或“已解决碎片化”的方法 claim。后续文章可展示多阈值 Pareto 曲线，并明确完整 interval reconstruction 仍需要更强全局 interval/set prediction 或 annotation audit。

## reframe_council_2026-06-23_final_pipeline

- 辩题：主线已基本完成后，是否执行最终补充 pipeline：NTv2/NTv3 model-size × window matrix、三重复 error bar、species-specific recovery audit、多 anchor 选择器、deployable decay formula、严格 fragmentation/HMM/CRF 诊断和短高置信 TE 可解释性。
- Quorum：3/3 council。Claude 支持分阶段执行；Codex 反对“盲目全矩阵前置”，要求 sentinel/adaptive gating；Antigravity 支持三阶递进，并强调 NTv2-500M 单 probe 不能作为物种剔除的唯一证据。
- 主裁决：采用 adaptive staged pipeline，而不是一次性全量 waterfall。第一阶段锁定 metric/adapter/smoke/prep/strict-segment；第二阶段运行代表性/完整矩阵和 species recovery audit；第三阶段才进入三重复、multi-anchor、selector 和 decay formula claim-facing 汇总。
- 已夯实：
  - 新增模型大小矩阵必须先下载/smoke，NTv3 adapter 或 remote-code 失败只能标记为 runtime blocker，不能解释为模型性能差。
  - species-specific NTv2-500M recovery 只是 soft label/source audit；若 F1 不能改善，先标记 `label-suspect/domain-hard/anchor-mismatch`，不得自动删除物种。强剔除需替代最强模型/窗口复验并结合 Label-A/B concordance 或 de novo evidence。
  - fragmentation claim 必须从旧 `IoU=0.5, boundary=100bp` 升级为多阈值：IoU 0.5/0.7/0.8/0.9 与 boundary 5/10/25/50/100bp，并报告短 fragment 是否被真实 TE 支撑。
  - multi-anchor/selector 骨架可与矩阵并行搭建，但不能在矩阵和三重复完成前写成最终推荐。
- 本轮执行对象：`PIPE-TEFM-FINAL-20260623`，profile=`screen/validation`，seed=42。第一批仅提交 download/prep/smoke/strict-segment；训练/eval array 需通过 code-review gate 与 smoke 后再提交。
# Latest bounded-cohort result (2026-08-12)

Direct-superfamily S0 remains blocked before data construction. Sharded partition-3 recovery Job `11526687` failed safely before scanning because `st_dev` differed across login/compute mount namespaces while stable source fields matched. Result/validate/2-of-3 tri-review/pivot are closed. The only next action is a narrow source-identity guard repair plus fresh review; GPU S0 and S1 remain unauthorized.

## 2026-08-12 bounded S component update

Job `11534847` closed the Dfam 3.9 read-lifecycle component: six frozen accessions were resolved exact-once across 12 leaf partitions with 72/72 calls, and 12/12 unique HDF5 handles were explicitly closed after immutable observation staging. This is a component PASS, not a direct-superfamily model or dataset result. RepeatMasker/annotation, representative/full catalog, homology split, DATA, GPU direct S0 and hierarchical S1 remain unauthorized pending tri-review/pivot and a separately reviewed next component.
