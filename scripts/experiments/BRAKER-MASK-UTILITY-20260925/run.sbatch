#!/bin/bash
#SBATCH --job-name=te_braker_etp
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-5%2
#SBATCH --output=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%A_%a.out
#SBATCH --error=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%A_%a.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
species=(chicken zebrafish chicken zebrafish chicken zebrafish)
arms=(D D RM2_FULL RM2_FULL RED_FULL RED_FULL)
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
python3 -u scripts/experiments/BRAKER-MASK-UTILITY-20260925/run.py "${species[$SLURM_ARRAY_TASK_ID]}" "${arms[$SLURM_ARRAY_TASK_ID]}"
