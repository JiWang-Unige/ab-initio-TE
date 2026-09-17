#!/usr/bin/env bash
# Matched inference-only NTv2 feature extraction plus frozen CPU readouts.
# The source panel is the non-sealed SIB 512-bp train/val/test panel. No
# encoder is trained in this job; BG and all comparator states are preserved.
# Submit this file explicitly after the loader smoke has passed.
#SBATCH --job-name=emb-match-ntv2
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:tesla_p100-pcie-12gb:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export TEFM_LOCAL_FILES_ONLY=1
export WANDB_DISABLED=true
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4

RUN_ROOT="${RUN_ROOT:-$ROOT/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-${SLURM_JOB_ID}}"
DATA_DIR="$ROOT/outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
D_MODEL="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model"
SCRIPT="$ROOT/scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917"
CONFIG="$ROOT/configs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917.yaml"

mkdir -p "$RUN_ROOT"
MAX_ARGS=()
if [[ -n "${MAX_RECORDS:-}" ]]; then
  MAX_ARGS=(--max-records "$MAX_RECORDS")
fi

python "$SCRIPT/extract_matched_ntv2.py" \
  --data-dir "$DATA_DIR" \
  --out-root "$RUN_ROOT/features" \
  --base-model "$BASE_MODEL" \
  --model "pretrained=$BASE_MODEL=pretrained" \
  --model "six_species_D=$D_MODEL=token_classifier" \
  --batch-size 8 \
  --max-length 2048 \
  --device cuda \
  "${MAX_ARGS[@]}"

if [[ -z "${MAX_RECORDS:-}" ]]; then
  for MODEL_ID in pretrained six_species_D; do
    python "$SCRIPT/evaluate_matched_embeddings.py" \
      --config "$CONFIG" \
      --feature-root "$RUN_ROOT/features/$MODEL_ID" \
      --out-dir "$RUN_ROOT/metrics/$MODEL_ID"
  done
fi

printf 'COMPLETED\n' > "$RUN_ROOT/STATUS"
printf 'job=%s\nrun_root=%s\n' "$SLURM_JOB_ID" "$RUN_ROOT" > "$RUN_ROOT/run_meta.txt"
