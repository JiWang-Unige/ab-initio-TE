#!/usr/bin/env bash
# One bounded CPU retrospective audit.  It streams the existing SF5 windows
# and comparator .out files and reads saved probability arrays; it does not
# train, infer, fit thresholds, or rewrite frozen D outputs.
#SBATCH --job-name=te_ontology_external
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_ontology_external_%A.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_ontology_external_%A.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONFIG="${ROOT}/scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/config/analysis.json"
SCRIPT="${ROOT}/scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/audit_ontology_external.py"
OUT="${DATA_ROOT}/outputs/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/run-${SLURM_JOB_ID}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4

for path in "${CONFIG}" "${SCRIPT}"; do
  test -s "${path}"
done
if [[ -e "${OUT}" ]]; then
  echo "refusing to overwrite existing output: ${OUT}" >&2
  exit 2
fi

mkdir -p "$(dirname "${OUT}")"
cd "${ROOT}"
start=$(date +%s)
python3 "${SCRIPT}" \
  --config "${CONFIG}" \
  --output-dir "${OUT}" \
  --remote-root "${DATA_ROOT}"
end=$(date +%s)

python3 - "${OUT}" "${start}" "${end}" "${SLURM_JOB_ID}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
payload = {
    "status": "COMPLETED",
    "job_id": sys.argv[4],
    "elapsed_seconds_wallclock_integer": int(sys.argv[3]) - int(sys.argv[2]),
    "host": "Slurm public-longrun-cpu",
    "cpus_per_task": 4,
    "memory": "16G",
    "inference_rerun": False,
    "training": False,
}
(out / "performance.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
