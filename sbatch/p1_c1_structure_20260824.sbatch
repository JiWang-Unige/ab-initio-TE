#!/usr/bin/env bash
#SBATCH --job-name=P1C1_STRUCT
#SBATCH --array=0-1%2
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --output=logs/p1_c1_structure_20260824/%x_%A_%a.out
#SBATCH --error=logs/p1_c1_structure_20260824/%x_%A_%a.err

set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
mkdir -p logs/p1_c1_structure_20260824
eval "$(conda shell.bash hook)"
conda activate te_benchmark

PROFILE="${PROFILE:?PROFILE must be smoke, pilot, or screen}"
case "${PROFILE}" in
  smoke)
    DATA_DIR="software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192"
    WINDOW=8192
    MAX_STEPS=2
    EVAL_STEPS=2
    MAX_EVAL_SAMPLES=8
    MAX_TEST_WINDOWS=8
    ;;
  pilot)
    DATA_DIR="software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192"
    WINDOW=8192
    MAX_STEPS=100
    EVAL_STEPS=100
    MAX_EVAL_SAMPLES=200
    MAX_TEST_WINDOWS=300
    ;;
  screen)
    DATA_DIR="software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192"
    WINDOW=8192
    MAX_STEPS=800
    EVAL_STEPS=100
    MAX_EVAL_SAMPLES=800
    MAX_TEST_WINDOWS=1200
    ;;
  *)
    echo "Unknown PROFILE=${PROFILE}" >&2
    exit 2
    ;;
esac

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    ARM="ce"
    BOUNDARY_WEIGHT=0.0
    RUN_WEIGHT=0.0
    ;;
  1)
    ARM="c1"
    BOUNDARY_WEIGHT=0.2
    RUN_WEIGHT=0.05
    ;;
esac

RUN_TAG="${PROFILE}_${ARM}_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
RUN_DIR="software_outputs/p1_c1_structure_20260824/runs/${RUN_TAG}"
REPORT_DIR="reports/p1_c1_structure_20260824/${RUN_TAG}"
mkdir -p "${REPORT_DIR}"

python3 pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py train \
  --model-path /home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base \
  --kind auto_token \
  --token-label-mode single_nt_nospecial \
  --data-dir "${DATA_DIR}" \
  --output-dir "${RUN_DIR}" \
  --window "${WINDOW}" \
  --seed 42 \
  --batch-size 1 \
  --grad-accum 16 \
  --learning-rate 2e-5 \
  --te-class-weight 3.0 \
  --max-steps "${MAX_STEPS}" \
  --eval-steps "${EVAL_STEPS}" \
  --max-eval-samples "${MAX_EVAL_SAMPLES}" \
  --bf16 \
  --gradient-checkpointing \
  --fixed-final-checkpoint \
  --structure-aux \
  --boundary-distance-weight "${BOUNDARY_WEIGHT}" \
  --run-contrastive-weight "${RUN_WEIGHT}"

python3 pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py \
  --exp-id "P1-C1-STRUCTURE-20260824-${RUN_TAG}" \
  --model-dir "${RUN_DIR}" \
  --data-jsonl "${DATA_DIR}/test/data.jsonl.gz" \
  --out-tsv "${REPORT_DIR}/strict_segment.tsv" \
  --out-json "${REPORT_DIR}/strict_segment.status.json" \
  --window "${WINDOW}" \
  --stride "${WINDOW}" \
  --weight-mode triangular \
  --threshold 0.5 \
  --iou-thresholds 0.5 0.7 0.8 0.9 \
  --boundary-tolerances 5 10 25 50 \
  --max-windows "${MAX_TEST_WINDOWS}"

printf 'run_tag=%s\nrun_dir=%s\nreport_dir=%s\n' "${RUN_TAG}" "${RUN_DIR}" "${REPORT_DIR}"
