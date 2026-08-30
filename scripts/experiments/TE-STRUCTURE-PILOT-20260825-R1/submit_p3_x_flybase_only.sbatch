#!/usr/bin/env bash
# Recover only the timed-out exact FlyBase r6.68 inference from P3-X 12115589.
# The completed Mouse result and prepared FlyBase input are not recomputed.
#SBATCH --job-name=TE_P3_X_FLY
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting FlyBase-only P3-X}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
INFERENCE_JSONL=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-20260829-x1/flybase/inference.jsonl.gz
LEMMI_ATTEMPT=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1/attempt-12066076
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-only-${ATTEMPT_TAG}

mkdir "${RUN_ROOT}"
cd "${ROOT}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python "${SCRIPT_ROOT}/te_unet_segmentation.py" evaluate \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${INFERENCE_JSONL}" \
  --prediction-tsv "${RUN_ROOT}/inference.prediction.tsv" \
  --truth-tsv "${RUN_ROOT}/inference.dummy-truth.tsv" \
  --lengths-json "${RUN_ROOT}/inference.lengths.json" \
  --metrics-json "${RUN_ROOT}/inference.dummy-metrics.json" \
  --threshold 0.5 \
  --weight-mode triangular \
  --max-windows 18935

python "${SCRIPT_ROOT}/p3_x_flybase_t1_eval.py" \
  --truth "${LEMMI_ATTEMPT}/truth.canonical.tsv" \
  --prediction "${RUN_ROOT}/inference.prediction.tsv" \
  --lengths "${LEMMI_ATTEMPT}/contig_lengths.json" \
  --iou-threshold 0.8 \
  --boundary-tolerances 5 25 \
  --out-json "${RUN_ROOT}/flybase.t1.json"

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
