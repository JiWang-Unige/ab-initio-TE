#!/usr/bin/env bash
#SBATCH --job-name=TFLOCK_PREP
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/prep_%A_%a.out
#SBATCH --error=logs/tefm_lock/PIPE-TEFM-LOCK-20260619/prep_%A_%a.err
#SBATCH --array=1-13%1

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_lock/PIPE-TEFM-LOCK-20260619
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-LOCK-20260619/run_cmd_array.sh configs/pipelines/PIPE-TEFM-LOCK-20260619.prep_jobs.tsv
