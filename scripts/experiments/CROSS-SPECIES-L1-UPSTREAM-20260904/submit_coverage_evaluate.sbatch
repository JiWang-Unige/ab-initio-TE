#!/usr/bin/env bash
#SBATCH --job-name=te_l1_coverage_eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_coverage_eval_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_coverage_eval_%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
ARMS=(L D)
python3 scripts/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate_upstream.py \
  --arm "${ARMS[$SLURM_ARRAY_TASK_ID]}" --seed "${PILOT_SEED:-42}" \
  --data-root "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" \
  --upstream-root "${UPSTREAM_ROOT:?materialization root required}" \
  --model-dir "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed${PILOT_SEED:-42}/${TRAIN_ARRAY_ID:?training array required}_${SLURM_ARRAY_TASK_ID}/final_model" \
  --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed${PILOT_SEED:-42}/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
