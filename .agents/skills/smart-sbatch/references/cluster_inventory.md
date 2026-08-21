# Teodoro Cluster Inventory Reference

This reference is based on the user-provided inventory. Treat it as static guidance only. Always query current Slurm state before submitting.

## Contents

1. Private partition
2. Shared GPU inventory by suitability
3. Default excluded nodes
4. Ambiguous nodes
5. Practical routing notes

## 1. Private partition

`private-teodoro-gpu`:

| Nodes | GPU | Count per node | VRAM assumption | Time limit |
|---|---|---:|---:|---:|
| gpu034-gpu035 | RTX 3090 | 8 | 24GB | 7 days |

These nodes also appear in `shared-gpu` with a 12h limit. Prefer their private partition for long jobs when queue time and GPU count are reasonable.

## 2. Shared GPU inventory by suitability

### Strong choices for large-model jobs

| Nodes | GPU type | Count | Notes |
|---|---|---:|---|
| gpu027 | A100 80GB PCIe | 1 | best for high-memory single-GPU runs |
| gpu029 | A100 80GB PCIe | 4 | strong high-memory multi-GPU node |
| gpu032-gpu033 | A100 80GB PCIe | 3 each | high-memory, 3-GPU nodes |
| gpu045 | A100 80GB PCIe | 2 | high-memory 2-GPU node |
| gpu020 | A100 40GB PCIe | 4 | strong for large models |
| gpu022 | A100 40GB PCIe | 7 | strong multi-GPU node |
| gpu028 | A100 40GB PCIe | 1 | high-memory single-GPU work |
| gpu030-gpu031 | A100 40GB PCIe | 4 each | strong for large models |
| gpu048 | RTX A6000 | 8 | 48GB GPUs, strong shared option |

### Usable >=20GB shared choices

| Nodes | GPU type | Count | Notes |
|---|---|---:|---|
| gpu049 | RTX 4090 | 8 | 24GB, high throughput, 12h shared only |
| gpu017 | RTX 3090 | 8 | 24GB |
| gpu021 | RTX 3090 | 8 | 24GB |
| gpu025 | RTX 3090 | 8 | 24GB |
| gpu026 | RTX 3090 | 8 | 24GB, large memory node |
| gpu034-gpu035 | RTX 3090 | 8 each | prefer private when suitable |
| gpu044 | RTX A5000 | 8 | 24GB |
| gpu046 | RTX A5500 | 8 | 24GB |
| gpu047 | RTX A5000 | 8 | 24GB |

## 3. Default excluded nodes

Exclude RTX 3080 nodes for large-model jobs unless the user explicitly allows lower VRAM:

```text
gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
```

Rationale: RTX 3080 is usually below the 20GB VRAM threshold and is not useful for the user's large-model training workload.

## 4. Ambiguous nodes

`gpu050` is listed as `nvidia_rtx_5000 x 4`. Confirm the exact model and VRAM before using it:

- If RTX 5000 Ada 32GB: eligible.
- If older RTX 5000 16GB: exclude for large-model jobs.

Check with Slurm GRES, node features, or `nvidia-smi` before routing large-model work there.

## 5. Practical routing notes

- Prefer A100 80GB and A100 40GB when memory is the bottleneck.
- Prefer RTX 4090 / A6000 / A100 when short shared runs need fast throughput.
- Prefer private RTX 3090 nodes for long continuous runs if queue and GPU count are acceptable.
- Do not use private with only 1–2 GPUs for multi-GPU training if this would make the run too slow and the job checkpoints reliably.
