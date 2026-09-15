#!/bin/bash
#SBATCH --job-name=te-long-D-gpu
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/D-gpu-%j.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
TE_DATASET=${1:?dataset required}
/usr/bin/time -v python3 scripts/experiments/TE-LONG-BENCH-20260915/glm.py \
  --root "$TASK_ROOT" --dataset "$TE_DATASET" \
  --output "outputs/TE-LONG-BENCH-20260915/D-gpu-$SLURM_JOB_ID/$TE_DATASET"
