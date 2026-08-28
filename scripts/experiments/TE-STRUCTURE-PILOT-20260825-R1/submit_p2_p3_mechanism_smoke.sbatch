#!/usr/bin/env bash
# P2/P3 mechanism smoke only: one GPU step per task, no CE or scientific eval.
# Set ATTEMPT_TAG and P2_CORPUS_ROOT for every submission; the two array tasks use separate outputs.
# Create logs/TE-STRUCTURE-PILOT-20260825-R1 before submitting this file.
#SBATCH --job-name=TE_P2P3_SMK
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --array=0-1%2
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/mechanism-smoke-%j_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/mechanism-smoke-%j_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting the mechanism smoke}"
: "${P2_CORPUS_ROOT:?set P2_CORPUS_ROOT before submitting the mechanism smoke}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
BASE_CHECKPOINT=${ROOT}/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base
CORPUS_ROOT=${P2_CORPUS_ROOT}
CORPUS_META=${CORPUS_ROOT}/human_reference_run_masks.meta.json
TASK_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/mechanism-smoke-${ATTEMPT_TAG}/task-${SLURM_ARRAY_TASK_ID}

mkdir -p "${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1"
mkdir "${TASK_ROOT}"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    CORPUS_DECISION=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["decision"])' "${CORPUS_ROOT}/decision.json")
    [[ "${CORPUS_DECISION}" == GO ]] || { echo "P2 corpus decision is ${CORPUS_DECISION}; smoke blocked" >&2; exit 3; }
    python "${SCRIPT_ROOT}/te_span_mlm.py" train \
      --data-jsonl "${CORPUS_ROOT}/human_reference_run_masks.jsonl.gz" \
      --metadata "${CORPUS_ROOT}/human_reference_run_masks.meta.json" \
      --base-checkpoint "${BASE_CHECKPOINT}" \
      --output-dir "${TASK_ROOT}/span_mlm" \
      --status-json "${TASK_ROOT}/span_mlm/status.json" \
      --records 2 \
      --max-steps 1 \
      --target-fraction 0.15 \
      --span-length 32
    ;;
  1)
    python "${SCRIPT_ROOT}/te_unet_segmentation.py" train \
      --checkpoint "${BASE_CHECKPOINT}" \
      --data-dir "${DATA_DIR}" \
      --output-dir "${TASK_ROOT}/unet" \
      --max-steps 1 \
      --eval-steps 1 \
      --max-eval-samples 2 \
      --width 128 \
      --seed 42 \
      --bf16
    ;;
  *)
    echo "unexpected array index: ${SLURM_ARRAY_TASK_ID}" >&2
    exit 2
    ;;
esac

echo "mechanism smoke task ${SLURM_ARRAY_TASK_ID} completed: ${TASK_ROOT}"
