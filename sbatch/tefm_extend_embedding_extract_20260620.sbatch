#!/usr/bin/env bash
#SBATCH --job-name=TFEXT_EMBEXT
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/emb_extract_%A_%a.out
#SBATCH --error=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/emb_extract_%A_%a.err
#SBATCH --array=1-5%5

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_extend/PIPE-TEFM-EXTEND-20260620
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-EXTEND-20260620/run_cmd_array.sh configs/pipelines/PIPE-TEFM-EXTEND-20260620.embedding_extract_jobs.tsv
