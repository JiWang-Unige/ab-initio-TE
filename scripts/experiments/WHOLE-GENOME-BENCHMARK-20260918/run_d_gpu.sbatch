#!/bin/bash
#SBATCH --job-name=wg-d-gpu
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/wg-d-gpu-%j.out
#SBATCH --error=logs/wg-d-gpu-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
output_args=()
if [[ -n "${OUTPUT_DIR:-}" ]]; then
  output_args+=(--output-dir "${OUTPUT_DIR}")
fi
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/run_d.py \
  --species "${SPECIES:?set SPECIES}" --mode gpu "${output_args[@]}"
