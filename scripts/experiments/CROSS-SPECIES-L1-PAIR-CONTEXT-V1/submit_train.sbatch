#!/usr/bin/env bash
#SBATCH --job-name=te_pair_train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:50:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_pair_train_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_pair_train_%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4
export HF_HUB_OFFLINE=1
ARMS=(BLOCK4 PAIR8)
python3 scripts/experiments/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/train_pair.py \
  --arm "${ARMS[$SLURM_ARRAY_TASK_ID]}" --seed "${PAIR_SEED:?explicit registered seed required}" \
  --activation-checkpointing \
  --data-root "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" \
  --upstream-root "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/train/seed${PAIR_SEED}/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
