#!/usr/bin/env bash
# CPU-only Stage 1 candidate manifest; explicitly excludes chr19.
#SBATCH --job-name=gap-s1-manifest
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/gap-neural-s1-manifest_%j.out
#SBATCH --error=logs/gap-neural-s1-manifest_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG}"
OUTPUT_DIR=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-${ATTEMPT_TAG}

cd "${ROOT}"
python3 scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_candidate_manifest.py \
  --source-root outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1 \
  --stage0-json outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0-oracle-20260902-r1/stage0_oracle.json \
  --output-dir "${OUTPUT_DIR}"
