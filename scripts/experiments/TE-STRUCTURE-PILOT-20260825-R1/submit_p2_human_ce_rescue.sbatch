#!/usr/bin/env bash
# Resume P2-H-R2 from the completed span-MLM artifact after CE logging failed.
#SBATCH --job-name=TE_P2_CE_R
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=10:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-ce-rescue-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-ce-rescue-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
SPAN_MLM=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-human-20260828-r2-12097890/span_mlm
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-ce-rescue-${SLURM_JOB_ID}

mkdir "${RUN_ROOT}"
mkdir "${RUN_ROOT}/strict_segment"
cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python "${ROOT}/pipelines/PIPE-TEFM-SUPP-20260617/te_token_task.py" train \
  --model-path "${SPAN_MLM}" \
  --kind auto_token \
  --token-label-mode single_nt_nospecial \
  --data-dir "${DATA_DIR}" \
  --output-dir "${RUN_ROOT}/ce" \
  --window 8192 \
  --seed 42 \
  --batch-size 1 \
  --grad-accum 16 \
  --learning-rate 2e-5 \
  --te-class-weight 3.0 \
  --max-steps 800 \
  --eval-steps 100 \
  --max-eval-samples 1200 \
  --bf16 \
  --gradient-checkpointing \
  --fixed-final-checkpoint

python "${ROOT}/pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py" \
  --exp-id TE-STRUCTURE-PILOT-20260825-R1-P2-H-R2-CE-RESCUE \
  --model-dir "${RUN_ROOT}/ce" \
  --data-jsonl "${DATA_DIR}/test/data.jsonl.gz" \
  --out-tsv "${RUN_ROOT}/strict_segment/human.tsv" \
  --out-json "${RUN_ROOT}/strict_segment/human.json" \
  --window 8192 \
  --stride 8192 \
  --weight-mode triangular \
  --threshold 0.5 \
  --iou-thresholds 0.5 0.7 0.8 0.9 \
  --boundary-tolerances 5 10 25 50 100 \
  --max-windows 1200

touch "${RUN_ROOT}/COMPLETED"
