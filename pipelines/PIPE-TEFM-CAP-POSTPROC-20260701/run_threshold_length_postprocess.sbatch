#!/usr/bin/env bash
#SBATCH --job-name=TEFM_POSTPROC
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=logs/PIPE-TEFM-CAP-POSTPROC-20260701/%x_%j.out
#SBATCH --error=logs/PIPE-TEFM-CAP-POSTPROC-20260701/%x_%j.err

set -euo pipefail

ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
cd "$ROOT"

EXP_ID=PIPE-TEFM-CAP-POSTPROC-20260701
OUT_DIR=reports/tefm_capability/${EXP_ID}
RUN_DIR=outputs/${EXP_ID}
mkdir -p "logs/${EXP_ID}" "${OUT_DIR}" "${RUN_DIR}"

python3 scripts/pre_submit_gate.py --exp-id "${EXP_ID}" --format text

date -Is > "${RUN_DIR}/STARTED"
echo RUNNING > "${RUN_DIR}/STATUS"

export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface

{
  echo "date=$(date -Is)"
  echo "host=$(hostname)"
  echo "python=/home/users/j/jwang/.conda/envs/te_benchmark/bin/python"
  /home/users/j/jwang/.conda/envs/te_benchmark/bin/python --version
  nvidia-smi || true
} > "${RUN_DIR}/env.txt"

/home/users/j/jwang/.conda/envs/te_benchmark/bin/python \
  pipelines/PIPE-TEFM-CAP-POSTPROC-20260701/threshold_length_postprocess_screen.py \
  --exp-id "${EXP_ID}" \
  --model-dir software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42 \
  --eval-panel human_test:software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick/test/data.jsonl.gz \
  --eval-panel mouse_quick:software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/mouse_A1_w4096_quick/test/data.jsonl.gz \
  --out-dir "${OUT_DIR}" \
  --window 4096 \
  --seed 42 \
  --max-eval-samples 40 \
  --thresholds 0.20 0.30 0.40 0.50 0.60 0.70 0.80 \
  --hmm-penalties 1 2 4 \
  --short-cutoffs 80 150 300 \
  --rescue-thresholds 0.50 0.60 0.70 \
  --rescue-max-lens 80 150 300 \
  --iou-thresholds 0.5 0.7 0.8 0.9 \
  --boundary-tolerances 5 10 25 \
  --primary-iou 0.8 \
  --primary-boundary 5

echo COMPLETED > "${RUN_DIR}/STATUS"
date -Is > "${RUN_DIR}/COMPLETED"
