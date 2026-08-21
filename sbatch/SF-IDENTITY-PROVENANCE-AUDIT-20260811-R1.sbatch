#!/usr/bin/env bash
# CPU-only exact Dfam identity/provenance audit; no split, clustering, or training.
#SBATCH --job-name=sf_identity_audit_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/slurm_%j.err

set -eo pipefail
AUDIT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
AUDIT_EXP=SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1
AUDIT_PREVIEW=${AUDIT_ROOT}/outputs/${AUDIT_EXP}/preview
cd "${AUDIT_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id "${AUDIT_EXP}"
test -z "${SLURM_JOB_GPUS:-}"
AUDIT_LOCK=${AUDIT_PREVIEW}/.owner.lock
if ! mkdir "${AUDIT_LOCK}"; then printf 'Audit owner lock exists: %s\n' "${AUDIT_LOCK}" >&2; exit 73; fi
printf '%s\n' "${SLURM_JOB_ID}" > "${AUDIT_LOCK}/job_id"
trap 'unlink "${AUDIT_LOCK}/job_id"; rmdir "${AUDIT_LOCK}"' EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
python "${AUDIT_ROOT}/scripts/experiments/${AUDIT_EXP}/test_identity_audit.py" -v
python "${AUDIT_ROOT}/scripts/experiments/${AUDIT_EXP}/identity_provenance_audit.py" \
  --config "${AUDIT_ROOT}/configs/${AUDIT_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}"
