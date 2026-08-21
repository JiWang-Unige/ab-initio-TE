#!/usr/bin/env bash
#SBATCH --job-name=frag-cons-col-r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/preview/logs/slurm-%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/preview/logs/slurm-%j.err

set -eo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXP_ID=FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1
OUTPUT_DIR="${PROJECT_ROOT}/outputs/${EXP_ID}"
LOCK_DIR="${OUTPUT_DIR}/.owner.lock"
BENCHMARK_PYTHON=/home/users/j/jwang/.conda/envs/benchmark_core/bin/python

if [[ ! "${SLURM_JOB_ID:-}" =~ ^[1-9][0-9]*$ ]]; then
  echo "positive numeric SLURM_JOB_ID required" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${OUTPUT_DIR}/preview/prepayload_failures"
LOCK_TOKEN="${SLURM_JOB_ID}:$$:${RANDOM}"
set -u

cleanup() {
  local rc=$?
  if (( rc != 0 )); then
    "${BENCHMARK_PYTHON}" "${PROJECT_ROOT}/scripts/experiments/${EXP_ID}/run_audit.py" \
      --root "${PROJECT_ROOT}" --owner-token "${LOCK_TOKEN}" \
      --record-wrapper-failure --wrapper-exit-code "${rc}" >/dev/null 2>&1 || true
    printf '{"attempt_id":"slurm-%s","status":"FAILED_PREPAYLOAD_OR_WRAPPER","wrapper_exit_code":%s}\n' "${SLURM_JOB_ID}" "${rc}" > "${OUTPUT_DIR}/preview/prepayload_failures/slurm-${SLURM_JOB_ID}.json.tmp.$$"
    mv "${OUTPUT_DIR}/preview/prepayload_failures/slurm-${SLURM_JOB_ID}.json.tmp.$$" "${OUTPUT_DIR}/preview/prepayload_failures/slurm-${SLURM_JOB_ID}.json"
  fi
  if [[ -f "${LOCK_DIR}/token" ]] && [[ "$(cat "${LOCK_DIR}/token")" == "${LOCK_TOKEN}" ]]; then
    rm -f "${LOCK_DIR}/token"
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
  exit "${rc}"
}
trap cleanup EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "experiment ownership lock exists; fail closed" >&2
  exit 2
fi
printf '%s\n' "${LOCK_TOKEN}" > "${LOCK_DIR}/token"

cd "${PROJECT_ROOT}"
PREFLIGHT_RECEIPT="${OUTPUT_DIR}/preflight_gate_and_tests_${SLURM_JOB_ID}.log"
PREFLIGHT_TMP="${PREFLIGHT_RECEIPT}.tmp.$$"
ENV_SNAPSHOT="${OUTPUT_DIR}/environment_conda_explicit_${SLURM_JOB_ID}.txt"
SCHEDULER_SNAPSHOT="${OUTPUT_DIR}/slurm_job_${SLURM_JOB_ID}.txt"
RUNTIME_PREHASH="${OUTPUT_DIR}/reviewed_runtime_pre_${SLURM_JOB_ID}.json"

# The entire gate+tests+environment+scheduler preflight is machine-bounded:
# 295 seconds plus a 5-second forced-kill interval, never more than 300 seconds.
timeout --signal=TERM --kill-after=5s 295s \
  bash "scripts/experiments/${EXP_ID}/preflight.sh" \
    "${PROJECT_ROOT}" "${EXP_ID}" "${ENV_SNAPSHOT}" "${SCHEDULER_SNAPSHOT}" "${RUNTIME_PREHASH}" \
    > "${PREFLIGHT_TMP}" 2>&1
mv "${PREFLIGHT_TMP}" "${PREFLIGHT_RECEIPT}"

timeout --signal=TERM --kill-after=30s 5940s \
  bash "scripts/experiments/${EXP_ID}/run_payload.sh" \
    "scripts/experiments/${EXP_ID}/run_audit.py" \
    --root "${PROJECT_ROOT}" \
    --config "${PROJECT_ROOT}/configs/${EXP_ID}.yaml" \
    --environment-snapshot "${ENV_SNAPSHOT}" \
    --preflight-receipt "${PREFLIGHT_RECEIPT}" \
    --scheduler-snapshot "${SCHEDULER_SNAPSHOT}" \
    --runtime-prehash "${RUNTIME_PREHASH}" \
    --owner-token "${LOCK_TOKEN}"
