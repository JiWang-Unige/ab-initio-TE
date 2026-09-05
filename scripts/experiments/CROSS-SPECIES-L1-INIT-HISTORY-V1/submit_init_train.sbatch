#!/usr/bin/env bash
#SBATCH --job-name=te_l1_init_train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_init_train_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_init_train_%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=8
ARMS=(H0R P0R)
python3 scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1/train_init.py \
  --arm "${ARMS[$SLURM_ARRAY_TASK_ID]}" --seed "${INIT_SEED:-42}" \
  --data-root "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" \
  --upstream-root "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/train/seed${INIT_SEED:-42}/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
