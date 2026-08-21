#!/usr/bin/env bash
#SBATCH --job-name=TFSEGSF_PREP
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/prep_%A_%a.out
#SBATCH --error=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/prep_%A_%a.err
#SBATCH --array=1-8

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-SEG-SF-20260618/run_cmd_array.sh configs/pipelines/PIPE-TEFM-SEG-SF-20260618.prep_jobs.tsv
