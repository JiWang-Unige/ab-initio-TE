#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-mapq
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --dependency=afterok:12696405
#SBATCH --output=logs/hg19-chm13-mapq_%j.out
#SBATCH --error=logs/hg19-chm13-mapq_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
CFG=configs/HG19-CHR1-REVISION-20260914-MAPPING-QUALIFICATION.json
OUT=outputs/HG19-CHR1-REVISION-20260914/mapping-qualification-${SLURM_JOB_ID}
SOFTWARE=software/ucsc
LIFTOVER="$SOFTWARE/liftOver"
LIFTOVER_URL=https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/liftOver

mkdir -p "$SOFTWARE"
if [[ ! -x "$LIFTOVER" ]]; then
    TMP="$SOFTWARE/.liftOver-${SLURM_JOB_ID}.tmp"
    curl -fL --retry 3 --connect-timeout 20 --max-time 600 \
        "$LIFTOVER_URL" -o "$TMP"
    chmod 0755 "$TMP"
    mv "$TMP" "$LIFTOVER"
fi

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/mapping_qualify.py \
    --config "$CFG" \
    --root . \
    --liftover "$LIFTOVER" \
    --output "$OUT"

echo MAPPING_QUALIFICATION_COMPLETED > "$OUT/STATUS"
