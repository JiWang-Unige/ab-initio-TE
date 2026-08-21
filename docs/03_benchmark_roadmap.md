# Benchmark + Roadmap

> 由 `$benchmark-roadmap` 维护。2026-08-11 additive cohort patch：`TEFM-NEW-DIRECTIONS-PILOTS-20260811`。
> 本合同只授权 bounded smoke/screen；任何结果均不具备 claim 资格。

## 1. Target task

- Input: 已冻结的五工具候选、Dfam/ontology snapshot、历史 predictions/truth 和带 provenance 的现有代码资产。
- Output: B 五工具身份/最小输入/adapter 矩阵；F 不删除 leaf 的 parent lattice；S hierarchical open-set；G/E 通过资产闸后才运行，否则 typed block。
- Evaluation setting: deterministic tiny smoke 或 frozen screen subset；数据单位、split key、truth tier、版本和 hash 在看结果前冻结。
- Explicitly out of scope: full/scale、多日训练、部署、数据库迁移、结果后换版本、MCHelper denominator、论文或 SOTA claim。

## 2. Metrics

### Primary metric

- Name: `route_primary_metric`
- Implementation: B 用 version/help/min-input/adapter 状态机；F 用 `strict_segment_eval.py` 与 versioned lattice evaluator；S 用同一 sealed split 上的 hierarchical selective evaluator；G/E 仅在资产闸通过后使用各自 frozen evaluator。
- Direction: higher_is_better
- Claim policy: smoke/screen 的 primary metric 只作 route-local promotion/stop 信号，不与 published SOTA 比较。

### Route-specific primary and guardrail metrics

| Route | Primary screen output | Required guardrails |
|---|---|---|
| B | 每个 frozen workflow 的 `engineering_status` | identity/version/db/license/help/min-input/adapter、exit code、elapsed、peak RSS、explicit block reason |
| F | parent segment F1 at predeclared IoU 0.5 and 0.8 | leaf retention=1；true-backed deletion=0；false fusion；nested preservation；boundary curves；per-genome paired uncertainty |
| S | selective risk at fixed coverage and hierarchical path distance | risk-coverage curve；conditional macro-F1；unknown recall；false-unknown；overconfident leaf error；per-clade uncertainty |
| G | top-k contains-best and regret | rank correlation；interval/conformal coverage；LOSO/leave-clade-out abstention |
| E | family clustering stability outside strong-baseline CI | copy/species leakage；multi-seed stability；correct-unit metrics；projection-independent conclusion |

## 3. Three-layer gates

| Gate | Threshold | Trigger |
|---|---|---|
| primary_progress_gate | B matrix complete with no silent substitution；F/S route-local metric improves without violating stop rule | 承认 bounded screen signal，不是 claim |
| sota_claim_gate | disabled for this cohort | smoke/screen 永不 claim；以后 full/scale 须严格超越且可比性全通过 |
| review_decision_gate | finite metrics + terminal Slurm reconciliation + semantic validation | cohort 收齐后触发 `$tri-review` + `$pivot` |

## 4. Frozen denominator and SOTA reference table

| Workflow/model | Frozen identity | Dataset/split | Screen output | Source | Comparable? | Notes |
|---|---|---|---|---|---|---|
| RepeatModeler2 + RepeatMasker | RM2 2.0.9 + RM 4.2.4 | deterministic tiny FASTA | engineering status | official releases + `docs/02` | engineering only | Dfam/FamDB identity must be explicit |
| EDTA | 2.3.0 | same tiny FASTA where supported | engineering status | official v2.3.0 | engineering only | legacy 2.2.x environment is forbidden |
| Earl Grey | 7.3.0, frozen before 7.3.1 appeared | same tiny FASTA where supported | engineering status | official v7.3.0 | engineering only | Dfam 4.0 configuration is a separate gate |
| HiTE | 3.3.3 exact digest/commit | same tiny FASTA where supported | engineering status | official v.3.3.3 | engineering only | legacy unpinned 3.0 SIF rejected |
| TEtrimmer | 1.7.4 source commit `61456873...` | same tiny FASTA where supported | engineering status | official source commit | conditional | 1.7.2 SIF is dependency host only, never target identity |
| TE_Bench | evaluator anchor only | canonicalized tool output | adapter/evaluator sanity | frozen local external tree hash | no denominator row | MCHelper is not added |

