#!/usr/bin/env bash
#SBATCH --job-name=TFANC_SF5CPU
#SBATCH --partition=shared-bigmem
#SBATCH --cpus-per-task=8
#SBATCH --mem=160G
#SBATCH --time=06:00:00
#SBATCH --output=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_cpu_%A.out
#SBATCH --error=logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/sf5_cpu_%A.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-ANCHOR-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-ANCHOR-20260621.sf5_jobs.tsv
