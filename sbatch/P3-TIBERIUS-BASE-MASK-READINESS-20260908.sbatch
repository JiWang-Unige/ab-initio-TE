#!/usr/bin/env bash
#SBATCH --job-name=p3-mask-readiness
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/p3-mask-readiness_%j.out
#SBATCH --error=logs/p3-mask-readiness_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python scripts/experiments/P3-TIBERIUS-BASE-MASK-READINESS-20260908/audit.py
