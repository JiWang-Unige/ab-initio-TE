#!/usr/bin/env bash
#SBATCH --job-name=te_l1_j0_scores
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_scores_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_scores_%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4
CODE=scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1
BASE=$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904
SEEDS=(42 17)
TRAIN_JOBS=(12307410_1 12361196_1)
EVAL_JOBS=(12353905_1 12366939_1)
SEED=${SEEDS[$SLURM_ARRAY_TASK_ID]}
MODEL=$BASE/train/seed$SEED/${TRAIN_JOBS[$SLURM_ARRAY_TASK_ID]}/final_model
EVAL=$BASE/evaluate/seed$SEED/${EVAL_JOBS[$SLURM_ARRAY_TASK_ID]}
python3 -m unittest discover -s "$CODE" -p test_diagnose_anchor_scores.py
python3 "$CODE/diagnose_anchor_scores.py" \
  --seed "$SEED" --model-dir "$MODEL" --tokenizer-dir "$MODEL" \
  --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --calibration-json "$EVAL/calibration.json" \
  --screen-data "$BASE/materialization/12306000/SCREEN/c_elegans.jsonl.gz" \
  --dev-data "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/c_elegans.jsonl.gz" \
  --screen-expected "$EVAL/screen_metrics.json" --dev-expected "$EVAL/dev_metrics.json" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_scores/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" \
  --batch-size 12
