#!/bin/bash
#SBATCH --job-name=tib-external-score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/P3-TIBERIUS-EXTERNAL-20260915/logs/score-%j.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/score.py
