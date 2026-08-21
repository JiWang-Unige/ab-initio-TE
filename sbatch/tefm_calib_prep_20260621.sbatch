#!/usr/bin/env bash
#SBATCH --job-name=TFCAL_PREP
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/prep_%A_%a.out
#SBATCH --error=logs/tefm_calib/PIPE-TEFM-CALIB-20260621/prep_%A_%a.err
#SBATCH --array=1-9%6

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_calib/PIPE-TEFM-CALIB-20260621
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-CALIB-20260621/run_cmd_array.sh configs/pipelines/PIPE-TEFM-CALIB-20260621.prep_jobs.tsv
