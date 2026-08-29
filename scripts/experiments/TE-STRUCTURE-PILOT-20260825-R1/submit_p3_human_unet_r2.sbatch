#!/usr/bin/env bash
# P3-H-R2: decoupled body/left/right U-Net with a matched boundary-shuffled control.
# Array task 0 is the true-boundary arm; task 1 relocates the same targets within
# each training window. Set ATTEMPT_TAG for every submission.
# Create logs/TE-STRUCTURE-PILOT-20260825-R1 before submitting this file.
#SBATCH --job-name=TE_P3_H_R2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --array=0-1%2
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-%j_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-%j_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting P3-H-R2}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
BASE_CHECKPOINT=${ROOT}/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    ARM=true-boundary
    TARGET_MODE=true
    ;;
  1)
    ARM=boundary-shuffled-control
    TARGET_MODE=shuffled
    ;;
  *)
    echo "unexpected array index: ${SLURM_ARRAY_TASK_ID}" >&2
    exit 2
    ;;
esac

RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-${ARM}-${ATTEMPT_TAG}

mkdir -p "${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1"
mkdir "${RUN_ROOT}"
mkdir -p "${RUN_ROOT}/eval"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python "${SCRIPT_ROOT}/te_unet_segmentation.py" train \
  --r2 \
  --boundary-target-mode "${TARGET_MODE}" \
  --checkpoint "${BASE_CHECKPOINT}" \
  --data-dir "${DATA_DIR}" \
  --output-dir "${RUN_ROOT}/unet" \
  --max-steps 800 \
  --eval-steps 100 \
  --max-eval-samples 800 \
  --width 128 \
  --seed 42 \
  --bf16

python "${SCRIPT_ROOT}/te_unet_segmentation.py" evaluate \
  --r2 \
  --model-dir "${RUN_ROOT}/unet" \
  --data-jsonl "${DATA_DIR}/test/data.jsonl.gz" \
  --prediction-tsv "${RUN_ROOT}/eval/human.prediction.tsv" \
  --truth-tsv "${RUN_ROOT}/eval/human.truth.tsv" \
  --lengths-json "${RUN_ROOT}/eval/human.lengths.json" \
  --metrics-json "${RUN_ROOT}/eval/human.metrics.json" \
  --threshold 0.5 \
  --weight-mode triangular \
  --max-windows 1200

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
