---
exp_id: SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1
date: 2026-08-12
approach_family: data-identity
parent_exp: SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1
motivated_by: "Job 11524255 exact-identity block plus user-frozen homology-split contract"
track: S0-predata
profile: smoke
status: failed
primary_metric: datasets_scanned_before_resource_stop
value: 30000
vs_anchor: "30,000/321,856; terminal identity unavailable"
one_liner: "Partition-3 exact metadata scan was healthy but the reviewed 2h walltime was insufficient"
---

# SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1

## 问题

前一轮 provenance audit 中共有 279 个 RepeatMasker P-state identifiers 被记为 `missing`。其中许多是标准 L1/L2 family；Dfam 3.9 partition 3 又恰好是 12 个 frozen H5 partition 中唯一明确缺少 `Lookup/ByName` 的 leaf。因此，本 R0 先隔离回答：这些 missing 是否只是索引缺失，而能从 partition 3 的 canonical `Families/...` datasets metadata 中通过 exact `name` 恢复。

这不是 homology clustering，也不构建 train/validation/test split。只有 R0 结果闭合后，才能单独决定是否建立全 partition sequence catalog 和 homology graph。

## 冻结合同

- targets 是 Job 11524255 原子 payload 中 `resolution_status=missing` 的 279 个唯一 identifiers；既有 ambiguity `X13_LINE` 不进入 targets。
- source 固定为 Dfam 3.9 `dfam39_full.3.h5`，精确 size 为 63,939,647,016 bytes，并绑定既有 layout-manifest SHA、`rmlib.config` SHA、Dfam/FamDB metadata 与最新 `docs/19_evaluator_contract.md` SHA。本轮不新增 64 GB H5 全文件哈希。
- 扫描 canonical `Families` accession-bin tree 的全部 321,856 datasets；同时强制 `consensus` attribute count = 321,856、`model` attribute count = 321,818，并报告 accession/name/version presence counts。每 10,000 datasets 追加一条结构化 JSON progress event。只比较 dataset `name` attribute 的区分大小写 exact equality。
- 禁止 prefix、substring、case-fold、copy-derived proxy、clustering、split construction 和 model execution。
- recovered 必须只有一个唯一 `(versioned accession, consensus SHA-256)` identity，且 accession、version、consensus 均存在。零候选为 missing；多个不同 identity 为 ambiguous；字段不全为 invalid metadata。
- identifier count 与 annotation occurrence mass 分别在 recovered/missing/ambiguous/invalid-metadata 四态间精确守恒。

## 终态

- `RECOVERY_COMPLETE`：279/279 均由唯一 exact metadata identity 恢复，`semantic_success=true`、rc0；它最多令 `full_catalog_stage_authorized=true`，仍不授权 homology split 或训练。根据 docs/19，下一步必须先独立扫描全部 12 partitions 建立 full catalog。
- `IDENTITY_RECOVERY_TYPED_BLOCK`：扫描完整但仍有 missing/ambiguous/invalid metadata，`semantic_success=true`、rc0；需要官方 Dfam flat export 等新资产，不能用 genome copy 解除。
- `RECOVERY_FAILED`：输入漂移、dataset count/layout 异常、读取失败或守恒失败，`semantic_success=false`、rc2。
- 当前 preview 必须保持 `IMPLEMENTED_NOT_RUN`，不是科学结果，也不是 code-review PASS。

## 资源与执行边界

CPU-only Slurm 合同为 `private-teodoro-gpu`、4 CPU、48 GiB、2 小时、0 GPU。runner 要求正整数 `SLURM_JOB_ID`、pre-submit gate、owner lock、测试先行和原子 attempt publish。正式扫描前先发布 `RUNNING`，冻结 RUN/env/input/package hash 闭包；节点异常退出时不得保留旧 `IMPLEMENTED_NOT_RUN` 双真相。本轮只完成实现及登录节点静态验证，不扫描完整 partition、不提交作业。

## Combined exp 暂停说明

早期草拟的 `SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1` 将 resolver repair 与 homology graph 合并，诊断边界不够清楚；它未生成 preview、未进入审查、未提交。R0 结果闭合前不得晋升该 combined 路径。

## Result

- Job `11525316` passed pre-submit and 13/13 allocation-side tests, then performed the intended exact canonical metadata scan with 0 GPU.
- It emitted complete checkpoints at 10k, 20k and 30k datasets with steady I/O and no traceback. At 30k, elapsed time was about 1,480 seconds; the exhaustive projection was about 4.41 hours, so the controller cancelled before the certain 2-hour timeout.
- Audited terminal: `FAILED_RUN_CANCELLED_RESOURCE_MISMATCH`; `validate_goal=failed_run`; raw runner `RUNNING` is preserved and explicitly superseded by the audited status. Seventeen audited manifest entries rehash correctly.
- The zero candidates observed in the first 30k are not a result. No recovery table or downstream authorization exists.

## Findings

- The biological hypothesis remains unknown. The failure is serial HDF5 metadata traversal throughput, not evidence that partition 3 lacks the 279 identifiers.
- Any retry must preserve exact exhaustive semantics and add a reviewed resource/parallelization contract; R1/R2/GPU/S1 remain blocked.

## Decision

- `2/3 DEGRADED_REVIEW` completed: Claude and Codex agree on a deterministic 4-way read-only shard preflight; Antigravity failed three CLI compatibility retries.
- Pivot=`sanity check first`: a new exp-scoped 4CPU/16GiB/20min/0GPU throughput/correctness preflight is the only next compute. No automatic formal R0 retry, R1/R2/GPU/S1.

## Links

- Result log: `docs/06_results_log.md`
- Audit: `outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/`
- Sbatch: `sbatch/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1.sbatch`
