#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_EV_N3S
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu051
#SBATCH --array=166-275,331-440%8
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/eval_ntv3_small_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/eval_ntv3_small_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token)"
python3 scripts/pre_submit_gate.py --exp-id tefm_final_eval_ntv3_small_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.eval_jobs.tsv
