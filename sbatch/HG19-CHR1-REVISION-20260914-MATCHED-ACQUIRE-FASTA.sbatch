#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-matched-fa
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:30:00
#SBATCH --output=logs/hg19-chm13-matched-fa_%j.out
#SBATCH --error=logs/hg19-chm13-matched-fa_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
OUT=outputs/HG19-CHR1-REVISION-20260914-MATCHED/assets
URL=https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz
FASTA="$OUT/chm13v2.0.fa.gz"
HEADERS="$OUT/chm13v2.0.fa.headers"
mkdir -p "$OUT"

if [[ -s "$FASTA" ]]; then
    ACQUISITION_STATUS=REUSED_EXISTING
else
    rm -f "$FASTA" "$FASTA.part-${SLURM_JOB_ID}"
    curl --fail --location --retry 2 --retry-delay 5 "$URL" \
        --output "$FASTA.part-${SLURM_JOB_ID}"
    mv "$FASTA.part-${SLURM_JOB_ID}" "$FASTA"
    ACQUISITION_STATUS=DOWNLOADED
fi
curl --fail --location --silent --show-error --head "$URL" > "$HEADERS"
gzip -t "$FASTA"

python3 - "$FASTA" "$URL" "$HEADERS" "$ACQUISITION_STATUS" > "$OUT/acquisition.json" <<'PY'
import json
import os
import sys
from pathlib import Path

fasta, url, headers, status = sys.argv[1:]
print(json.dumps({
    "status": status,
    "url": url,
    "path": os.path.abspath(fasta),
    "bytes": os.path.getsize(fasta),
    "gzip_test": True,
    "header_path": os.path.abspath(headers),
    "scope": "The downstream reader is restricted to CHM13v2 chr2/chr3/chr4.",
}, indent=2, sort_keys=True))
PY

echo CHM13V2_FASTA_READY > "$OUT/STATUS"
