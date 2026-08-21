#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_FULLPART_CHR
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=4-00:00:00
#SBATCH --array=1-495%36
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_FULLPART_CHR_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_FULLPART_CHR_20260617_%A_%a.err

set -euo pipefail

RUN_ID="${RUN_ID:-RMDFAM_FULLPARTITIONS_RERUN_20260617}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
RUN_ROOT="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/${RUN_ID}"
MANIFEST="${RUN_ROOT}/chunk_manifest.tsv"
REPEATMASKER="${REPEATMASKER:-/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker}"
RM_LIB_OVERLAY="${RM_LIB_OVERLAY:-${RUN_ROOT}/rm_lib_overlay}"
RM_SHARE="${RM_SHARE:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker}"
RM_PA="${RM_PA:-4}"

cd "${PROJECT_ROOT}"
mkdir -p "${RUN_ROOT}" "logs/repeatmasker_dfam"

if [[ ! -s "${MANIFEST}" ]]; then
  echo "Missing chunk manifest: ${MANIFEST}" >&2
  exit 2
fi
if [[ ! -d "${RM_LIB_OVERLAY}" || ! -e "${RM_LIB_OVERLAY}/famdb" ]]; then
  echo "Missing run library overlay with famdb symlink: ${RM_LIB_OVERLAY}" >&2
  exit 3
fi
for matrix in "${RM_SHARE}/Matrices/crossmatch/18p35g.matrix" "${RM_SHARE}/Matrices/crossmatch/simple1.matrix"; do
  if [[ ! -r "${matrix}" ]]; then
    echo "Missing required RepeatMasker matrix: ${matrix}" >&2
    exit 4
  fi
done

meta_env="$(mktemp)"
python3 - "${MANIFEST}" "${SLURM_ARRAY_TASK_ID}" "${meta_env}" <<'PY'
import csv
import shlex
import sys

csv.field_size_limit(sys.maxsize)

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
  exit 5
fi

local_base="${SLURM_TMPDIR:-/tmp/${USER:-jwang}}"
local_work="${local_base}/repeatmasker_dfam_${RUN_ID}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "${local_work}"
trap 'rm -rf "${local_work}"' EXIT
export TMPDIR="${local_work}"
TASK_RM_LIB_OVERLAY="${local_work}/rm_lib_overlay"
mkdir -p "${TASK_RM_LIB_OVERLAY}/CONS-Dfam_3.9"

TASK_RM_SHARE="${local_work}/RepeatMasker"
mkdir -p "${TASK_RM_SHARE}"
find "${RM_SHARE}" -maxdepth 1 -type f -print0 |
  while IFS= read -r -d '' entry; do
    cp -a "${entry}" "${TASK_RM_SHARE}/"
  done
mkdir -p "${TASK_RM_SHARE}/Matrices"
find -L "${RM_SHARE}/Matrices" -type f -readable -print0 |
  while IFS= read -r -d '' matrix_file; do
    rel_path="${matrix_file#${RM_SHARE}/Matrices/}"
    mkdir -p "${TASK_RM_SHARE}/Matrices/$(dirname "${rel_path}")"
    cp -L "${matrix_file}" "${TASK_RM_SHARE}/Matrices/${rel_path}"
  done

find "${RM_LIB_OVERLAY}" -maxdepth 1 -mindepth 1 ! -name "CONS-Dfam_3.9" -print0 |
  while IFS= read -r -d '' entry; do
    ln -s "${entry}" "${TASK_RM_LIB_OVERLAY}/$(basename "${entry}")"
  done

species_lib_dir="$(
  python3 - "${repeatmasker_species}" <<'PY'
import re
import sys
print(re.sub(r"[^A-Za-z0-9]+", "_", sys.argv[1].strip().lower()).strip("_"))
PY
)"
repeatmasker_custom_lib="${repeatmasker_custom_lib:-}"
if [[ -d "${RM_LIB_OVERLAY}/CONS-Dfam_3.9/${species_lib_dir}" ]]; then
  cp -a "${RM_LIB_OVERLAY}/CONS-Dfam_3.9/${species_lib_dir}" "${TASK_RM_LIB_OVERLAY}/CONS-Dfam_3.9/"
