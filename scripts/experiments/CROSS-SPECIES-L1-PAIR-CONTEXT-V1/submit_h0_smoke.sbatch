#!/usr/bin/env bash
#SBATCH --job-name=te_pair_h0_smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_pair_h0_smoke_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_pair_h0_smoke_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4
export HF_HUB_OFFLINE=1
python3 scripts/experiments/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/smoke_h0.py \
  --data-root "$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" \
  --upstream-root "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/h0-smoke/$SLURM_JOB_ID"
