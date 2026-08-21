#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_STN3R
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu051
#SBATCH --array=1-33%4
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/strict_ntv3_retry_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/strict_ntv3_retry_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token 2>/dev/null || true)"
python3 scripts/pre_submit_gate.py --exp-id tefm_final_strictseg_ntv3_retry_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-STRICTSEG-20260629.ntv3_retry_jobs.tsv
