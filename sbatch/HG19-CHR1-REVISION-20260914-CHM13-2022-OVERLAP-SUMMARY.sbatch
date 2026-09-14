#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-ovl-sum
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
# The upstream overlap job 12705941 was observed COMPLETED before this
# reporting pass; no live dependency is needed for an already-finished job.
#SBATCH --output=logs/hg19-chm13-ovl-sum_%j.out
#SBATCH --error=logs/hg19-chm13-ovl-sum_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
UPSTREAM=outputs/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-12705941
OUT=outputs/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-summary-${SLURM_JOB_ID}

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/summarize_annotation_overlap.py \
    --table "$UPSTREAM/annotation_overlap.tsv" \
    --source-summary "$UPSTREAM/summary.json" \
    --output "$OUT/summary.json"

echo CHM13_2022_DESCRIPTIVE_OVERLAP_AGGREGATED > "$OUT/STATUS"
