#!/usr/bin/env bash
# CPU-only canonical data, asset, synthetic-test and leakage gate.
# PRE-SUBMIT REQUIRED: preflight_sbatch.py --stage cpu (Slurm opens log path before this script runs).
#SBATCH --job-name=sf_direct_data_r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/data_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/data_%j.err

set -eo pipefail
TEFM_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
TEFM_EXP=SF-DIRECT-BASELINE-SCREEN-20260811-R2
TEFM_OUT=${TEFM_ROOT}/outputs/${TEFM_EXP}
cd "${TEFM_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id "${TEFM_EXP}"
mkdir -p "${TEFM_OUT}" "${TEFM_ROOT}/logs/${TEFM_EXP}"
TEFM_LOCK=${TEFM_OUT}/.stage_owner.lock
if ! mkdir "${TEFM_LOCK}"; then printf 'CPU/GPU stage owner lock exists: %s\n' "${TEFM_LOCK}" >&2; exit 73; fi
printf 'cpu\n' > "${TEFM_LOCK}/stage"
trap 'unlink "${TEFM_LOCK}/stage"; rmdir "${TEFM_LOCK}"' EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
set -u
{
  date --iso-8601=seconds
  printf 'stage=cpu_data\nconda_env=%s\npython=%s\n' "${CONDA_DEFAULT_ENV:-UNSET}" "$(command -v python)"
  python --version
  conda list --explicit
} > "${TEFM_OUT}/env.cpu.${SLURM_JOB_ID}.txt.tmp"
mv "${TEFM_OUT}/env.cpu.${SLURM_JOB_ID}.txt.tmp" "${TEFM_OUT}/env.cpu.${SLURM_JOB_ID}.txt"
python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/run_cpu_data_stage.py" \
  --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}" \
  --external-env-manifest "${TEFM_OUT}/env.cpu.${SLURM_JOB_ID}.txt"
