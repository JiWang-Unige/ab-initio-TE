#!/usr/bin/env bash
# CPU readouts for the bounded target-centered context diagnostic.
#SBATCH --job-name=ntv2-length-eval
#SBATCH --partition=debug-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-eval-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
LENGTH_ROOT="${LENGTH_ROOT:?Set LENGTH_ROOT to the completed length_context output}"
OUT_DIR="${LENGTH_EVAL_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/length-evaluation-${SLURM_JOB_ID}}"

if [[ -f "$LENGTH_ROOT/STATUS" ]] && grep -qx 'BLOCKED_NATIVE_OFFSET' "$LENGTH_ROOT/STATUS"; then
  mkdir -p "$OUT_DIR"
  printf '{"status":"BLOCKED_NATIVE_OFFSET","length_root":"%s"}\n' "$LENGTH_ROOT" > "$OUT_DIR/metrics.json"
  printf 'BLOCKED_NATIVE_OFFSET\n' > "$OUT_DIR/EVAL_STATUS"
  printf 'job=%s\nlength_root=%s\nout_dir=%s\n' "$SLURM_JOB_ID" "$LENGTH_ROOT" "$OUT_DIR" > "$OUT_DIR/run_meta.txt"
  exit 0
fi

python3 "$CODE/evaluate_length_context.py" \
  --input-root "$LENGTH_ROOT" \
  --out-dir "$OUT_DIR" \
  --seed 42
printf 'PASS\n' > "$OUT_DIR/EVAL_STATUS"
printf 'job=%s\nlength_root=%s\nout_dir=%s\n' "$SLURM_JOB_ID" "$LENGTH_ROOT" "$OUT_DIR" > "$OUT_DIR/run_meta.txt"
