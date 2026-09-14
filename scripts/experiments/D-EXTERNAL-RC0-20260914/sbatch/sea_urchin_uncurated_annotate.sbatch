#!/usr/bin/env bash
# Annotate the unchanged saved sea-urchin D panel with the exported uncurated
# FamDB library.  This output is a separate comparator and never replaces
# Label-A.
#SBATCH --job-name=te_d_sea_uncurated_annot
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_annot_%A.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_annot_%A.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
BASE="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam"
LIB="${BASE}/uncurated_lineage_taxon7668.fa"
LIB_MANIFEST="${BASE}/library_manifest.json"
PANEL="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin/slurm-12696615_1/panel_regions.fa"
# RepeatMasker accepts query identifiers of at most 50 characters.  The
# frozen panel IDs are intentionally descriptive and longer, so this is a
# derived short-ID input with an explicit one-to-one mapping back to them.
ANN="${BASE}/annotation_lifted"
SHORT_PANEL="${ANN}/panel_regions.short_ids.fa"
ID_MAP="${ANN}/panel_regions.id_map.tsv"
PANEL_REGIONS_JSON="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin/slurm-12696615_1/panel_regions.json"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export PYTHONPATH="${ROOT}/scripts/experiments/D-EXTERNAL-RC0-20260914:${PYTHONPATH:-}"

test -s "${LIB}"
test -s "${PANEL}"
test -s "${PANEL_REGIONS_JSON}"
test -s "${LIB_MANIFEST}"
mkdir -p "${ANN}"
if [[ -e "${ANN}/panel_regions.lifted.out" ]]; then
  echo "refusing to overwrite existing annotation: ${ANN}/panel_regions.lifted.out" >&2
  exit 2
fi

RM=$(command -v RepeatMasker)
test -x "${RM}"

python3 - "${PANEL}" "${PANEL_REGIONS_JSON}" "${SHORT_PANEL}" "${ID_MAP}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from panel_coordinate_lift import write_short_panel

panel, regions_json, short_panel, id_map = map(Path, sys.argv[1:])
write_short_panel(panel, regions_json, short_panel, id_map)
PY
test -s "${SHORT_PANEL}"
test -s "${ID_MAP}"

cd "${ANN}"
"${RM}" -pa 4 -xsmall -gff -lib "${LIB}" "${SHORT_PANEL}"
RAW_OUT="${ANN}/panel_regions.short_ids.fa.out"
MAPPED_OUT="${ANN}/panel_regions.lifted.out"
test -s "${RAW_OUT}"

python3 - "${RAW_OUT}" "${ID_MAP}" "${MAPPED_OUT}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from panel_coordinate_lift import lift_repeatmasker_out

raw_out, id_map, mapped_out = map(Path, sys.argv[1:])
lift_repeatmasker_out(raw_out, id_map, mapped_out)
PY
test -s "${MAPPED_OUT}"

python3 - "${RM}" "${LIB}" "${PANEL}" "${PANEL_REGIONS_JSON}" "${SHORT_PANEL}" "${ID_MAP}" "${RAW_OUT}" "${MAPPED_OUT}" "${LIB_MANIFEST}" > "${ANN}/annotation_manifest.json" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

rm, lib, panel, regions_json, short_panel, id_map, raw_out, mapped_out, lib_manifest = map(Path, sys.argv[1:])
lines = mapped_out.read_text(encoding="utf-8", errors="replace").splitlines()
rows = [line for line in lines if re.match(r"^\s*\d+\s+", line)]
manifest = {
    "status": "COMPLETED",
    "annotation_engine": str(rm),
    "parameters": ["-pa", "4", "-xsmall", "-gff", "-lib", str(lib.resolve())],
    "library_fasta": str(lib.resolve()),
    "library_manifest": str(lib_manifest.resolve()),
    "panel_fasta": str(panel.resolve()),
    "frozen_panel_regions_json": str(regions_json.resolve()),
    "annotation_input_short_ids": str(short_panel.resolve()),
    "id_mapping": str(id_map.resolve()),
    "raw_annotation_out": str(raw_out.resolve()),
    "annotation_out": str(mapped_out.resolve()),
    "repeatmasker_out_rows": len(rows),
    "panel_fasta_bytes": panel.stat().st_size,
    "query_identifier_limit_workaround": "four deterministic short IDs; lifted .out retains frozen region IDs",
    "coordinate_lift": "add each frozen region start_bp to RepeatMasker panel-relative 1-based begin/end",
    "coordinate_bounds_validated": True,
    "interpretation": "derived Dfam uncurated comparator annotation; not an independent accuracy truth",
}
print(json.dumps(manifest, indent=2, sort_keys=True))
PY
printf '%s\n' "{\"status\":\"COMPLETED\",\"manifest\":\"${ANN}/annotation_manifest.json\"}" > "${ANN}/STATUS.json"
cat "${ANN}/annotation_manifest.json"