## 5. Comparability contract

| Route | Dataset version | Split scheme | Metric impl | Preprocessing | Runtime/weights | Verdict rule |
|---|---|---|---|---|---|---|
| B | one hashed synthetic FASTA and optional official fixtures | no train/test | versioned adapter + schema validator | identical canonical coordinate conversion | immutable SIF/digest/source commit and database hashes | cell PASS, BLOCKED, VERSION_MISMATCH or INVALID; no substitution |
| F | one frozen prediction/truth registry | genome/truth-tier blocks | same evaluator for raw/CENTER70/merge/postprocess/lattice | immutable leaves; half-open coordinates | code/config/input hashes | no promotion if true-backed leaves deleted or false fusion materially rises |
| S | PRE-S0 canonical snapshot | family/homology component plus clade holdout | same selective evaluator for all baselines | ontology mapping frozen before split | train-only prototypes/calibration | no promotion if split leaks or usable coverage collapses |
| G | exact reconstructed run records only | genome LOSO and clade holdout | same router evaluator | genome-level features only | exact checkpoints/code/config | missing provenance or insufficient independent species => typed block |
| E | exact 2,200 binding registry only | sealed family/copy/species split | identical projection/clustering budget | zero-based half-open coordinates | frozen pretrained and untrained weights | missing bindings/weights => typed block |

## 6. Dataset readiness plan

| Dataset/asset | Purpose | Timing | Readiness | Hash needed? | Notes |
|---|---|---|---|---|---|
| synthetic tiny FASTA | B identity/min-input | now | generated deterministically inside allocation | yes | non-biological, non-claim |
| candidate SIFs + Dfam candidates | B runtime | now | RM/EDTA/EarlGrey present；HiTE exact SIF absent；TEtrimmer exact source overlay present | yes | each cell fail-closed |
| Real-T0/H0 registry | F truth | now | not yet proven complete | yes | if absent, use explicit partial tier or typed block; never pretend T0 |
| PRE-S0 canonical snapshot | S source | now | 105 annotations + 15 genome links independently verified | yes | split and homology pins still required |
| five selector anchor run records | G provenance | later/gated | all `PROV_RUN_RECORD_MISSING` | yes | clean rebuild only if bounded and asset gate opens |
| 2,200 fragment binding + model weights | E falsification | later/gated | bindings/backend/weights incomplete | yes | no run before exact freeze |

## 7. Technical Roadmap

### 7.1 Mechanism-level weaknesses

| Existing approach | Weakness | Mechanism attacked | Evidence status |
|---|---|---|---|
| mutable/legacy workflow wrappers | version and DB drift can masquerade as algorithm differences | exact identity + offline min-input + canonical adapter | official sources and candidate records verified；runtime smoke pending |
| fixed gap/threshold merging | may delete fragments or fuse unrelated/nested elements | immutable leaves + typed parent joins | historical cousin routes abandoned；new no-deletion mechanism is distinct |
| flat superfamily classification | remote family errors are overconfident and Unknown is incoherent | ontology-aware depth prediction + abstention | canonical snapshot ready；blocked split must be constructed |
| scalar transfer formula | species/clade dependence and anti-conservative OOD | genome-level surface + conservative router | historical top-2 evidence exists；exact anchor provenance missing |
| embedding-only visualization | UMAP separation can reflect species/copy/context leakage | sealed strong-baseline falsification | exact 2,200 binding and weights missing |

### 7.2 Differentiated paths

#### Path 1: Five-workflow fail-closed smoke
- Hypothesis: exact frozen workflows can be invoked and standardized without silent version/database substitution.
- Architecture change: identity manifest and deterministic canonical adapter around each upstream workflow.
- Screen design: CPU-only, one deterministic tiny input, ≤12h per job, seed not applicable.
- Promotion rule: matrix complete and every unavailable cell has a typed reason; engineering PASS is not biological validation.
- Failure detection: version mismatch, absent DB/index/license, nonzero min-launch, invalid coordinates or mutable identity.

