#!/usr/bin/env bash
# CPU-only S0 sequence-homology component and leakage-safe split gate.
#SBATCH --job-name=sf_homology_split_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1/preview/slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1/preview/slurm_%j.err

set -eo pipefail
HOMOLOGY_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
HOMOLOGY_EXP=SF-DIRECT-HOMOLOGY-SPLIT-SCREEN-20260812-R1
HOMOLOGY_PREVIEW=${HOMOLOGY_ROOT}/outputs/${HOMOLOGY_EXP}/preview
mkdir -p "${HOMOLOGY_PREVIEW}"
cd "${HOMOLOGY_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id "${HOMOLOGY_EXP}"
test -z "${SLURM_JOB_GPUS:-}"
HOMOLOGY_LOCK=${HOMOLOGY_PREVIEW}/.owner.lock
if ! mkdir "${HOMOLOGY_LOCK}"; then printf 'Homology split owner lock exists: %s\n' "${HOMOLOGY_LOCK}" >&2; exit 73; fi
printf '%s\n' "${SLURM_JOB_ID}" > "${HOMOLOGY_LOCK}/job_id"
trap 'unlink "${HOMOLOGY_LOCK}/job_id"; rmdir "${HOMOLOGY_LOCK}"' EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
python "${HOMOLOGY_ROOT}/scripts/experiments/${HOMOLOGY_EXP}/test_homology_split.py" -v
python "${HOMOLOGY_ROOT}/scripts/experiments/${HOMOLOGY_EXP}/build_homology_split.py" \
  --config "${HOMOLOGY_ROOT}/configs/${HOMOLOGY_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}"
