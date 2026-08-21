#!/usr/bin/env bash
# Asset-gate verifier only. Do not treat this as authorization for a scientific run.
#SBATCH --job-name=decay-g-gate
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=logs/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1-%j.out

set -euo pipefail
PROJECT_ROOT="${SLURM_SUBMIT_DIR:?submit from the project root}"
cd "${PROJECT_ROOT}"
STATUS_FILE="${PROJECT_ROOT}/outputs/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1/STATUS"
mkdir -p "$(dirname "${STATUS_FILE}")"
trap 'rc=$?; current=$(tr -d "\r\n" < "${STATUS_FILE}" 2>/dev/null || true); if [ "$rc" -ne 0 ] && { [ -z "$current" ] || [ "$current" = "RUNNING" ]; }; then printf "FAILED\n" > "${STATUS_FILE}"; fi' EXIT
set +e
python3 scripts/experiments/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1/verify_asset_gate.py \
  --project-root "${PROJECT_ROOT}" \
  --config configs/DECAY-TRANSFER-SURFACE-SCREEN-20260811-R1.yaml
rc=$?
set -e
if [ "$rc" -eq 2 ] && [ "$(tr -d '\r\n' < "${STATUS_FILE}")" = "FOUNDATIONAL_TYPED_BLOCK" ]; then
  trap - EXIT
  exit 0
fi
exit "$rc"
