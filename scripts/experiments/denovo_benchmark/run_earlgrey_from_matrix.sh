#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <earlgrey_task_matrix.tsv> <task_id_1based>" >&2
  exit 2
fi

MATRIX=$1
TASK_ID=$2
LINE=$(awk -v n="$TASK_ID" 'NR==n+1 {print; exit}' "$MATRIX")
if [[ -z "$LINE" ]]; then
  echo "No EarlGrey task row for task id ${TASK_ID} in ${MATRIX}" >&2
  exit 3
fi

IFS=$'\t' read -r task_id species genome output_dir container cpus rm_search_term <<< "$LINE"
if [[ "$task_id" != "$TASK_ID" ]]; then
  echo "Task id mismatch: array=${TASK_ID}, row=${task_id}" >&2
  exit 4
fi

args=(
  --species "$species"
  --genome "$genome"
  --outdir "$output_dir"
  --container "$container"
  --cpus "$cpus"
)

if [[ -n "$rm_search_term" && "$rm_search_term" != "NA" ]]; then
  args+=(--repeatmasker-search-term "$rm_search_term")
fi

python3 scripts/experiments/denovo_benchmark/run_earlgrey_tool.py "${args[@]}"
