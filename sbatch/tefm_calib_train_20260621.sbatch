#!/usr/bin/env bash
#SBATCH --job-name=TFCAL_TRAIN
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --exclude=gpu051
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/train_%A_%a.out
#SBATCH --error=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/train_%A_%a.err
#SBATCH --array=1-5%2

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_calib/PIPE-TEFM-CALIB-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-CALIB-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-CALIB-20260621.train_jobs.tsv
