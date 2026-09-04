#!/usr/bin/env bash
#SBATCH --job-name=te_l1_train_gap
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_rtx_a5000:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_train_gap_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_train_gap_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 -m unittest discover -s scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904 -p 'test_diagnose*.py'
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/diagnose_worm_generalization.py \
  --root /home/users/j/jwang/ab-initio-TE \
  --upstream-root "${UPSTREAM_ROOT:?materialization root required}" \
  --output-dir "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/generalization/${SLURM_JOB_ID}"
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/diagnose_error_strata.py \
  --root /home/users/j/jwang/ab-initio-TE \
  --upstream-root "${UPSTREAM_ROOT}" \
  --diagnostic-root "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/generalization/${SLURM_JOB_ID}" \
  --output-dir "outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/generalization/${SLURM_JOB_ID}"
