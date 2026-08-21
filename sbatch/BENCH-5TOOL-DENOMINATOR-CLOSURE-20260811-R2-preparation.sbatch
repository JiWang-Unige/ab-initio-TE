#!/usr/bin/env bash
# Explicit CPU preparation only. Set TEFM_PREP_ACTION=famdb|hite|edta; never runs a biological benchmark.
#SBATCH --job-name=tefm_b5prep_r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/prep_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/prep_%j.err
set -eo pipefail
TEFM_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
TEFM_EXP=BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2
TEFM_ASSET=${TEFM_ROOT}/software_outputs/tefm_new_directions/${TEFM_EXP}
TEFM_OUT=${TEFM_ROOT}/outputs/${TEFM_EXP}
tefm_environment_failure() {
  TEFM_ENV_RC=$1
  TEFM_ENV_PHASE=$2
  mkdir -p "${TEFM_OUT}"
  TEFM_PREP_STATUS=${TEFM_OUT}/PREPARATION_STATUS_${SLURM_JOB_ID:-nojob}.txt
  printf 'FAILED_ENVIRONMENT:%s\n' "${TEFM_ENV_PHASE}" > "${TEFM_PREP_STATUS}.tmp"
  mv "${TEFM_PREP_STATUS}.tmp" "${TEFM_PREP_STATUS}"
  printf 'preparation environment bootstrap failed: phase=%s rc=%s\n' "${TEFM_ENV_PHASE}" "${TEFM_ENV_RC}" >&2
  exit "${TEFM_ENV_RC}"
}
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh || tefm_environment_failure "$?" conda_source
conda activate benchmark_core || tefm_environment_failure "$?" conda_activate
set -u
python "${TEFM_ROOT}/scripts/pre_submit_gate.py" --exp-id "${TEFM_EXP}"
mkdir -p "${TEFM_ASSET}" "${TEFM_OUT}" "${TEFM_ROOT}/logs/${TEFM_EXP}"
TEFM_PREP_ACTION=${TEFM_PREP_ACTION:?set famdb|hite|edta; pfam is deliberately non-submittable until official release hashes are frozen}
if [[ ${TEFM_PREP_ACTION} == pfam ]]; then
  echo "PREPARATION_TYPED_BLOCK: Pfam current_release hashes are not frozen; this known-failing action is non-submittable" >&2
  exit 65
fi
TEFM_LOCK=${TEFM_ASSET}/.preparation-${TEFM_PREP_ACTION}.lock
TEFM_LOCK_TOKEN=$(python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/prep_lock.py" acquire --lock "${TEFM_LOCK}" --job-id "${SLURM_JOB_ID}")
trap 'rc=$?; python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/prep_lock.py" release --lock "${TEFM_LOCK}" --token "${TEFM_LOCK_TOKEN}" >/dev/null 2>&1 || true; exit $rc' EXIT
export TEFM_PREP_ENV_FILE=${TEFM_OUT}/preparation_environment_${SLURM_JOB_ID}.txt
TEFM_ENV_FILE=${TEFM_PREP_ENV_FILE}
TEFM_ENV_TMP=${TEFM_ENV_FILE}.tmp
conda list --explicit > "${TEFM_ENV_TMP}"
mv "${TEFM_ENV_TMP}" "${TEFM_ENV_FILE}"
export TEFM_PREP_ENV_SHA256
TEFM_PREP_ENV_SHA256=$(sha256sum "${TEFM_ENV_FILE}" | awk '{print $1}')
case ${TEFM_PREP_ACTION} in
 famdb) python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/prepare_famdb.py" --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" --asset-root "${TEFM_ROOT}/software_outputs/tefm_new_directions/${TEFM_EXP}" ;;
 hite) TEFM_ALLOW_NETWORK=1 bash "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/acquire_hite_exact.sh" "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" "${TEFM_ROOT}" ;;
 edta) TEFM_ALLOW_NETWORK=1 bash "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/acquire_edta_230_overlay.sh" "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" "${TEFM_ROOT}" ;;
 *) echo "unknown TEFM_PREP_ACTION" >&2; exit 64 ;;
esac
