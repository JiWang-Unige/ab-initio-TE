#!/usr/bin/env bash
#SBATCH --job-name=TFEXT_SUM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/summary_%j.out
#SBATCH --error=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/summary_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_extend/PIPE-TEFM-EXTEND-20260620
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-EXTEND-20260620/run_cmd_array.sh configs/pipelines/PIPE-TEFM-EXTEND-20260620.summarize_jobs.tsv
