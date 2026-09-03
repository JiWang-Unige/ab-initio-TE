#!/usr/bin/env bash
# Fit the frozen six-species CAL calibration and apply it to six-species DEV.
# ARM=I0 uses the frozen H0 step-800 checkpoint and the original NTv2 tokenizer.
# ARM=B1, ARM=B2, or ARM=H1 requires MODEL_DIR and TOKENIZER_DIR for that final model.
# Set X0_MATERIALIZATION_ROOT to the completed TRAIN materialization directory.
# Set EVAL_OUTPUT_DIR to override the job-id-scoped result directory.
#SBATCH --job-name=te_l1_cal_dev
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_cal_dev_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_cal_dev_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py"
BASE_MODEL="${ROOT}/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
H0_CHECKPOINT="${ROOT}/software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_ntv2_500m_H0_w4096_seed42/checkpoints/checkpoint-800"
DATA_ROOT="${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory}"
ARM="${ARM:-I0}"
SEED="${SEED:-42}"
BATCH_SIZE="${BATCH_SIZE:-12}"
MODEL_CODE_ARGS=()

case "${ARM}" in
  I0)
    LABEL=I0-H0-INIT
    MODEL_DIR="${H0_CHECKPOINT}"
    TOKENIZER_DIR="${BASE_MODEL}"
    MODEL_CODE_ARGS=(--model-code-dir "${BASE_MODEL}")
    SEED=42
    ;;
  B1|B2|H1)
    LABEL="${ARM}"
    : "${MODEL_DIR:?set MODEL_DIR to the completed ${ARM} final_model directory}"
    : "${TOKENIZER_DIR:?set TOKENIZER_DIR to the tokenizer directory for ${ARM}}"
    ;;
  *)
    echo "unsupported ARM=${ARM}; expected I0, B1, B2, or H1" >&2
    exit 2
    ;;
esac

RUN_ROOT="${EVAL_OUTPUT_DIR:-${ROOT}/outputs/CROSS-SPECIES-L1-EVAL-20260903/${LABEL}/${SLURM_JOB_ID:?SLURM_JOB_ID is required}}"
CALIBRATION_JSON="${RUN_ROOT}/calibration.json"
CALIBRATION_METRICS_JSON="${RUN_ROOT}/calibration_metrics.json"
DEV_METRICS_JSON="${RUN_ROOT}/dev_metrics.json"

CAL_DATA=(
  --data "human=${DATA_ROOT}/CAL/human.jsonl.gz"
  --data "mouse=${DATA_ROOT}/CAL/mouse.jsonl.gz"
  --data "chicken=${DATA_ROOT}/CAL/chicken.jsonl.gz"
  --data "zebrafish=${DATA_ROOT}/CAL/zebrafish.jsonl.gz"
  --data "pig=${DATA_ROOT}/CAL/pig.jsonl.gz"
  --data "c_elegans=${DATA_ROOT}/CAL/c_elegans.jsonl.gz"
)
DEV_DATA=(
  --data "human=${DATA_ROOT}/DEV/human.jsonl.gz"
  --data "mouse=${DATA_ROOT}/DEV/mouse.jsonl.gz"
  --data "chicken=${DATA_ROOT}/DEV/chicken.jsonl.gz"
  --data "zebrafish=${DATA_ROOT}/DEV/zebrafish.jsonl.gz"
  --data "pig=${DATA_ROOT}/DEV/pig.jsonl.gz"
  --data "c_elegans=${DATA_ROOT}/DEV/c_elegans.jsonl.gz"
)

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd "${ROOT}"

python3 "${SCRIPT}" fit-cal \
  --model-dir "${MODEL_DIR}" \
  --tokenizer-dir "${TOKENIZER_DIR}" \
  "${MODEL_CODE_ARGS[@]}" \
  "${CAL_DATA[@]}" \
  --seed "${SEED}" \
  --calibration-json "${CALIBRATION_JSON}" \
  --metrics-json "${CALIBRATION_METRICS_JSON}" \
  --batch-size "${BATCH_SIZE}"

python3 "${SCRIPT}" apply-only \
  --model-dir "${MODEL_DIR}" \
  --tokenizer-dir "${TOKENIZER_DIR}" \
  "${MODEL_CODE_ARGS[@]}" \
  "${DEV_DATA[@]}" \
  --calibration-json "${CALIBRATION_JSON}" \
  --metrics-json "${DEV_METRICS_JSON}" \
  --batch-size "${BATCH_SIZE}"
