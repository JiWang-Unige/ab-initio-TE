#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_DL_N3
#SBATCH --partition=shared-bigmem
#SBATCH --array=4-9%2
#SBATCH --cpus-per-task=4
#SBATCH --mem=180G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-20260623/download_ntv3_%A_%a.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-20260623/download_ntv3_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-20260623
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token)"
python3 scripts/pre_submit_gate.py --exp-id tefm_final_download_ntv3_20260629
bash pipelines/PIPE-TEFM-FINAL-20260623/run_cmd_array.sh configs/pipelines/PIPE-TEFM-FINAL-20260623.download_jobs.tsv
