#!/usr/bin/env bash
#SBATCH --job-name=hg19-chm13-2022-ovl
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
# Mapping prerequisite 12705502 was independently observed COMPLETED before
# submission; Slurm no longer accepts that completed id as a live dependency.
#SBATCH --output=logs/hg19-chm13-2022-ovl_%j.out
#SBATCH --error=logs/hg19-chm13-2022-ovl_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
CFG=configs/HG19-CHR1-REVISION-20260914-CHM13-2022-OVERLAP.json
OUT=outputs/HG19-CHR1-REVISION-20260914/chm13-2022-overlap-${SLURM_JOB_ID}

python3 scripts/experiments/HG19-CHR1-REVISION-20260914/annotation_overlap.py \
    --config "$CFG" \
    --root . \
    --output "$OUT"

echo CHM13_2022_DESCRIPTIVE_OVERLAP_COMPLETED > "$OUT/STATUS"
