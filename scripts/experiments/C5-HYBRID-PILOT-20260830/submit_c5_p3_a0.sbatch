#!/usr/bin/env bash
# Frozen P3-R1 chr11 seed calibration and chr17 A0 export.
# Set ATTEMPT_TAG to a new value for every submission.
#SBATCH --job-name=TE_C5_P3_A0
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/p3-a0-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/C5-HYBRID-PILOT-20260830/p3-a0-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG for C5 P3 A0}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/C5-HYBRID-PILOT-20260830/c5_hybrid_pilot.py
DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
MODEL=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
ASSEMBLY=${ROOT}/.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa
RUN_ROOT=${ROOT}/outputs/C5-HYBRID-PILOT-20260830/${ATTEMPT_TAG}

mkdir -p "${ROOT}/outputs/C5-HYBRID-PILOT-20260830"
mkdir "${RUN_ROOT}"
cd "${ROOT}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python "${SCRIPT}" a0-tune \
  --model-dir "${MODEL}" \
  --validation-jsonl "${DATA}/val/data.jsonl.gz" \
  --validation-chrom chr11 \
  --max-validation-windows 800 \
  --body-threshold 0.5 \
  --weight-mode triangular \
  --selection-json "${RUN_ROOT}/a0.selection.json"

python "${SCRIPT}" a0-export \
  --model-dir "${MODEL}" \
  --test-jsonl "${DATA}/test/data.jsonl.gz" \
  --max-test-windows 1200 \
  --selection-json "${RUN_ROOT}/a0.selection.json" \
  --assembly "${ASSEMBLY}" \
  --chrom chr17 \
  --prefix-end 9830400 \
  --weight-mode triangular \
  --out-dir "${RUN_ROOT}/a0"

printf 'PASS\n' > "${RUN_ROOT}/A0_STATUS"
