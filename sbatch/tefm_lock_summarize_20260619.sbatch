#!/usr/bin/env bash
#SBATCH --job-name=TFLOCK_SUM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/summarize_%j.out
#SBATCH --error=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/summarize_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_lock/PIPE-TEFM-LOCK-20260619
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export SLURM_ARRAY_TASK_ID=1
bash pipelines/PIPE-TEFM-LOCK-20260619/run_cmd_array.sh configs/pipelines/PIPE-TEFM-LOCK-20260619.summarize_jobs.tsv
