#!/usr/bin/env bash
# Matched NTv2 class fine-tune initialized from the frozen binary D checkpoint.
# The protocol fixes the class ontology, split, projection, and validation
# selection before the DEV test pass.
#SBATCH --job-name=ntv2-matched-class-train
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-train-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-train-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
D_MODEL="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
DATA_DIR="$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/matched_class_data"
OUT_DIR="${CLASS_TRAIN_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/class_training/last2-seed42-${SLURM_JOB_ID}}"

python3 "$CODE/train_matched_class.py" \
  --init-checkpoint "$D_MODEL" \
  --base-model "$BASE_MODEL" \
  --data-dir "$DATA_DIR" \
  --output-dir "$OUT_DIR" \
  --seed 42 \
  --train-scope last2 \
  --max-steps 900 \
  --eval-steps 150 \
  --warmup-steps 90 \
  --learning-rate 2e-5 \
  --weight-decay 0.01 \
  --grad-clip 1.0 \
  --bf16

printf 'PASS\n' > "$OUT_DIR/CLASS_TRAIN_STATUS"
printf 'job=%s\noutput_dir=%s\n' "$SLURM_JOB_ID" "$OUT_DIR" > "$OUT_DIR/run_meta.txt"
