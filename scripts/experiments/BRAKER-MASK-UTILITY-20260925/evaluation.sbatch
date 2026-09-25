#!/bin/bash
#SBATCH --job-name=te_braker_eval_prepare
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.out
#SBATCH --error=outputs/BRAKER-MASK-UTILITY-20260925/logs/%x-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
python3 -u scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py prepare --species chicken
python3 -u scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py prepare --species zebrafish --download-long-read
