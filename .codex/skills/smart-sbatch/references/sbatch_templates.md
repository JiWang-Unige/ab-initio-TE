# Sbatch Templates

Use these as starting points. Always adapt CPU count, memory, modules, conda environment, command, log paths, and exact GRES syntax to the local cluster.

## Contents

1. CPU-only private job, 0 GPUs
2. Private GPU long job
3. Shared GPU checkpointable job
4. GPU filter and exclude examples
5. Resume-friendly training notes

## 1. CPU-only private job, 0 GPUs

Use this for CPU-only commands. The important rule is to request no GPUs while using `private-teodoro-gpu`.

```bash
#!/bin/bash
#SBATCH --job-name=cpu_private
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs

# No GPU request: omit --gres=gpu and --gpus.
# If the local Slurm requires explicit zero GPUs, use the cluster-approved syntax only.

srun bash -lc 'python your_cpu_script.py --arg value'
```

If the command is expected to run 5 days and no maintenance intervenes, use `--time=5-00:00:00`. If maintenance starts in 2 days, use a shorter valid walltime only if partial CPU progress is useful.

## 2. Private GPU long job

Use this when private is suitable for a long GPU run.

```bash
#!/bin/bash
#SBATCH --job-name=train_private
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=4-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs checkpoints

# Load modules / activate env here.
# module load cuda
# conda activate your_env

srun bash -lc 'python train.py --checkpoint-dir checkpoints --resume auto'
```

If the local Slurm supports typed GRES and the exact GPU type is known, use a typed request such as:

```bash
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:4
```

If typed GRES is not reliable, request a GPU count and use the partition/node filter strategy approved for the cluster.

## 3. Shared GPU checkpointable job

Use this for checkpointable jobs where shared is faster or private has too few GPUs.

```bash
#!/bin/bash
#SBATCH --job-name=train_shared_ckpt
#SBATCH --partition=shared-gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=11:50:00
#SBATCH --signal=B:USR1@600
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs checkpoints

_term() {
  echo "Received pre-time-limit signal; request training script to save checkpoint" >&2
  # If the training script supports a signal file, uncomment:
  # touch checkpoints/REQUEST_SAVE_AND_EXIT
}
trap _term USR1

srun bash -lc 'python train.py --checkpoint-dir checkpoints --resume auto --save-every-minutes 30'
```

Request less than 12h, such as `11:50:00`, to leave shutdown/checkpoint time.

## 4. GPU filter and exclude examples

Default exclude list for large-model jobs:

```bash
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
```

Prefer typed GRES or node constraints when supported, for example:

```bash
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:4
```

or:

```bash
#SBATCH --nodelist=gpu020,gpu022,gpu030,gpu031
```

Use exact names from `sinfo -o %G` rather than guessing.

## 5. Resume-friendly training notes

For any shared run expected to continue beyond 12h:
- save checkpoints frequently
- resume from `latest` or a known checkpoint path
- write checkpoints atomically if possible
- record the Slurm job ID and training step in logs
- test restart once with a short run before relying on multi-segment training
