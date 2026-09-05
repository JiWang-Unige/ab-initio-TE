#!/usr/bin/env bash
#SBATCH --job-name=te_l1_j0_recover
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_recover_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_j0_recover_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=2
CODE=scripts/experiments/CROSS-SPECIES-L1-INIT-HISTORY-V1
BASE=$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904
SEEDS=(42 17)
TRAIN_JOBS=(12307410_1 12361196_1)
EVAL_JOBS=(12353905_1 12366939_1)
python3 -m unittest discover -s "$CODE" -p test_diagnose_anchor_scores.py
for INDEX in 0 1; do
  SEED=${SEEDS[$INDEX]}
  MODEL=$BASE/train/seed$SEED/${TRAIN_JOBS[$INDEX]}/final_model
  EVAL=$BASE/evaluate/seed$SEED/${EVAL_JOBS[$INDEX]}
  CACHE=$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_scores/12385292_$INDEX/margins
  test -s "$CACHE/SCREEN/c_elegans.npz"
  test -s "$CACHE/DEV/c_elegans.npz"
  python3 "$CODE/diagnose_anchor_scores.py" \
    --seed "$SEED" --model-dir "$MODEL" --tokenizer-dir "$MODEL" \
    --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
    --calibration-json "$EVAL/calibration.json" \
    --screen-data "$BASE/materialization/12306000/SCREEN/c_elegans.jsonl.gz" \
    --dev-data "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/c_elegans.jsonl.gz" \
    --screen-expected "$EVAL/screen_metrics.json" --dev-expected "$EVAL/dev_metrics.json" \
    --cache-root "$CACHE" \
    --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-INIT-HISTORY-V1/j0_recover/$SLURM_JOB_ID/seed$SEED"
done
