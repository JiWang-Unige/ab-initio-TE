#!/usr/bin/env bash
#SBATCH --job-name=TFANC_SF5
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --exclude=gpu051
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_%A_%a.out
#SBATCH --error=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_%A_%a.err
#SBATCH --array=1-1%1

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-ANCHOR-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-ANCHOR-20260621.sf5_jobs.tsv
