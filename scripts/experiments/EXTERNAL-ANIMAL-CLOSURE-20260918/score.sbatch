#!/usr/bin/env bash
#SBATCH --job-name=d_ext_score
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/ext_score_%A_%a.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
SPECIES=${1:?species is required}
INFERENCE=${2:?inference directory is required}
PANEL="outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES}/prepared"
REFERENCE=$(python - "$SPECIES" <<'PY'
import json
import sys
cfg=json.load(open("configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json"))
print(cfg["species"][sys.argv[1]]["historical_rm_out"])
PY
)
OUT="outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES}/score"
python scripts/experiments/EXTERNAL-ANIMAL-CLOSURE-20260918/score.py \
  --panel "$PANEL" --inference "$INFERENCE" --reference "$REFERENCE" --output "$OUT"
