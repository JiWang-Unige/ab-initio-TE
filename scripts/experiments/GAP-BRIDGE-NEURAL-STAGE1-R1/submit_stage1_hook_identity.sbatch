#!/usr/bin/env bash
# Engineering-only identity check for the frozen P3-R1 pre-classifier hook.
#SBATCH --job-name=gap-s1-hook-id
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-neural-s1-hook_%j.out
#SBATCH --error=logs/gap-neural-s1-hook_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG}"
OUTPUT_DIR=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/hook-identity-${ATTEMPT_TAG}

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python3 scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_hook_identity.py \
  --model-dir outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet \
  --data-jsonl software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/test/data.jsonl.gz \
  --expected-canonical outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.prediction.tsv \
  --expected-lengths-json outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.lengths.json \
  --output-dir "${OUTPUT_DIR}" \
  --max-windows 1200
