#!/usr/bin/env bash
#SBATCH --job-name=te-chm13-assets
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=02:00:00
#SBATCH --output=logs/te-chm13-assets_%j.out
#SBATCH --error=logs/te-chm13-assets_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
python3 scripts/experiments/ANNOTATION-REVISION-20260914/acquire_chm13.py --output outputs/ANNOTATION-REVISION-20260914/chm13-assets-${SLURM_JOB_ID}
