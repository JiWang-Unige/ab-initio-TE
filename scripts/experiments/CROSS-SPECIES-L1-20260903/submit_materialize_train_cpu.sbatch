#!/usr/bin/env bash
# CPU-only materialization of the frozen X0-R2 TRAIN tiles.
# The X0 audit output is fixed at job 12175761; external cohorts are not read.
# Submit only after the smart-sbatch policy gate has passed.
#SBATCH --job-name=te_l1_materialize_train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_materialize_train_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_materialize_train_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
X0_TILES="${ROOT}/outputs/CROSS-SPECIES-L1-MATERIAL-X0-R2/12175761/tiles.tsv"
SPECIES_TABLE="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv"
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/materialize_x0_windows.py"
OUTPUT_DIR="${ROOT}/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/${SLURM_JOB_ID:?SLURM_JOB_ID is required}"

cd "${ROOT}"

python3 "${SCRIPT}" \
  --species-table "${SPECIES_TABLE}" \
  --tiles-tsv "${X0_TILES}" \
  --output-dir "${OUTPUT_DIR}" \
  --cohort-role train
