#!/usr/bin/env bash
# CPU-only exhaustive Dfam partition-3 exact-name metadata recovery.
#SBATCH --job-name=sf_dfam_p3_recovery_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/preview/slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1/preview/slurm_%j.err

set -eo pipefail
RECOVERY_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RECOVERY_EXP=SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1
RECOVERY_PREVIEW=${RECOVERY_ROOT}/outputs/${RECOVERY_EXP}/preview
mkdir -p "${RECOVERY_PREVIEW}"
cd "${RECOVERY_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id "${RECOVERY_EXP}"
test -z "${SLURM_JOB_GPUS:-}"
RECOVERY_LOCK=${RECOVERY_PREVIEW}/.owner.lock
if ! mkdir "${RECOVERY_LOCK}"; then printf 'P3 recovery owner lock exists: %s\n' "${RECOVERY_LOCK}" >&2; exit 73; fi
printf '%s\n' "${SLURM_JOB_ID}" > "${RECOVERY_LOCK}/job_id"
trap 'unlink "${RECOVERY_LOCK}/job_id"; rmdir "${RECOVERY_LOCK}"' EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
python "${RECOVERY_ROOT}/scripts/experiments/${RECOVERY_EXP}/recover_p3_identities.py" \
  --config "${RECOVERY_ROOT}/configs/${RECOVERY_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}" \
  --prepare-running-only
python "${RECOVERY_ROOT}/scripts/experiments/${RECOVERY_EXP}/test_recover_p3_identities.py" -v
python "${RECOVERY_ROOT}/scripts/experiments/${RECOVERY_EXP}/recover_p3_identities.py" \
  --config "${RECOVERY_ROOT}/configs/${RECOVERY_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}"
