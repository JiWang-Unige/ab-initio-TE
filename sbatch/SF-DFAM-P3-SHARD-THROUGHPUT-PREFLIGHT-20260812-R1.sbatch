#!/usr/bin/env bash
# CPU-only 4-way read-only HDF5 shard throughput/correctness preflight.
#SBATCH --job-name=sf_p3_shard_preflight_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1/preview/logs/slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1/preview/logs/slurm_%j.err

set -eo pipefail
PREFLIGHT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
PREFLIGHT_EXP=SF-DFAM-P3-SHARD-THROUGHPUT-PREFLIGHT-20260812-R1
PREFLIGHT_PREVIEW=${PREFLIGHT_ROOT}/outputs/${PREFLIGHT_EXP}/preview
cd "${PREFLIGHT_ROOT}"
test -d "${PREFLIGHT_PREVIEW}/logs"
test -w "${PREFLIGHT_PREVIEW}/logs"
test -f "${PREFLIGHT_PREVIEW}/logs/.slurm_parent_precreated.json"
python3 scripts/pre_submit_gate.py --exp-id "${PREFLIGHT_EXP}"
test -z "${SLURM_JOB_GPUS:-}"
PREFLIGHT_LOCK=${PREFLIGHT_PREVIEW}/.shard-preflight-owner.lock
if ! mkdir "${PREFLIGHT_LOCK}"; then printf 'Shard preflight owner lock exists: %s\n' "${PREFLIGHT_LOCK}" >&2; exit 73; fi
printf '%s\n' "${SLURM_JOB_ID}" > "${PREFLIGHT_LOCK}/job_id"
PREFLIGHT_PREPARED=0
preflight_cleanup() {
  PREFLIGHT_RC=$?
  set +e
  if [ "${PREFLIGHT_RC}" -ne 0 ] && [ "${PREFLIGHT_PREPARED}" -eq 1 ]; then
    python "${PREFLIGHT_ROOT}/scripts/experiments/${PREFLIGHT_EXP}/shard_preflight.py" \
      --config "${PREFLIGHT_ROOT}/configs/${PREFLIGHT_EXP}.yaml" \
      --attempt-id "slurm-${SLURM_JOB_ID}" \
      --finalize-failed-only \
      --failure-reason "sbatch_post_prepare_exit_${PREFLIGHT_RC}"
  fi
  unlink "${PREFLIGHT_LOCK}/job_id"
  rmdir "${PREFLIGHT_LOCK}"
  exit "${PREFLIGHT_RC}"
}
trap preflight_cleanup EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
PREFLIGHT_PREPARED=1
python "${PREFLIGHT_ROOT}/scripts/experiments/${PREFLIGHT_EXP}/shard_preflight.py" \
  --config "${PREFLIGHT_ROOT}/configs/${PREFLIGHT_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}" \
  --prepare-running-only
python "${PREFLIGHT_ROOT}/scripts/experiments/${PREFLIGHT_EXP}/test_shard_preflight.py" -v
python "${PREFLIGHT_ROOT}/scripts/experiments/${PREFLIGHT_EXP}/shard_preflight.py" \
  --config "${PREFLIGHT_ROOT}/configs/${PREFLIGHT_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}"
