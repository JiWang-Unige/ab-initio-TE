#!/bin/bash
#SBATCH --job-name=te_braker_readiness
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=outputs/TRADITIONAL-GENE-PIPELINE-20260925/logs/%x-%j.out
#SBATCH --error=outputs/TRADITIONAL-GENE-PIPELINE-20260925/logs/%x-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
python3 -u scripts/experiments/TRADITIONAL-GENE-PIPELINE-20260925/preflight.py "$@"
