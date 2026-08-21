#!/usr/bin/env bash
#SBATCH --job-name=TFSEGSF_EMB
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/emb_%A_%a.out
#SBATCH --error=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/emb_%A_%a.err
#SBATCH --array=1-48

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618
eval "$(conda shell.bash hook)"
conda activate te_benchmark
bash pipelines/PIPE-TEFM-SEG-SF-20260618/run_cmd_array.sh configs/pipelines/PIPE-TEFM-SEG-SF-20260618.embedding_cluster_jobs.tsv
