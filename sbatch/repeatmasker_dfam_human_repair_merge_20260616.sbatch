#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_HMERGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_HMERGE_20260616_%j.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_HMERGE_20260616_%j.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_HUMAN_CHR12_CHR19_REPAIR_20260616}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
REPAIR_ROOT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}"
CHUNK_MANIFEST="${REPAIR_ROOT}/human_merge_chunk_manifest.tsv"
SPECIES_MANIFEST="${REPAIR_ROOT}/species_manifest.tsv"
HUMAN_OUT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/RMDFAM_SPECIES_ANIMALS_CHR_20260615/human"
BACKUP_DIR="${HUMAN_OUT}/pre_repair_20260616"
REPORT_DIR="${PROJECT_ROOT}/reports/repeatmasker_dfam"

cd "${PROJECT_ROOT}"
mkdir -p "${BACKUP_DIR}" "${REPORT_DIR}" "logs/repeatmasker_dfam"

for path in \
  "${HUMAN_OUT}/human.repeatmasker.out.gz" \
  "${HUMAN_OUT}/human.repeatmasker.out.gff.gz" \
  "${HUMAN_OUT}/human.repeatmasker.tbl.gz" \
  "${HUMAN_OUT}/human.repeatmasker.masked.fa.gz" \
  "${HUMAN_OUT}/MERGE_METADATA.txt" \
  "${HUMAN_OUT}/COMPLETE"; do
  if [[ -e "${path}" ]]; then
    cp -n "${path}" "${BACKUP_DIR}/$(basename "${path}")"
  fi
done

python3 scripts/experiments/merge_repeatmasker_species_chunks.py \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}" \
  --run-id "${RUN_ID}" \
  --species-code human \
  --force

python3 scripts/experiments/audit_repeatmasker_chunk_outputs.py \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}" \
  --summary-out "${REPORT_DIR}/${RUN_ID}_human_chunk_audit_summary.tsv" \
  --details-out "${REPORT_DIR}/${RUN_ID}_human_chunk_audit_details.tsv"

awk -F'\t' 'NR==1 || $1=="human" {print}' "${REPORT_DIR}/${RUN_ID}_human_chunk_audit_summary.tsv"
