#!/usr/bin/env bash
# Merge four completed FlyBase prediction shards and evaluate positive-only T1.
#SBATCH --job-name=TE_P3_X_FLYMERGE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flymerge-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flymerge-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG used by the FlyBase shard array}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
LEMMI_ATTEMPT=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1/attempt-12066076
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-shards-${ATTEMPT_TAG}
MERGED=${RUN_ROOT}/prediction.tsv

cd "${ROOT}"
python - "${RUN_ROOT}" "${MERGED}" <<'PY'
import csv
import sys
from pathlib import Path

root = Path(sys.argv[1])
output = Path(sys.argv[2])
writer = None
with output.open("w", newline="", encoding="utf-8") as handle:
    for shard in range(4):
        path = root / f"shard-{shard}" / "prediction.tsv"
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source, delimiter="\t")
            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=reader.fieldnames, delimiter="\t", lineterminator="\n")
                writer.writeheader()
            writer.writerows(reader)
PY

python "${SCRIPT_ROOT}/p3_x_flybase_t1_eval.py" \
  --truth "${LEMMI_ATTEMPT}/truth.canonical.tsv" \
  --prediction "${MERGED}" \
  --lengths "${LEMMI_ATTEMPT}/contig_lengths.json" \
  --iou-threshold 0.8 \
  --boundary-tolerances 5 25 \
  --out-json "${RUN_ROOT}/flybase.t1.json"

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
