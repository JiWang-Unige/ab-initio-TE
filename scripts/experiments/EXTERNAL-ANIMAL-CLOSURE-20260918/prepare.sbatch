#!/usr/bin/env bash
#SBATCH --job-name=d_ext_prep
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=logs/ext_prep_%A_%a.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
SPECIES=${1:?species is required}
QUALITY="outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES}/quality.json"
OUT="outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES}/prepared"
test -s "$QUALITY"
python - "$QUALITY" <<'PY'
import json
import sys
quality = json.load(open(sys.argv[1]))
if quality.get("status") != "QUALIFIED":
    raise SystemExit(f"quality gate did not pass: {quality.get('status')}")
PY
python scripts/experiments/EXTERNAL-ANIMAL-CLOSURE-20260918/prepare.py \
  --config configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json \
  --species "$SPECIES" --output "$OUT"
