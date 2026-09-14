#!/usr/bin/env bash
#SBATCH --job-name=te-mm10-revision
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=logs/te-mm10-revision_%j.out
#SBATCH --error=logs/te-mm10-revision_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
OUT=outputs/ANNOTATION-REVISION-20260914/mm10-${SLURM_JOB_ID}
python3 scripts/experiments/ANNOTATION-REVISION-20260914/qualify_mm10.py --output "$OUT" --acquire
