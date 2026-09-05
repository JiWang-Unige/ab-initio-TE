#!/usr/bin/env bash
#SBATCH --job-name=te_l1_init_ci
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_init_ci_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_init_ci_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
# Seed42 scientific NO-GO: descriptive cached uncertainty only, no seed17.
srun python3 scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1/assess_init_uncertainty.py \
  --seed42-p0r-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/evaluate/seed42/12398639_1" \
  --seed42-h0r-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/evaluate/seed42/12398639_0" \
  --seed42-d-anchor-j0-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_recover/12385502/seed42" \
  --output "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/uncertainty/$SLURM_JOB_ID/seed42.json"
