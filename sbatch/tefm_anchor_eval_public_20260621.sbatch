#!/usr/bin/env bash
#SBATCH --job-name=TFANC_EVALPUB
#SBATCH --partition=public-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=03:00:00
#SBATCH --output=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/eval_public_%A_%a.out
#SBATCH --error=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/eval_public_%A_%a.err
#SBATCH --array=1-24%6

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-ANCHOR-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-ANCHOR-20260621.eval_jobs.tsv
