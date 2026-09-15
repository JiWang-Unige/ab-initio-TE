#!/bin/bash
#SBATCH --job-name=te-long-native
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=24:00:00
#SBATCH --array=0-4%3
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/native-%A_%a.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 MKL_NUM_THREADS=16
TE_METHODS=(fixed_rm rm2_rm hite edta earlgrey)
TE_METHOD=${TE_METHODS[$SLURM_ARRAY_TASK_ID]}
TE_DATASET=${1:?dataset required}
python3 scripts/experiments/TE-LONG-BENCH-20260915/native.py --root "$TASK_ROOT" \
  --dataset "$TE_DATASET" --method "$TE_METHOD" \
  --output "outputs/TE-LONG-BENCH-20260915/native-$SLURM_ARRAY_JOB_ID/$TE_DATASET-$TE_METHOD"
