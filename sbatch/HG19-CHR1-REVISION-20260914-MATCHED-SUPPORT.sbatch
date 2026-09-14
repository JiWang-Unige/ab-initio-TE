#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-matched-sup
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
# The source-only matching job 12708406 must be COMPLETED before this
# post-selection join is submitted.  The join reads only its outputs and the
# fixed precomputed overlap table; it never feeds support back into selection.
#SBATCH --output=logs/hg19-chm13-matched-sup_%j.out
#SBATCH --error=logs/hg19-chm13-matched-sup_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
MATCH=outputs/HG19-CHR1-REVISION-20260914-MATCHED/match-12708406
OVERLAP=outputs/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-12705941
test -s "$MATCH/matched_controls.tsv"
test -s "$OVERLAP/annotation_overlap.tsv"
OUT=outputs/HG19-CHR1-REVISION-20260914-MATCHED/support-${SLURM_JOB_ID}

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/summarize_matched_support.py \
    --matched-controls "$MATCH/matched_controls.tsv" \
    --overlap-table "$OVERLAP/annotation_overlap.tsv" \
    --qualification-summary "$MATCH/summary.json" \
    --qualification-table "$MATCH/interval_qualification.tsv" \
    --output "$OUT"

echo MATCHED_CHM13_SUPPORT_REPORT_COMPLETED > "$OUT/STATUS"
