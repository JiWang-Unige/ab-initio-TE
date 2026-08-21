#!/usr/bin/env bash
#SBATCH --job-name=TFEXT_EVAL
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --exclude=gpu051
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=03:00:00
#SBATCH --output=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/eval_%A_%a.out
#SBATCH --error=logs/tefm_extend/PIPE-TEFM-EXTEND-20260620/eval_%A_%a.err
#SBATCH --array=1-81%4

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_extend/PIPE-TEFM-EXTEND-20260620
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-EXTEND-20260620/run_cmd_array.sh configs/pipelines/PIPE-TEFM-EXTEND-20260620.eval_jobs.tsv
