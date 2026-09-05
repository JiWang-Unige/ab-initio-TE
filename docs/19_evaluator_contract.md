# Evaluator Contract / 评估器与可比性合约

## 2026-09-05 Human gap A/C 局部合约

仅适用于 `GAP-BRIDGE-P3-NT-R2` 与 `GAP-BRIDGE-DOWNSTREAM-C-R1`；
不替换以下历史路由合约。细则和固定资产见
`experiments/GAP-BRIDGE-A-C-PARALLEL-20260905.md`。
A 当前无训练/评分，仅输出 label-blind 配对坐标、finite、H0 新槽为零和原输入一致性；
不产生模型性能 primary metric。C 容器准备同样不产生科学指标。
C 下游拟采用 chr13 全部 9 DEV core 的 distinct complete CDS-chain exact-match
micro precision/recall/F1（零容差，方向及所有 CDS 区间一致），另报 M0-correct
保留/丢失及分母；不是 gene-level F1。CDS stop-codon 与 core 归属细则必须在预测前冻结。
无外部 SOTA 可比性或 confirmatory claim；无 CAL-GATE/chr19 评价；不使用旧 draft
`F1 +0.005` / `lost-correct <=0.1%` 自动判通过。

> 由 `/benchmark-roadmap`、`/reproduce-baselines`、`/code-review-gate`、`/result-log` 共同维护。本文档是“我们的指标到底怎么算、什么结果可 claim”的中央真相源。

## 0. Contract Status
- Status: bounded-screen-ready; claim-not-ready
- Owner skill: `$benchmark-roadmap` + per-route `$code-review-gate`
- Last verified: 2026-08-11
- Applies to goal: `TEFM-NEW-DIRECTIONS-PILOTS-20260811` and historical TE-FM goal where explicitly cross-referenced

## 1. Primary Metric Definition
| Field | Value |
|---|---|
| Metric name | route_primary_metric |
| Direction | higher_is_better |
| Prediction granularity | route-specific genome interval and workflow units |
| Positive class / label mapping | P is TE positive; RN is reliable negative; U is ignored uncertainty; hardN is non-TE repeat-like negative |
| Threshold / calibration rule | B and F are deterministic; S thresholds fit on validation only and never test; claim-bearing thresholds remain separately frozen |
| Averaging | route-local only: B cell status; F per-genome interval metrics; S per-clade selective metrics; no cross-route aggregate headline |
| Excluded labels / masks | `U` ignored for negative metrics; `SPECIES_SPECIFIC_RARE` and audit-only superfamilies excluded from headline macro-F1 |
| Tie / boundary handling | Boundary tolerance and segment IoU thresholds must be versioned before claim; default candidates: segment IoU@0.5, boundary F1@50/100bp |

## 2. Evaluator Implementation
| Component | Path / version | Required behavior | Verified by |
|---|---|---|---|
| External workflow evaluator anchor | `/home/users/j/jwang/TE_compare/TE-Benchmark/core/workflow/` frozen by tree manifest per B run | adapters must not select legacy containers by default | B code review + output schema validation |
| Existing strict interval evaluator | `pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py` | zero-based half-open interval evaluation; versioned copy/hash in F manifest | F synthetic tests + code review |
| Our evaluator script | `scripts/experiments/BENCH-5TOOL-SMOKE-20260811-R1/run_smoke.py`; F/S paths become exact before their submission | finite JSON, explicit truth tier/split/evaluator hash, route stop-rule fields | per-route `code_review_gate.json` |
| Metric libraries | Python standard library plus explicitly hashed environment packages | no hidden test-time calibration; coordinates validated | environment manifest + job logs |
| Unit/smoke test | `scripts/experiments/<exp_id>/` synthetic fixtures executed only inside Slurm allocation | deterministic expected statuses and edge cases | captured test report and exit status |

## 3. Dataset And Split Contract
| Dataset | Version/hash | Split scheme | Leakage guard | Comparable to SOTA? |
|---|---|---|---|---|
| B deterministic tiny workflow input | generated and hashed per run | no train/validation/test | input identity and output-coordinate audit | no; engineering smoke only |
| F frozen interval registry | manifest and truth tier frozen before result | genome and truth-tier blocked | no cross-genome fitting; leaves immutable; hard-N/nesting joins rejected | no; internal screen only |
| S PRE-S0 canonical snapshot | `PRE-S0-CANONICAL-20260810-R2` plus derived manifest | family or homology-component blocks plus clade holdout | component overlap and calibration/test separation audit | no; internal screen only |
| TE-FM production / matched-label panel | pending `species_manifest.tsv` + genome/annotation hashes | fixed species/chromosome roles; no random adjacent segment split | chromosome-level holdout where possible; otherwise large-block holdout; homologous/near-duplicate train-test leakage check required | pending baseline reproduction |
| TE-FM zero-human panel | pending `species_manifest.tsv` | human and non-human primates excluded from training; hs1/T2T held out as anchor | train/validation/test species roles fixed before model selection; human threshold not fit on test | pending P8 matrix |

