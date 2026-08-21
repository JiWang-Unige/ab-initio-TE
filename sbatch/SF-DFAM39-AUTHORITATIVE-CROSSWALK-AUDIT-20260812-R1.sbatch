#!/usr/bin/env bash
#SBATCH --job-name=sf-dfam39-xwalk
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=outputs/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1/preview/logs/slurm-%j.out
#SBATCH --error=outputs/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1/preview/logs/slurm-%j.err

set -eo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXP_ID=SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1
CONFIG_PATH="${PROJECT_ROOT}/configs/${EXP_ID}.yaml"
RUNNER_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/audit_crosswalk.py"
TEST_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/test_audit_crosswalk.py"
LOCK_DIR="${PROJECT_ROOT}/outputs/${EXP_ID}/preview/.authoritative-crosswalk-owner.lock"

if [[ ! "${SLURM_JOB_ID:-}" =~ ^[1-9][0-9]*$ ]]; then
  echo "positive numeric SLURM_JOB_ID required" >&2
  exit 2
fi
ATTEMPT_ID="slurm-${SLURM_JOB_ID}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
set -u

unset MKL_NUM_THREADS MKL_DYNAMIC OMP_NUM_THREADS OPENBLAS_NUM_THREADS || true

cleanup() {
  local rc=$?
  if (( rc != 0 )); then
    python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}" \
      --record-wrapper-failure >/dev/null 2>&1 || true
  fi
  if [[ -d "${LOCK_DIR}" ]] && [[ "$(cat "${LOCK_DIR}/job_id" 2>/dev/null || true)" == "${SLURM_JOB_ID}" ]]; then
    rm -f "${LOCK_DIR}/job_id"
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
  exit "${rc}"
}
trap cleanup EXIT

if [[ ! -d "${PROJECT_ROOT}/outputs/${EXP_ID}/preview/logs" ]] || \
   [[ ! -w "${PROJECT_ROOT}/outputs/${EXP_ID}/preview/logs" ]]; then
  echo "pre-created writable Slurm log directory required" >&2
  exit 2
fi
mkdir "${LOCK_DIR}"
printf '%s\n' "${SLURM_JOB_ID}" > "${LOCK_DIR}/job_id"

cd "${PROJECT_ROOT}"
python scripts/pre_submit_gate.py --exp-id "${EXP_ID}"
python "${TEST_PATH}"
python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}"
