#!/usr/bin/env bash
#SBATCH --job-name=TEFM_RETCON
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=logs/PIPE-TEFM-PURSUE-RETCONSTR-20260630/TEFM_RETCON_%j.out
#SBATCH --error=logs/PIPE-TEFM-PURSUE-RETCONSTR-20260630/TEFM_RETCON_%j.err

set -euo pipefail

ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
cd "$ROOT"

mkdir -p logs/PIPE-TEFM-PURSUE-RETCONSTR-20260630 outputs/PIPE-TEFM-PURSUE-RETCONSTR-20260630

/home/users/j/jwang/.conda/envs/te_benchmark/bin/python \
  pipelines/PIPE-TEFM-STRUCTDEC-20260630/train_joint_structured_decoders.py \
  --init-model-dir software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42 \
  --data-dir software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/data/human_H0_w4096_quick \
  --out-dir reports/tefm_final/PIPE-TEFM-PURSUE-RETCONSTR-20260630 \
  --window 4096 \
  --seed 42 \
  --max-train-samples 96 \
  --max-eval-samples 40 \
  --max-steps 40 \
  --epochs 1 \
  --batch-size 1 \
  --learning-rate 2e-5 \
  --te-class-weight 3.0 \
  --threshold 0.5 \
  --rescue-threshold 0.65 \
  --min-rescue-len 8 \
  --smooth-penalty 2.0 \
  --max-deleted-true-backed-fraction 0.15 \
  --iou-threshold 0.8 \
  --boundary-tol-bp 5 \
  --variant-set retention_constrained
