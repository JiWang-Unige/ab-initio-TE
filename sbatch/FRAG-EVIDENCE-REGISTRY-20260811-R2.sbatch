#!/usr/bin/env bash
# Asset hashing and semantic probes only; no model inference or scientific screen.
#SBATCH --job-name=frag-reg-r2
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=logs/FRAG-EVIDENCE-REGISTRY-20260811-R2-%j.out
#SBATCH --error=logs/FRAG-EVIDENCE-REGISTRY-20260811-R2-%j.err

set -eo pipefail
PROJECT_ROOT="${SLURM_SUBMIT_DIR:?submit from the project root}"
cd "${PROJECT_ROOT}"

OUTPUT_DIR="${PROJECT_ROOT}/outputs/FRAG-EVIDENCE-REGISTRY-20260811-R2"
PAYLOAD_STARTED=0
mkdir -p "${OUTPUT_DIR}"

on_exit() {
  local rc=$?
  if [[ ${rc} -ne 0 && ${PAYLOAD_STARTED:-0} -eq 0 ]]; then
    printf '%s\n' FAILED_ENV > "${OUTPUT_DIR}/STATUS.tmp" || true
    mv "${OUTPUT_DIR}/STATUS.tmp" "${OUTPUT_DIR}/STATUS" || true
    printf 'FRAG R2 environment bootstrap failed before payload (rc=%s)\n' "${rc}" >&2
  fi
  exit "${rc}"
}
trap on_exit EXIT

printf '%s\n' RUNNING_ENV > "${OUTPUT_DIR}/STATUS.tmp"
mv "${OUTPUT_DIR}/STATUS.tmp" "${OUTPUT_DIR}/STATUS"

# shellcheck source=/dev/null
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
set -u

{
  echo "CONDA_DEFAULT_ENV=${CONDA_DEFAULT_ENV:-}"
  echo "CONDA_PREFIX=${CONDA_PREFIX:-}"
  echo "python=$(command -v python)"
  python --version
  conda --version
} > "${OUTPUT_DIR}/env.txt.tmp"
mv "${OUTPUT_DIR}/env.txt.tmp" "${OUTPUT_DIR}/env.txt"

PAYLOAD_STARTED=1
python scripts/experiments/FRAG-EVIDENCE-REGISTRY-20260811-R2/build_registry.py \
  --project-root "${PROJECT_ROOT}" \
  --config configs/FRAG-EVIDENCE-REGISTRY-20260811-R2.yaml
