# cluster_config.yaml Schema

`smart-sbatch` reads `cluster_config.yaml` from the project root when it exists. The file overrides static inventory (e.g. `references/cluster_inventory.md`) and supplies project-specific limits, preferences, and output conventions.

If `cluster_config.yaml` is missing, fall back to defaults baked into `SKILL.md` and `references/cluster_inventory.md`.

## Sections

The file has 4 top-level sections:

| Section | Used by | Purpose |
|---|---|---|
| `hard_limits` | Phase 1 (policy guard) | Hard pass/fail gates. Any ❌ blocks submission. |
| `preferences` | Phase 2 (optimization) | Soft routing preferences (private bonus, queue tolerance, etc.). |
| `partitions` | Phase 1 (VRAM filter) + Phase 2 (routing) | Per-partition node lists, GPU types, VRAM, time limits. |
| `path_conventions` | Phase 1 (uniqueness checks) + output paths | Project-level output / log / checkpoint roots. Overrides lwcr default `outputs/<exp_id>/`. |

## Minimal example

```yaml
hard_limits:
  max_concurrent_jobs: 6
  max_array_size: 128
  min_vram_gb_default: 20      # large-model training filter
  partition_time_limits:
    private-teodoro-gpu: 168   # hours (7 days)
    shared-gpu: 12             # hours
  forbid_claim_from_profiles: [smoke, screen]

preferences:
  prefer_private_when_close: true
  private_bonus_hours: 0       # set >0 to bias toward private even when slightly slower
  shared_checkpoint_overhead_hours: 0.25
  default_efficient_min_gpus: 1
  always_exclude_nodes: [gpu023, gpu024, gpu036, gpu037, gpu038, gpu039, gpu040, gpu041, gpu042, gpu043]

partitions:
  private-teodoro-gpu:
    nodes: [gpu034, gpu035]
    gpu_type: nvidia_geforce_rtx_3090
    gpus_per_node: 8
    vram_gb: 24
    time_limit_hours: 168
  shared-gpu:
    # Subset of /shared/ pool relevant to large-model jobs.
    high_memory_nodes:
      - {nodes: [gpu027], gpu_type: a100_80gb_pcie, gpus_per_node: 1, vram_gb: 80}
      - {nodes: [gpu029], gpu_type: a100_80gb_pcie, gpus_per_node: 4, vram_gb: 80}
      - {nodes: [gpu032, gpu033], gpu_type: a100_80gb_pcie, gpus_per_node: 3, vram_gb: 80}
      - {nodes: [gpu020, gpu030, gpu031], gpu_type: a100_40gb_pcie, gpus_per_node: 4, vram_gb: 40}
      - {nodes: [gpu022], gpu_type: a100_40gb_pcie, gpus_per_node: 7, vram_gb: 40}
      - {nodes: [gpu048], gpu_type: rtx_a6000, gpus_per_node: 8, vram_gb: 48}
    standard_24gb_nodes:
      - {nodes: [gpu017, gpu021, gpu025, gpu026, gpu034, gpu035, gpu049], gpu_type: rtx_3090_or_4090, gpus_per_node: 8, vram_gb: 24}
      - {nodes: [gpu044, gpu046, gpu047], gpu_type: rtx_a5000_or_a5500, gpus_per_node: 8, vram_gb: 24}
    excluded_nodes: [gpu023, gpu024, gpu036, gpu037, gpu038, gpu039, gpu040, gpu041, gpu042, gpu043]
    ambiguous_nodes: [gpu050]   # confirm exact VRAM via sinfo/nvidia-smi before use
    time_limit_hours: 12

path_conventions:
  output_root: outputs/         # all per-experiment artifacts under <output_root>/<exp_id>/
  log_root: logs/               # sbatch --output / --error
  checkpoint_root: outputs/     # <output_root>/<exp_id>/checkpoints/
```

## Field reference

### `hard_limits` (Phase 1 enforced)

| Field | Type | Meaning |
|---|---|---|
| `max_concurrent_jobs` | int | Block submission if `running + queued ≥` this value. |
| `max_array_size` | int | Block `sbatch --array` requests above this size. |
| `min_vram_gb_default` | float | Default minimum VRAM filter for large-model jobs. Per-job override allowed via `$ARGUMENTS`. |
| `partition_time_limits` | dict | Hard wall-clock cap per partition. |
| `forbid_claim_from_profiles` | list | Profile names (`smoke`, `screen`, …) that may NOT claim SOTA in `/result-log` / `/pivot`. |

### `preferences` (Phase 2 soft tuning)

| Field | Type | Meaning |
|---|---|---|
| `prefer_private_when_close` | bool | When private and shared completion estimates differ by < ~1h, pick private. |
| `private_bonus_hours` | float | Subtract this from private completion score to model "free quota" preference. `0` = pure speed. |
| `shared_checkpoint_overhead_hours` | float | Per-segment restart cost added to shared completion estimate when splitting across 12h chunks. |
| `default_efficient_min_gpus` | int | If `$ARGUMENTS` does not give `efficient_min_gpus`, use this. |
| `always_exclude_nodes` | list | Project-wide default exclude list (applied to `--exclude=…`). |

### `partitions`

Each partition entry should give enough detail for the VRAM filter and routing tables. The shared-gpu structure shown above (`high_memory_nodes` + `standard_24gb_nodes` + `excluded_nodes` + `ambiguous_nodes`) mirrors `references/cluster_inventory.md` so the two can be cross-checked.

### `path_conventions`

| Field | Type | Meaning |
|---|---|---|
| `output_root` | path | Parent of `<exp_id>/` per-experiment artifacts. Default `outputs/`. |
| `log_root` | path | sbatch log root. Default `logs/`. |
| `checkpoint_root` | path | Checkpoint parent. Default same as `output_root`. |

`smart-sbatch` Phase 1 checks that `<output_root>/<exp_id>/`, `<checkpoint_root>/<exp_id>/`, `<log_root>/<job_name>_%j.{out,err}` are unique across concurrent jobs.

## How Phase 1 vs Phase 2 consume the schema

| Phase | Reads |
|---|---|
| Phase 1 (policy guard) | `hard_limits` + `partitions.*.vram_gb` + `partitions.*.time_limit_hours` + `path_conventions` |
| Phase 2 (optimization) | `preferences` + `partitions` (all fields) + live `sinfo`/`squeue`/`scontrol show reservation` output |

Phase 1 is strictly non-negotiable; Phase 2 is allowed to weigh trade-offs.

## When to customize per project

When a new project clones the lwcr template:

1. Copy `cluster_config.yaml.example` to `cluster_config.yaml`.
2. Adjust `hard_limits.max_concurrent_jobs` to your real quota.
3. Adjust `path_conventions.*` if the project uses `runs/`, `experiments/`, etc.
4. Keep `partitions` aligned with `references/cluster_inventory.md` unless your cluster differs.
