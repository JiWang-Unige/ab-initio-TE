#!/usr/bin/env bash
#SBATCH --job-name=te_l1_conf_eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --array=0-3%4
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_eval_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_conf_eval_%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
SEEDS=(42 42 17 17)
ARMS=(L D L D)
TRAIN_IDS=(12307410_0 12307410_1 12361196_0 12361196_1)
EVAL_IDS=(12353905_0 12353905_1 12366939_0 12366939_1)
INDEX=$SLURM_ARRAY_TASK_ID
BASE=$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate_conf.py \
  --arm "${ARMS[$INDEX]}" --seed "${SEEDS[$INDEX]}" \
  --model-dir "$BASE/train/seed${SEEDS[$INDEX]}/${TRAIN_IDS[$INDEX]}/final_model" \
  --calibration-json "$BASE/evaluate/seed${SEEDS[$INDEX]}/${EVAL_IDS[$INDEX]}/calibration.json" \
  --data-root "${CONF_DATA_ROOT:?completed frozen CONF materialization required}" \
  --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --output-dir "$BASE/conf_evaluate/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
