#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_FULLPART_MERGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=1-30%10
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_FULLPART_MERGE_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_FULLPART_MERGE_20260617_%A_%a.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_FULLPARTITIONS_RERUN_20260617}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
RUN_ROOT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/${RUN_ID}"
CHUNK_MANIFEST="${RUN_ROOT}/chunk_manifest.tsv"
SPECIES_MANIFEST="${RUN_ROOT}/species_manifest.tsv"

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam

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

echo "merged_species=${species_code}"
