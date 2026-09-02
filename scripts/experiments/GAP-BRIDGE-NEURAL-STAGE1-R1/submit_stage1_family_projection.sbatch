#!/usr/bin/env bash
# Evaluation-only chr13 projection of strict RepeatMasker class/family labels.
# ATTEMPT_TAG identifies one immutable output directory.
# This job must not read chr19 or any candidate comparator/target label fields.
#SBATCH --job-name=gap-s1-family
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/gap-neural-s1-family_%j.out
#SBATCH --error=logs/gap-neural-s1-family_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_family_projection.py
MANIFEST=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
STRICT_BED=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
: "${ATTEMPT_TAG:?set a unique Stage 1 family-projection tag}"
OUTPUT_DIR=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/family-projection-${ATTEMPT_TAG}

cd "${ROOT}"
python3 "${SCRIPT}" \
  --candidate-manifest "${MANIFEST}" \
  --strict-bed "${STRICT_BED}" \
  --output-dir "${OUTPUT_DIR}"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUTPUT_DIR}/JOBID"
