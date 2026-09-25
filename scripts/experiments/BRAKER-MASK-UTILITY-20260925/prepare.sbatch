#!/bin/bash
#SBATCH --job-name=te_braker_prepare
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.out
#SBATCH --error=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
python3 -u "scripts/experiments/BRAKER-MASK-UTILITY-20260925/$1.py" "${@:2}"
