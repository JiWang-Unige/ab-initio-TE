#!/usr/bin/env bash
# Repair the completed derived-library manifest's wrapped-FASTA length audit.
# The library and annotations are not regenerated; the first-pass manifest is
# retained beside the corrected one.
#SBATCH --job-name=te_d_sea_uncurated_reaudit
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_reaudit_%A.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_reaudit_%A.err

set -euo pipefail

DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
BASE="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam"
LIB="${BASE}/uncurated_lineage_taxon7668.fa"
MANIFEST="${BASE}/library_manifest.json"
FIRST_PASS="${BASE}/library_manifest.first_pass.json"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
for path in "${LIB}" "${MANIFEST}"; do
  test -s "${path}"
done
if [[ ! -e "${FIRST_PASS}" ]]; then
  cp "${MANIFEST}" "${FIRST_PASS}"
fi

python3 - "${LIB}" "${MANIFEST}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

library, manifest_path = map(Path, sys.argv[1:])
lengths: list[int] = []
current: list[str] | None = None
for line in library.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith(">"):
        if current is not None:
            lengths.append(len("".join(current)))
        current = []
    elif current is not None:
        current.append(line.strip())
if current is not None:
    lengths.append(len("".join(current)))
payload = json.loads(manifest_path.read_text(encoding="utf-8"))
expected = int(payload["fasta_consensus_records"])
if len(lengths) != expected:
    raise SystemExit(f"library record count changed: {len(lengths)} != {expected}")
payload["sequence_length_bp"] = {
    "count": len(lengths),
    "min": min(lengths),
    "max": max(lengths),
    "total": sum(lengths),
}
payload["length_audit"] = "re-audited from complete wrapped FASTA records on Slurm"
payload["first_pass_manifest"] = str(manifest_path.with_name("library_manifest.first_pass.json").resolve())
tmp = manifest_path.with_suffix(".corrected.tmp")
tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tmp.replace(manifest_path)
print(json.dumps({"status": "COMPLETED", "records": len(lengths), "sequence_length_bp": payload["sequence_length_bp"]}, sort_keys=True))
PY
printf '%s\n' "{\"status\":\"COMPLETED\",\"manifest\":\"${MANIFEST}\",\"first_pass_manifest\":\"${FIRST_PASS}\"}" > "${BASE}/reaudit_STATUS.json"
cat "${MANIFEST}"
