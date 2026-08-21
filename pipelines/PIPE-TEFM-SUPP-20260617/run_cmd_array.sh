#!/usr/bin/env bash
set -euo pipefail

JOBS_TSV="$1"
TASK_ID="${SLURM_ARRAY_TASK_ID:-1}"
CMD="$(awk -F '\t' -v id="$TASK_ID" 'NR == id {print $2}' "$JOBS_TSV")"
if [[ -z "${CMD}" ]]; then
  echo "No command for task ${TASK_ID} in ${JOBS_TSV}" >&2
  exit 2
fi

echo "[task ${TASK_ID}] ${CMD}"
eval "${CMD}"
