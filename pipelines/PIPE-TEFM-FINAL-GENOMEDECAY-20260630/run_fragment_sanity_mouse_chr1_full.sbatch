#!/bin/bash
#SBATCH --job-name=TEFM_FRAGSAN_FULL
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=logs/PIPE-TEFM-FINAL-FRAGSANITY-20260630/%x_%j.out
#SBATCH --error=logs/PIPE-TEFM-FINAL-FRAGSANITY-20260630/%x_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/PIPE-TEFM-FINAL-FRAGSANITY-20260630
mkdir -p reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity

export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface

python3 pipelines/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/fragment_sanity_eval.py \
  --exp-id PIPE-TEFM-FINAL-FRAGSANITY-20260630 \
  --model-dir software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --data-jsonl software_outputs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/data/w4096/animal_fine/mouse/chr1/mouse/test/data.jsonl.gz \
  --out-tsv reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity/mouse_chr1_full.tsv \
  --out-json reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/fragment_sanity/mouse_chr1_full.json \
  --window 4096 \
  --stride 4096 \
  --weight-mode triangular \
  --threshold 0.5 \
  --iou-thresholds 0.8 0.9 \
  --boundary-tolerances 5 10 25 \
  --max-windows 1200
