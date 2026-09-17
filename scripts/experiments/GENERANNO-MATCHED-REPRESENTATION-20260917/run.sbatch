#!/usr/bin/env bash
# Inference-only matched GENERanno representation extraction and fixed CPU readouts.
# The caller must submit this file explicitly; no training or checkpoint selection
# occurs here.  Set MAX_RECORDS for the bounded loader smoke only.
#SBATCH --job-name=emb-match-generanno
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:tesla_p100-pcie-12gb:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/generanno-embedding-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/generanno-embedding-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4

RUN_ROOT="${RUN_ROOT:-$ROOT/outputs/GENERANNO-MATCHED-REPRESENTATION-20260917/run-${SLURM_JOB_ID}}"
DATA_DIR="$ROOT/outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512"
TOKENIZER="$ROOT/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base"
BASE="$ROOT/.backup/pretrained_models/GENERanno-eukaryote-0.5b-base"
BINARY="$ROOT/software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42/best_model"
CLASS="$ROOT/software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/runs/SF5_ONTOLOGY_CLOSURE_base_seed42_12731987/best_model"
SCRIPT="$ROOT/scripts/experiments/GENERANNO-MATCHED-REPRESENTATION-20260917"
CONFIG="$ROOT/configs/GENERANNO-MATCHED-REPRESENTATION-20260917.yaml"
EVALUATOR="$ROOT/scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/evaluate_matched_embeddings.py"

mkdir -p "$RUN_ROOT"
MAX_ARGS=()
if [[ -n "${MAX_RECORDS:-}" ]]; then
  MAX_ARGS=(--max-records "$MAX_RECORDS")
fi

python "$SCRIPT/extract_matched_generanno.py" \
  --data-dir "$DATA_DIR" \
  --out-root "$RUN_ROOT/features" \
  --tokenizer-checkpoint "$TOKENIZER" \
  --model "pretrained=$BASE=pretrained" \
  --model "binary_finetuned=$BINARY=token_classifier" \
  --model "multiclass_finetuned=$CLASS=token_classifier" \
  --batch-size 4 \
  --max-length 2048 \
  --device cuda \
  "${MAX_ARGS[@]}"

if [[ -z "${MAX_RECORDS:-}" ]]; then
  for MODEL_ID in pretrained binary_finetuned multiclass_finetuned; do
    python "$EVALUATOR" \
      --config "$CONFIG" \
      --feature-root "$RUN_ROOT/features/$MODEL_ID" \
      --out-dir "$RUN_ROOT/metrics/$MODEL_ID"
  done
fi

printf 'COMPLETED\n' > "$RUN_ROOT/STATUS"
printf 'job=%s\nrun_root=%s\n' "$SLURM_JOB_ID" "$RUN_ROOT" > "$RUN_ROOT/run_meta.txt"