Minimum `species_manifest.tsv` fields:
- species, taxid, kingdom/clade, role, assembly source/accession/name/level, genome size, N50/QV/BUSCO if available.
- RepeatMasker version, Dfam/library version, annotation source, label run ID, MD5 for genome and library.
- chosen primary chromosome, stability-check chromosome, exclusion reason for sex/micro/extreme contigs.

Minimum sampling audit fields:
- realized counts and bp by species, chromosome, stratum, label state, superfamily, and split.
- strata must distinguish TE-internal, TE-boundary, hardN, RN, random background, and U-calibration/ignored.
- v0 sampling ratios are defaults only; any deviation must be recorded, and easy random negatives cannot replace matched hard negatives.

## 4. Metrics JSON Schema
Every comparable run must write `reports/<exp_id>.json` with:

```json
{
  "exp_id": "<id>",
  "profile": "smoke|screen|full|scale",
  "primary_metric": 0.0,
  "metrics": {},
  "dataset": {"name": "", "version": "", "split": ""},
  "evaluator": {"path": "", "version": ""},
  "semantic_success": true,
  "claim_eligible": false
}
```

## 5. Claim Eligibility Checklist
| Check | Required for claim | Current status | Evidence |
|---|---:|---|---|
| full/scale profile, not smoke/screen | yes |  |  |
| strict exceedance over SOTA | yes |  |  |
| same dataset/split/version or justified comparable mapping | yes |  |  |
| metric implementation verified against baseline | yes |  |  |
| no leakage / preprocessing fit on train only | yes |  |  |
| code-review-gate passed for evaluator changes | yes |  |  |
| tri-review quorum passed | yes |  |  |
| species/chromosome role manifest fixed before baseline/full comparison | yes | pending | docs/13 §7.1 |
| sampling audit written for every comparable run | yes | pending | docs/13 §7.1; reports/<exp_id>.json |
| context-trap diagnostic completed or explicitly waived before context/generalization claim | yes | pending | docs/13 §7.6; docs/14 §3 |
| UHC evidence tier used for any candidate/novel wording | yes | pending | docs/14 §8 |
| `SF-TARGET` frozen before full/scale claim | yes | pending | docs/13 §7.5; refs/dossiers/sf_target_set.md |
| `WIN-MATRIX` comparison rule frozen before model comparison | yes | pending | docs/13 §7.6; refs/dossiers/window_matrix.md |
| P8 baseline rows defined for generalization claim | yes | pending | docs/14 §7 |

## 6. TE-FM label and metric rules

### 6.0 Label source hierarchy

| Layer | Source | Training / evaluation role | Claim status |
|---|---|---|---|
| `Label-A` | self-run RepeatMasker + Dfam with fixed software/library/species parameters | primary `P` source for claim-bearing training and main metrics | primary reference |
| `Label-B` | RepeatModeler2 / EDTA / HiTE + Dfam + RepeatMasker | U-shield, sensitivity audit, de novo baseline, candidate validation | not primary by default |
| `Label-C` | structure/copy/consensus/domain/cross-assembly/manual evidence | UHC evidence cards and case studies | support tier only |

Rules:
- Main TE-F1/AUPRC/segment metrics are computed against Label-A unless a new user-approved route decision explicitly defines another primary reference.
- Label-B-only TE-like intervals must be masked as `U` for loss and primary FP calculations unless rejected as `hardN`/blacklist. They are not default positive labels.
- If model performance collapses for a species, chromosome, or superfamily, a bounded de novo+Dfam diagnostic may be run for that unit. The diagnostic can support claim narrowing, audit-only demotion, or U-shield expansion; it does not automatically change the primary reference.
- Any Label-B promotion to primary/co-primary is a route change requiring Label-A/B concordance, U-QUALITY, independent support when available, and user approval.

### 6.1 Label states

| State | Meaning | Training use | Evaluation use |
|---|---|---|---|
| `P` | high/medium confidence TE positive | positive loss | TE reference/support tier |
| `RN` | reliable negative after excluding TE/repeat/uncertain/problematic regions | negative loss | specificity and RN-FPR |
| `U` | unannotated or uncertain region | ignore | candidate evidence only |
| `hardN` | simple repeat, low complexity, satellite, tandem, other non-TE repeat-like sequence | hard negative | hardN-FPR |

