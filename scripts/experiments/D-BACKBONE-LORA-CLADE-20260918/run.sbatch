#!/usr/bin/env bash
# Fixed seed-42 clade-conditioned last-two-layer LoRA comparison.
# The job runs the shared rank-16 and routed two-rank-8 arms sequentially.
# No external labels or evaluation are read by this training/evaluation run.
#SBATCH --job-name=d_lora_clade
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/d_lora_clade_%j.out
#SBATCH --error=logs/d_lora_clade_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME="$ROOT/.cache/huggingface"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export PYTHONUNBUFFERED=1

CONFIG="$ROOT/configs/D-BACKBONE-LORA-CLADE-20260918.json"
OUTPUT="$ROOT/outputs/D-BACKBONE-LORA-CLADE-20260918/run-${SLURM_JOB_ID}"
test -s "$CONFIG"
if [[ -e "$OUTPUT" ]]; then
  echo "refusing to reuse output directory: $OUTPUT" >&2
  exit 2
fi

python scripts/experiments/D-BACKBONE-LORA-CLADE-20260918/lora_clade.py \
  --config "$CONFIG" \
  --output-dir "$OUTPUT"

printf '%s\n' "$SLURM_JOB_ID" > "$OUTPUT/JOBID"
