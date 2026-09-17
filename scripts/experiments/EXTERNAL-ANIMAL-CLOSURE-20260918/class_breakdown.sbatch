#!/usr/bin/env bash
# Post-hoc class breakdown over completed external predictions; no GPU.
#SBATCH --job-name=d_ext_class
#SBATCH --array=0-1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/ext_class_%A_%a.log
#SBATCH --error=logs/ext_class_%A_%a.err
set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4

CFG="$ROOT/configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json"
SPECIES=(torafugu zebra_finch)
SPECIES_ID=${SPECIES[$SLURM_ARRAY_TASK_ID]:?invalid array index}
INFERENCE_JOB=(12887633 12887634)
INFERENCE="$ROOT/outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES_ID}/inference-${INFERENCE_JOB[$SLURM_ARRAY_TASK_ID]}"
PANEL="$ROOT/outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES_ID}/prepared"
REFERENCE=$(python - "$SPECIES_ID" "$CFG" <<'PY'
import json
import sys
cfg=json.load(open(sys.argv[2]))
print(cfg["species"][sys.argv[1]]["historical_rm_out"])
PY
)
OUT="$ROOT/outputs/EXTERNAL-ANIMAL-CLOSURE-20260918/${SPECIES_ID}/class_breakdown"
python scripts/experiments/EXTERNAL-ANIMAL-CLOSURE-20260918/class_breakdown.py \
  --panel "$PANEL" --inference "$INFERENCE" --reference "$REFERENCE" --output "$OUT"
