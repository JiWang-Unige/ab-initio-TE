---
exp_id: DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1
date: 2026-08-11
approach_family: conservative-transfer-routing
parent_exp: PIPE-TEFM-PURSUE-SELECTOR-MINHASH-20260630
motivated_by: "exact provenance gate before any transfer-surface fitting"
track: A
profile: smoke
status: parked
primary_metric: asset_gate_pass
value: 0.0
vs_anchor: "FOUNDATIONAL_TYPED_BLOCK"
one_liner: "5/5 anchor run records 缺失；transfer surface 不可启动"
---

# DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1

- 路线：G，decay/transfer surface。
- 实际动作：计算节点上的只读资产闸门审计；未运行科学 screen。
- Asset-gate allocation：短 `srun` Job `11519717`，`COMPLETED 0:0`，1 CPU/1 GB、0 GPU、实际 1 秒。
- 终态：`FOUNDATIONAL_TYPED_BLOCK`。
- claim eligibility：否。

## 判定

现有 P1 seal 不能授权 G 的 scientific screen。5 个固定 anchor 的 provenance run record 全部缺失，因此无法确认 exact training genomes、代码、配置与评估口径，也不能合法构建 clade holdout 或拟合 uncertainty surface。

类型化阻塞：`G_P1_ALL_FIVE_PROV_RUN_RECORD_MISSING`。

缺失 anchor：

- `animal`: `PROV_RUN_RECORD_MISSING`
- `cross`: `PROV_RUN_RECORD_MISSING`
- `human_h0`: `PROV_RUN_RECORD_MISSING`
- `insect`: `PROV_RUN_RECORD_MISSING`
- `plant`: `PROV_RUN_RECORD_MISSING`

## 冻结证据入口

- seal：`reports/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R2/P1_READINESS_SEAL_V1.json`
- run summary：`software_outputs/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R2/SLURM_RUN_SUMMARY.json`
- anchor provenance：`reports/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R2/FIXED_ANCHOR_PROVENANCE_V1.json`
- failure table：`reports/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R2/PROVENANCE_FAILURE_REPORT_V1.tsv`

所有输入 SHA-256 见 `outputs/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1/input_manifest.tsv`。

## 可重现入口与边界

`scripts/experiments/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1/verify_asset_gate.py` 只校验输入哈希、P1 readiness 与 5-anchor 精确状态，并重建有限 `metrics.json`、manifests、报告及 `STATUS`。仅在完整复现当前阻塞时返回 code 2；证据缺失或状态漂移会写 `INVALID_RUN`、`semantic_success=false` 并返回 code 3。

P1 seal 明确不授权 Mash 获取/运行、panel/cube 构建、checkpoint evaluation、FATS/PAS 拟合、模型训练或 scientific claim。解锁前必须为 5 个 anchor 补齐可验证的 run record，再重建 provenance 并取得新的 PASS seal；随后仍需另行冻结物种/基因组集合、clade holdout、checkpoint/evaluator 和 uncertainty calibration 合约。

Cohort closeout：3/3 tri-review 保持本路线 asset-gated；五 anchor provenance reconstruction 只作为 reviewer-proposed 后续，不用 clean rebuild 绕过缺失 run records。
