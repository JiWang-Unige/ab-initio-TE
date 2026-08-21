#!/usr/bin/env bash
#SBATCH --job-name=TFREPAIR_SUM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/summarize_%j.out
#SBATCH --error=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/summarize_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_repair/PIPE-TEFM-REPAIR-20260618 reports/tefm_repair/PIPE-TEFM-REPAIR-20260618/summaries
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-REPAIR-20260618/run_cmd_array.sh configs/pipelines/PIPE-TEFM-REPAIR-20260618.summarize_jobs.tsv 1
