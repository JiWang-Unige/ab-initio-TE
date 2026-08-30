#!/usr/bin/env bash
# Exact FlyBase r6.68 inference split into four disjoint JSONL row ranges.
#SBATCH --job-name=TE_P3_X_FLY4
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --array=0-3%4
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-fly4-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-fly4-%A_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting sharded FlyBase P3-X}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
INFERENCE_JSONL=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-20260829-x1/flybase/inference.jsonl.gz
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-shards-${ATTEMPT_TAG}
SHARD_ROOT=${RUN_ROOT}/shard-${SLURM_ARRAY_TASK_ID}
SHARD_SIZE=4734
START_WINDOW=$((SLURM_ARRAY_TASK_ID * SHARD_SIZE))
WINDOW_COUNT=${SHARD_SIZE}
if (( START_WINDOW + WINDOW_COUNT > 18935 )); then
  WINDOW_COUNT=$((18935 - START_WINDOW))
fi

mkdir -p "${RUN_ROOT}"
mkdir "${SHARD_ROOT}"
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
  --prediction-tsv "${SHARD_ROOT}/prediction.tsv" \
  --truth-tsv "${SHARD_ROOT}/dummy-truth.tsv" \
  --lengths-json "${SHARD_ROOT}/lengths.json" \
  --metrics-json "${SHARD_ROOT}/dummy-metrics.json" \
  --threshold 0.5 \
  --weight-mode triangular \
  --start-window "${START_WINDOW}" \
  --max-windows "${WINDOW_COUNT}"

printf 'PASS\n' > "${SHARD_ROOT}/STATUS"
