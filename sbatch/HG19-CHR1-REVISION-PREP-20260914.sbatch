#!/usr/bin/env bash
#SBATCH --job-name=te-hg19-chr1-prep
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=01:00:00
#SBATCH --output=logs/te-hg19-chr1-prep_%j.out
#SBATCH --error=logs/te-hg19-chr1-prep_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
OUT=outputs/HG19-CHR1-REVISION-20260914/data-${SLURM_JOB_ID}
python3 scripts/experiments/HG19-CHR1-REVISION-20260914/prepare.py --config configs/HG19-CHR1-REVISION-20260914.json --output "$OUT"
