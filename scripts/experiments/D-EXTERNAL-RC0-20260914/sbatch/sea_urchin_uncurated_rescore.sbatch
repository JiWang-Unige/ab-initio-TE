#!/usr/bin/env bash
# Cache-only rescore of the already completed D predictions under the separate
# uncurated-library comparator.  No model, inference, threshold fitting, or
# panel selection is performed here.
#SBATCH --job-name=te_d_sea_uncurated_rescore
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_rescore_%A.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_rescore_%A.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONFIG="${ROOT}/scripts/experiments/D-EXTERNAL-RC0-20260914/config/panel.json"
SCRIPT="${ROOT}/scripts/experiments/D-EXTERNAL-RC0-20260914/rescore.py"
SOURCE="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin/slurm-12696615_1"
LABEL="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam/annotation_lifted/panel_regions.lifted.out"
OUT="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam/rescore_lifted"
PANEL_REGIONS_JSON="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin/slurm-12696615_1/panel_regions.json"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4

test -s "${SOURCE}/summary.json"
test -s "${SOURCE}/probabilities.npz"
test -s "${SOURCE}/panel_regions.json"
test -s "${SOURCE}/panel_regions.fa"
test -s "${LABEL}"
test -s "${PANEL_REGIONS_JSON}"
if [[ -e "${OUT}" ]]; then
  echo "refusing to overwrite existing rescore output: ${OUT}" >&2
  exit 2
fi

mkdir -p "$(dirname "${OUT}")"
# Fail closed if a mapped query ID or lifted coordinate would be silently
# dropped by the sparse truth builder.  D .out coordinates are now expected
# in assembly-absolute, zero-based/half-open semantics after adapter parsing.
python3 - "${LABEL}" "${PANEL_REGIONS_JSON}" "${ROOT}/scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py" <<'PY'
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

label, regions_json, adapter_path = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("d_adapter", adapter_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot load adapter: {adapter_path}")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
regions = json.loads(regions_json.read_text(encoding="utf-8"))
bounds = {
    str(row["id"]): (int(row["start_bp"]), int(row["end_bp"]))
    for row in regions
}
rows = list(adapter.parse_repeatmasker_out(label))
if not rows:
    raise SystemExit("lifted RepeatMasker annotation contains no rows")
for row in rows:
    seqid = str(row["seqid"])
    if seqid not in bounds:
        raise SystemExit(f"lifted annotation contains unknown frozen region ID: {seqid}")
    start_bp, end_bp = bounds[seqid]
    if not (start_bp <= int(row["start"]) < int(row["end"]) <= end_bp):
        raise SystemExit(f"lifted annotation row exceeds frozen region: {row}")
print(json.dumps({"status": "PASS", "rows": len(rows), "region_ids": sorted({str(row['seqid']) for row in rows})}))
PY
cd "${ROOT}"
start=$(date +%s)
python3 "${SCRIPT}" \
  --config "${CONFIG}" \
  --candidate sea_urchin \
  --existing-output "${SOURCE}" \
  --output-dir "${OUT}" \
  --remote-root "${DATA_ROOT}" \
  --label-out "${LABEL}" \
  --label-source "Dfam3.9_uncurated_lineage_taxon7668"
end=$(date +%s)

python3 - "${OUT}" "${start}" "${end}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

out, start, end = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
payload = {
    "status": "COMPLETED",
    "elapsed_seconds_wallclock_integer": end - start,
    "host": "Slurm public-longrun-cpu",
    "cpus_per_task": 4,
    "memory": "16G",
    "source_prediction_output": str((out.parent.parent / "sea_urchin" / "slurm-12696615_1").resolve()),
    "label_source": "Dfam3.9_uncurated_lineage_taxon7668",
    "inference_rerun": False,
    "threshold_refit": False,
}
(out / "rescore_timing.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
