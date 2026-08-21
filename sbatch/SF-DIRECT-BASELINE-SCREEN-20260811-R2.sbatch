#!/usr/bin/env bash
# GPU-only clean direct-head smoke/train/eval. Requires frozen DATA PASS pointer.
# PRE-SUBMIT REQUIRED: preflight_sbatch.py --stage gpu (Slurm opens log path before this script runs).
#SBATCH --job-name=sf_direct_gpu_r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/gpu_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/gpu_%j.err

set -eo pipefail
TEFM_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
TEFM_EXP=SF-DIRECT-BASELINE-SCREEN-20260811-R2
TEFM_OUT=${TEFM_ROOT}/outputs/${TEFM_EXP}
cd "${TEFM_ROOT}"
python3 scripts/pre_submit_gate.py --exp-id "${TEFM_EXP}"
test -s "${TEFM_OUT}/DATA_PASS_MANIFEST.json"
mkdir -p "${TEFM_OUT}" "${TEFM_ROOT}/logs/${TEFM_EXP}"
TEFM_LOCK=${TEFM_OUT}/.stage_owner.lock
if ! mkdir "${TEFM_LOCK}"; then printf 'CPU/GPU stage owner lock exists: %s\n' "${TEFM_LOCK}" >&2; exit 73; fi
printf 'gpu\n' > "${TEFM_LOCK}/stage"
trap 'unlink "${TEFM_LOCK}/stage"; rmdir "${TEFM_LOCK}"' EXIT
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate generanno
set -u
{
  date --iso-8601=seconds
  printf 'stage=gpu_s0\nconda_env=%s\npython=%s\n' "${CONDA_DEFAULT_ENV:-UNSET}" "$(command -v python)"
  python --version
  conda list --explicit
  nvidia-smi
} > "${TEFM_OUT}/env.gpu.${SLURM_JOB_ID}.txt.tmp"
mv "${TEFM_OUT}/env.gpu.${SLURM_JOB_ID}.txt.tmp" "${TEFM_OUT}/env.gpu.${SLURM_JOB_ID}.txt"
python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/run_direct_screen.py" \
  --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" \
  --attempt-id "slurm-${SLURM_JOB_ID}" \
  --external-env-manifest "${TEFM_OUT}/env.gpu.${SLURM_JOB_ID}.txt"
