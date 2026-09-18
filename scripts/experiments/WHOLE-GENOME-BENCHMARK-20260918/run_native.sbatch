#!/bin/bash
#SBATCH --job-name=wg-native
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/wg-native-%j.out
#SBATCH --error=logs/wg-native-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/run_native.py \
  --species "${SPECIES:?set SPECIES}" --method "${METHOD:?set METHOD}"
