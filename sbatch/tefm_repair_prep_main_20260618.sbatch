#!/usr/bin/env bash
#SBATCH --job-name=TFREPAIR_PREP
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/prep_main_%A_%a.out
#SBATCH --error=logs/tefm_repair/PIPE-TEFM-REPAIR-20260618/prep_main_%A_%a.err
#SBATCH --array=1-2,5-8

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_repair/PIPE-TEFM-REPAIR-20260618
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-REPAIR-20260618/run_cmd_array.sh configs/pipelines/PIPE-TEFM-REPAIR-20260618.prep_jobs.tsv
