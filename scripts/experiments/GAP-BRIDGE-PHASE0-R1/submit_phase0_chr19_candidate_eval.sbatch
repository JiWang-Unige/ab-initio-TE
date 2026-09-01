#!/usr/bin/env bash
# One-use chr19 comparator projection and locked candidate-level evaluation.
#SBATCH --job-name=TE_GAP_CHR19_EVAL
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/chr19-eval-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/chr19-eval-%j.err

set -euo pipefail

: "${SOURCE_TAG:?set SOURCE_TAG to the completed whole-chromosome attempt}"
: "${LOCK_TAG:?set LOCK_TAG to the completed feature-lock attempt}"
: "${PURGE_TAG:?set PURGE_TAG to the completed label-blind purge attempt}"
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for the one-use test}"

ROOT=/home/users/j/jwang/ab-initio-TE
GAP_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gap_table.py
EVAL_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_chr19_evaluate.py
COMPARATOR_POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
COMPARATOR_UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-${SOURCE_TAG}
LOCK_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/feature-lock-${LOCK_TAG}
PURGE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/homology-purge-${PURGE_TAG}
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/chr19-test-${ATTEMPT_TAG}

for required_path in \
  "${GAP_SCRIPT}" \
  "${EVAL_SCRIPT}" \
  "${COMPARATOR_POSITIVE}" \
  "${COMPARATOR_UNKNOWN}" \
  "${SOURCE_ROOT}/chr19/candidates.tsv" \
  "${SOURCE_ROOT}/chr19/TEST_LABELS_SEALED" \
  "${LOCK_ROOT}/feature_lock.json" \
  "${PURGE_ROOT}/purge_membership.tsv"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing chr19 locked-evaluation asset: ${required_path}" >&2
    exit 2
  fi
done
if [[ -e "${SOURCE_ROOT}/chr19/labeled.tsv" ]]; then
  echo "source chr19 label seal was violated" >&2
  exit 2
fi
if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse one-use chr19 output: ${RUN_ROOT}" >&2
  exit 2
fi

LOCK_STATUS=$(python3 -c 'import json, sys; x=json.load(open(sys.argv[1])); print(x["status"], x["test_label_release_allowed"])' "${LOCK_ROOT}/feature_lock.json")
if [[ "${LOCK_STATUS}" != "PASS_TO_TEST True" ]]; then
  echo "feature lock does not authorize chr19 label release: ${LOCK_STATUS}" >&2
  exit 3
fi

LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}
TASK_ROOT=$(mktemp -d "${LOCAL_SCRATCH}/te-gap-chr19-${SLURM_JOB_ID}-XXXXXX")
trap 'rm -rf "${TASK_ROOT}"' EXIT

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

python3 "${GAP_SCRIPT}" project-labels \
  --candidates "${SOURCE_ROOT}/chr19/candidates.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --output "${TASK_ROOT}/labeled.tsv"

python3 "${EVAL_SCRIPT}" \
  --feature-lock "${LOCK_ROOT}/feature_lock.json" \
  --labeled "${TASK_ROOT}/labeled.tsv" \
  --purge-membership "${PURGE_ROOT}/purge_membership.tsv" \
  --output "${TASK_ROOT}/candidate_evaluation.json" >/dev/null

EVAL_STATUS=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["status"])' "${TASK_ROOT}/candidate_evaluation.json")
printf '%s\n' "${SLURM_JOB_ID}" > "${TASK_ROOT}/JOBID"
printf '%s\n' "${EVAL_STATUS}" > "${TASK_ROOT}/STATUS"
printf 'CHR19_TEST_LABELS_CONSUMED_ONCE\n' > "${TASK_ROOT}/TEST_LABELS_CONSUMED"

mkdir -p "$(dirname "${RUN_ROOT}")"
TRANSFER_ROOT=$(dirname "${RUN_ROOT}")/.transfer-chr19-${SLURM_JOB_ID}
mkdir "${TRANSFER_ROOT}"
cp -a "${TASK_ROOT}/." "${TRANSFER_ROOT}/"
mv "${TRANSFER_ROOT}" "${RUN_ROOT}"
