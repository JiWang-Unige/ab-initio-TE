#!/usr/bin/env bash
# P3-H-R2 CPU preflight: exhaustively verify all Human train/val windows before
# either GPU arm is submitted. Set ATTEMPT_TAG for a unique evidence directory.
#SBATCH --job-name=TE_P3_H_R2_PF
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-preflight-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-preflight-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting P3-H-R2 preflight}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-r2-preflight-${ATTEMPT_TAG}

mkdir -p "${RUN_ROOT}"
cd "${ROOT}"

python "${SCRIPT_ROOT}/te_unet_segmentation.py" preflight \
  --data-dir "${DATA_DIR}" \
  --output-json "${RUN_ROOT}/true.json" \
  --boundary-target-mode true \
  --max-eval-samples 800 \
  --seed 42

python "${SCRIPT_ROOT}/te_unet_segmentation.py" preflight \
  --data-dir "${DATA_DIR}" \
  --output-json "${RUN_ROOT}/shuffled.json" \
  --boundary-target-mode shuffled \
  --max-eval-samples 800 \
  --seed 42

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
