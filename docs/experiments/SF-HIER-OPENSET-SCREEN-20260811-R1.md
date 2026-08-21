---
exp_id: SF-HIER-OPENSET-SCREEN-20260811-R1
date: 2026-08-11
approach_family: hierarchical-open-set-superfamily
parent_exp: PIPE-TEFM-LOCK-20260619
motivated_by: "remote-family severe-error reduction with ontology-aware abstention"
track: A
profile: smoke
status: parked
primary_metric: asset_gate_pass
value: 0.0
vs_anchor: "FOUNDATIONAL_TYPED_BLOCK"
one_liner: "ontology/homology-component/clade split 未冻结；科学 screen 未授权"
---

# SF-HIER-OPENSET-SCREEN-20260811-R1

## 结论

状态为 `FOUNDATIONAL_TYPED_BLOCK`。这是一次计算节点上的只读、claim-ineligible 资产闸核验；未实现、未运行 hierarchical open-set 科学 screen。

## 假设与必需合同

只有在 Dfam/ontology target、family 或 homology components、clade-held-out split、validation-only calibration，以及 historical direct-head exact rejoin 全部冻结并通过泄漏审计后，才允许比较 flat head、k-mer/prototype 与 hierarchical predictor。

## 复现入口

```bash
srun <cpu-allocation> python3 scripts/experiments/SF-HIER-OPENSET-SCREEN-20260811-R1/verify_asset_gate.py \
  --config configs/SF-HIER-OPENSET-SCREEN-20260811-R1.yaml \
  --output outputs/SF-HIER-OPENSET-SCREEN-20260811-R1
```

该入口只复核已冻结证据并输出 typed blocker；若资产闸意外全部通过，它会拒绝继续，因为本 exp 不包含科学 screen 实现。

## 当前阻塞

- canonical snapshot 仅授权 S0 input review，不授权模型/科学运行；
- split manifest 没有 family/homology-component 与 clade keys；
- `SF-TARGET` 仍为 draft/TBD；
- production homology allowlist/manifest 缺失；
- historical direct-superfamily head 未 exact-rejoin 到 canonical loci。

## 产物

- `asset_gate_report.json`：逐项 fail-closed 审计；
- `metrics.json`：有限数值、`primary_metric=0.0`，且明确 screen 未运行；
- `input_manifest.json`、`environment_manifest.json`、`output_manifest.sha256`；
- `STATUS=FOUNDATIONAL_TYPED_BLOCK`。

Asset-gate allocation：短 `srun` Job `11519729`，`COMPLETED 0:0`，1 CPU/1 GB、0 GPU、实际 2 秒（与 E 共用 allocation）。Scientific screen job：未提交。Claim eligibility：false。

Cohort closeout：3/3 tri-review 保持本路线 asset-gated；ontology/homology-component/clade split 物化被保留为正交后续，但未获本 cohort 的继续执行授权。
