#!/usr/bin/env bash
#SBATCH --job-name=TFSEGSF_GPU
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/gpu_%A_%a.out
#SBATCH --error=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/gpu_%A_%a.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618
eval "$(conda shell.bash hook)"
conda activate te_benchmark
JOBS_TSV="${JOBS_TSV:?JOBS_TSV required}"
bash pipelines/PIPE-TEFM-SEG-SF-20260618/run_cmd_array.sh "${JOBS_TSV}"