#### Path 2: Preservation-constrained parent-aware lattice
- Hypothesis: typed parent joins recover parent intervals while raw positive leaves remain immutable.
- Architecture change: candidate edge typing, compatibility rejection, parent/leaf/rejected-edge audit tables.
- Screen design: one frozen subset, single deterministic configuration, raw/CENTER70/MERGE_STRICT/MERGE_LOOSE/current-postprocess comparators.
- Promotion rule: parent recovery improves at more than one tolerance with leaf retention 1.0 and no material false-fusion rise.
- Failure detection: true-backed deletion, chromosome/hard-N/nesting violation, permissive-tolerance-only gain.

#### Path 3: Hierarchical calibrated open set
- Hypothesis: returning the deepest supported ontology node or abstaining lowers severe remote-family errors at usable coverage.
- Architecture change: train-only prototypes/hierarchical score, validation-only calibration, explicit Unknown/abstain.
- Screen design: family/homology-component blocks and clade holdout; identical budget for flat, k-mer prototype and direct head.
- Promotion rule: lower selective/hierarchical risk with retained usable coverage and no test-label calibration.
- Failure detection: random-copy leakage, clade result collapse, false-unknown explosion or abstention hides nearly all errors.

##### 2026-08-11 S0 direct-baseline prerequisite

Per the user's continuation decision, Path 3 is now sequential. `SF-DIRECT-BASELINE-SCREEN-20260811-R2` must first establish that direct superfamily annotation is acceptable on the leakage-safe family/homology-component and clade-held-out split. Only after S0 passes may `SF-HIER-OPENSET-SCREEN-20260811-R3` attempt to reduce severe misclassification.

S0 screen gates are preregistered from the historical SF5 range, before new results are observed: main4 conditional macro-F1 `>=0.80`, TE-detect F1 `>=0.85`, Unknown recall `>=0.30`, main4 false-Unknown rate `<=0.02`, eligible main4 coverage `>=0.70`, minimum clade macro-F1 `>=0.60`, zero homology-component overlap, and zero test calibration. Failure means diagnose annotation/split/direct-head identity first; hierarchical abstention cannot hide a failed direct baseline.

##### 2026-08-12 S0 benchmark-version replacement gate

The frozen Dfam 3.9 post-hoc resolver route is closed by Job `11528267`: 50 identifiers resolve uniquely, 2 remain ambiguous and 227 remain missing, covering only 26.595% of the original occurrence mass. The next S0 action is therefore a new benchmark version, not a repair of the old annotations.

The replacement must be generated annotation-time with a frozen official Dfam release and RepeatMasker tool/config. Each P-state annotation must retain a unique versioned accession, official consensus SHA256 and the raw RepeatMasker class. Raw class remains the only label source; accession/consensus are used only for provenance and label-blind homology blocking.

Execution is staged and fail-closed:

1. CPU six-family round-trip smoke: prove that paired name-based and accession-based exports contain identical ordered sequences/classes and that RepeatMasker `.out` retains accession and raw class without a heuristic join. This is an engineering smoke, not representative concordance.
2. CPU representative concordance probe on frozen real windows selected from old outputs before viewing new annotations. Every old occurrence in scope is assigned exactly once to exact, same-class-overlap, split, merge, class-conflict, ambiguous or unmatched; report interval-, bp-, class-, species- and clade-level coverage and shifts.
3. CPU full DATA/homology gate: require unique identity for every included P hit, explicit typed blockers for ambiguity/conflict, deterministic consensus components, and zero component overlap across train/validation/test.
4. Only after all CPU gates pass may the existing direct-S0 numeric screen run. S1 remains conditional on all S0 floors.

The full concordance ledger may not shrink the 6,432,583 occurrence denominator: its exact-once categories must sum to 6,432,583. Coordinate/bp overlap is audit evidence only and may never assign an accession to a new hit. The route may not train on the resolved subset, use current-release APIs, infer accessions by prefix/case/fuzzy aliases, derive identity from genomic copies, or majority-relabel a conflicting component. This is a benchmark-version change and all old/new coverage differences must remain visible.

#### Path 4: Genome-level transfer surface
- Hypothesis: a conservative top-k router with abstention is useful within supported clades, without claiming universal F1 prediction.
- Screen design: only after exact anchor provenance; LOSO and leave-clade-out at genome unit.
- Promotion rule: predefined top-k/regret/coverage targets with calibrated abstention.
- Failure detection: missing run record, insufficient independent species, invalid clade holdout or anti-conservative intervals.

