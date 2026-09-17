#!/usr/bin/env bash
# Re-evaluate the completed feature extraction with the corrected species
# metadata/readout implementation. No model is loaded in this CPU-only job.
#SBATCH --job-name=emb-match-eval
#SBATCH --partition=debug-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/embedding-closure-eval-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
ROOT=$(pwd -P)
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
RUN_ROOT="$ROOT/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477"
SCRIPT="$ROOT/scripts/experiments/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/evaluate_matched_embeddings.py"
CONFIG="$ROOT/configs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917.yaml"
for MODEL_ID in pretrained six_species_D; do
  python "$SCRIPT" --config "$CONFIG" \
    --feature-root "$RUN_ROOT/features/$MODEL_ID" \
    --out-dir "$RUN_ROOT/metrics/$MODEL_ID"
done
printf 'EVALUATION_COMPLETED\n' > "$RUN_ROOT/EVALUATION_STATUS"
