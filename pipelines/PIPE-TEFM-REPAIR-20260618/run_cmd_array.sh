#!/usr/bin/env bash
set -euo pipefail
JOBS_TSV="$1"
TASK_ID="${SLURM_ARRAY_TASK_ID:-${2:-1}}"
CMD="$(awk -F '\t' -v id="$TASK_ID" 'NR == id {print $2}' "$JOBS_TSV")"
CMD="${CMD//$'\r'/}"
if [[ -z "$CMD" ]]; then
  echo "No command for task ${TASK_ID} in ${JOBS_TSV}" >&2
  exit 2
fi
echo "[run_cmd_array] task=${TASK_ID}"
echo "[run_cmd_array] cmd=${CMD}"
eval "$CMD"
