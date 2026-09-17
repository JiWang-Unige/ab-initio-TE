#!/usr/bin/env bash
#SBATCH --job-name=d_external_decompose
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=logs/d_external_decompose_%j.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
for PAIR in silkworm:12856610 d_simulans:12856612; do
  SPECIES=${PAIR%:*}
  SCORE_JOB=${PAIR#*:}
  OUT="outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES"
  python scripts/experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/decompose.py \
    --panel "$OUT/prepared" --score "$OUT/score-$SCORE_JOB" \
    --output "$OUT/source_decomposition_$SLURM_JOB_ID.json"
done
