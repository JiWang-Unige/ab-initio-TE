#!/usr/bin/env bash
# CPU-only whole-chromosome stitch, candidate export and comparator projection.
# Submit afterok on the full chunk array.
#SBATCH --job-name=TE_GAP_FULL_STITCH
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --array=0-3%4
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/full-stitch-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/full-stitch-%A_%a.err

set -euo pipefail

: "${SOURCE_TAG:?set SOURCE_TAG to the completed full chunk attempt}"
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for whole-chromosome outputs}"

ROOT=/home/users/j/jwang/ab-initio-TE
E0_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py
GAP_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gap_table.py
COMPARATOR_POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
COMPARATOR_UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz

case "${SLURM_ARRAY_TASK_ID}" in
  0) SEQID=chr3; LENGTH=198295559 ;;
  1) SEQID=chr5; LENGTH=181538259 ;;
  2) SEQID=chr13; LENGTH=114364328 ;;
  3) SEQID=chr19; LENGTH=58617616 ;;
  *) echo "unexpected full Phase-0 stitch task: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

CHUNK_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-chunks-${SOURCE_TAG}/${SEQID}
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-${ATTEMPT_TAG}
TASK_ROOT=${RUN_ROOT}/${SEQID}

for required_path in \
  "${E0_SCRIPT}" \
  "${GAP_SCRIPT}" \
  "${CHUNK_ROOT}" \
  "${COMPARATOR_POSITIVE}" \
  "${COMPARATOR_UNKNOWN}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing full Phase-0 stitch asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${TASK_ROOT}" ]]; then
  echo "refusing to reuse full Phase-0 whole output: ${TASK_ROOT}" >&2
  exit 2
fi

mkdir -p "${RUN_ROOT}"
mkdir "${TASK_ROOT}"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

python3 "${E0_SCRIPT}" stitch-chunks \
  --chunk-root "${CHUNK_ROOT}" \
  --seqid "${SEQID}" \
  --expected-length "${LENGTH}" \
  --output-region-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --output-region-manifest "${TASK_ROOT}/region.manifest.json" \
  --output-pte "${TASK_ROOT}/p_te.npy" \
  --output-states "${TASK_ROOT}/states.npy" \
  --output-canonical "${TASK_ROOT}/prediction.canonical.tsv" \
  --output-export-manifest "${TASK_ROOT}/export.manifest.json" >/dev/null

python3 "${GAP_SCRIPT}" candidates \
  --p3-canonical "${TASK_ROOT}/prediction.canonical.tsv" \
  --data-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --pte-npy "${TASK_ROOT}/p_te.npy" \
  --state-probabilities-npy "${TASK_ROOT}/states.npy" \
  --output "${TASK_ROOT}/candidates.tsv" >/dev/null

if [[ "${SEQID}" != "chr19" ]]; then
  python3 "${GAP_SCRIPT}" project-labels \
    --candidates "${TASK_ROOT}/candidates.tsv" \
    --comparator-positive "${COMPARATOR_POSITIVE}" \
    --comparator-unknown "${COMPARATOR_UNKNOWN}" \
    --output "${TASK_ROOT}/labeled.tsv" >/dev/null

  python3 "${GAP_SCRIPT}" census \
    --labeled "${TASK_ROOT}/labeled.tsv" \
    --output "${TASK_ROOT}/candidate_census.json" >/dev/null
else
  printf 'SEALED_UNTIL_CHR13_SELECTION_LOCK\n' > "${TASK_ROOT}/TEST_LABELS_SEALED"
fi

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${TASK_ROOT}/JOBID"
printf 'PASS\n' > "${TASK_ROOT}/STATUS"
