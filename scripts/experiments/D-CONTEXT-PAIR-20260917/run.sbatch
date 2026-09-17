#!/bin/bash
#SBATCH --job-name=D-context-pair
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/D-context-pair-%j.out
#SBATCH --error=logs/D-context-pair-%j.err
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
python3 scripts/experiments/D-CONTEXT-PAIR-20260917/context_pair.py --root "$TASK_ROOT" \
  --output "outputs/D-CONTEXT-PAIR-20260917/run-$SLURM_JOB_ID"
