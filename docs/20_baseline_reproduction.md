# Baseline Reproduction Ledger / SOTA 复现中央账本

> 由 `/reproduce-baselines` 维护。`refs/dossiers/*` 存每篇/每模型的一手细节；本文档存所有复现尝试的中央索引、结论和对 evaluator/benchmark 的影响。

## 0. Status
- Required before own model iteration: yes, unless `reproduce_waived:<reason>` is recorded in `docs/03` or `ACTIVE_GOAL.json`.
- Current gate: waived only for `TEFM-NEW-DIRECTIONS-PILOTS-20260811` smoke/screen; incomplete for claim-bearing work

## 1. Reproduction Runs
| ID | Date | Model | Source paper/repo | Dataset/split | Reported metric | Reproduced metric | Tolerance pass? | Output/report path | Verdict |
|---|---|---|---|---|---:|---:|---|---|---|

## 2. Verified Facts To Transfer
| Fact type | Model/source | Finding | Evidence path | Propagated to |
|---|---|---|---|---|
| metric_impl |  |  | refs/dossiers/... | docs/19 |
| dataset_rawness |  |  | refs/dossiers/... | docs/03 |
| split_scheme |  |  | refs/dossiers/... | docs/03 |
| preprocessing |  |  | refs/dossiers/... | docs/19 |

## 3. Failed / Partial Reproductions
| Date | Model | Failure type | What was still learned | Next action |
|---|---|---|---|---|

## 4. Waivers
| Date | Waived item | Reason | Risk accepted | User/agent |
|---|---|---|---|---|
| 2026-08-11 | Formal 1-2 SOTA reproduction before this bounded cohort | B is itself the executable five-workflow ground-truth smoke; F/S only compare frozen internal comparators; no full/scale or claim is authorized | no published-SOTA comparison, no manuscript wording, and every later claim-bearing run still requires formal reproduction | user explicitly authorized bounded cohort; agent recorded scope-limited waiver |

## 5. Impact On Benchmark
| Date | Impact | File updated | Notes |
|---|---|---|---|
| 2026-08-11 | Established denominator identities and route-local internal comparators, but not reproduced biological accuracy | `docs/02`, `docs/03`, `docs/19` | B outputs can establish engineering availability only; F/S remain claim-ineligible screens |
