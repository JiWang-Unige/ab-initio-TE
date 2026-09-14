#!/usr/bin/env bash
#SBATCH --job-name=hg19_exact_support
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/hg19_exact_support_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/hg19_exact_support_%j.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
cd "$ROOT"
python3 scripts/experiments/HG19-CHR1-REVISION-20260914/summarize_sequence_exact_support.py --root "$ROOT" \
 --output "$ROOT/outputs/HG19-CHR1-REVISION-20260914-MATCHED/exact-support-${SLURM_JOB_ID}.json"
