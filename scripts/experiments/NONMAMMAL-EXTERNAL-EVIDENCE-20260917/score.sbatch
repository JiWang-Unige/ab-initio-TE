#!/usr/bin/env bash
#SBATCH --job-name=d_external_score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=logs/d_external_score_%j.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SPECIES=${1:?species is required}
INFERENCE_JOB=${2:?inference job id is required}
STRUCTURE_JOB=${3:?structure job id is required}
OUT="outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES"
python scripts/experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/score.py \
  --panel "$OUT/prepared" --inference "$OUT/inference-$INFERENCE_JOB" \
  --structure "$OUT/structure-$STRUCTURE_JOB" --output "$OUT/score-$SLURM_JOB_ID"
