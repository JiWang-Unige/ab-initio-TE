#!/usr/bin/env bash
# CPU-only fixed chr10/chr20 extraction; no labels or model outputs are read.
#SBATCH --job-name=classmap-prepare
#SBATCH --array=0-1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/classmap-prepare-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/classmap-prepare-%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
SPECIES=(chicken zebrafish)
python3 scripts/experiments/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/prepare_targets.py \
  --species "${SPECIES[$SLURM_ARRAY_TASK_ID]}"
