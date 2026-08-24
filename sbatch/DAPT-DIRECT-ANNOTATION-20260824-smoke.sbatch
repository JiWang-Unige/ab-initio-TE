#!/usr/bin/env bash
# One-step GPU smoke for the literal DAPT implementation.
# Resource selection is intentionally left to submission CLI, e.g. --time=12:00:00 --gres=gpu:a100:1.
# Full recipe is in DAPT-DIRECT-ANNOTATION-20260824-profile.sbatch.
#SBATCH --job-name=dapt_direct_smoke
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-SMOKE/smoke_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-SMOKE/smoke_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
eval "$(conda shell.bash hook)"
conda activate te_benchmark
cd "$ROOT"
EXP=DAPT-DIRECT-ANNOTATION-20260824-SMOKE
RUN_DIR="$ROOT/software_outputs/dapt_direct_annotation/$EXP/runs/smoke-$SLURM_JOB_ID"
STATUS_DIR="$ROOT/outputs/$EXP/$SLURM_JOB_ID"
mkdir -p "$STATUS_DIR" "$ROOT/logs/$EXP"
printf 'RUNNING\n' > "$STATUS_DIR/STATUS"
trap 'rc=$?; if ((rc == 0)); then printf "COMPLETED\n" > "$STATUS_DIR/STATUS"; else printf "FAILED\n" > "$STATUS_DIR/STATUS"; fi; exit "$rc"' EXIT
python scripts/experiments/DAPT-DIRECT-ANNOTATION-20260824/dapt_direct_annotation.py train \
  --data-jsonl "$DAPT_HUMAN_CHR1_TRAIN_JSONL" \
  --output-dir "$RUN_DIR" \
  --records 1 --window 8192 --max-steps 1 --smoke
