#!/usr/bin/env bash
set -euo pipefail

jobs_tsv="$1"
task_id="${SLURM_ARRAY_TASK_ID:-}"
if [[ -z "$task_id" ]]; then
  echo "SLURM_ARRAY_TASK_ID is required for array execution" >&2
  exit 2
fi

line="$(sed -n "${task_id}p" "$jobs_tsv" | tr -d '\r')"
if [[ -z "$line" ]]; then
  echo "No command at task ${task_id} in ${jobs_tsv}" >&2
  exit 2
fi

name="${line%%$'\t'*}"
cmd="${line#*$'\t'}"
echo "[$(date -Is)] ${name}"
echo "${cmd}"
eval "${cmd}"
