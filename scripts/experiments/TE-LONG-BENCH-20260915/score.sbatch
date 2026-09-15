#!/bin/bash
#SBATCH --job-name=te-long-score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=01:00:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/score-%j.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 scripts/experiments/TE-LONG-BENCH-20260915/score.py \
  --output "outputs/TE-LONG-BENCH-20260915/score-$SLURM_JOB_ID/result.json"
