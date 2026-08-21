#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_SMOKE
#SBATCH --partition=shared-bigmem
#SBATCH --array=1-9%2
#SBATCH --cpus-per-task=4
#SBATCH --mem=180G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/smoke_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/smoke_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.smoke_jobs.tsv
