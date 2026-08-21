#!/usr/bin/env bash
#SBATCH --job-name=TFLOCK_SEG
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --exclude=gpu051
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/segment_%A_%a.out
#SBATCH --error=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/segment_%A_%a.err
#SBATCH --array=1-10%1

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_lock/PIPE-TEFM-LOCK-20260619
export PYTHONDONTWRITEBYTECODE=1
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-LOCK-20260619/run_cmd_array.sh configs/pipelines/PIPE-TEFM-LOCK-20260619.segment_jobs.tsv
