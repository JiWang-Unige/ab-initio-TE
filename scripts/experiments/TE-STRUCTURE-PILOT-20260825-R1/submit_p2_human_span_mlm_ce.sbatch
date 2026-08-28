#!/usr/bin/env bash
# P2-H-R2: frozen-plan span-MLM, then the matched 800-step CE head.
# Set ATTEMPT_TAG, P2_CORPUS_ROOT and P2_PLAN_JSON for every submission.
# Create logs/TE-STRUCTURE-PILOT-20260825-R1 before submitting this file.
#SBATCH --job-name=TE_P2_H
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-human-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-human-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting P2-H}"
: "${P2_CORPUS_ROOT:?set P2_CORPUS_ROOT before submitting P2-H}"
: "${P2_PLAN_JSON:?set P2_PLAN_JSON before submitting P2-H-R2}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
BASE_CHECKPOINT=${ROOT}/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-human-${ATTEMPT_TAG}

mkdir -p "${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1"
mkdir "${RUN_ROOT}"
mkdir -p "${RUN_ROOT}/strict_segment"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

CORPUS=${P2_CORPUS_ROOT}/human_reference_run_masks.jsonl.gz
CORPUS_META=${P2_CORPUS_ROOT}/human_reference_run_masks.meta.json

PLAN_DECISION=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["decision"])' "${P2_PLAN_JSON}")
[[ "${PLAN_DECISION}" == GO ]] || { echo "P2-H-R2 plan decision is ${PLAN_DECISION}; training blocked" >&2; exit 3; }
RETAINED_RECORDS=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["retained_records"])' "${CORPUS_META}")

python "${SCRIPT_ROOT}/te_span_mlm.py" train \
  --data-jsonl "${CORPUS}" \
  --metadata "${CORPUS_META}" \
  --base-checkpoint "${BASE_CHECKPOINT}" \
  --output-dir "${RUN_ROOT}/span_mlm" \
  --status-json "${RUN_ROOT}/span_mlm/status.json" \
  --plan-json "${P2_PLAN_JSON}" \
  --records "${RETAINED_RECORDS}" \
  --max-steps 800 \
  --target-fraction 0.15 \
  --span-length 32

# This is the same Human 8192-bp CE recipe used by the completed DAPT match:
# auto_token, single_nt_nospecial, batch 1, accumulation 16, 2e-5, 800 steps.
python "${ROOT}/pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py" train \
  --model-path "${RUN_ROOT}/span_mlm" \
  --kind auto_token \
  --token-label-mode single_nt_nospecial \
  --data-dir "${DATA_DIR}" \
  --output-dir "${RUN_ROOT}/ce" \
  --window 8192 \
  --seed 42 \
  --batch-size 1 \
  --grad-accum 16 \
  --learning-rate 2e-5 \
  --te-class-weight 3.0 \
  --max-steps 800 \
  --eval-steps 100 \
  --max-eval-samples 1200 \
  --bf16 \
  --gradient-checkpointing \
  --fixed-final-checkpoint

python "${ROOT}/pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py" \
  --exp-id TE-STRUCTURE-PILOT-20260825-R1-P2-H-R2 \
  --model-dir "${RUN_ROOT}/ce" \
  --data-jsonl "${DATA_DIR}/test/data.jsonl.gz" \
  --out-tsv "${RUN_ROOT}/strict_segment/human.tsv" \
  --out-json "${RUN_ROOT}/strict_segment/human.json" \
  --window 8192 \
  --stride 8192 \
  --weight-mode triangular \
  --threshold 0.5 \
  --iou-thresholds 0.5 0.7 0.8 0.9 \
  --boundary-tolerances 5 10 25 50 100 \
  --max-windows 1200

echo "P2-H completed: ${RUN_ROOT}"
