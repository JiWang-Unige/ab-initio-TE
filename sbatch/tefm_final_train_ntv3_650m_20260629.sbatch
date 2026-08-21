#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_TR_N3650
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_a100_80gb_pcie:1
#SBATCH --exclude=gpu051
#SBATCH --array=26-30,41-45%1
#SBATCH --cpus-per-task=6
#SBATCH --mem=120G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/train_ntv3_650m_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/train_ntv3_650m_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token)"
python3 scripts/pre_submit_gate.py --exp-id tefm_final_train_ntv3_650m_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.train_jobs.tsv
