#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_PLANT_MERGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --array=1-7%7
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_PLANT_MERGE_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_PLANT_MERGE_20260617_%A_%a.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_PLANTTE_COMPLETION_20260617}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
CHUNK_MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/chunk_manifest.tsv"
SPECIES_MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/species_manifest.tsv"
REPORT_DIR="${PROJECT_ROOT}/reports/repeatmasker_dfam"

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${REPORT_DIR}"

species_code="$(
  python3 - "${SPECIES_MANIFEST}" "${SLURM_ARRAY_TASK_ID}" <<'PY'
import csv
import sys

manifest, task_id = sys.argv[1:3]
with open(manifest, newline="") as handle:
    for idx, row in enumerate(csv.DictReader(handle, delimiter="\t"), start=1):
        if str(idx) == task_id:
            print(row["species_code"])
            break
    else:
        raise SystemExit(f"No species manifest row for array task {task_id}")
PY
)"

python3 scripts/experiments/merge_repeatmasker_species_chunks.py \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}" \
  --run-id "${RUN_ID}" \
  --species-code "${species_code}" \
  --force

python3 scripts/experiments/audit_repeatmasker_chunk_outputs.py \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}" \
  --summary-out "${REPORT_DIR}/${RUN_ID}_chunk_audit_summary.in_progress.tsv" \
  --details-out "${REPORT_DIR}/${RUN_ID}_chunk_audit_details.in_progress.tsv"

awk -F'\t' -v species="${species_code}" 'NR==1 || $1==species {print}' \
  "${REPORT_DIR}/${RUN_ID}_chunk_audit_summary.in_progress.tsv"
