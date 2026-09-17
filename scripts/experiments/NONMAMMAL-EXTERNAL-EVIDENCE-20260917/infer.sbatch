#!/usr/bin/env bash
#SBATCH --job-name=d_external_long
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=logs/d_external_long_%j.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
SPECIES=${1:?species is required}
OUT="outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES/inference-$SLURM_JOB_ID"
python scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py \
  --fasta "outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES/prepared/panel.fa" \
  --model-dir "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model" \
  --model-code-dir "$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species" \
  --calibration-json "$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json" \
  --output-dir "$OUT" --batch-size 12
