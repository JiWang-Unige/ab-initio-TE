#!/usr/bin/env bash
#SBATCH --job-name=TFREPAIR_TRAIN
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/train_%A_%a.out
#SBATCH --error=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/train_%A_%a.err
#SBATCH --array=1-4%2

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_repair/PIPE-TEFM-REPAIR-20260618
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-REPAIR-20260618/run_cmd_array.sh configs/pipelines/PIPE-TEFM-REPAIR-20260618.train_jobs.tsv
