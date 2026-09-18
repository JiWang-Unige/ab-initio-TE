#!/usr/bin/env bash
# CPU-only class-map scorer.  The submitter must supply afterok dependencies
# for the class-map array and all four terminal native cells; this script does
# not infer or replace scheduler dependencies.
# Example:
# sbatch --dependency=afterok:<classmap_0>:<classmap_1>:<edta_chicken>:<rm2_chicken>:<edta_zebrafish>:<rm2_zebrafish> score.sbatch
#SBATCH --job-name=classmap-score
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/classmap-score-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/classmap-score-%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
CLASSMAP_OUTPUT_ROOT="${CLASSMAP_OUTPUT_ROOT:-$ROOT/outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/ntv2}"
CLASSMAP_SCORE_OUTPUT="${CLASSMAP_SCORE_OUTPUT:-$ROOT/outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/score}"
python3 scripts/experiments/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/score_class_maps.py \
  --config configs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918.json \
  --ntv2-root "$CLASSMAP_OUTPUT_ROOT" \
  --output-dir "$CLASSMAP_SCORE_OUTPUT"
