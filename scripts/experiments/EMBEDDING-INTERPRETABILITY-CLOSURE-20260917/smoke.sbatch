#!/usr/bin/env bash
# One-record-per-split loader and pooling smoke. It is not a scientific run.
#SBATCH --job-name=emb-match-smoke
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:tesla_p100-pcie-12gb:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-smoke-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-smoke-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
RUN_ROOT="$ROOT/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/smoke-${SLURM_JOB_ID}"
SCRIPT="$ROOT/scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917"
DATA_DIR="$ROOT/outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
D_MODEL="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model"
mkdir -p "$RUN_ROOT"
python "$SCRIPT/extract_matched_ntv2.py" \
  --data-dir "$DATA_DIR" \
  --out-root "$RUN_ROOT/features" \
  --base-model "$BASE_MODEL" \
  --model "pretrained=$BASE_MODEL=pretrained" \
  --model "six_species_D=$D_MODEL=token_classifier" \
  --batch-size 2 --max-length 2048 --max-records 1 --device cuda
test -f "$RUN_ROOT/features/input_manifest.json"
test -f "$RUN_ROOT/features/pretrained/train_features.npy"
test -f "$RUN_ROOT/features/six_species_D/test_features.npy"
printf 'SMOKE_COMPLETED\n' > "$RUN_ROOT/STATUS"
printf 'job=%s\nrun_root=%s\n' "$SLURM_JOB_ID" "$RUN_ROOT" > "$RUN_ROOT/run_meta.txt"
