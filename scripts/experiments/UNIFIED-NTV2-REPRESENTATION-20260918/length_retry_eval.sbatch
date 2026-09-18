#!/usr/bin/env bash
# CPU evaluator for a completed length-only retry.
# LENGTH_RETRY_ROOT must point to that retry's output directory.
#SBATCH --job-name=ntv2-length-retry-eval
#SBATCH --partition=debug-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-retry-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-retry-eval-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
LENGTH_RETRY_ROOT="${LENGTH_RETRY_ROOT:?Set LENGTH_RETRY_ROOT to the completed length retry output}"
OUT_DIR="${LENGTH_RETRY_EVAL_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/length-retry-evaluation-${SLURM_JOB_ID}}"
mkdir -p "$OUT_DIR"

python3 "$CODE/evaluate_length_context.py" \
  --input-root "$LENGTH_RETRY_ROOT" \
  --out-dir "$OUT_DIR" \
  --seed 42
printf 'PASS\n' > "$OUT_DIR/EVAL_STATUS"
printf 'job=%s\nlength_root=%s\nout_dir=%s\n' "$SLURM_JOB_ID" "$LENGTH_RETRY_ROOT" "$OUT_DIR" > "$OUT_DIR/run_meta.txt"
