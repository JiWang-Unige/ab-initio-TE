#!/bin/bash
#SBATCH --job-name=plat-strong-tib
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --array=0-19%1
#SBATCH --output=logs/plat-strong-tib-%A_%a.out
#SBATCH --error=logs/plat-strong-tib-%A_%a.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 scripts/experiments/PLATYPUS-STRONG-MASK-CONTROLS-20260917/run_tiberius_core.py "${MASK_METHOD:?}" "${SLURM_ARRAY_TASK_ID}"
