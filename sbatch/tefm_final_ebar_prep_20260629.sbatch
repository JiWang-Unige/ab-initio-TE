#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_EBAR_PREP
#SBATCH --partition=shared-cpu
#SBATCH --array=1-66%12
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/prep_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/prep_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629
eval "$(conda shell.bash hook)"
conda activate te_benchmark
python3 scripts/pre_submit_gate.py --exp-id tefm_final_ebar_prep_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-EBAR-20260629.prep_jobs.tsv
