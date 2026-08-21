#!/usr/bin/env bash
#SBATCH --job-name=sf-acc-preserve
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/preview/logs/slurm-%j.out
#SBATCH --error=outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/preview/logs/slurm-%j.err

set -eo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXP_ID=SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1
CONFIG_PATH="${PROJECT_ROOT}/configs/${EXP_ID}.yaml"
RUNNER_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/run_preflight.py"
TEST_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/test_preflight.py"
LOCK_DIR="${PROJECT_ROOT}/outputs/${EXP_ID}/preview/.accession-preflight-owner.lock"
STATE_LOCK="${PROJECT_ROOT}/outputs/${EXP_ID}/preview/.state-writer.lock"
OWNS_LOCK=0

if [[ ! "${SLURM_JOB_ID:-}" =~ ^[1-9][0-9]*$ ]]; then
  echo "positive numeric SLURM_JOB_ID required" >&2
  exit 2
fi
ATTEMPT_ID="slurm-${SLURM_JOB_ID}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
unset MKL_NUM_THREADS MKL_DYNAMIC OMP_NUM_THREADS OPENBLAS_NUM_THREADS || true

cleanup() {
  local rc=$?
  if (( rc != 0 && OWNS_LOCK == 1 )); then
    python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}" \
      --record-wrapper-failure >/dev/null 2>&1 || true
  fi
  if [[ -d "${LOCK_DIR}" ]] && [[ "$(cat "${LOCK_DIR}/job_id" 2>/dev/null || true)" == "${SLURM_JOB_ID}" ]]; then
    exec 9>>"${STATE_LOCK}"
    if flock -w 30 9; then
      rm -f "${LOCK_DIR}/job_id"
      rmdir "${LOCK_DIR}" 2>/dev/null || true
      flock -u 9
    fi
    exec 9>&-
  fi
  exit "${rc}"
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

if [[ ! -d "${PROJECT_ROOT}/outputs/${EXP_ID}/preview/logs" ]] || \
   [[ ! -w "${PROJECT_ROOT}/outputs/${EXP_ID}/preview/logs" ]]; then
  echo "pre-created writable Slurm log directory required" >&2
  exit 2
fi
exec 9>>"${STATE_LOCK}"
flock -n 9
mkdir "${LOCK_DIR}"
OWNS_LOCK=1
printf '%s\n' "${SLURM_JOB_ID}" > "${LOCK_DIR}/job_id"
flock -u 9
exec 9>&-

cd "${PROJECT_ROOT}"
python scripts/pre_submit_gate.py --exp-id "${EXP_ID}"
python "${TEST_PATH}"
python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}"
