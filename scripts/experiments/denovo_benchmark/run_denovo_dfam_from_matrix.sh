#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <task_matrix.tsv> <task_id_1based>" >&2
  exit 2
fi

MATRIX=$1
TASK_ID=$2

mapfile -t ROW < <(
  python3 - "$MATRIX" "$TASK_ID" <<'PY'
import csv
import sys

matrix = sys.argv[1]
task_id = sys.argv[2]
fields = [
    "species_code",
    "repeatmasker_species",
    "genome",
    "denovo_tool",
    "denovo_library",
    "output_dir",
]

with open(matrix, newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        if row.get("task_id", "").rstrip("\r") != task_id:
            continue
        for field in fields:
            print((row.get(field, "") or "").rstrip("\r"))
        raise SystemExit(0)

raise SystemExit(3)
PY
)

if [[ ${#ROW[@]} -ne 6 ]]; then
  echo "task_id=$TASK_ID not found in $MATRIX" >&2
  exit 3
fi

SPECIES=${ROW[0]}
RM_SPECIES=${ROW[1]}
GENOME=${ROW[2]}
TOOL=${ROW[3]}
LIB=${ROW[4]}
OUTDIR=${ROW[5]}

python3 scripts/experiments/denovo_benchmark/run_denovo_dfam_repeatmasker.py \
  --species "$SPECIES" \
  --repeatmasker-species "$RM_SPECIES" \
  --genome "$GENOME" \
  --denovo-tool "$TOOL" \
  --denovo-library "$LIB" \
  --overlay "/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/dfam_overlay_20260629/rm_lib_overlay" \
  --outdir "$OUTDIR" \
  --cpus "${RM_PA:-8}"
