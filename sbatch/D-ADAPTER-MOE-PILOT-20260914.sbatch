#!/usr/bin/env bash
# Bounded frozen-D hidden-feature adapter/MoE pilot, seed 42 only.
# The MoE is a two-expert prediction head; the NTv2/D backbone is frozen.
# Config is copied to the shared project before submission.
#
# Example:
# sbatch sbatch/D-ADAPTER-MOE-PILOT-20260914.sbatch

#SBATCH --job-name=d_adapter_moe
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/d_adapter_moe_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/d_adapter_moe_%j.err

set -euo pipefail

ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

cd "$ROOT"
CONFIG="$ROOT/configs/D-ADAPTER-MOE-PILOT-20260914.json"
SOURCE="$ROOT/scripts/experiments/D-ADAPTER-MOE-PILOT-20260914/pilot.py"
OUT="$ROOT/outputs/D-ADAPTER-MOE-PILOT-20260914/seed42/slurm-${SLURM_JOB_ID}"

test -s "$CONFIG"
test -s "$SOURCE"
mkdir -p "$OUT"
python3 "$SOURCE" --config "$CONFIG" --output-dir "$OUT"
