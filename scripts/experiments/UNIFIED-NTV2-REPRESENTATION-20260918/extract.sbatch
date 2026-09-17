#!/usr/bin/env bash
# Extract all three matched representations with one tokenizer/pooling path.
# This job is inference-only; the SIB split and labels are never changed.
#SBATCH --job-name=ntv2-matched-extract
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:45:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-extract-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-extract-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
DATA_DIR="$ROOT/outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
D_MODEL="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model"
CLASS_MODEL="${CLASS_MODEL:?Set CLASS_MODEL to the validation-selected class checkpoint}"
OUT_ROOT="${EXTRACT_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/embeddings-${SLURM_JOB_ID}}"
mkdir -p "$OUT_ROOT"

python3 "$CODE/extract_matched_ntv2.py" \
  --data-dir "$DATA_DIR" \
  --out-root "$OUT_ROOT" \
  --base-model "$BASE_MODEL" \
  --batch-size 8 \
  --max-length 2048 \
  --model "pretrained=$BASE_MODEL=pretrained" \
  --model "binary_D=$D_MODEL=token_classifier" \
  --model "class_D_last2=$CLASS_MODEL=token_classifier"

# Bounded context-length diagnostic on the same GPU and source lane.  It uses
# the same three weights but pools only the exact central 512-bp target.
BINARY_DATA="$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
CLASS_DATA="$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/matched_class_data"
WORM_OVERRIDE="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/TRAIN/c_elegans.jsonl.gz"
set +e
python3 "$CODE/extract_length_context.py" \
  --binary-data-root "$BINARY_DATA" \
  --class-data-root "$CLASS_DATA" \
  --worm-train-override "$WORM_OVERRIDE" \
  --base-model "$BASE_MODEL" \
  --out-root "$OUT_ROOT/length_context" \
  --batch-size 2 \
  --seed 42 \
  --model "pretrained=$BASE_MODEL=pretrained" \
  --model "binary_D=$D_MODEL=token_classifier" \
  --model "class_D_last2=$CLASS_MODEL=token_classifier"
LENGTH_RC=$?
set -e
if [[ "$LENGTH_RC" -ne 0 ]]; then
  printf 'BLOCKED_NATIVE_OFFSET\n' > "$OUT_ROOT/length_context/STATUS"
  printf 'length_context_exit=%s\n' "$LENGTH_RC" > "$OUT_ROOT/length_context/BLOCKED_REASON"
fi

printf 'PASS\n' > "$OUT_ROOT/EXTRACT_STATUS"
printf 'job=%s\nrun_root=%s\nclass_model=%s\n' "$SLURM_JOB_ID" "$OUT_ROOT" "$CLASS_MODEL" > "$OUT_ROOT/run_meta.txt"
