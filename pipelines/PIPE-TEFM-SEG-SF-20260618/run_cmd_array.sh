#!/usr/bin/env bash
set -euo pipefail

JOBS_TSV="$1"
if [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
  echo "SLURM_ARRAY_TASK_ID is required; submit this script as an sbatch array." >&2
  exit 2
fi
TASK_ID="${SLURM_ARRAY_TASK_ID}"
CMD="$(awk -F '\t' -v id="$TASK_ID" 'NR == id {print $2}' "$JOBS_TSV")"
CMD="${CMD//$'\r'/}"
if [[ -z "${CMD}" ]]; then
  echo "No command for task ${TASK_ID} in ${JOBS_TSV}" >&2
  exit 2
fi

echo "[task ${TASK_ID}] ${CMD}"
eval "${CMD}"
