#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_PROBE_PREP
#SBATCH --partition=shared-cpu
#SBATCH --array=1-22%6
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/species_probe_prep_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/species_probe_prep_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
python3 scripts/pre_submit_gate.py --exp-id tefm_final_species_probe_prep_20260623
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.species_probe_prep_jobs.tsv
