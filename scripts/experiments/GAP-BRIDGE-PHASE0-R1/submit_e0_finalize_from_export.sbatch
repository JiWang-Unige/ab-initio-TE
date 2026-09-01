#!/usr/bin/env bash
# CPU-only recovery of candidate tables from the complete 20260901-r2 P3
# exports.  The two GPU jobs failed only while flushing Slurm stdout after the
# export manifests and tracks had been written with status PASS.
#SBATCH --job-name=TE_E0_FINALIZE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-finalize-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-finalize-%A_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submitting E0 finalization}"

ROOT=/home/users/j/jwang/ab-initio-TE
GAP_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gap_table.py
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/e0-preflight-20260901-r2
FINAL_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/e0-finalize-${ATTEMPT_TAG}
COMPARATOR_POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
COMPARATOR_UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz

case "${SLURM_ARRAY_TASK_ID}" in
  0) SEQID=chr3 ;;
  1) SEQID=chr5 ;;
  *) echo "unexpected E0 finalization array task: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

SOURCE_TASK=${SOURCE_ROOT}/${SEQID}
FINAL_TASK=${FINAL_ROOT}/${SEQID}

for required_path in \
  "${GAP_SCRIPT}" \
  "${SOURCE_TASK}/region.jsonl.gz" \
  "${SOURCE_TASK}/prediction.canonical.tsv" \
  "${SOURCE_TASK}/p_te.npy" \
  "${SOURCE_TASK}/states.npy" \
  "${SOURCE_TASK}/export.manifest.json" \
  "${COMPARATOR_POSITIVE}" \
  "${COMPARATOR_UNKNOWN}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing E0 finalization asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${FINAL_TASK}" ]]; then
  echo "refusing to reuse E0 finalization output directory: ${FINAL_TASK}" >&2
  exit 2
fi

mkdir -p "${FINAL_ROOT}"
mkdir "${FINAL_TASK}"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

python3 "${GAP_SCRIPT}" candidates \
  --p3-canonical "${SOURCE_TASK}/prediction.canonical.tsv" \
  --data-jsonl "${SOURCE_TASK}/region.jsonl.gz" \
  --pte-npy "${SOURCE_TASK}/p_te.npy" \
  --state-probabilities-npy "${SOURCE_TASK}/states.npy" \
  --output "${FINAL_TASK}/candidates.tsv" >/dev/null

python3 "${GAP_SCRIPT}" project-labels \
  --candidates "${FINAL_TASK}/candidates.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --output "${FINAL_TASK}/labeled.tsv" >/dev/null

python3 "${GAP_SCRIPT}" census \
  --labeled "${FINAL_TASK}/labeled.tsv" \
  --output "${FINAL_TASK}/candidate_census.json" >/dev/null

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${FINAL_TASK}/JOBID"
printf 'PASS\n' > "${FINAL_TASK}/STATUS"
