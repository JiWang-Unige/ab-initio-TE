#!/usr/bin/env bash
# CPU-only class-map scorer. The submitter must supply a dependency that keeps
# completed class-map cells available; native cells may be absent or failed and
# are recorded as explicit NA rows. This script does not infer or replace
# scheduler dependencies.
# Example (class maps must pass; native attempts only need to settle):
# sbatch --dependency=afterok:<classmap-array>,afterany:<native-attempts> score.sbatch
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
