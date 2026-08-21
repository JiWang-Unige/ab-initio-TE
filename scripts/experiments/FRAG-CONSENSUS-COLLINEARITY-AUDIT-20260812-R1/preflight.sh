#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT=$1
EXP_ID=$2
ENV_SNAPSHOT=$3
SCHEDULER_SNAPSHOT=$4
RUNTIME_PREHASH=$5
CONFIG_PATH="${PROJECT_ROOT}/configs/${EXP_ID}.yaml"
SCRIPT_DIR="${PROJECT_ROOT}/scripts/experiments/${EXP_ID}"
BENCHMARK_PYTHON=/home/users/j/jwang/.conda/envs/benchmark_core/bin/python

# This is deliberately the first child process: no scientific asset or other
# command may run until the independently reviewed runtime is byte-verified.
"${BENCHMARK_PYTHON}" "${SCRIPT_DIR}/runtime_hashes.py" \
  --root "${PROJECT_ROOT}" --config "${CONFIG_PATH}" --exp-id "${EXP_ID}" --out "${RUNTIME_PREHASH}"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
set -u
cd "${PROJECT_ROOT}"
python scripts/pre_submit_gate.py --exp-id "${EXP_ID}"
python "scripts/experiments/${EXP_ID}/test_contract.py"

ENV_TMP="${ENV_SNAPSHOT}.tmp.$$"
conda list --explicit > "${ENV_TMP}"
mv "${ENV_TMP}" "${ENV_SNAPSHOT}"

SCHEDULER_TMP="${SCHEDULER_SNAPSHOT}.tmp.$$"
scontrol show job -o "${SLURM_JOB_ID}" > "${SCHEDULER_TMP}"
test "$(wc -l < "${SCHEDULER_TMP}")" -eq 1
mv "${SCHEDULER_TMP}" "${SCHEDULER_SNAPSHOT}"