fi
ln -s "${TASK_RM_LIB_OVERLAY}" "${TASK_RM_SHARE}/Libraries"
TASK_REPEATMASKER="${TASK_RM_SHARE}/RepeatMasker"
TASK_CUSTOM_LIB=""
if [[ -n "${repeatmasker_custom_lib}" ]]; then
  if [[ ! -s "${repeatmasker_custom_lib}" ]]; then
    echo "Missing custom RepeatMasker library: ${repeatmasker_custom_lib}" >&2
    exit 7
  fi
  TASK_CUSTOM_LIB="${local_work}/custom_repeatmasker.lib.fa"
  cp -a "${repeatmasker_custom_lib}" "${TASK_CUSTOM_LIB}"
fi

{
  echo "run_id=${RUN_ID}"
  echo "chunk_index=${chunk_index}"
  echo "chunk_id=${chunk_id}"
  echo "species_code=${species_code}"
  echo "scientific_name=${scientific_name}"
  echo "repeatmasker_species=${repeatmasker_species}"
  echo "species_lib_dir=${species_lib_dir}"
  echo "taxid=${taxid}"
  echo "source_fasta=${source_fasta}"
  echo "source_fasta_bytes=${source_fasta_bytes}"
  echo "source_fasta_md5=${source_fasta_md5}"
  echo "chunk_fasta=${chunk_fasta}"
  echo "chunk_bases=${chunk_bases}"
  echo "record_count=${record_count}"
  echo "records=${records}"
  echo "libdir=${TASK_RM_LIB_OVERLAY}"
  echo "source_libdir=${RM_LIB_OVERLAY}"
  echo "repeatmasker_share=${RM_SHARE}"
  echo "task_repeatmasker_share=${TASK_RM_SHARE}"
  echo "local_work=${local_work}"
  echo "repeatmasker_custom_lib=${repeatmasker_custom_lib}"
  if [[ -n "${TASK_CUSTOM_LIB}" ]]; then
    echo "repeatmasker_flags=-pa ${RM_PA} -xsmall -gff -lib ${TASK_CUSTOM_LIB}; no -a"
  else
    echo "repeatmasker_flags=-pa ${RM_PA} -xsmall -gff -species ${repeatmasker_species}; no -a"
  fi
  echo "slurm_job_id=${SLURM_JOB_ID:-}"
  echo "slurm_array_job_id=${SLURM_ARRAY_JOB_ID:-}"
  echo "slurm_array_task_id=${SLURM_ARRAY_TASK_ID:-}"
  echo "host=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  LIBDIR="${TASK_RM_LIB_OVERLAY}" "${TASK_REPEATMASKER}" -v 2>&1 | sed 's/^/repeatmasker_version: /'
} > "${output_dir}/RUN_METADATA.txt"

cd "${local_work}"
if [[ -n "${TASK_CUSTOM_LIB}" ]]; then
  LIBDIR="${TASK_RM_LIB_OVERLAY}" "${TASK_REPEATMASKER}" \
    -pa "${RM_PA}" \
    -xsmall \
    -gff \
    -dir "${output_dir}" \
    -lib "${TASK_CUSTOM_LIB}" \
    "${chunk_fasta}"
else
  LIBDIR="${TASK_RM_LIB_OVERLAY}" "${TASK_REPEATMASKER}" \
    -pa "${RM_PA}" \
    -xsmall \
    -gff \
    -dir "${output_dir}" \
    -species "${repeatmasker_species}" \
    "${chunk_fasta}"
fi

find "${output_dir}" -maxdepth 1 -type f \( -name "*.out" -o -name "*.tbl" -o -name "*.masked" -o -name "*.out.gff" -o -name "*.cat" \) -print0 |
  xargs -0 -r gzip -f

missing_outputs=()
for suffix in ".fa.out.gz" ".fa.out.gff.gz" ".fa.tbl.gz" ".fa.masked.gz"; do
  if ! compgen -G "${output_dir}/*${suffix}" > /dev/null; then
    missing_outputs+=("${suffix}")
  fi
done
if (( ${#missing_outputs[@]} > 0 )); then
  echo "RepeatMasker finished without required final outputs: ${missing_outputs[*]}" >&2
  exit 6
fi

{
  echo "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  find "${output_dir}" -maxdepth 1 -type f -printf "%f\t%s\n" | sort
} >> "${output_dir}/RUN_METADATA.txt"
touch "${output_dir}/COMPLETE"
