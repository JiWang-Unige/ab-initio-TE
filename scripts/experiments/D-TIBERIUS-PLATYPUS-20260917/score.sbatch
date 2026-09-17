#!/bin/bash
#SBATCH --job-name=D-tib-plat-score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=logs/D-tib-plat-score-%j.out
#SBATCH --error=logs/D-tib-plat-score-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
python3 scripts/experiments/D-TIBERIUS-PLATYPUS-20260917/score.py
