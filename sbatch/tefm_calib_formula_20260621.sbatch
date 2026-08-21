#!/usr/bin/env bash
#SBATCH --job-name=TFCAL_FORM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/formula_%j.out
#SBATCH --error=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/formula_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_calib/PIPE-TEFM-CALIB-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-CALIB-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-CALIB-20260621.formula_jobs.tsv
