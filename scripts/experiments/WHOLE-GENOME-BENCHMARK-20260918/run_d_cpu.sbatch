#!/bin/bash
#SBATCH --job-name=wg-d-cpu
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/wg-d-cpu-%j.out
#SBATCH --error=logs/wg-d-cpu-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
output_args=()
if [[ -n "${OUTPUT_DIR:-}" ]]; then
  output_args+=(--output-dir "${OUTPUT_DIR}")
fi
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/run_d.py \
  --species "${SPECIES:?set SPECIES}" --mode cpu "${output_args[@]}"
