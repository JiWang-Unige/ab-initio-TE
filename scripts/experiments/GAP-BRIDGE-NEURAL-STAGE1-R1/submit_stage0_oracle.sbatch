#!/usr/bin/env bash
#SBATCH --job-name=gap-neural-s0-oracle
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --output=logs/gap-neural-s0-oracle_%j.out
#SBATCH --error=logs/gap-neural-s0-oracle_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG}"
OUTPUT_ROOT="${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0-oracle-${ATTEMPT_TAG}"

cd "${ROOT}"

python3 scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage0_oracle.py \
  --source-root outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1 \
  --comparator-positive software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz \
  --comparator-unknown software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz \
  --refgene data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz \
  --output-dir "${OUTPUT_ROOT}"
