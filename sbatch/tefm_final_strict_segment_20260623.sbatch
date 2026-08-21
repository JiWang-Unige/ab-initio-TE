#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_SEG
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --exclude=gpu051
#SBATCH --array=1-12%3
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/strict_segment_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/strict_segment_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.strict_segment_jobs.tsv
