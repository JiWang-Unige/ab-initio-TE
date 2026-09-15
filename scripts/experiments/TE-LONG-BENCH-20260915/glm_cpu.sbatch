#!/bin/bash
#SBATCH --job-name=te-long-D-cpu
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=24:00:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/D-cpu-%j.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 MKL_NUM_THREADS=16
TE_DATASET=${1:?dataset required}
/usr/bin/time -v python3 scripts/experiments/TE-LONG-BENCH-20260915/glm.py \
  --root "$TASK_ROOT" --dataset "$TE_DATASET" --cpu \
  --output "outputs/TE-LONG-BENCH-20260915/D-cpu-$SLURM_JOB_ID/$TE_DATASET"