Rules:
- `U` must never be treated as a true negative.
- Model-only high score in `U` is a candidate, not a novel TE claim.
- hardN and RN metrics are guardrails; improving TE recall by flooding hardN is a failure.
- Label-B-only TE-like intervals are included in `U` / candidate evidence, not `RN`; evaluator implementations must expose counts for Label-A-only, Label-A/B overlap, and Label-B-only masked bp.

### 6.2 Superfamily scoring and rare class masks

`SF-TARGET` defines which superfamilies are headline labels. Until `refs/dossiers/sf_target_set.md` is frozen, per-superfamily macro-F1 is exploratory only.

Default handling:
- Retained superfamilies enter headline per-superfamily macro-F1.
- `Other_TE` is reported but not used to inflate biological specificity claims.
- `SPECIES_SPECIFIC_RARE`, single-species low-sample classes, low-concordance classes, and audit-only classes are excluded from headline macro-F1 and reported separately.
- If per-kingdom label spaces differ, report kingdom-masked macro-F1: only labels valid for that kingdom are averaged for that kingdom, and cross-kingdom comparisons must state the active label mask.

#### 2026-08-11 direct-superfamily-first contract

- Stage S0 uses the existing direct SF5 label space `BG/SINE/LINE/LTR/DNA/Unknown`; `Unknown` remains a heterogeneous reject/audit bucket, not a coherent biological superfamily.
- The 2026-08-12 identity gate freezes **direct annotation as label truth and sequence homology only as the split firewall**. Homology components may join identifiers for train/validation/test blocking, but may not rewrite an identifier's direct superfamily label.
- Split unit is a frozen sequence-homology component, with a separate clade-held-out audit. Any component overlap across train/validation/test invalidates the run. A component containing conflicting direct main4 labels is an explicit typed blocker/audit stratum, not a majority-vote relabeling opportunity.
- The ten identifiers excluded by the frozen S0 label contract remain `U/ignore` and are reported in a separate coverage audit; they never enter the primary denominator. `X13_LINE` remains an ambiguity stratum and is likewise excluded from primary scoring.
- Before homology construction, all Dfam identities must be resolved from frozen family metadata independently of optional name indexes. In particular, absence of `Lookup/ByName` in Dfam 3.9 partition 3 cannot by itself be interpreted as biological absence. Unresolved identities remain explicit coverage blockers; random fallback, prefix guessing and silent copy-derived substitution are forbidden.
- Historical SF5 weights are continuity comparators only if their training data overlap held-out components. The leakage-safe primary is a clean direct head initialized from the frozen base-pretrained checkpoint and trained only on the new blocked train/validation data.
- A sequence window with non-background TE components assigned to multiple splits is excluded from fitting/evaluation and counted in the coverage denominator; it may not be assigned by majority label.
- Primary metric is main4 conditional macro-F1 over eligible main4 labels; TE-detect F1, Unknown recall, main4 false-Unknown rate, eligible coverage, minimum/per-clade macro-F1, hierarchical path distance and overconfident leaf error are mandatory secondary fields.
- Acceptance floors are fixed before execution: `0.80`, `0.85`, `0.30`, `0.02`, `0.70`, and `0.60` respectively for main4 macro-F1, TE-detect F1, Unknown recall, false-Unknown, coverage and minimum-clade macro-F1.
- Model selection/calibration uses training/validation only. Test calibration count must be zero.
- Hierarchical/open-set Stage S1 is conditionally authorized only when every S0 acceptance and leakage gate passes. S0/S1 remain screen-only and claim-ineligible.

#### 2026-08-12 accession-preserving benchmark-version amendment

