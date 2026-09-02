#!/usr/bin/env bash
# Label-blind chr13 Stage 1 scoring with the frozen P3 backbone and nine heads.
# Submit only after Stage 1 training has completed PASS.
# ATTEMPT_TAG identifies one immutable scoring output directory.
# TRAINING_TAG names the completed Stage 1 training output.
#SBATCH --job-name=gap-s1-score
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=24:00:00
#SBATCH --output=logs/gap-neural-s1-score_%j.out
#SBATCH --error=logs/gap-neural-s1-score_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_score.py
MANIFEST=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
: "${TRAINING_TAG:?set the completed Stage 1 training tag}"
: "${ATTEMPT_TAG:?set a unique Stage 1 scoring tag}"
TRAINING_OUTPUT=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/train-${TRAINING_TAG}
OUTPUT_DIR=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/score-${ATTEMPT_TAG}

for required_path in \
  "${SCRIPT}" \
  "${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_train.py" \
  "${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_model.py" \
  "${MANIFEST}" \
  "${SOURCE_ROOT}/chr13/region.jsonl.gz" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/tokenizer" \
  "${TRAINING_OUTPUT}/scalar_stats.json" \
  "${TRAINING_OUTPUT}/heads"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing Stage 1 scoring asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "refusing to reuse Stage 1 scoring output: ${OUTPUT_DIR}" >&2
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
  --chr13-region "${SOURCE_ROOT}/chr13/region.jsonl.gz" \
  --model-dir "${MODEL_DIR}" \
  --training-output "${TRAINING_OUTPUT}" \
  --output-dir "${OUTPUT_DIR}"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUTPUT_DIR}/JOBID"
