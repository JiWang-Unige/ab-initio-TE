#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_FULLPART_QC
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_FULLPART_QC_20260617_%j.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_FULLPART_QC_20260617_%j.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_FULLPARTITIONS_RERUN_20260617}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
RUN_ROOT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/${RUN_ID}"
CHUNK_MANIFEST="${RUN_ROOT}/chunk_manifest.tsv"
SPECIES_MANIFEST="${RUN_ROOT}/species_manifest.tsv"
REPORT_DIR="${PROJECT_ROOT}/reports/repeatmasker_dfam/${RUN_ID}"

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${REPORT_DIR}"

python3 scripts/experiments/audit_repeatmasker_chunk_outputs.py \
  --chunk-manifest "${CHUNK_MANIFEST}" \
  --species-manifest "${SPECIES_MANIFEST}" \
  --summary-out "${REPORT_DIR}/chunk_audit_summary.tsv" \
  --details-out "${REPORT_DIR}/chunk_audit_details.tsv"

python3 - "${REPORT_DIR}/chunk_audit_summary.tsv" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
bad = []
with path.open(newline="") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        if row["status"] != "OK":
            bad.append(f"{row['species_code']}:{row['status']}")
if bad:
    raise SystemExit("chunk/merge audit failed: " + ", ".join(bad[:30]))
PY

python3 scripts/experiments/summarize_repeatmasker_strict_te.py \
  --species-manifest "${SPECIES_MANIFEST}" \
  --summary-out "${REPORT_DIR}/strict_te_summary.tsv" \
  --fail-zero

touch "${RUN_ROOT}/QC_PASS"
echo "qc_pass=${RUN_ROOT}/QC_PASS"
