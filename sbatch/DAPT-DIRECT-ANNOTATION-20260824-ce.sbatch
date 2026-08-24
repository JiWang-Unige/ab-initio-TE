#!/usr/bin/env bash
# Matched Base->CE (task 0) and DAPT->CE (task 1), followed by raw strict evaluation.
# Resource selection is intentionally left to submission CLI, e.g. --time=12:00:00 --gres=gpu:a100:1.
# Required environment: CE_DATA_DIR and DAPT_CHECKPOINT; CE_BASE_CHECKPOINT is optional.
#SBATCH --job-name=dapt_direct_ce
#SBATCH --array=0-1%2
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-CE/ce_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-CE/ce_%A_%a.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
EXP=DAPT-DIRECT-ANNOTATION-20260824-CE
TASK="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}"
BASE_CHECKPOINT="${CE_BASE_CHECKPOINT:-$ROOT/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base}"
DAPT_CHECKPOINT="${DAPT_CHECKPOINT:?DAPT_CHECKPOINT must point to the final DAPT HF checkpoint}"
CE_DATA_DIR="${CE_DATA_DIR:?CE_DATA_DIR must contain train/val/test data.jsonl.gz}"

eval "$(conda shell.bash hook)"
conda activate te_benchmark
cd "$ROOT"

STATUS_ROOT="$ROOT/outputs/$EXP/$SLURM_ARRAY_JOB_ID"
RUN_TAG="matched-${SLURM_ARRAY_JOB_ID}-${TASK}"
RUN_DIR="$ROOT/software_outputs/dapt_direct_annotation/$EXP/runs/$RUN_TAG"
REPORT_DIR="$ROOT/reports/dapt_direct_annotation/$EXP/$RUN_TAG"
mkdir -p "$STATUS_ROOT" "$STATUS_ROOT/task_status" "$ROOT/logs/DAPT-DIRECT-ANNOTATION-20260824-CE" "$REPORT_DIR"
printf 'RUNNING\n' > "$STATUS_ROOT/STATUS"

update_status() {
  local rc="$1"
  if ((rc == 0)); then
    printf 'COMPLETED\n' > "$STATUS_ROOT/task_status/$TASK"
  else
    printf 'FAILED\n' > "$STATUS_ROOT/task_status/$TASK"
  fi
  if grep -qs FAILED "$STATUS_ROOT/task_status/"* 2>/dev/null; then
    printf 'FAILED\n' > "$STATUS_ROOT/STATUS"
  elif [[ -s "$STATUS_ROOT/task_status/0" && -s "$STATUS_ROOT/task_status/1" ]]; then
    if grep -q FAILED "$STATUS_ROOT/task_status/0" "$STATUS_ROOT/task_status/1"; then
      printf 'FAILED\n' > "$STATUS_ROOT/STATUS"
    else
      printf 'COMPLETED\n' > "$STATUS_ROOT/STATUS"
    fi
  fi
  exit "$rc"
}
trap 'update_status $?' EXIT

case "$TASK" in
  0) MODEL_KEY=base; MODEL_CHECKPOINT="$BASE_CHECKPOINT" ;;
  1) MODEL_KEY=dapt; MODEL_CHECKPOINT="$DAPT_CHECKPOINT" ;;
  *) echo "unsupported array task: $TASK" >&2; exit 2 ;;
esac

python scripts/experiments/DAPT-DIRECT-ANNOTATION-20260824/dapt_direct_annotation.py audit \
  --base-checkpoint "$BASE_CHECKPOINT" \
  --dapt-checkpoint "$DAPT_CHECKPOINT" \
  --out-json "$REPORT_DIR/loading_audit.json"

python pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py train \
  --model-path "$MODEL_CHECKPOINT" \
  --kind auto_token \
  --token-label-mode single_nt_nospecial \
  --data-dir "$CE_DATA_DIR" \
  --output-dir "$RUN_DIR" \
  --window 8192 --seed 42 --batch-size 1 --grad-accum 16 \
  --learning-rate 2e-5 --te-class-weight 3.0 --max-steps 800 --eval-steps 100 \
  --max-eval-samples 1200 --bf16 --gradient-checkpointing --fixed-final-checkpoint

python pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py eval \
  --model-dir "$RUN_DIR" --data-dir "$CE_DATA_DIR" \
  --out-json "$REPORT_DIR/raw_eval.json" --batch-size 1 --max-samples 1200 \
  --stage matched_ce --model-key "$MODEL_KEY" --model "$MODEL_KEY" \
  --window 8192

python pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py \
  --exp-id "$EXP-$RUN_TAG" --model-dir "$RUN_DIR" \
  --data-jsonl "$CE_DATA_DIR/test/data.jsonl.gz" \
  --out-tsv "$REPORT_DIR/strict_raw.tsv" --out-json "$REPORT_DIR/strict_raw.json" \
  --window 8192 --stride 8192 --weight-mode triangular --threshold 0.5 \
  --iou-thresholds 0.5 0.7 0.8 0.9 --boundary-tolerances 5 10 25 50 \
  --max-windows 1200
