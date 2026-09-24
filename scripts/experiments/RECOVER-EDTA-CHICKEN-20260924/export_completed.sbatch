#!/bin/bash
#SBATCH --job-name=edta-export-completed
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=logs/edta-export-%j.out
#SBATCH --error=logs/edta-export-%j.err
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
python3 scripts/experiments/RECOVER-EDTA-CHICKEN-20260924/export_completed.py \
  --root "$TASK_ROOT" \
  --source "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-aggregate-final-13190938" \
  --output "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-export-${SLURM_JOB_ID}"
