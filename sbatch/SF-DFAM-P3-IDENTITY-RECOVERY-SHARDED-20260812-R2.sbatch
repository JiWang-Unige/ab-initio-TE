#!/usr/bin/env bash
# Resumable CPU-only four-worker exact-name recovery over Dfam partition 3.
#SBATCH --job-name=sf_p3_recovery_sharded_r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=B:TERM@900
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2/preview/logs/slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2/preview/logs/slurm_%j.err

set -eo pipefail
RECOVERY_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RECOVERY_EXP=SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2
RECOVERY_CONFIG=${RECOVERY_ROOT}/configs/${RECOVERY_EXP}.yaml
RECOVERY_SCRIPT=${RECOVERY_ROOT}/scripts/experiments/${RECOVERY_EXP}/recover_sharded.py
RECOVERY_PREVIEW=${RECOVERY_ROOT}/outputs/${RECOVERY_EXP}/preview
RECOVERY_ATTEMPT=slurm-${SLURM_JOB_ID}
RECOVERY_ATTEMPT_START_EPOCH=$(date +%s)
RECOVERY_PREPARED=0
RECOVERY_LOCK_ACQUIRED=0
RECOVERY_PID=

cd "${RECOVERY_ROOT}"
test -d "${RECOVERY_PREVIEW}/logs"
test -w "${RECOVERY_PREVIEW}/logs"
test -f "${RECOVERY_PREVIEW}/logs/.slurm_parent_precreated.json"
python3 scripts/pre_submit_gate.py --exp-id "${RECOVERY_EXP}"
test -z "${SLURM_JOB_GPUS:-}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u

recovery_term() {
  set +e
  if [ -n "${RECOVERY_PID}" ]; then
    kill -TERM "${RECOVERY_PID}"
    wait "${RECOVERY_PID}"
    exit $?
  fi
  exit 75
}

recovery_cleanup() {
  RECOVERY_RC=$?
  set +e
  if [ "${RECOVERY_RC}" -ne 0 ] && [ "${RECOVERY_PREPARED}" -eq 1 ]; then
    python "${RECOVERY_SCRIPT}" --config "${RECOVERY_CONFIG}" --attempt-id "${RECOVERY_ATTEMPT}" \
      --shell-failure-finalize --shell-exit-code "${RECOVERY_RC}"
  fi
  if [ "${RECOVERY_LOCK_ACQUIRED}" -eq 1 ]; then
    python "${RECOVERY_SCRIPT}" --config "${RECOVERY_CONFIG}" --release-owner-lock-only
  fi
  exit "${RECOVERY_RC}"
}

trap recovery_term TERM
trap recovery_cleanup EXIT

python "${RECOVERY_SCRIPT}" --config "${RECOVERY_CONFIG}" --acquire-owner-lock-only
RECOVERY_LOCK_ACQUIRED=1
RECOVERY_PREPARED=1
python "${RECOVERY_SCRIPT}" --config "${RECOVERY_CONFIG}" --attempt-id "${RECOVERY_ATTEMPT}" \
  --attempt-start-epoch "${RECOVERY_ATTEMPT_START_EPOCH}" --prepare-running-only
python "${RECOVERY_ROOT}/scripts/experiments/${RECOVERY_EXP}/test_recover_sharded.py" -v
python "${RECOVERY_SCRIPT}" --config "${RECOVERY_CONFIG}" --attempt-id "${RECOVERY_ATTEMPT}" \
  --attempt-start-epoch "${RECOVERY_ATTEMPT_START_EPOCH}" &
RECOVERY_PID=$!
wait "${RECOVERY_PID}"
RECOVERY_PID=
