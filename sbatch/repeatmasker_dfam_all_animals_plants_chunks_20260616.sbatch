#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_AP_CHR
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=20G
#SBATCH --time=2-00:00:00
#SBATCH --array=1-1%24
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_AP_CHR_20260616_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_AP_CHR_20260616_%A_%a.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_SPECIES_ANIMALS_PLANTS_FULL_20260616}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/chunk_manifest.tsv"
REPEATMASKER="${REPEATMASKER:-/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker}"
RM_LIB_OVERLAY="${RM_LIB_OVERLAY:-${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615/rm_lib_overlay}"
RM_PA="${RM_PA:-4}"

cd "${PROJECT_ROOT}"
mkdir -p "software_outputs/repeatmasker_dfam/${RUN_ID}" "logs/repeatmasker_dfam"

if [[ ! -s "${MANIFEST}" ]]; then
  echo "Missing chunk manifest: ${MANIFEST}" >&2
  exit 2
fi

if [[ ! -d "${RM_LIB_OVERLAY}/famdb" ]]; then
  echo "Missing full FamDB overlay: ${RM_LIB_OVERLAY}/famdb" >&2
  exit 3
fi

meta_env="$(mktemp)"
python3 - "${MANIFEST}" "${SLURM_ARRAY_TASK_ID}" "${meta_env}" <<'PY'
import csv
import shlex
import sys

manifest, task_id, meta_env = sys.argv[1:4]
with open(manifest, newline="") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        if row["chunk_index"] == task_id:
            with open(meta_env, "w") as out:
                for key, value in row.items():
                    out.write(f"{key}={shlex.quote(value)}\n")
            break
    else:
        raise SystemExit(f"No manifest row for chunk_index={task_id}")
PY
# shellcheck disable=SC1090
source "${meta_env}"
rm -f "${meta_env}"

if [[ -e "${output_dir}/COMPLETE" ]]; then
  echo "Skipped existing chunk COMPLETE: ${output_dir}"
  exit 0
fi
if [[ -d "${output_dir}" ]]; then
  rm -rf "${output_dir}"
fi
mkdir -p "${output_dir}"

if [[ ! -s "${chunk_fasta}" ]]; then
  echo "Missing chunk FASTA: ${chunk_fasta}" >&2
  exit 4
fi

local_base="${SLURM_TMPDIR:-/tmp/${USER:-jwang}}"
local_work="${local_base}/repeatmasker_dfam_${RUN_ID}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "${local_work}"
trap 'rm -rf "${local_work}"' EXIT
export TMPDIR="${local_work}"

{
  echo "run_id=${RUN_ID}"
  echo "chunk_index=${chunk_index}"
  echo "chunk_id=${chunk_id}"
  echo "species_code=${species_code}"
  echo "scientific_name=${scientific_name}"
  echo "repeatmasker_species=${repeatmasker_species}"
  echo "taxid=${taxid}"
  echo "source_fasta=${source_fasta}"
  echo "source_fasta_bytes=${source_fasta_bytes}"
  echo "source_fasta_md5=${source_fasta_md5}"
  echo "chunk_fasta=${chunk_fasta}"
  echo "chunk_bases=${chunk_bases}"
  echo "record_count=${record_count}"
  echo "records=${records}"
  echo "libdir=${RM_LIB_OVERLAY}"
  echo "local_work=${local_work}"
  echo "repeatmasker_flags=-pa ${RM_PA} -xsmall -gff -species ${repeatmasker_species}"
  echo "slurm_job_id=${SLURM_JOB_ID:-}"
  echo "slurm_array_job_id=${SLURM_ARRAY_JOB_ID:-}"
  echo "slurm_array_task_id=${SLURM_ARRAY_TASK_ID:-}"
  echo "host=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  LIBDIR="${RM_LIB_OVERLAY}" "${REPEATMASKER}" -v 2>&1 | sed 's/^/repeatmasker_version: /'
} > "${output_dir}/RUN_METADATA.txt"

cd "${local_work}"
LIBDIR="${RM_LIB_OVERLAY}" "${REPEATMASKER}" \
  -pa "${RM_PA}" \
  -xsmall \
  -gff \
  -dir "${output_dir}" \
  -species "${repeatmasker_species}" \
  "${chunk_fasta}"

find "${output_dir}" -maxdepth 1 -type f \( -name "*.out" -o -name "*.tbl" -o -name "*.masked" -o -name "*.out.gff" \) -print0 \
  | xargs -0 -r gzip -f

missing_outputs=()
for suffix in ".fa.out.gz" ".fa.out.gff.gz" ".fa.tbl.gz" ".fa.masked.gz"; do
  if ! compgen -G "${output_dir}/*${suffix}" > /dev/null; then
    missing_outputs+=("${suffix}")
  fi
done
if (( ${#missing_outputs[@]} > 0 )); then
  echo "RepeatMasker finished without required final outputs: ${missing_outputs[*]}" >&2
  exit 5
fi

{
  echo "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  find "${output_dir}" -maxdepth 1 -type f -printf "%f\t%s\n" | sort
} >> "${output_dir}/RUN_METADATA.txt"
touch "${output_dir}/COMPLETE"
