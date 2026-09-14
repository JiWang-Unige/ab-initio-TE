#!/usr/bin/env bash
#SBATCH --job-name=te_pair_operator
#SBATCH --partition=public-short-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_pair_operator_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_pair_operator_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4
export HF_HUB_OFFLINE=1
python3 scripts/experiments/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/test_operator.py \
  --base-model "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --output "$ROOT/outputs/CROSS-SPECIES-L1-PAIR-CONTEXT-V1/operator/$SLURM_JOB_ID/result.json"
