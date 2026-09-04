#!/usr/bin/env bash
# Fit a C. elegans-only CAL threshold for B0, then compare matched B0/B1 DEV.
# Pass TRAIN_ARRAY_ID and X0_MATERIALIZATION_ROOT from the completed inputs.
#SBATCH --job-name=te_l1_b0_worm_eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b0_worm_eval_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b0_worm_eval_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${TRAIN_ARRAY_ID:?set TRAIN_ARRAY_ID to the completed B0 training array job id}"
DATA_ROOT="${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory}"
BASE_MODEL="${ROOT}/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py"

case "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}" in
  0)
    SEED=17
    B1_MODEL="${ROOT}/outputs/CROSS-SPECIES-L1-B1-CONFIRMATION-20260903/seed17/12181383_0/final_model"
    B1_CAL="${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/seed17/12181384_0/calibration.json"
    ;;
  1)
    SEED=42
    B1_MODEL="${ROOT}/outputs/CROSS-SPECIES-L1-SEED42-FROZEN-20260903/B1/12177426_1/final_model"
    B1_CAL="${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/12178443_1/calibration.json"
    ;;
  2)
    SEED=20260903
    B1_MODEL="${ROOT}/outputs/CROSS-SPECIES-L1-B1-CONFIRMATION-20260903/seed20260903/12181383_1/final_model"
    B1_CAL="${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/seed20260903/12181384_1/calibration.json"
    ;;
  *) echo "unexpected B0 evaluation array index: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

B0_MODEL="${ROOT}/outputs/CROSS-SPECIES-L1-B0-C-ELEGANS-20260903/seed${SEED}/${TRAIN_ARRAY_ID}_${SLURM_ARRAY_TASK_ID}/final_model"
RUN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-B0-C-ELEGANS-EVAL-20260903/seed${SEED}/${SLURM_ARRAY_JOB_ID:?SLURM_ARRAY_JOB_ID is required}_${SLURM_ARRAY_TASK_ID}"
CAL_DATA="c_elegans=${DATA_ROOT}/CAL/c_elegans.jsonl.gz"
DEV_DATA="c_elegans=${DATA_ROOT}/DEV/c_elegans.jsonl.gz"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd "${ROOT}"

python3 "${SCRIPT}" fit-cal \
  --model-dir "${B0_MODEL}" \
  --tokenizer-dir "${B0_MODEL}" \
  --model-code-dir "${BASE_MODEL}" \
  --data "${CAL_DATA}" \
  --single-species \
  --seed "${SEED}" \
  --calibration-json "${RUN_ROOT}/specialist_calibration.json" \
  --metrics-json "${RUN_ROOT}/specialist_cal_metrics.json" \
  --batch-size 12

python3 "${SCRIPT}" apply-only \
  --model-dir "${B0_MODEL}" \
  --tokenizer-dir "${B0_MODEL}" \
  --model-code-dir "${BASE_MODEL}" \
  --data "${DEV_DATA}" \
  --calibration-json "${RUN_ROOT}/specialist_calibration.json" \
  --metrics-json "${RUN_ROOT}/specialist_dev_metrics.json" \
  --batch-size 12

python3 "${SCRIPT}" apply-only \
  --model-dir "${B1_MODEL}" \
  --tokenizer-dir "${B1_MODEL}" \
  --model-code-dir "${BASE_MODEL}" \
  --data "${DEV_DATA}" \
  --calibration-json "${B1_CAL}" \
  --metrics-json "${RUN_ROOT}/shared_dev_metrics.json" \
  --batch-size 12
