#!/bin/bash
# Repair the completed EarlGrey cells whose resumed final RM omitted -l.
# The Python driver copies the preserved work tree and never mutates its source.
#SBATCH --job-name=te-long-eg-repair
#SBATCH --partition=public-cpu
#SBATCH --constraint=E5-2630V4
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=24:00:00
#SBATCH --array=0-1%2
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/earlgrey-recovery-%A_%a.log
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 MKL_NUM_THREADS=16

DATASETS=(c_briggsae sim100)
if [[ -n "${EARLGREY_RECOVERY_SOURCE_ARRAY_JOB_ID:-}" ]]; then
  SOURCE_ARRAY_JOB_ID=$EARLGREY_RECOVERY_SOURCE_ARRAY_JOB_ID
  COMPLETED=(
    "outputs/TE-LONG-BENCH-20260915/native-$SOURCE_ARRAY_JOB_ID/c_briggsae-earlgrey"
    "outputs/TE-LONG-BENCH-20260915/native-$SOURCE_ARRAY_JOB_ID/sim100-earlgrey"
  )
else
  COMPLETED=(
    "outputs/TE-LONG-BENCH-20260915/native-12738271/c_briggsae-earlgrey"
    "outputs/TE-LONG-BENCH-20260915/native-12738272/sim100-earlgrey"
  )
fi

DATASET=${DATASETS[$SLURM_ARRAY_TASK_ID]}
COMPLETED_CELL=${COMPLETED[$SLURM_ARRAY_TASK_ID]}
python3 scripts/experiments/TE-LONG-BENCH-20260915/earlgrey_recovery.py \
  --root "$TASK_ROOT" \
  --dataset "$DATASET" \
  --completed "$COMPLETED_CELL" \
  --output "outputs/TE-LONG-BENCH-20260915/native-$SLURM_ARRAY_JOB_ID/$DATASET-earlgrey"
