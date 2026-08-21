#!/usr/bin/env bash
#SBATCH --job-name=TFCAL_EMBEXT
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/emb_extract_%A_%a.out
#SBATCH --error=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/emb_extract_%A_%a.err
#SBATCH --array=1-1%1

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_calib/PIPE-TEFM-CALIB-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-CALIB-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-CALIB-20260621.embedding_extract_jobs.tsv
