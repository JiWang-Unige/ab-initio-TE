# Decision Policy

## Contents

0. **Allocation is authoritative (NOT physical occupancy)**
1. Core objective
2. CPU-only routing
3. GPU memory filter
4. Private-vs-shared decision logic
5. Maintenance and reservation windows
6. Low private GPU availability
7. Checkpointing requirements
8. Recommended final answer format

## 0. Allocation is authoritative (NOT physical occupancy) — HARD

A GPU is usable to you **only if Slurm has not already allocated it**, regardless of
how idle it looks physically. A node can show near-zero GPU memory use in `nvidia-smi`
yet be fully allocated to a running/suspended job or held by a pending reservation —
in that case you **cannot** get it. Decide availability from the Slurm scheduler, never
from physical occupancy.

**Authoritative free-GPU count per node:**

```text
free_gpus(node) = CfgTRES.gres/gpu(node) - AllocTRES.gres/gpu(node)
```

Read it from the scheduler:

```bash
# Per-node total vs allocated GRES (one line per node):
sinfo -p private-teodoro-gpu,shared-gpu -N -O "nodehost,statecompact,gres:30,gresused:30"
# or, exact TRES on a node:
scontrol show node gpu034 | egrep "CfgTRES=|AllocTRES=|State=|Reason="
```

- `gres` = configured total; `gresused` = currently allocated. Free = total − used.
- `alloc` state = fully allocated (0 free even if physically idle). `mix` = partially free (compute free from gresused). `idle` = fully free. `drain/down/maint/resv` = unusable.

**Also subtract the queue ahead of you.** Even if free GPUs exist now, pending jobs
with higher priority / earlier submission may consume them before yours starts:

```bash
squeue -p private-teodoro-gpu,shared-gpu -t PD -o "%.10i %.8u %.6D %.4C %b %r" --sort=i
squeue --start -p private-teodoro-gpu,shared-gpu   # scheduler's own start-time estimate (best signal)
```

Effective availability for your job ≈ `free_gpus_now − GPUs claimed by pending jobs ahead`,
or simply trust `squeue --start` when the cluster provides it.

**Rules:**
- NEVER use `nvidia-smi` memory/utilization to decide whether a GPU is *available*. Use it
  only (if at all) to confirm GPU *type/VRAM* on a node you have already been allocated.
- If `gresused`/`AllocTRES` cannot be read (no shell access), fall back to the static
  inventory in `references/cluster_inventory.md` and **state the assumption explicitly**;
  do not assume idle.
- Prefer `squeue --start` over any local heuristic for queue-wait estimation.

## 1. Core objective

Optimize for fastest reliable completion while efficiently using `private-teodoro-gpu` quota. `private-teodoro-gpu` has a preference because it is free and can run up to 7 days, but that preference must not override obviously faster or safer `shared-gpu` plans.

Think in terms of:

```text
estimated_completion_time = queue_wait_time + runtime + checkpoint/restart_overhead + failure_or_maintenance_risk
```

Prefer private when the private plan is close to shared. Prefer shared when shared reaches a useful result substantially earlier.

## 2. CPU-only routing

CPU-only commands are a hard fast path:

```text
if job_requires_gpu == false:
    partition = private-teodoro-gpu
    gpus = 0
    walltime = min(estimated_runtime, private_time_limit, maintenance_free_window)
```

Rationale: other CPU partitions are time-limited, while `private-teodoro-gpu` can run up to 7 days and can be used with 0 GPUs.

Implementation notes:
- Omit GPU directives in Slurm unless explicit zero-GPU syntax is required locally.
- Do not use `shared-gpu` for CPU-only work by default.
- Do not route CPU-only work to normal CPU nodes by default.
- Still check maintenance/reservation windows; do not request 7 days if fewer days are actually available.

## 3. GPU memory filter

For large-model GPU jobs:

```text
effective_vram_requirement = max(user_requested_vram, 20GB)
```

Default behavior:
- allow GPU types with >=20GB VRAM
- exclude RTX 3080 nodes
- treat ambiguous GPU names as unknown until checked with `sinfo -O gres`/`scontrol show node`/cluster docs (VRAM/type only; for *availability* use §0 allocation, not nvidia-smi)

If the user explicitly says the job is small enough for a lower-memory GPU, this filter may be relaxed.

## 4. Private-vs-shared decision logic

### Short jobs, expected runtime <= 12h

Use the plan that starts and finishes sooner.

```text
if expected_runtime <= 12h:
    if private starts quickly and has enough GPUs:
        choose private
    else:
        choose shared
```

Examples: debugging, evaluation, short ablation, data preprocessing, 3h training. If private queue wait is longer than the entire shared run, use shared.

### Long checkpointable jobs, expected runtime > 12h

Compare private continuous execution with shared 12h chunks.

Choose private when:
- private queue is reasonable
- private has at least `efficient_min_gpus`
- the maintenance-free window is enough for a useful run

Choose shared when:
- checkpointing is reliable
- shared can start much earlier
- shared has more or better GPUs
- private has too few GPUs for useful throughput

Use shared only with regular checkpointing and a pre-time-limit save signal when possible.

### Long non-checkpointable jobs, expected runtime > 12h

Prefer `private-teodoro-gpu` even if waiting is necessary. Do not put a multi-day non-checkpointable job on a 12h partition unless the job can be restructured or only a short partial run is useful.

## 5. Maintenance and reservation windows

Do not hardcode 7 days. Always check actual available time before requesting walltime.

```text
private_walltime = min(estimated_needed_time, 7 days, time_until_maintenance - safety_buffer)
shared_walltime  = min(estimated_needed_time_or_segment, 12h, time_until_maintenance - safety_buffer)
```

If private has only 2–3 days before maintenance and the task needs 1–2 days, submit with the shorter valid walltime. If the task needs 5 days and is non-checkpointable, do not submit into a 2–3 day window.

## 6. Low private GPU availability

Distinguish between `min_gpus` and `efficient_min_gpus`:

- `min_gpus`: the job can technically run
- `efficient_min_gpus`: the job is worth running at useful speed

If private has fewer than `efficient_min_gpus`, do not submit there just because it is free.

For private availability of only 1–2 GPUs:
- OK for single-card experiments, evaluation, LoRA, inference, debugging, or CPU-only jobs
- usually bad for large multi-GPU training that needs 4–8 GPUs for useful throughput
- if checkpointable, prefer shared when shared has enough GPUs and starts sooner
- if non-checkpointable and multi-day, waiting for private may still be better

## 7. Checkpointing requirements

When using `shared-gpu` for jobs that exceed 12h:
- require frequent checkpoints
- verify that restart from checkpoint works
- save at least once well before the time limit
- use a Slurm signal such as `#SBATCH --signal=B:USR1@600` when supported
- restart from the latest checkpoint on resubmission

If checkpointing is unreliable, shared is appropriate only for debug runs or short partial results.

## 8. Recommended final answer format

Use this format:

```text
Recommendation: <partition and reason>
GPU/CPU request: <0 GPUs for CPU-only, or GPU count/type>
Walltime: <time and why it fits maintenance/time limit>
Nodes/GPU filter: <allowed/excluded>
Checkpoint plan: <if applicable>
Command/script: <sbatch/srun>
Assumptions: <only meaningful assumptions>
```
