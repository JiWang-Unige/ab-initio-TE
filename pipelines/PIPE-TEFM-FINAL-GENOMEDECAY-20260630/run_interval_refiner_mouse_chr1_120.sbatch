#!/bin/bash
#SBATCH --job-name=TEFM_INTREF_120
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=logs/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/%x_%j.out
#SBATCH --error=logs/PIPE-TEFM-FINAL-INTERVALREFINER-20260630/%x_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/PIPE-TEFM-FINAL-INTERVALREFINER-20260630
mkdir -p reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630

export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface

python3 pipelines/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/interval_refiner_prototype.py \
  --exp-id PIPE-TEFM-FINAL-INTERVALREFINER-20260630 \
  --model-dir software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --data-jsonl software_outputs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/data/w4096/animal_fine/mouse/chr1/mouse/test/data.jsonl.gz \
  --out-dir reports/tefm_final/PIPE-TEFM-FINAL-INTERVALREFINER-20260630 \
  --window 4096 \
  --stride 4096 \
  --weight-mode triangular \
  --threshold 0.5 \
  --prob-mode consensus_min \
  --train-fraction 0.6 \
  --max-gap 1000 \
  --iou-thresholds 0.8 \
  --boundary-tolerances 5 \
  --max-windows 120 \
  --seed 42
