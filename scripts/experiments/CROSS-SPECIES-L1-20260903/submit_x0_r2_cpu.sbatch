#!/bin/bash
#SBATCH --job-name=te_l1_x0_r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=6
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=logs/te_l1_x0_r2_%j.out
#SBATCH --error=logs/te_l1_x0_r2_%j.err

set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE

python3 scripts/experiments/CROSS-SPECIES-L1-20260903/x0_label_split_audit.py \
  --species-table scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv \
  --output-dir "outputs/CROSS-SPECIES-L1-MATERIAL-X0-R2/${SLURM_JOB_ID}" \
  --workers "${SLURM_CPUS_PER_TASK}"
