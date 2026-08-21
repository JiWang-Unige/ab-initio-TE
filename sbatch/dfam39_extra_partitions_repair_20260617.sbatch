#!/usr/bin/env bash
#SBATCH --job-name=dfam39_parts_repair
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=12:00:00
#SBATCH --array=1-6%3
#SBATCH --output=logs/repeatmasker_dfam/dfam39_parts_repair_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/dfam39_parts_repair_20260617_%A_%a.err

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
FAMDB="${FAMDB:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker/Libraries/famdb}"
LOGDIR="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/99_internal/dfam_partition_downloads/DFAM39_EXTRA_PARTITIONS_REPAIR_20260617"
BASE_URL="https://www.dfam.org/releases/Dfam_3.9/families/FamDB"
PART_LIST=(2 5 6 12 13 15)

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${LOGDIR}" "${FAMDB}"

idx=$((SLURM_ARRAY_TASK_ID - 1))
p="${PART_LIST[$idx]}"
h5="${FAMDB}/dfam39_full.${p}.h5"
gz="${h5}.gz"
lock="${FAMDB}/dfam39_full.${p}.lock"
url="${BASE_URL}/$(basename "${gz}")"
stamp="$(date +%Y%m%dT%H%M%S)"

download_fresh() {
  local tmp="${gz}.download.${SLURM_JOB_ID:-manual}.${SLURM_ARRAY_TASK_ID:-0}.${stamp}"
  rm -f "${tmp}"
  echo "fresh_download_url=${url}"
  curl -L --fail --retry 20 --retry-delay 30 --retry-all-errors \
    --connect-timeout 60 --speed-time 300 --speed-limit 1024 \
    -o "${tmp}" "${url}" \
    >"${LOGDIR}/part_${p}.fresh_download.${stamp}.curl.log" 2>&1
  test -s "${tmp}"
  gzip -t "${tmp}"
  mv -f "${tmp}" "${gz}"
}

decompress_to_h5() {
  local tmp_h5="${h5}.decompress.${SLURM_JOB_ID:-manual}.${SLURM_ARRAY_TASK_ID:-0}.${stamp}"
  rm -f "${tmp_h5}"
  if command -v pigz >/dev/null 2>&1; then
    pigz -p "${SLURM_CPUS_PER_TASK:-2}" -dc "${gz}" >"${tmp_h5}"
  else
    gzip -dc "${gz}" >"${tmp_h5}"
  fi
  test -s "${tmp_h5}"
  mv -f "${tmp_h5}" "${h5}"
}

exec 9>"${lock}"
flock 9

echo "partition=${p}"
echo "host=$(hostname)"
echo "started=$(date -Is)"

if [[ -s "${h5}" ]]; then
  echo "already_ready_h5=$(stat -c%s "${h5}")"
  exit 0
fi

if [[ -s "${gz}" ]]; then
  if gzip -t "${gz}"; then
    echo "existing_gz_valid=$(stat -c%s "${gz}")"
  else
    bad="${gz}.bad.${stamp}"
    echo "existing_gz_invalid_renaming=${bad}"
    mv -f "${gz}" "${bad}"
    download_fresh
  fi
else
  if [[ -e "${gz}" ]]; then
    echo "removing_zero_byte_gz=${gz}"
    rm -f "${gz}"
  fi
  download_fresh
fi

gzip -t "${gz}"
echo "ready_gz=$(stat -c%s "${gz}")"

decompress_to_h5
test -s "${h5}"
echo "ready_h5=$(stat -c%s "${h5}")"
echo "finished=$(date -Is)"