- Job `11528267` closes the frozen Dfam 3.9 post-hoc identifier-resolution route at 50 unique / 2 ambiguous / 227 missing. These old annotations remain immutable evidence and may not be silently enriched, subsetted or relabeled.
- The only proposed S0 re-entry is a new, explicitly versioned annotation dataset generated with a frozen official Dfam library and RepeatMasker execution. Every P-state hit must retain the versioned accession and official consensus SHA256 at annotation time.
- The RepeatMasker raw class remains the sole source of `SINE/LINE/LTR/DNA/Unknown`; accession, canonical name, Dfam ontology and homology component are forbidden inputs to direct-label construction.
- The first gate is a six-family paired CPU round-trip smoke: identical ordered consensus sequences/classes with name-based versus accession-based FASTA identifiers must yield identical normalized query/start/end/strand/score/divergence/deletion/insertion/repeat-coordinate/raw-class/fragment geometry. Only repeat identifier may differ. The accession run must retain a unique exact accession for every P hit. Passing this gate authorizes only a frozen-real-window representative CPU proposal; it is not concordance evidence.
- The old/new concordance ledger must conserve the frozen 6,432,583 occurrence mass with every old occurrence assigned exactly once to exact, same-class-overlap, split, merge, class-conflict, ambiguous or unmatched. Coordinate and bp overlap are audit evidence only and may not impute accession. Report interval, bp, class, species and clade coverage. No denominator shrinkage or resolved-only training is allowed.
- Before any GPU run, all retained P hits require unique accession/consensus identity; ambiguity and cross-source conflicts are typed blockers. Homology construction remains label-blind and train/validation/test component overlap must be zero.
- A benchmark-version change cannot inherit old S0 performance numbers as directly comparable. The new direct-S0 screen must rerun the full preregistered metric set; S1 remains disabled until every numeric, coverage, calibration and leakage gate passes.

### 6.3 Window comparability

Window length is part of the evaluator/comparability contract.

Rules:
- `2048bp` is the default shared anchor for cross-backbone comparison.
- If a model cannot support 2048bp, the nearest native context not exceeding 2048bp may be marked `2048eq:<actual_bp>`; it cannot be described as perfectly fair with true 2048bp runs.
- Long-context results at `4096/8192bp` are upper-bound or Enhanced results unless the final anchor sweep explicitly promotes them.

### 6.4 P8 claim eligibility

Generalization claims require the P8 rows in `docs/14 §7` to be present at the relevant layer.

Minimum requirements:
- Human-only FM vs Dfam-human-only RepeatMasker for database-bias audit.
- No-human FM vs target/clade Dfam RepeatMasker for zero-human/de novo generalization.
- Same-kingdom holdout for Core OOD.
- Cross-kingdom transfer only supports Enhanced/sentinel claims unless explicitly promoted in `docs/11`.

### 6.5 Context-trap diagnostics

Context length is not only a model hyperparameter; it can create a biological shortcut if predictions depend on species-specific flanks, repeat density, GC/k-mer background, or annotation artefacts.

Rules:
- `WIN-MATRIX` can select screen candidates without full perturbation experiments, but any claim that a context length improves biological generalization requires context-trap diagnostics.
- Required diagnostics are flank masking, flank swap, matched negative evaluation, and embedding species leakage when embeddings are used for representation/family claims.
- Metrics must report prediction delta between full/center-only/flank-only inputs, matched-negative RN-FPR/hardN-FPR, and species-vs-family clustering signal for embeddings.
- If a model has high same-species F1 but fails matched negatives or is flank-sensitive, the result may be used as an engineering baseline but not as evidence of TE-internal biological generalization.

### 6.6 UHC candidate evidence tiers

`UHC` means unannotated high-confidence model hit. UHC is not a false positive by default, but it is also not a novel TE by default.

Rules:
- Tier 0 model-only hits are diagnostics only.
- Candidate claims require a populated evidence card in `docs/14 §8` or a run-specific report linked from it.
- The strongest manuscript wording must not exceed the evidence tier.
- Family embedding and novel-family clustering remain Enhanced/Parked unless promoted by an explicit route decision in `docs/11`.

## 7. Change Log
| Date | Change | Reason | Approved by | Follow-up |
|---|---|---|---|---|
| 2026-06-15 | Added TE-FM label, rare class, window comparability, and P8 claim rules | `$council` found TE length, superfamily, window, and P8 details were missing from the route | user requested execution | Fill evaluator script paths and run `SF-TARGET`/`WIN-MATRIX` gates |
| 2026-06-15 | Added species/sampling contract, context-trap diagnostics, and UHC evidence-tier claim rules | Second `$council` compared current route against GENERANNO execution plan and approved embedding gaps into existing gates without expanding scope | user approved with “落” | Produce `species_manifest.tsv`, sampling audit schema, and minimal context-trap/UHC reports |
| 2026-06-15 | Added Label-A/B/C source hierarchy and Label-B U-shield rule | `$council` on RepeatMasker+Dfam vs de novo+Dfam label sources; user confirmed de novo diagnostics may be run when model performance is poor | user confirmed | Implement label-source manifest, Label-A/B concordance, U-shield BED, and poor-performance diagnostic trigger |
| 2026-08-11 | Added bounded B/F/S evaluator and split contract | direct-pilot protocol requires versioned evaluators, finite metrics and fail-closed data gates before submission | user authorized bounded cohort | Fill exact per-exp paths/hashes during implementation; this does not make the contract claim-ready |
