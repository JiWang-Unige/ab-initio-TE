#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_PRELIB_AP
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_PRELIB_AP_20260616_%j.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_PRELIB_AP_20260616_%j.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_SPECIES_ANIMALS_PLANTS_FULL_20260616}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
SPECIES_MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/species_manifest.tsv"
REPEATMASKER="${REPEATMASKER:-/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker}"
RM_LIB_OVERLAY="${RM_LIB_OVERLAY:-${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/rm_lib_overlay}"

cd "${PROJECT_ROOT}"
mkdir -p "software_outputs/repeatmasker_dfam/${RUN_ID}/prelib" "logs/repeatmasker_dfam"

if [[ ! -s "${SPECIES_MANIFEST}" ]]; then
  echo "Missing species manifest: ${SPECIES_MANIFEST}" >&2
  exit 2
fi
if [[ ! -d "${RM_LIB_OVERLAY}/famdb" ]]; then
  echo "Missing full FamDB overlay: ${RM_LIB_OVERLAY}/famdb" >&2
  exit 3
fi

python3 - "${SPECIES_MANIFEST}" > "software_outputs/repeatmasker_dfam/${RUN_ID}/prelib/prelib_species.tsv" <<'PY'
import csv
import re
import sys

manifest = sys.argv[1]
seen = set()
with open(manifest, newline="") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        if row["action"] != "submit_chunked":
            continue
        key = re.sub(r"[^a-z0-9]+", "_", row["repeatmasker_species"].lower()).strip("_")
        if key in seen:
            continue
        seen.add(key)
        print("\t".join([row["species_code"], row["repeatmasker_species"], key]))
PY

while IFS=$'\t' read -r species_code repeatmasker_species species_key; do
  species_dir="${RM_LIB_OVERLAY}/CONS-Dfam_3.9/${species_key}"
  working_dir="${species_dir}.working"
  prelib_dir="software_outputs/repeatmasker_dfam/${RUN_ID}/prelib/${species_code}"
  tiny_fasta="${prelib_dir}/${species_code}.prelib_probe.fa"

  echo "===== prebuild ${species_code} (${repeatmasker_species}; ${species_key}) $(date -u +%Y-%m-%dT%H:%M:%SZ) ====="
  rm -rf "${working_dir}" "${species_dir}"
  mkdir -p "${prelib_dir}"
  cat > "${tiny_fasta}" <<EOF
>${species_code}_prelib_probe
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

  LIBDIR="${RM_LIB_OVERLAY}" "${REPEATMASKER}" \
    -pa 1 \
    -xsmall \
    -gff \
    -dir "${prelib_dir}" \
    -species "${repeatmasker_species}" \
    "${tiny_fasta}"

  test -d "${species_dir}"
  touch "${prelib_dir}/PRELIB_COMPLETE"
done < "software_outputs/repeatmasker_dfam/${RUN_ID}/prelib/prelib_species.tsv"
