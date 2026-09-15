#!/bin/bash
#SBATCH --job-name=te-long-cb4-input
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=outputs/TE-LONG-BENCH-20260915/logs/prepare-%j.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
python3 scripts/experiments/TE-LONG-BENCH-20260915/prepare_real.py
