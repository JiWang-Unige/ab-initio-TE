#!/usr/bin/env bash
#SBATCH --job-name=hg19-2009-audit
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/hg19-2009-audit_%j.out
#SBATCH --error=logs/hg19-2009-audit_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
CFG=configs/HG19-CHR1-REVISION-20260914.json
OUT=outputs/HG19-CHR1-REVISION-20260914/audit-2009-${SLURM_JOB_ID}
OFFICIAL="$OUT/hg19.fa.out.gz"
REPORT="$OUT/report"
URL=https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/hg19.fa.out.gz

mkdir -p "$OUT"
curl -fL --retry 3 --connect-timeout 20 --max-time 1800 "$URL" -o "$OFFICIAL"
python3 scripts/experiments/HG19-CHR1-REVISION-20260914/audit_2009_provenance.py \
  --config "$CFG" --root . \
  --rmsk "$(python3 -c 'import json; print(json.load(open("configs/HG19-CHR1-REVISION-20260914.json"))["comparator"])')" \
  --official-out "$OFFICIAL" --output "$REPORT"
printf 'AUDIT_COMPLETED\n' > "$OUT/STATUS"
