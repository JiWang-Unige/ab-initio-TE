#!/usr/bin/env bash
#SBATCH --job-name=TFSEGSF_SUM
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summarize_%j.out
#SBATCH --error=logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summarize_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618 reports/tefm_seg_sf/PIPE-TEFM-SEG-SF-20260618/summaries
eval "$(conda shell.bash hook)"
conda activate te_benchmark
python3 pipelines/PIPE-TEFM-SEG-SF-20260618/summarize_results.py
