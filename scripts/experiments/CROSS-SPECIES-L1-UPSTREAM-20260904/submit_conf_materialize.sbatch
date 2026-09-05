#!/usr/bin/env bash
#SBATCH --job-name=te_l1_conf_material
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_material_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_material_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
CODE=scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904
python3 -m unittest discover -s "$CODE" -p test_materialize_conf.py
python3 -m unittest discover -s "$CODE" -p test_evaluate_conf.py
python3 "$CODE/materialize_conf.py" --root "$ROOT" \
  --upstream-root "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/conf_materialization/$SLURM_JOB_ID"
