# Slurm Diagnostics Commands

Use these commands when shell access to the cluster is available. They are examples; adapt format strings to local Slurm version if needed.

## Contents

1. Partition and node status
2. Queue status
3. Reservations and maintenance
4. GPU allocation details
5. Common interpretation rules

## 1. Partition and node status

```bash
sinfo -p private-teodoro-gpu,shared-gpu -N -o "%N|%P|%T|%G|%c|%m|%l|%E"
```

**Allocation-aware (preferred — total vs used GRES per node):**

```bash
sinfo -p private-teodoro-gpu,shared-gpu -N -O "nodehost,statecompact,gres:30,gresused:30"
```

`gres` = configured GPUs, `gresused` = allocated GPUs. **Free GPUs = gres − gresused**.
This, not `nvidia-smi`, decides whether you can actually get a GPU (see decision_policy §0).

Useful fields:
- node name
- partition
- state
- GRES/GPU type
- CPUs
- memory
- time limit
- reason, including drain/down/maintenance notes

Alternative detailed format:

```bash
sinfo -p private-teodoro-gpu,shared-gpu -N -O nodehost,partition,statecompact,gres,cpusstate,memory,timelimit,reason
```

## 2. Queue status

```bash
squeue -p private-teodoro-gpu,shared-gpu -o "%.18i %.12P %.30j %.12u %.2t %.10M %.10l %.6D %R"
```

For the user's own jobs:

```bash
squeue -u "$USER" -o "%.18i %.12P %.30j %.2t %.10M %.10l %.6D %R"
```

Estimate start time if the cluster supports it:

```bash
squeue --start -p private-teodoro-gpu,shared-gpu
```

## 3. Reservations and maintenance

```bash
scontrol show reservation
```

For specific private nodes:

```bash
scontrol show node gpu034
scontrol show node gpu035
```

Look for reservation, drain, planned maintenance, or unavailable windows. Use the earliest relevant maintenance/reservation start as the upper bound for requested walltime.

## 4. GPU allocation details

```bash
scontrol show node gpu034 | egrep "NodeName=|Gres=|CfgTRES=|AllocTRES=|State=|Reason="
scontrol show node gpu035 | egrep "NodeName=|Gres=|CfgTRES=|AllocTRES=|State=|Reason="
```

If allowed on an allocated node:

```bash
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
```

## 5. Common interpretation rules

- **Allocation, not physical occupancy, decides availability** (decision_policy §0). Free GPUs per node = `gres − gresused` (= `CfgTRES.gpu − AllocTRES.gpu`). A node idle in `nvidia-smi` but `alloc` in Slurm is **not** usable.
- `idle` nodes are fully free and immediately usable if partition and constraints match.
- `mix` nodes are partially free; compute free GPUs from `gresused` / `AllocTRES`, don't assume a whole node.
- `alloc` nodes have 0 free GPUs even if physically idle — skip them.
- `drain`, `down`, `maint`, or reservation reasons mean the node may not be usable even if it appears in the inventory.
- **Subtract the queue ahead**: pending jobs (`squeue -t PD`) with priority may take free GPUs before you. Prefer `squeue --start` for the scheduler's own start-time estimate.
- If `squeue --start` predicts a private start time later than a short job would finish on shared, prefer shared.
- If a 7-day private request fails because of maintenance, retry with a shorter walltime only if that shorter window is useful.
