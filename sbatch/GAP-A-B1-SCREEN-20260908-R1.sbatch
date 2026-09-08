#!/usr/bin/env bash
# CPU prepare/evaluate use --gres=none and shorter --time at submission.
#SBATCH --job-name=gap-ab1-screen
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=logs/gap-ab1-screen_%j.out
#SBATCH --error=logs/gap-ab1-screen_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface
export PYTHONUNBUFFERED=1 WANDB_DISABLED=true OMP_NUM_THREADS=8
SCRIPT=scripts/experiments/GAP-A-B1-SCREEN-20260908-R1/screen.py
: "${SCREEN_STAGE:?submit with explicit SCREEN_STAGE}"
if [[ "$SCREEN_STAGE" == prepare ]]; then
  python -m unittest discover -s scripts/experiments/GAP-A-B1-SCREEN-20260908-R1 -p 'test_screen.py' -v
fi
if [[ "$SCREEN_STAGE" == evaluate ]]; then
  : "${PURGE_PATH:?original DEV homology purge path required}"
  python "$SCRIPT" evaluate --purge "$PURGE_PATH"
else
  python "$SCRIPT" "$SCREEN_STAGE"
fi
