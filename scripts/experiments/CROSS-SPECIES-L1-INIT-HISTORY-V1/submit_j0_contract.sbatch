#!/usr/bin/env bash
#SBATCH --job-name=te_l1_j0_contract
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_contract_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_contract_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=2
CODE=scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-20260903 -p test_cross_species_token_task.py
python3 -m unittest discover -s "$CODE" -p test_init_model.py
python3 -m unittest discover -s "$CODE" -p test_assess_init.py
python3 "$CODE/check_init_contract.py" \
  --data-root "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" \
  --upstream-root "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000" \
  --output-json "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_contract/$SLURM_JOB_ID/init_contract.json" \
  --seeds 42 17 --sample-steps 4
