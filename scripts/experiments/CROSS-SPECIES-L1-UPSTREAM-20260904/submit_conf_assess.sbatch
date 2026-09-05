#!/usr/bin/env bash
#SBATCH --job-name=te_l1_conf_assess
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_assess_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_assess_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
CODE=scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904
BASE=$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904
python3 -m unittest discover -s "$CODE" -p test_assess_conf.py
python3 "$CODE/assess_conf.py" \
  --seed42-l-dir "$BASE/conf_evaluate/${CONF_EVAL_ARRAY:?four completed CONF evaluations required}_0" \
  --seed42-d-dir "$BASE/conf_evaluate/${CONF_EVAL_ARRAY}_1" \
  --seed17-l-dir "$BASE/conf_evaluate/${CONF_EVAL_ARRAY}_2" \
  --seed17-d-dir "$BASE/conf_evaluate/${CONF_EVAL_ARRAY}_3" \
  --output "$BASE/conf_assessment/$SLURM_JOB_ID/assessment.json"
