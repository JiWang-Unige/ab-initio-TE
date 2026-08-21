#!/usr/bin/env bash
# Implemented but deliberately code-review BLOCKED; do not submit before an independent PASS.
#SBATCH --job-name=tefm_rm_hite_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-RM-HITE-VALIDITY-20260811-R1_slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-RM-HITE-VALIDITY-20260811-R1_slurm_%j.err
set -eo pipefail
TEFM_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
TEFM_EXP=BENCH-RM-HITE-VALIDITY-20260811-R1
TEFM_OUT=${TEFM_ROOT}/outputs/${TEFM_EXP}
tefm_environment_failure() {
  TEFM_ENV_RC=$1
  TEFM_ENV_PHASE=$2
  mkdir -p "${TEFM_OUT}"
  printf 'FAILED_ENVIRONMENT\n' > "${TEFM_OUT}/STATUS.tmp.${SLURM_JOB_ID:-nojob}"
  mv "${TEFM_OUT}/STATUS.tmp.${SLURM_JOB_ID:-nojob}" "${TEFM_OUT}/STATUS"
  printf 'environment bootstrap failed: phase=%s rc=%s\n' "${TEFM_ENV_PHASE}" "${TEFM_ENV_RC}" >&2
  exit "${TEFM_ENV_RC}"
}
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh || tefm_environment_failure "$?" conda_source
conda activate benchmark_core || tefm_environment_failure "$?" conda_activate
set -u
cd "${TEFM_ROOT}"
python "${TEFM_ROOT}/scripts/pre_submit_gate.py" --exp-id "${TEFM_EXP}" "${TEFM_ROOT}"
mkdir -p "${TEFM_OUT}"
export TEFM_ENV_FILE=${TEFM_OUT}/environment_conda_explicit_${SLURM_JOB_ID}.txt
TEFM_ENV_TMP=${TEFM_ENV_FILE}.tmp
conda list --explicit > "${TEFM_ENV_TMP}"
mv "${TEFM_ENV_TMP}" "${TEFM_ENV_FILE}"
python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/run_validity_smoke.py" \
  --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" \
  --output "${TEFM_OUT}"
