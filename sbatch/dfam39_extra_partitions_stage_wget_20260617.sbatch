#!/usr/bin/env bash
#SBATCH --job-name=dfam39_parts_wget
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --array=1-6%2
#SBATCH --output=logs/repeatmasker_dfam/dfam39_parts_wget_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/dfam39_parts_wget_20260617_%A_%a.err

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
FAMDB="${FAMDB:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker/Libraries/famdb}"
STAGE="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/99_internal/dfam_partition_downloads/DFAM39_EXTRA_PARTITIONS_STAGE_WGET_20260617"
LOGDIR="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/99_internal/dfam_partition_downloads/DFAM39_EXTRA_PARTITIONS_STAGE_WGET_20260617/logs"
BASE_URL="https://www.dfam.org/releases/Dfam_3.9/families/FamDB"
PART_LIST=(2 5 6 12 13 15)

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${LOGDIR}" "${FAMDB}" "${STAGE}"

idx=$((SLURM_ARRAY_TASK_ID - 1))
p="${PART_LIST[$idx]}"
base="dfam39_full.${p}.h5"
h5="${FAMDB}/${base}"
gz="${h5}.gz"
stage_gz="${STAGE}/${base}.gz"
stage_h5="${STAGE}/${base}"
lock="${FAMDB}/dfam39_full.${p}.lock"
url="${BASE_URL}/${base}.gz"
stamp="$(date +%Y%m%dT%H%M%S)"

download_to_stage() {
  local attempt
  rm -f "${stage_gz}.tmp"
  for attempt in $(seq 1 12); do
    echo "wget_attempt=${attempt}"
    (
      cd "${STAGE}"
      wget -c --tries=8 --timeout=60 --read-timeout=300 --waitretry=30 \
        -o "${LOGDIR}/part_${p}.wget.${stamp}.attempt_${attempt}.log" \
        "${url}"
    ) || true
    if [[ -s "${stage_gz}" ]] && gzip -t "${stage_gz}"; then
      return 0
    fi
    sleep 30
  done
  echo "Failed to obtain valid ${stage_gz}" >&2
  return 23
}

decompress_to_stage() {
  local tmp="${stage_h5}.tmp.${SLURM_JOB_ID:-manual}.${SLURM_ARRAY_TASK_ID:-0}.${stamp}"
  rm -f "${tmp}"
  if command -v pigz >/dev/null 2>&1; then
    pigz -p "${SLURM_CPUS_PER_TASK:-2}" -dc "${stage_gz}" >"${tmp}"
  else
    gzip -dc "${stage_gz}" >"${tmp}"
  fi
  test -s "${tmp}"
  mv -f "${tmp}" "${stage_h5}"
}

publish_h5() {
  local tmp="${h5}.copy.${SLURM_JOB_ID:-manual}.${SLURM_ARRAY_TASK_ID:-0}.${stamp}"
  rm -f "${tmp}"
  cp -f "${stage_h5}" "${tmp}"
  test -s "${tmp}"
  mv -f "${tmp}" "${h5}"
}

exec 9>"${lock}"
flock 9

echo "partition=${p}"
echo "host=$(hostname)"
echo "started=$(date -Is)"
echo "stage=${STAGE}"

if [[ -s "${h5}" ]]; then
  echo "already_ready_h5=$(stat -c%s "${h5}")"
  exit 0
fi

if [[ -s "${gz}" ]] && gzip -t "${gz}"; then
  echo "copying_valid_existing_famdb_gz=$(stat -c%s "${gz}")"
  cp -f "${gz}" "${stage_gz}"
elif [[ -s "${stage_gz}" ]] && gzip -t "${stage_gz}"; then
  echo "using_valid_stage_gz=$(stat -c%s "${stage_gz}")"
else
  download_to_stage
fi

gzip -t "${stage_gz}"
echo "ready_stage_gz=$(stat -c%s "${stage_gz}")"

decompress_to_stage
echo "ready_stage_h5=$(stat -c%s "${stage_h5}")"

publish_h5
echo "ready_h5=$(stat -c%s "${h5}")"
echo "finished=$(date -Is)"
