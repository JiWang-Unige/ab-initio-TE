#!/usr/bin/env bash
#SBATCH --job-name=sf-leaf-adapter
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/logs/slurm-%j.out
#SBATCH --error=outputs/SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1/preview/logs/slurm-%j.err

set -eo pipefail
PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXP_ID=SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1
CONFIG_PATH="${PROJECT_ROOT}/configs/${EXP_ID}.yaml"
RUNNER_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/leaf_adapter_preflight.py"
TEST_PATH="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/test_leaf_adapter_preflight.py"
PREVIEW="${PROJECT_ROOT}/outputs/${EXP_ID}/preview"
OWNER="${PREVIEW}/.leaf-adapter-owner.lock"
WRITER="${PREVIEW}/.state-writer.lock"
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
    timeout --signal=TERM --kill-after=5s 30s \
      python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}" --record-wrapper-failure \
      >/dev/null 2>&1 || true
  fi
  if [[ -d "${OWNER}" ]] && [[ "$(cat "${OWNER}/job_id" 2>/dev/null || true)" == "${SLURM_JOB_ID}" ]]; then
    exec 9>>"${WRITER}"
    if flock -w 30 9; then
      rm -f "${OWNER}/job_id"; rmdir "${OWNER}" 2>/dev/null || true; flock -u 9
    fi
    exec 9>&-
  fi
  exit "${rc}"
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

if [[ ! -d "${PREVIEW}/logs" ]] || [[ ! -w "${PREVIEW}/logs" ]]; then
  echo "pre-created writable Slurm log directory required" >&2
  exit 2
fi
exec 9>>"${WRITER}"; flock -n 9
mkdir "${OWNER}"; OWNS_LOCK=1; printf '%s\n' "${SLURM_JOB_ID}" > "${OWNER}/job_id"
flock -u 9; exec 9>&-

python "${PROJECT_ROOT}/scripts/pre_submit_gate.py" --exp-id "${EXP_ID}" "${PROJECT_ROOT}"
cd "${PROJECT_ROOT}"
python "${TEST_PATH}"
timeout --signal=TERM --kill-after=30s 480s \
  python "${RUNNER_PATH}" --config "${CONFIG_PATH}" --attempt-id "${ATTEMPT_ID}"
