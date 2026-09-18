#!/bin/bash
#SBATCH --job-name=wg-score
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/wg-score-%j.out
#SBATCH --error=logs/wg-score-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/score.py
