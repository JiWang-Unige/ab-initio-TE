#!/usr/bin/env bash
# Evaluate the frozen B1 confirmation seeds with the same six-species CAL/DEV.
# Pass X0_MATERIALIZATION_ROOT and TRAIN_ARRAY_ID from the completed training array.
#SBATCH --job-name=te_l1_b1_confirm_eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b1_confirm_eval_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b1_confirm_eval_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory}"
: "${TRAIN_ARRAY_ID:?set TRAIN_ARRAY_ID to the completed B1 confirmation training array job id}"

case "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}" in
  0) SEED=17 ;;
  1) SEED=20260903 ;;
  *) echo "unexpected B1 confirmation evaluation index: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

TRAIN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-B1-CONFIRMATION-20260903/seed${SEED}/${TRAIN_ARRAY_ID}_${SLURM_ARRAY_TASK_ID}/final_model"
EVAL_OUTPUT_DIR="${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/B1/seed${SEED}/${SLURM_ARRAY_JOB_ID:?SLURM_ARRAY_JOB_ID is required}_${SLURM_ARRAY_TASK_ID}"
EVAL_SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/submit_calibrate_evaluate.sbatch"
ARM=B1
MODEL_DIR="${TRAIN_ROOT}"
TOKENIZER_DIR="${TRAIN_ROOT}"

export ARM SEED MODEL_DIR TOKENIZER_DIR EVAL_OUTPUT_DIR

bash "${EVAL_SCRIPT}"
