#!/usr/bin/env bash
#SBATCH --job-name=tefm_s_asset_gate
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/SF-HIER-OPENSET-SCREEN-20260811-R1/slurm_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/SF-HIER-OPENSET-SCREEN-20260811-R1/slurm_%j.err

# ASSET-GATE ONLY. This job cannot train, infer, calibrate, or run a scientific screen.
set -euo pipefail
TEFM_ROOT=/home/users/j/jwang/ab-initio-TE
TEFM_EXP=SF-HIER-OPENSET-SCREEN-20260811-R1
mkdir -p "${TEFM_ROOT}/outputs/${TEFM_EXP}" "${TEFM_ROOT}/logs/${TEFM_EXP}"
STATUS_FILE="${TEFM_ROOT}/outputs/${TEFM_EXP}/STATUS"
trap 'rc=$?; current=$(tr -d "\r\n" < "${STATUS_FILE}" 2>/dev/null || true); if [ "$rc" -ne 0 ] && { [ -z "$current" ] || [ "$current" = "RUNNING" ]; }; then printf "FAILED\n" > "${STATUS_FILE}"; fi' EXIT
set +e
python3 "${TEFM_ROOT}/scripts/experiments/${TEFM_EXP}/verify_asset_gate.py" \
  --config "${TEFM_ROOT}/configs/${TEFM_EXP}.yaml" \
  --output "${TEFM_ROOT}/outputs/${TEFM_EXP}"
rc=$?
set -e
if [ "$rc" -eq 2 ] && [ "$(tr -d '\r\n' < "${STATUS_FILE}")" = "FOUNDATIONAL_TYPED_BLOCK" ]; then
  trap - EXIT
  exit 0
fi
exit "$rc"
