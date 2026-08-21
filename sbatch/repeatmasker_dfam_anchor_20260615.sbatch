#!/usr/bin/env bash
#SBATCH --job-name=RMDFAM_ANCHOR
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=32
#SBATCH --mem=160G
#SBATCH --time=5-00:00:00
#SBATCH --array=1-6%2
#SBATCH --output=logs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/RMDFAM_ANCHOR_20260615_%A_%a.err

set -euo pipefail

RUN_ID="RMDFAM_ANCHOR_20260615"
PROJECT_ROOT="/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE"
MANIFEST="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/${RUN_ID}/anchor_manifest.tsv"
REPEATMASKER="/home/users/j/jwang/.conda/envs/te_benchmark/bin/RepeatMasker"
RM_PA="${RM_PA:-8}"

cd "${PROJECT_ROOT}"
mkdir -p "software_outputs/repeatmasker_dfam/${RUN_ID}" "logs/repeatmasker_dfam"

meta_env="$(mktemp)"
python3 - "${MANIFEST}" "${SLURM_ARRAY_TASK_ID}" "${meta_env}" <<'PY'
import csv
import shlex
import sys

manifest, task_id, meta_env = sys.argv[1:4]
with open(manifest, newline="") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        if row["array_index"] == task_id:
            with open(meta_env, "w") as out:
                for key, value in row.items():
                    out.write(f"{key}={shlex.quote(value)}\n")
            break
    else:
        raise SystemExit(f"No manifest row for array task {task_id}")
PY
# shellcheck disable=SC1090
source "${meta_env}"
rm -f "${meta_env}"

mkdir -p "${output_dir}"
{
  echo "run_id=${RUN_ID}"
  echo "array_index=${array_index}"
  echo "species_code=${species_code}"
  echo "scientific_name=${scientific_name}"
  echo "repeatmasker_species=${repeatmasker_species}"
  echo "fasta_path=${fasta_path}"
  echo "fasta_bytes=${fasta_bytes}"
  echo "fasta_md5=${fasta_md5}"
  echo "legacy_backup_out=${legacy_backup_out}"
  echo "action=${action}"
  echo "reason=${reason}"
  echo "slurm_job_id=${SLURM_JOB_ID:-}"
  echo "slurm_array_task_id=${SLURM_ARRAY_TASK_ID:-}"
  echo "host=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  "${REPEATMASKER}" -v 2>&1 | sed 's/^/repeatmasker_version: /'
} > "${output_dir}/RUN_METADATA.txt"

if [[ "${action}" == skip_existing_run ]]; then
  echo "Skipped: ${reason}" | tee "${output_dir}/SKIPPED"
  exit 0
fi

if [[ "${action}" != submit ]]; then
  echo "Manifest action is not submit: ${action} (${reason})" >&2
  exit 20
fi

if [[ ! -s "${fasta_path}" ]]; then
  echo "Missing FASTA: ${fasta_path}" >&2
  exit 21
fi

"${REPEATMASKER}" -pa "${RM_PA}" -xsmall -gff -a -dir "${output_dir}" -species "${repeatmasker_species}" "${fasta_path}"

find "${output_dir}" -maxdepth 1 -type f \( -name "*.out" -o -name "*.tbl" -o -name "*.cat" -o -name "*.align" -o -name "*.masked" -o -name "*.gff" \) -print0 \
  | xargs -0 -r gzip -f

{
  echo "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  find "${output_dir}" -maxdepth 1 -type f -printf "%f\t%s\n" | sort
} >> "${output_dir}/RUN_METADATA.txt"
touch "${output_dir}/COMPLETE"
