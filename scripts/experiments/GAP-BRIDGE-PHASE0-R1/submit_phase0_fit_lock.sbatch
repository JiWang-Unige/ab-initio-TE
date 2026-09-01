#!/usr/bin/env bash
# CPU-only train/validation lock. chr19 labels are explicitly absent.
#SBATCH --job-name=TE_GAP_FIT_LOCK
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/fit-lock-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/fit-lock-%j.err

set -euo pipefail

: "${SOURCE_TAG:?set SOURCE_TAG to the completed whole-chromosome attempt}"
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG for the feature lock}"

ROOT=/home/users/j/jwang/ab-initio-TE
PROBE=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_feature_probe.py
SOURCE_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-whole-${SOURCE_TAG}
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/feature-lock-${ATTEMPT_TAG}

for required_path in \
  "${PROBE}" \
  "${SOURCE_ROOT}/chr3/labeled.tsv" \
  "${SOURCE_ROOT}/chr5/labeled.tsv" \
  "${SOURCE_ROOT}/chr13/labeled.tsv" \
  "${SOURCE_ROOT}/chr19/candidates.tsv" \
  "${SOURCE_ROOT}/chr19/TEST_LABELS_SEALED"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing Phase-0 fit-lock asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${SOURCE_ROOT}/chr19/labeled.tsv" ]]; then
  echo "chr19 labels exist before selection lock" >&2
  exit 2
fi
if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse Phase-0 feature-lock output: ${RUN_ROOT}" >&2
  exit 2
fi
mkdir -p "${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1"
mkdir "${RUN_ROOT}"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

python3 "${PROBE}" fit-lock \
  --train "${SOURCE_ROOT}/chr3/labeled.tsv" \
  --train "${SOURCE_ROOT}/chr5/labeled.tsv" \
  --validation "${SOURCE_ROOT}/chr13/labeled.tsv" \
  --output "${RUN_ROOT}/feature_lock.json" >/dev/null

LOCK_STATUS=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["status"])' "${RUN_ROOT}/feature_lock.json")
printf '%s\n' "${SLURM_JOB_ID}" > "${RUN_ROOT}/JOBID"
printf '%s\n' "${LOCK_STATUS}" > "${RUN_ROOT}/STATUS"
