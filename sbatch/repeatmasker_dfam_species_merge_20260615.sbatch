#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_MERGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_MERGE_20260615_%j.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_MERGE_20260615_%j.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_SPECIES_ANIMALS_CHR_20260615}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
CHUNK_MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/chunk_manifest.tsv"
SPECIES_MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/species_manifest.tsv"

cd "${PROJECT_ROOT}"
python3 scripts/experiments/merge_repeatmasker_species_chunks.py \
  --run-id "${RUN_ID}" \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}"
