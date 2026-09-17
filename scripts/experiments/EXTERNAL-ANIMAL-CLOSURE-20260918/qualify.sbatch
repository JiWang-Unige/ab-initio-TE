#!/usr/bin/env bash
#SBATCH --job-name=d_ext_qual
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/ext_qual_%A_%a.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
SPECIES=${1:?species is required}
OUT="outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES}/quality.json"
mkdir -p "$(dirname "$OUT")"
python scripts/experiments/EXTERNAL-ANIMAL-CLOSURE-20260918/qualify.py \
  --config configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json \
  --species "$SPECIES" --output "$OUT"
