#!/usr/bin/env bash
#SBATCH --job-name=te_l1_strata_repair
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_strata_repair_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_strata_repair_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904 -p test_diagnose_error_strata.py
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/diagnose_error_strata.py \
  --root /home/users/j/jwang/ab-initio-TE \
  --upstream-root outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000 \
  --diagnostic-root outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/generalization/12306016 \
  --output-dir "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/strata_repair/${SLURM_JOB_ID}"
