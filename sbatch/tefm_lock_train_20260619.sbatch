#!/usr/bin/env bash
#SBATCH --job-name=TFLOCK_TRAIN
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/train_%A_%a.out
#SBATCH --error=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/train_%A_%a.err
#SBATCH --array=1-6%2

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_lock/PIPE-TEFM-LOCK-20260619
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-LOCK-20260619/run_cmd_array.sh configs/pipelines/PIPE-TEFM-LOCK-20260619.train_jobs.tsv
