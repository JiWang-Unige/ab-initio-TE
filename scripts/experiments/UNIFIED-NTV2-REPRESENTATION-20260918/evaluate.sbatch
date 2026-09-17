#!/usr/bin/env bash
# Train-only kNN/logistic and fixed-K clustering evaluation for one extraction.
# FEATURE_ROOT must point to the completed three-arm extraction's model
# subdirectory; no test-driven parameter selection is performed.
#SBATCH --job-name=ntv2-matched-eval
#SBATCH --partition=debug-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-eval-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
CONFIG="$ROOT/configs/UNIFIED-NTV2-REPRESENTATION-20260918.yaml"
FEATURE_ROOT="${FEATURE_ROOT:?Set FEATURE_ROOT to one model subdirectory in the extraction output}"
OUT_DIR="${EVAL_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/evaluation-${SLURM_JOB_ID}}"

python3 "$CODE/evaluate_matched_embeddings.py" \
  --config "$CONFIG" \
  --feature-root "$FEATURE_ROOT" \
  --out-dir "$OUT_DIR" \
  --seed 42
printf 'PASS\n' > "$OUT_DIR/EVAL_STATUS"
printf 'job=%s\nfeature_root=%s\nout_dir=%s\n' "$SLURM_JOB_ID" "$FEATURE_ROOT" "$OUT_DIR" > "$OUT_DIR/run_meta.txt"
