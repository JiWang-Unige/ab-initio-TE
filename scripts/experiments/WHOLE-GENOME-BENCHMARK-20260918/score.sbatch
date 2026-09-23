#!/bin/bash
#SBATCH --job-name=wg-score
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/wg-score-%j.out
#SBATCH --error=logs/wg-score-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

ARGS=(--output-dir "${OUTPUT_DIR:-/home/users/j/jwang/ab-initio-TE/outputs/WHOLE-GENOME-BENCHMARK-20260918/score}")
if [[ -n "${NATIVE_METHOD_ROOTS:-}" ]]; then
  ARGS+=(--native-method-roots "$NATIVE_METHOD_ROOTS")
fi
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/score.py "${ARGS[@]}"
