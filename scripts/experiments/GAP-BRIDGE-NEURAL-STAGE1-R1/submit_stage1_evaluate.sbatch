#!/usr/bin/env bash
# Frozen chr13 Stage 1 evaluation and CAL-GATE action lock.
# This is CPU-only and may run only after label-blind scoring has completed.
# No chr19 input is referenced here.
# ATTEMPT_TAG, SCORE_TAG, PURGE_TAG and FAMILY_TAG identify immutable inputs.
#SBATCH --job-name=gap-s1-evaluate
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=24:00:00
#SBATCH --output=logs/gap-neural-s1-evaluate_%j.out
#SBATCH --error=logs/gap-neural-s1-evaluate_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-NEURAL-STAGE1-R1/stage1_evaluate.py
MANIFEST=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1
POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz
REFGENE=${ROOT}/data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz
: "${SCORE_TAG:?set the completed Stage 1 scoring tag}"
: "${PURGE_TAG:?set the completed DEV purge tag}"
: "${FAMILY_TAG:?set the completed family projection tag}"
: "${ATTEMPT_TAG:?set a unique Stage 1 evaluation tag}"
SCORE=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/score-${SCORE_TAG}/chr13_stage1_raw_logits.tsv
PURGE=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/dev-homology-purge-${PURGE_TAG}/dev_purge_membership.tsv
FAMILY=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/family-projection-${FAMILY_TAG}/chr13_family_projection.tsv
OUTPUT=${ROOT}/outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/evaluate-${ATTEMPT_TAG}

for required_path in "${SCRIPT}" "${MANIFEST}" "${SCORE}" "${PURGE}" "${FAMILY}" \
  "${SOURCE_ROOT}/chr13/region.jsonl.gz" "${SOURCE_ROOT}/chr13/prediction.canonical.tsv" \
  "${POSITIVE}" "${UNKNOWN}" "${REFGENE}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing Stage 1 evaluation asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT}" ]]; then
  echo "refusing to reuse Stage 1 evaluation output: ${OUTPUT}" >&2
  exit 2
fi

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export PYTHONUNBUFFERED=1

python3 "${SCRIPT}" \
  --candidate-manifest "${MANIFEST}" \
  --raw-score "${SCORE}" \
  --homology-purge "${PURGE}" \
  --family-projection "${FAMILY}" \
  --source-root "${SOURCE_ROOT}" \
  --comparator-positive "${POSITIVE}" \
  --comparator-unknown "${UNKNOWN}" \
  --refgene "${REFGENE}" \
  --output-dir "${OUTPUT}"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUTPUT}/JOBID"
