---
exp_id: EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1
date: 2026-08-11
approach_family: representation-falsification
parent_exp: PIPE-TEFM-EMBED-R2-CODEGATE-20260809-R3
motivated_by: "sealed fair-baseline test before interpreting pretrained embeddings"
track: A
profile: smoke
status: parked
primary_metric: asset_gate_pass
value: 0.0
vs_anchor: "FOUNDATIONAL_TYPED_BLOCK"
one_liner: "2,200 bindings/weights/backend pins 未闭合；falsification screen 未授权"
---

# EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1

## 结论

状态为 `FOUNDATIONAL_TYPED_BLOCK`。这是一次计算节点上的只读、claim-ineligible 资产闸核验；未实现、未运行 embedding representation 科学 falsification screen。

## 假设与必需合同

只有 exact 2,200 family/copy/species/component bindings、sealed split、backend pins，以及 exact pretrained/untrained weights 全部冻结后，才允许用同一预算比较 representation 与 k-mer/MinHash/alignment/length-GC/random/untrained controls。

## 复现入口

```bash
srun <cpu-allocation> python3 scripts/experiments/EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1/verify_asset_gate.py \
  --config configs/EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1.yaml \
  --output outputs/EMB-REPRESENTATION-FALSIFICATION-SCREEN-20260811-R1
```

该入口只复核已冻结证据并输出 typed blocker；若资产闸意外全部通过，它会拒绝继续，因为本 exp 不包含科学 screen 实现。

## 当前阻塞

- Dfam 2,200 records 存在，但没有 exact `family_id/copy_id/component_id/accession` bindings；
- genomic records 没有 assembly/family/copy/component 完整绑定；
- 既往审计没有 validated fallback；exact backend、pretrained/untrained weight identities 未闭合；
- 因而 family/copy/species leakage audit 与 sealed biological split 均不可成立。

## 产物

- `asset_gate_report.json`：逐项 fail-closed 审计；
- `metrics.json`：有限数值、`primary_metric=0.0`，且明确 screen 未运行；
- `input_manifest.json`、`environment_manifest.json`、`output_manifest.sha256`；
- `STATUS=FOUNDATIONAL_TYPED_BLOCK`。

Asset-gate allocation：短 `srun` Job `11519729`，`COMPLETED 0:0`，1 CPU/1 GB、0 GPU、实际 2 秒（与 S 共用 allocation）。Scientific screen job：未提交。Claim eligibility：false。

Cohort closeout：3/3 tri-review 保持本路线 asset-gated；exact bindings、sealed split、backend/weight identities 未冻结前不得启动 representation comparison。
