#!/usr/bin/env bash
# Frozen Stage 1 G/R/H joint training on the private RTX 3090 partition.
# Submit only after the repository smart-sbatch preflight has passed.
# The output tag must identify one immutable attempt.
#SBATCH --job-name=gap-s1-train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=4-00:00:00
#SBATCH --output=logs/gap-neural-s1-train_%j.out
#SBATCH --error=logs/gap-neural-s1-train_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_train.py
MANIFEST=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for Stage 1 training}"
OUTPUT_DIR=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/train-${ATTEMPT_TAG}

for required_path in \
  "${SCRIPT}" \
  "${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_model.py" \
  "${MANIFEST}" \
  "${SOURCE_ROOT}/chr3/region.jsonl.gz" \
  "${SOURCE_ROOT}/chr5/region.jsonl.gz" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/tokenizer"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing Stage 1 training asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "refusing to reuse Stage 1 training output: ${OUTPUT_DIR}" >&2
  exit 2
fi

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface
export PYTHONUNBUFFERED=1

python3 "${SCRIPT}" \
  --candidate-manifest "${MANIFEST}" \
  --chr3-region "${SOURCE_ROOT}/chr3/region.jsonl.gz" \
  --chr5-region "${SOURCE_ROOT}/chr5/region.jsonl.gz" \
  --model-dir "${MODEL_DIR}" \
  --output-dir "${OUTPUT_DIR}"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUTPUT_DIR}/JOBID"
