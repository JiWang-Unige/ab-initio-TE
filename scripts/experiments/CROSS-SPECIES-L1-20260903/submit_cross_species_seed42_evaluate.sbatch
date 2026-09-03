#!/usr/bin/env bash
# Evaluate the frozen seed-42 H1/B1/B2 training array with frozen CAL/DEV.
# Pass X0_MATERIALIZATION_ROOT as the completed TRAIN materialization path and
# TRAIN_ARRAY_ID as the completed seed-42 training array job id.
# The existing calibration/evaluation wrapper runs in this Slurm task; it is
# not submitted as a nested job.
#SBATCH --job-name=te_l1_seed42_eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_seed42_eval_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_seed42_eval_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory}"
: "${TRAIN_ARRAY_ID:?set TRAIN_ARRAY_ID to the completed seed-42 training array job id}"

case "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}" in
  0) ARM=H1 ;;
  1) ARM=B1 ;;
  2) ARM=B2 ;;
  *) echo "unexpected H1/B1/B2 array index: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

TRAIN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-SEED42-FROZEN-20260903/${ARM}/${TRAIN_ARRAY_ID}_${SLURM_ARRAY_TASK_ID}/final_model"
MODEL_DIR="${TRAIN_ROOT}"
TOKENIZER_DIR="${TRAIN_ROOT}"
EVAL_OUTPUT_DIR="${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/${ARM}/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
EVAL_SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/submit_calibrate_evaluate.sbatch"

export ARM MODEL_DIR TOKENIZER_DIR EVAL_OUTPUT_DIR

bash "${EVAL_SCRIPT}"
