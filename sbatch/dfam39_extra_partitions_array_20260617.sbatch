#!/usr/bin/env bash
#SBATCH --job-name=dfam39_parts_arr
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --array=1-9%6
#SBATCH --output=logs/repeatmasker_dfam/dfam39_parts_arr_20260617_%A_%a.out
#SBATCH --error=logs/repeatmasker_dfam/dfam39_parts_arr_20260617_%A_%a.err

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
FAMDB="${FAMDB:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker/Libraries/famdb}"
LOGDIR="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/99_internal/dfam_partition_downloads/DFAM39_EXTRA_PARTITIONS_20260617"
BASE_URL="https://www.dfam.org/releases/Dfam_3.9/families/FamDB"
PART_LIST=(1 2 3 4 5 6 12 13 15)

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${LOGDIR}" "${FAMDB}"

idx=$((SLURM_ARRAY_TASK_ID - 1))
p="${PART_LIST[$idx]}"
h5="${FAMDB}/dfam39_full.${p}.h5"
gz="${h5}.gz"
lock="${FAMDB}/dfam39_full.${p}.lock"
url="${BASE_URL}/$(basename "${gz}")"

exec 9>"${lock}"
flock 9

echo "partition=${p}"
echo "host=$(hostname)"
echo "started=$(date -Is)"

if [[ -s "${h5}" ]]; then
  echo "already_ready_h5=$(stat -c%s "${h5}")"
  exit 0
fi

curl -L --fail --retry 12 --retry-delay 20 --retry-all-errors -C - \
  -o "${gz}" "${url}" \
  >"${LOGDIR}/array_part_${p}.curl.log" 2>&1

test -s "${gz}"
echo "downloaded_gz=$(stat -c%s "${gz}")"

if command -v pigz >/dev/null 2>&1; then
  pigz -p "${SLURM_CPUS_PER_TASK:-2}" -dkf "${gz}" >"${LOGDIR}/array_part_${p}.decompress.log" 2>&1
else
  gzip -dkf "${gz}" >"${LOGDIR}/array_part_${p}.decompress.log" 2>&1
fi

test -s "${h5}"
echo "ready_h5=$(stat -c%s "${h5}")"
echo "finished=$(date -Is)"
