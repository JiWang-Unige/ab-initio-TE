#!/usr/bin/env bash
# Export and audit the fixed sea-urchin Dfam lineage-specific library.
# This is a derived comparator asset; it does not modify Label-A or the D panel.
#SBATCH --job-name=te_d_sea_uncurated_export
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_export_%A.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_sea_uncurated_export_%A.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
DFAM_ROOT="${DATA_ROOT}/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617/famdb_fullpartitions"
FAMDB="${DATA_ROOT}/software_outputs/L1-PANEL-PREP-20260908-kqZrej/labela-12664906-1/RepeatMasker/famdb.py"
OUT="${DATA_ROOT}/outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam"
RAW="${OUT}/uncurated_lineage.raw.txt"
SUMMARY="${OUT}/uncurated_lineage.summary.txt"
LIB="${OUT}/uncurated_lineage_taxon7668.fa"
MANIFEST="${OUT}/library_manifest.json"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4

mkdir -p "${OUT}"
if [[ -e "${LIB}" || -e "${MANIFEST}" ]]; then
  echo "refusing to overwrite existing library export: ${OUT}" >&2
  exit 2
fi
test -s "${FAMDB}"
test -d "${DFAM_ROOT}"

cd "${ROOT}"
python3 "${FAMDB}" -i "${DFAM_ROOT}" families -f fasta_acc --include-class-in-name -ad --uncurated 7668 > "${RAW}"
python3 "${FAMDB}" -i "${DFAM_ROOT}" families -f summary -ad --uncurated 7668 > "${SUMMARY}"

# famdb includes a human-readable preamble.  Retain only actual FASTA records
# for RepeatMasker while preserving the raw export and summary for provenance.
awk '/^>/{seen=1} seen{print}' "${RAW}" > "${LIB}"
test -s "${LIB}"

python3 - "${RAW}" "${LIB}" "${SUMMARY}" "${MANIFEST}" <<'PY'
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

raw_path, lib_path, summary_path, manifest_path = map(Path, sys.argv[1:])
raw_lines = raw_path.read_text(encoding="utf-8", errors="replace").splitlines()
library_lines = lib_path.read_text(encoding="utf-8", errors="replace").splitlines()
summary_lines = summary_path.read_text(encoding="utf-8", errors="replace").splitlines()
headers = [line for line in raw_lines if line.startswith(">")]
lengths = []
current = None
for line in library_lines:
    if line.startswith(">"):
        if current is not None:
            lengths.append(len(current))
        current = ""
    elif current is not None:
        current += line.strip()
        # Sequence records are commonly wrapped at 60 bases.  Do not record
        # a length until the next header (or EOF), otherwise only the first
        # wrapped line is counted.
if current is not None:
    lengths.append(len(current))

# Summary mode has one family record per line ending in len=<n>.  Keep the
# text-derived class audit deliberately conservative: the strict D bucket is
# decided later by rc0._truth_bucket on the annotation output.
record_lines = [
    line.strip()
    for line in summary_lines
    if re.search(r"\blen=\d+\s*$", line) and not line.lstrip().startswith(("#", "License"))
]
te_tokens = re.compile(r"(?:Transposable_Element|\bLINE\b|\bSINE\b|\bLTR\b|\bDNA\b|\bRC\b|\bRetroposon\b)", re.I)
unknown_tokens = re.compile(r"\b(?:Unknown|Unclassified)\b", re.I)
class_audit = Counter(
    "transposable_element_like" if te_tokens.search(line)
    else "unknown_or_unclassified" if unknown_tokens.search(line)
    else "other_or_unparsed"
    for line in record_lines
)
expected = 3324
actual = len(headers)
manifest = {
    "status": "COMPLETED",
    "species": "Strongylocentrotus purpuratus",
    "assembly": "GCF_000002235.5",
    "famdb_release": "Dfam 3.9",
    "famdb_taxon_id": 7668,
    "selection": "lineage-specific uncurated families from famdb families -ad --uncurated 7668",
    "expected_lineage_specific_consensus": expected,
    "fasta_consensus_records": actual,
    "expected_count_match": actual == expected,
    "summary_record_count": len(record_lines),
    "summary_class_audit": dict(sorted(class_audit.items())),
    "library_fasta": str(lib_path.resolve()),
    "raw_export": str(raw_path.resolve()),
    "raw_summary": str(summary_path.resolve()),
    "sequence_length_bp": {
        "count": len(lengths),
        "min": min(lengths) if lengths else None,
        "max": max(lengths) if lengths else None,
        "total": sum(lengths),
    },
    "interpretation": "derived library audit only; RepeatMasker annotation remains a separate comparator and cannot establish independent truth",
}
if actual == 0:
    manifest["status"] = "FAILED_EMPTY_LIBRARY"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if actual == 0:
    raise SystemExit("uncurated export produced no FASTA records")
PY

printf '%s\n' "{\"status\":\"COMPLETED\",\"manifest\":\"${MANIFEST}\"}" > "${OUT}/STATUS.json"
cat "${MANIFEST}"
