#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <task_matrix.tsv> <task_id_1based> [prepare|tool]" >&2
  exit 2
fi

MATRIX=$1
TASK_ID=$2
MODE=${3:-tool}

LINE=$(awk -v n="$TASK_ID" 'NR==n+1 {print; exit}' "$MATRIX")
if [[ -z "${LINE}" ]]; then
  echo "No task row for task id ${TASK_ID} in ${MATRIX}" >&2
  exit 3
fi

IFS=$'\t' read -r task_id species tool source_genome normalized_genome output_dir cpus memory_gb <<< "$LINE"

if [[ "$MODE" == "prepare" ]]; then
  python3 scripts/experiments/denovo_benchmark/prepare_genome.py \
    --species "$species" \
    --source "$source_genome" \
    --output "$normalized_genome" \
    --stats "${normalized_genome}.stats.json"
elif [[ "$MODE" == "tool" ]]; then
  python3 scripts/experiments/denovo_benchmark/run_tecompare_tool.py \
    --tool "$tool" \
    --species "$species" \
    --genome "$normalized_genome" \
    --outdir "$output_dir" \
    --cpus "$cpus" \
    --memory-gb "$memory_gb"
else
  echo "Unknown mode: $MODE" >&2
  exit 4
fi
