#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-map-smoke
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=logs/hg19-chm13-map-smoke_%j.out
#SBATCH --error=logs/hg19-chm13-map-smoke_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
OUT=outputs/HG19-CHR1-REVISION-20260914/mapping-smoke-${SLURM_JOB_ID}
SOFTWARE=software/ucsc
LIFTOVER="$SOFTWARE/liftOver"
LIFTOVER_URL=https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/liftOver

mkdir -p "$SOFTWARE"
if [[ ! -x "$LIFTOVER" ]]; then
    TMP="$SOFTWARE/.liftOver-smoke-${SLURM_JOB_ID}.tmp"
    curl -fL --retry 3 --connect-timeout 20 --max-time 600 \
        "$LIFTOVER_URL" -o "$TMP"
    chmod 0755 "$TMP"
    mv "$TMP" "$LIFTOVER"
fi

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/mapping_qualify.py \
    --self-test \
    --liftover "$LIFTOVER" \
    --output "$OUT"

echo LIFTOVER_SYNTHETIC_CLI_SMOKE_PASS > "$OUT/STATUS"
