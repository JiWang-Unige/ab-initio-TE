#!/usr/bin/env bash
#SBATCH --job-name=gap-ab1-audit
#SBATCH --partition=shared-cpu
#SBATCH --gres=none
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=logs/gap-ab1-audit_%j.out
#SBATCH --error=logs/gap-ab1-audit_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 PYTHONUNBUFFERED=1
python scripts/experiments/GAP-A-B1-SCREEN-20260908-R1/verify_result.py
