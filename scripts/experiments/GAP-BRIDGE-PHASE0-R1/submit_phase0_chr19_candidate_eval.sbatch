#!/usr/bin/env bash
# One-use chr19 comparator projection and complete locked Phase-0 gate.
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
MASK_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_mask_fragment_gate.py
GENE_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gene_safety.py
DECISION_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gate_decision.py
COMPARATOR_POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
COMPARATOR_UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz
REFGENE=${ROOT}/data/raw/ucsc/human/hg38/genes/ncbiRefSeqCurated-20250813.txt.gz
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-${SOURCE_TAG}
LOCK_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/feature-lock-${LOCK_TAG}
PURGE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/homology-purge-${PURGE_TAG}
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/chr19-test-${ATTEMPT_TAG}

for required_path in \
  "${GAP_SCRIPT}" \
  "${EVAL_SCRIPT}" \
  "${MASK_SCRIPT}" \
  "${GENE_SCRIPT}" \
  "${DECISION_SCRIPT}" \
  "${COMPARATOR_POSITIVE}" \
  "${COMPARATOR_UNKNOWN}" \
  "${REFGENE}" \
  "${SOURCE_ROOT}/chr19/candidates.tsv" \
  "${SOURCE_ROOT}/chr19/prediction.canonical.tsv" \
  "${SOURCE_ROOT}/chr19/TEST_LABELS_SEALED" \
  "${LOCK_ROOT}/feature_lock.json" \
  "${PURGE_ROOT}/purge_membership.tsv" \
  "${PURGE_ROOT}/purge_census.json" \
  "${PURGE_ROOT}/STATUS"; do
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

LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}
TASK_ROOT=$(mktemp -d "${LOCAL_SCRATCH}/te-gap-chr19-${SLURM_JOB_ID}-XXXXXX")
CURRENT_STAGE=feature_lock_purge_preflight
LABELS_RELEASED=0
# Preflight requires a PASS_TO_TEST True feature lock and PASS purge contract.
finish() {
  rc=$?
  trap - EXIT
  set +e
  if [[ "${rc}" -ne 0 ]]; then
    printf 'FAILED\n' > "${TASK_ROOT}/STATUS"
    printf '%s\n' "${CURRENT_STAGE}" > "${TASK_ROOT}/FAILURE_STAGE"
    printf '%s\n' "${rc}" > "${TASK_ROOT}/FAILURE_RC"
  fi
  if [[ "${LABELS_RELEASED}" == 1 && ! -e "${TASK_ROOT}/TEST_LABELS_CONSUMED" ]]; then
    printf 'CHR19_TEST_LABELS_CONSUMED_ONCE\n' > "${TASK_ROOT}/TEST_LABELS_CONSUMED"
  fi
  mkdir -p "$(dirname "${RUN_ROOT}")"
  TRANSFER_ROOT=$(dirname "${RUN_ROOT}")/.transfer-chr19-${SLURM_JOB_ID}
  mkdir "${TRANSFER_ROOT}" \
    && cp -a "${TASK_ROOT}/." "${TRANSFER_ROOT}/" \
    && mv "${TRANSFER_ROOT}" "${RUN_ROOT}"
  transfer_rc=$?
  rm -rf "${TASK_ROOT}"
  if [[ "${transfer_rc}" -ne 0 ]]; then
    exit "${transfer_rc}"
  fi
  exit "${rc}"
}
trap finish EXIT

python3 - "${LOCK_ROOT}/feature_lock.json" "${PURGE_ROOT}/purge_census.json" "${PURGE_ROOT}/STATUS" <<'PY'
import json
import sys

lock_path, purge_json_path, purge_status_path = sys.argv[1:]
lock = json.loads(open(lock_path, encoding="utf-8").read())
if (
    lock.get("status"),
    lock.get("selection_locked"),
    lock.get("test_labels_read"),
    lock.get("test_label_release_allowed"),
) != ("PASS_TO_TEST", True, False, True):
    raise SystemExit("feature lock does not authorize chr19 label release")
purge = json.loads(open(purge_json_path, encoding="utf-8").read())
if purge.get("status") != "PASS":
    raise SystemExit("homology purge census is not PASS")
purge_status = open(purge_status_path, encoding="utf-8").read().strip()
if purge_status != "PASS":
    raise SystemExit("homology purge STATUS is not PASS")
PY

cd "${ROOT}"
CURRENT_STAGE=environment
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

CURRENT_STAGE=project_labels
python3 "${GAP_SCRIPT}" project-labels \
  --candidates "${SOURCE_ROOT}/chr19/candidates.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --output "${TASK_ROOT}/labeled.tsv"
LABELS_RELEASED=1
printf 'CHR19_TEST_LABELS_CONSUMED_ONCE\n' > "${TASK_ROOT}/TEST_LABELS_CONSUMED"

CURRENT_STAGE=candidate_evaluation
python3 "${EVAL_SCRIPT}" \
  --feature-lock "${LOCK_ROOT}/feature_lock.json" \
  --labeled "${TASK_ROOT}/labeled.tsv" \
  --purge-membership "${PURGE_ROOT}/purge_membership.tsv" \
  --output "${TASK_ROOT}/candidate_evaluation.json" >/dev/null

CURRENT_STAGE=mask_fragment_gate
python3 "${MASK_SCRIPT}" \
  --feature-lock "${LOCK_ROOT}/feature_lock.json" \
  --candidate-evaluation "${TASK_ROOT}/candidate_evaluation.json" \
  --labeled "${TASK_ROOT}/labeled.tsv" \
  --p3-canonical "${SOURCE_ROOT}/chr19/prediction.canonical.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --chromosome-length 58617616 \
  --output "${TASK_ROOT}/mask_fragment.json" \
  --refined-canonical "${TASK_ROOT}/refined.canonical.tsv" \
  --selected-sidecar "${TASK_ROOT}/selected.tsv" >/dev/null

CURRENT_STAGE=gene_safety
python3 "${GENE_SCRIPT}" \
  --intervals "${TASK_ROOT}/selected.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --refgene "${REFGENE}" \
  --annotation-version ncbiRefSeqCurated-20250813 \
  --annotation-url https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/ncbiRefSeqCurated.txt.gz \
  --positive-version hg38-rmsk_te_strict \
  --unknown-version hg38-rmsk_te_plus_unknown \
  --output-json "${TASK_ROOT}/gene_safety.json" \
  --output-tsv "${TASK_ROOT}/gene_safety.tsv" >/dev/null

CURRENT_STAGE=gate_decision
python3 "${DECISION_SCRIPT}" \
  --candidate-evaluation "${TASK_ROOT}/candidate_evaluation.json" \
  --mask-fragment "${TASK_ROOT}/mask_fragment.json" \
  --gene-safety "${TASK_ROOT}/gene_safety.json" \
  --output "${TASK_ROOT}/gate_decision.json" >/dev/null

DECISION_STATUS=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["status"])' "${TASK_ROOT}/gate_decision.json")
printf '%s\n' "${SLURM_JOB_ID}" > "${TASK_ROOT}/JOBID"
printf '%s\n' "${DECISION_STATUS}" > "${TASK_ROOT}/STATUS"
