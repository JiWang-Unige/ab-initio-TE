#!/bin/bash
#SBATCH --job-name=te-long-edta-recovery
#SBATCH --partition=public-cpu
#SBATCH --constraint=E5-2630V4
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=24:00:00
#SBATCH --array=0-1%2
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/edta-recovery-%A_%a.log
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 MKL_NUM_THREADS=16

DATASETS=(c_briggsae sim100)
if [[ -n "${EDTA_RECOVERY_SOURCE_ARRAY_JOB_ID:-}" ]]; then
  SOURCE_ARRAY_JOB_ID=$EDTA_RECOVERY_SOURCE_ARRAY_JOB_ID
  FAILED=(
    outputs/TE-LONG-BENCH-20260915/native-$SOURCE_ARRAY_JOB_ID/c_briggsae-edta
    outputs/TE-LONG-BENCH-20260915/native-$SOURCE_ARRAY_JOB_ID/sim100-edta
  )
else
  FAILED=(
    outputs/TE-LONG-BENCH-20260915/native-12731946/c_briggsae-edta
    outputs/TE-LONG-BENCH-20260915/native-12731947/sim100-edta
  )
fi
DATASET=${DATASETS[$SLURM_ARRAY_TASK_ID]}
FAILED_CELL=${FAILED[$SLURM_ARRAY_TASK_ID]}
python3 scripts/experiments/TE-LONG-BENCH-20260915/edta_recovery.py \
  --root "$TASK_ROOT" \
  --dataset "$DATASET" \
  --failed "$FAILED_CELL" \
  --output "outputs/TE-LONG-BENCH-20260915/native-$SLURM_ARRAY_JOB_ID/$DATASET-edta"
