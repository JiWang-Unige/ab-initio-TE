#!/usr/bin/env bash
set -euo pipefail

TSV="$1"
IDX="${SLURM_ARRAY_TASK_ID:-1}"

LINE="$(sed -n "${IDX}p" "$TSV" | tr -d '\r')"
if [[ -z "$LINE" ]]; then
  echo "No command at array index ${IDX} in ${TSV}" >&2
  exit 2
fi

NAME="${LINE%%$'\t'*}"
CMD="${LINE#*$'\t'}"
echo "[$(date -Is)] START ${NAME}"
echo "${CMD}"
eval "${CMD}"
echo "[$(date -Is)] DONE ${NAME}"
