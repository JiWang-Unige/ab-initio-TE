#!/usr/bin/env bash
# Loader-only CPU smoke for the native D -> fresh 8-class head transfer.
# It consumes no GPU and is intentionally not a scientific score.
#SBATCH --job-name=ntv2-matched-class-smoke-cpu
#SBATCH --partition=debug-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-smoke-cpu-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-smoke-cpu-%j.err

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
RECORD="$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/TRAIN/human.jsonl.gz"
RUN_ROOT="${RUN_ROOT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/smoke-cpu-${SLURM_JOB_ID}}"
mkdir -p "$RUN_ROOT"
python3 "$CODE/smoke_model.py" \
  --init-checkpoint "$D_MODEL" \
  --base-model "$BASE_MODEL" \
  --data-record "$RECORD" \
  --out-json "$RUN_ROOT/smoke.json"
printf 'PASS\n' > "$RUN_ROOT/STATUS"
printf 'job=%s\nrun_root=%s\n' "$SLURM_JOB_ID" "$RUN_ROOT" > "$RUN_ROOT/run_meta.txt"
