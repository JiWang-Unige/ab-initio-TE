#!/usr/bin/env bash
#SBATCH --job-name=te_l1_ceiling
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_ceiling_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_ceiling_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904 -p test_diagnose_token_ceiling.py
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-20260903 -p test_calibrate_evaluate_x0.py
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/diagnose_token_ceiling.py \
  --data-root outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202 \
  --output "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/ceiling/${SLURM_JOB_ID}/ceiling.json"
