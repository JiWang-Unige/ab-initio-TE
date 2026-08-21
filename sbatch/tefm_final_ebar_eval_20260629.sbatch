#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_EBAR_EVAL
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu051
#SBATCH --array=1-66%8
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/eval_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629/eval_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-EBAR-20260629
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token 2>/dev/null || true)"
python3 scripts/pre_submit_gate.py --exp-id tefm_final_ebar_eval_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-EBAR-20260629.eval_jobs.tsv