#### Path 5: Representation falsification
- Hypothesis: pretrained representation must beat k-mer/MinHash/alignment/length-GC/random/untrained controls on a sealed biological split.
- Screen design: exact 2,200 bindings, identical projection/clustering selection budget, multiple seeds inside 24 GPU-hour cohort cap.
- Promotion rule: improvement outside confidence intervals and stable after family/copy/species leakage audit.
- Failure detection: missing weights/bindings, visual-projection-only conclusion or strong baseline tie/loss.

### 7.3 Cohort strategy and order

- Track: bounded Discovery/Publication-Validation support; all profiles smoke or screen.
- Order: Stage-A guard → B first → F and S may run concurrently after independent reviews → G/E only if asset gates pass.
- Default seeds: B/F deterministic; S single-seed screen unless evaluator resampling is CPU-bounded; E multiple seeds only if authorized by its asset gate.
- Parallel candidates: at most 3 orthogonal directions and never more than `cluster_config.yaml` allows.
- Claim policy: never claim SOTA from this cohort.

### 7.4 Milestones

| ID | Milestone | Threshold | Expected run | Completion evidence |
|---|---|---|---|---|
| M0 | deterministic research-flow guard opens | `ok_to_goal=true` | CPU audit | saved guard JSON |
| M1 | B smoke reconciled | all five cells terminal and explicit | 1 CPU job | job ID + manifests + finite metrics |
| M2 | F screen or typed block | semantic pass under stop rule, or proven truth-tier block | ≤1 CPU/GPU job | evaluator report + review |
| M3 | S screen or typed block | sealed nonleaking split and finite selective metrics, or proven block | ≤1 GPU job | split audit + report |
| M4 | G/E asset decision | gate pass before run, otherwise typed block | 0 unless eligible | asset manifests |
| M5 | cohort decision | all submitted jobs terminal and independently reviewed | no extra compute | result matrix + tri-review + pivot |

### 7.5 Risk dial and resource budget

| Path | Risk | User priority | Resource ceiling |
|---|---|---|---|
| B | low scientific, medium integration | first | CPU-only, ≤12h |
| F | medium truth-tier risk | second, parallel with S | prefer CPU; ≤12h |
| S | medium/high leakage-calibration risk | second, parallel with F | ≤1 GPU, ≤12 GPU-hours |
| G | high provenance risk | gated | no run while anchor records missing |
| E | high asset/leakage risk | gated | no run while bindings/weights missing |

Aggregate new allocation: ≤24 GPU-hours；CPU audits/smoke request zero GPUs；no full/scale.

## 8. User-confirmed technical choices

- Priority: Stage-A repair and B smoke first；F/S are the two main scientific pilots；G/E asset-gated.
- Risk preference: fail closed, preserve negative evidence, no silent fallback.
- Directions explicitly avoided: replicate/wait for Pro package, mutable old containers, ordinary Unknown class, universal scalar transfer formula, UMAP-only representation claims, threshold-tuning cousin of abandoned fragment routes.
- First batch size: B one CPU job；then at most F+S concurrently.
- Promotion rule: only route-local screen promotion after code review, leakage audit, terminal reconciliation and stop-rule check.

## 9. Baseline reproduction exception for this cohort

reproduce_waived: 2026-08-11 bounded non-claim cohort uses the five-workflow smoke itself to establish executable technical ground truth; no own-model full/scale or SOTA claim is authorized, and formal baseline reproduction remains mandatory before any later claim-bearing run.

This is a scope-limited waiver, not evidence that a published baseline has reproduced. The five-tool smoke and F/S internal comparators remain part of the current evidence work.

## 10. Open uncertainties and TODO

- [ ] B: acquire/freeze exact HiTE 3.3.3 SIF or record the cell as typed block.
- [ ] B: verify whether Dfam 4.0 candidates are sufficient for offline EarlGrey/RM min-input; do not perform a database migration.
- [ ] F: prove Real-T0/H0 registry and truth tier before whole-genome precision wording.
- [ ] S: materialize and audit homology components before fitting/calibration.
- [ ] G: reconstruct all five exact anchor run records or retain `FOUNDATIONAL_TYPED_BLOCK`.
- [ ] E: freeze exact 2,200 bindings, component assignments, backend pins and weights or retain `FOUNDATIONAL_TYPED_BLOCK`.
