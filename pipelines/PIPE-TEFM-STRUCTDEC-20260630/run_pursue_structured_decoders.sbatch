#!/bin/bash
#SBATCH --job-name=TEFM_PURSUE_STRUCT
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=02:30:00
#SBATCH --output=logs/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/%x_%j.out
#SBATCH --error=logs/PIPE-TEFM-PURSUE-STRUCTDEC-20260630/%x_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE

EXP_ID=PIPE-TEFM-PURSUE-STRUCTDEC-20260630
OUT_DIR=reports/tefm_final/${EXP_ID}
RUN_DIR=outputs/${EXP_ID}
mkdir -p "logs/${EXP_ID}" "${OUT_DIR}" "${RUN_DIR}"

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

/home/users/j/jwang/.conda/envs/te_benchmark/bin/python pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py \
  --init-model-dir software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42 \
  --data-dir software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick \
  --out-dir "${OUT_DIR}" \
  --window 4096 \
  --seed 42 \
  --max-train-samples 96 \
  --max-eval-samples 40 \
  --max-steps 40 \
  --epochs 1 \
  --batch-size 1 \
  --learning-rate 2e-5 \
  --iou-threshold 0.8 \
  --boundary-tol-bp 5

echo COMPLETED > "${RUN_DIR}/STATUS"
date -Is > "${RUN_DIR}/COMPLETED"
