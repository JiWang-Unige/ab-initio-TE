#!/usr/bin/env bash
#SBATCH --job-name=TFANC_SUM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summarize_%A.out
#SBATCH --error=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/summarize_%A.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-ANCHOR-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-ANCHOR-20260621.summarize_jobs.tsv
