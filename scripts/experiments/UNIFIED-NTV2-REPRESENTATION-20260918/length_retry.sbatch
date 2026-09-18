#!/usr/bin/env bash
# Length-only retry after repairing source/context coordinate indexing.
# This intentionally does not rerun the completed three-arm SIB extraction.
# LENGTH_RETRY_OUT may be set by the submitting dependency chain.
#SBATCH --job-name=ntv2-length-retry
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-retry-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-length-retry-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
BINARY_DATA="$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
CLASS_DATA="$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/matched_class_data"
WORM_OVERRIDE="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/TRAIN/c_elegans.jsonl.gz"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
D_MODEL="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model"
CLASS_MODEL="${CLASS_MODEL:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/class_training/last2-seed42-12889091/best_model}"
OUT_ROOT="${LENGTH_RETRY_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/length-retry-${SLURM_JOB_ID}}"
mkdir -p "$OUT_ROOT"

python3 "$CODE/extract_length_context.py" \
  --binary-data-root "$BINARY_DATA" \
  --class-data-root "$CLASS_DATA" \
  --worm-train-override "$WORM_OVERRIDE" \
  --base-model "$BASE_MODEL" \
  --out-root "$OUT_ROOT" \
  --batch-size 2 \
  --seed 42 \
  --model "pretrained=$BASE_MODEL=pretrained" \
  --model "binary_D=$D_MODEL=token_classifier" \
  --model "class_D_last2=$CLASS_MODEL=token_classifier"

printf 'PASS_EXTRACTION\n' > "$OUT_ROOT/RETRY_STATUS"
printf 'job=%s\nrun_root=%s\nclass_model=%s\ncoordinate_contract=central_target_source_slice_v2\n' \
  "$SLURM_JOB_ID" "$OUT_ROOT" "$CLASS_MODEL" > "$OUT_ROOT/run_meta.txt"
