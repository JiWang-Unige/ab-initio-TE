#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-matched
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
# The FASTA acquisition job 12708300 was observed COMPLETED before
# submission; the matcher reads its verified output and has no live
# dependency on the expired Slurm record.
#SBATCH --output=logs/hg19-chm13-matched_%j.out
#SBATCH --error=logs/hg19-chm13-matched_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
CFG=configs/HG19-CHR1-REVISION-20260914-MATCHED.json
FASTA=outputs/HG19-CHR1-REVISION-20260914-MATCHED/assets/chm13v2.0.fa.gz
test -s "$FASTA"
OUT=outputs/HG19-CHR1-REVISION-20260914-MATCHED/match-${SLURM_JOB_ID}

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/match_qualify.py \
    --config "$CFG" \
    --root . \
    --output "$OUT"

echo MATCHED_BACKGROUND_AND_SEQUENCE_QUALIFICATION_COMPLETED > "$OUT/STATUS"
