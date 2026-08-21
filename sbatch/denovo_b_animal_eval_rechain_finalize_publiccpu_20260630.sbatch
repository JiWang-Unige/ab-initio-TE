#!/usr/bin/env bash
# Rechain finalization after the repaired EarlGrey tail jobs.
# This script is CPU-only postprocessing; it standardizes existing outputs and
# rebuilds the full manifests for base and de novo+Dfam comparison.
#SBATCH --job-name=DENOVO_B_FINALIZE_R2
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_20260630/finalize_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_20260630/finalize_%j.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
READY_MANIFEST=/home/users/j/jwang/ab-initio-TE/software_outputs/repeatmasker_dfam/02_ready_by_design/manifests/MANIFEST_ALL.tsv
LOG_DIR=${RUN_ROOT}/slurm_logs/rechain_20260630

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

python3 scripts/experiments/denovo_benchmark/finalize_existing_outputs.py \
  --run-root "${RUN_ROOT}" \
  | tee "${RUN_ROOT}/finalize_existing_outputs_20260630.tsv"

python3 scripts/experiments/denovo_benchmark/build_denovo_ucsc_manifest.py \
  --ready-manifest "${READY_MANIFEST}" \
  --run-root "${RUN_ROOT}" \
  --out "${RUN_ROOT}/denovo_ucsc_manifest_full_20260630.tsv"

python3 scripts/experiments/denovo_benchmark/build_denovo_dfam_species_table.py \
  --out "${RUN_ROOT}/denovo_dfam_species_table_20260630.tsv"

python3 scripts/experiments/denovo_benchmark/build_denovo_dfam_task_manifest.py \
  --species-manifest "${RUN_ROOT}/manifests/species_manifest.tsv" \
  --species-table "${RUN_ROOT}/denovo_dfam_species_table_20260630.tsv" \
  --run-root "${RUN_ROOT}" \
  --out "${RUN_ROOT}/denovo_dfam_task_manifest_full_20260630.tsv"
