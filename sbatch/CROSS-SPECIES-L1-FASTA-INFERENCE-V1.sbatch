#!/usr/bin/env bash
#SBATCH --job-name=te_l1_fasta_smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_fasta_smoke_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_fasta_smoke_%j.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
srun python3 scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/smoke_fasta.py \
  --model-dir "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model" \
  --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --calibration-json "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json" \
  --output-dir "$ROOT/outputs/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/$SLURM_JOB_ID"
