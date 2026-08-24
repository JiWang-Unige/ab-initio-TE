#!/usr/bin/env bash
# CPU-only identity-gate runner for the archived Module 5 input.
# Resource directives are intentionally omitted: smart-sbatch/sbatch CLI owns
# partition, CPU, memory, and walltime selection.
#SBATCH --job-name=contrastive_identity_gate_r1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/contrastive_identity_gate_r1_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/contrastive_identity_gate_r1_%j.err

set -euo pipefail

PROJECT_ROOT="/home/users/j/jwang/ab-initio-TE"
INPUT="/home/users/j/jwang/TE_final/archive/v1_modules/module5_contrastive/data/te_fragments.jsonl"
SCRIPT="${PROJECT_ROOT}/scripts/experiments/CONTRASTIVE-IDENTITY-SCREEN-20260824-R1/contrastive_identity_screen.py"
RUN_ID="${SLURM_JOB_ID:-manual_$$}"
OUTPUT="${PROJECT_ROOT}/outputs/contrastive_identity_screen_r1_${RUN_ID}"

export CUDA_VISIBLE_DEVICES=""
mkdir -p "${PROJECT_ROOT}/logs" "${OUTPUT}"
cd "${PROJECT_ROOT}"

set +e
python3 "${SCRIPT}" \
  --input "${INPUT}" \
  --output "${OUTPUT}" \
  >"${OUTPUT}/runner.stdout" \
  2>"${OUTPUT}/runner.stderr"
SCREEN_RC=$?
set -e

STATUS=""
if [[ -f "${OUTPUT}/STATUS" ]]; then
  STATUS="$(tr -d '\r\n' < "${OUTPUT}/STATUS")"
fi

if [[ "${SCREEN_RC}" -eq 2 && "${STATUS}" == "BLOCKED_IDENTITY_FIELDS" ]]; then
  {
    echo "EXPECTED_BLOCKED"
    echo "screen_rc=${SCREEN_RC}"
    echo "status=${STATUS}"
    echo "input=${INPUT}"
  } >"${OUTPUT}/EXPECTED_BLOCKED"
  exit 0
fi

{
  echo "UNEXPECTED_GATE_OUTCOME"
  echo "screen_rc=${SCREEN_RC}"
  echo "status=${STATUS:-MISSING}"
  echo "expected_rc=2"
  echo "expected_status=BLOCKED_IDENTITY_FIELDS"
} >"${OUTPUT}/UNEXPECTED_GATE_OUTCOME"
exit 1
