---
exp_id: BENCH-5TOOL-SMOKE-20260811-R1
date: 2026-08-11
approach_family: external-workflow-benchmark
parent_exp: -
motivated_by: "TEFM-NEW-DIRECTIONS-PILOTS-20260811 denominator identity gate"
track: baseline
profile: smoke
status: done
primary_metric: engineering_pass_fraction
value: 0.0
vs_anchor: "0/5 engineering-pass; valid negative matrix"
one_liner: "五工具身份/最小输入 fail-closed smoke；5/5 有终态但无完整可用 workflow"
---

# BENCH-5TOOL-SMOKE-20260811-R1

## Hypothesis

五个预先冻结的工作流能否在不静默换版本/数据库的前提下完成 exact identity、离线 help/version、最小输入和 canonical interval adapter 检查；不能运行的单元格必须给出 typed blocker。

## Scope and design

- Profile: smoke；CPU-only；claim-ineligible。
- Denominator: RepeatModeler2 2.0.9 + RepeatMasker 4.2.4、EDTA 2.3.0、Earl Grey 7.3.0、HiTE 3.3.3、conditional TEtrimmer 1.7.4 source commit。
- Inputs: official tiny installation fixtures with SHA-256 manifest；no training/test split。
- Canonical coordinates: zero-based half-open TSV；GFF one-based closed is converted explicitly。
- Fail-closed: HiTE legacy unpinned 3.0 and TEtrimmer native 1.7.2 cannot satisfy the target version；Dfam candidates are not treated as configured databases.

## Gates

- Stage-A guard: PASS (`RESEARCH_FLOW_GUARD_OPEN_20260811.json`).
- Code review: `PASS_WITH_WARNINGS`; final fail-closed incremental re-review PASS; machine gate `ok=true`.
- Data leakage: statically `PASS_NOT_APPLICABLE` because no model/split/calibration；deterministic adapter/data audit also runs inside Slurm.
- smart-sbatch: Phase 1 PASS；Phase 2 chose private CPU-only fast path with zero GRES. Debug preflight jobs `11518384`/`11519282` exposed and closed two environment bootstrap bugs; job `11519305` completed all syntax/adapter checks in 4 seconds.

## Runtime and result

- Job ID: `11519312`.
- Terminal state: `COMPLETED`, exit `0:0`; elapsed `00:15:13` (913 s), 8 CPU, 64 GB requested, batch MaxRSS 1,686,288 KB, 0 GPU.
- Metrics: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/metrics.json`.
- Semantic validation: PASS (`matrix_cells=5`, `invalid_cells=0`, adapter self-test PASS, leakage `PASS_NOT_APPLICABLE`, 764/764 output hashes verified).
- Result: `engineering_pass_cells=0`, `typed_block_cells=4`, `version_mismatch_cells=1`.
- Cells: RM2+RM / Earl Grey / HiTE / TEtrimmer are `FOUNDATIONAL_TYPED_BLOCK`; EDTA is `VERSION_MISMATCH` because its payload prints only `v2.3`, so patch version `2.3.0` is not runtime-provable even though the frozen SIF identity is exact.
- Claim eligibility: false.

## Decision

Valid negative identity smoke. Do not use any of the five rows as a complete benchmark denominator yet. Resolve Dfam/FamDB configuration, exact HiTE acquisition, EDTA runtime patch identity, and TEtrimmer output/Pfam closure before a biological comparator run.

## Links

- Result log: `docs/06_results_log.md#result-bench-5tool-smoke-20260811-r1`
- Metrics: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/metrics.json`
- Accounting: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/slurm_accounting.json`
- Semantic validation: `outputs/BENCH-5TOOL-SMOKE-20260811-R1/semantic_validation.json`
- Tri-review / pivot: `3/3`; comparability audit first, with B exact runtime/database denominator as the primary dependency. See `docs/07_tri_review.md` and `docs/08_pivot_decisions.md`.

## Parent and provenance

- Protocol: `codex_jobs/handoffs/TEFM-NEW-DIRECTIONS-PILOTS-20260811/UNIGE_DIRECT_PILOTS_PROTOCOL_20260811.md`.
- Runtime candidates: `codex_jobs/E1B-OCI-ACQUIRE-20260809A/evidence/candidate_records.tsv` and `codex_jobs/E1B2R2-EARLGREY-ACQUIRE-20260809A/evidence/candidate_record.tsv`.
- This implementation was independently reconstructed from the repository and official sources; it does not consume a Pro implementation package.
