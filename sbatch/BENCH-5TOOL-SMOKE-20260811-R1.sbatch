#!/usr/bin/env bash
#SBATCH --job-name=tefm_b5_smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/BENCH-5TOOL-SMOKE-20260811-R1/slurm_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/BENCH-5TOOL-SMOKE-20260811-R1/slurm_%j.err

set -eo pipefail

TEFM_ROOT=/home/users/j/jwang/ab-initio-TE
TEFM_EXP=BENCH-5TOOL-SMOKE-20260811-R1
TEFM_OUTPUT=${TEFM_ROOT}/outputs/${TEFM_EXP}
TEFM_STATUS=${TEFM_OUTPUT}/STATUS

on_exit() {
  local rc=$?
  if [[ ${rc} -ne 0 && -d ${TEFM_OUTPUT} && -w ${TEFM_OUTPUT} ]]; then
    printf '%s\n' FAILED > "${TEFM_STATUS}" || true
  fi
  exit "${rc}"
}
trap on_exit EXIT

mkdir -p "${TEFM_OUTPUT}" "${TEFM_ROOT}/logs/${TEFM_EXP}"
printf '%s\n' RUNNING > "${TEFM_STATUS}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
set -u

conda list --explicit > "${TEFM_OUTPUT}/environment_conda_explicit.txt"
python "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/run_smoke.py" \
  --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" \
  --output "${TEFM_OUTPUT}"
printf '%s\n' COMPLETED > "${TEFM_STATUS}"
