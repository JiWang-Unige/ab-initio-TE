#!/usr/bin/env bash
#SBATCH --job-name=te_l1_new_tiles
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_new_tiles_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_new_tiles_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904 -p test_materialize_upstream.py
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/materialize_upstream.py \
  --root /home/users/j/jwang/ab-initio-TE \
  --output-dir "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/${SLURM_JOB_ID}"
