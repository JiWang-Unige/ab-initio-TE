#!/usr/bin/env bash
# Retrospective inference-only screen; no fitting or threshold tuning.
#SBATCH --job-name=tefm-ensemble-overlap
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=80G
#SBATCH --time=08:00:00
#SBATCH --output=logs/tefm-ensemble-overlap_%j.out
#SBATCH --error=logs/tefm-ensemble-overlap_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/TEFM-BACKBONE-ENSEMBLE-DIAGNOSTIC-20260903/ensemble_overlap.py
GENERANNO=${ROOT}/software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs/TFSUPP_generanno_H0_w4096_seed42
NT=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42
DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w4096/test/data.jsonl.gz
: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG}"
OUTPUT=${ROOT}/outputs/TEFM-BACKBONE-ENSEMBLE-DIAGNOSTIC-20260903/${ATTEMPT_TAG}

for path in "${SCRIPT}" "${GENERANNO}/best_model/pytorch_model.bin" "${NT}/best_model/pytorch_model.bin" "${DATA}"; do
  if [[ ! -e "${path}" ]]; then
    echo "missing ensemble diagnostic input: ${path}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT}" ]]; then
  echo "refusing to reuse ensemble output: ${OUTPUT}" >&2
  exit 2
fi

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TEFM_LOCAL_FILES_ONLY=1
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export PYTHONUNBUFFERED=1

python3 "${SCRIPT}" \
  --generanno-model "${GENERANNO}" \
  --nt-model "${NT}" \
  --data-jsonl "${DATA}" \
  --output-dir "${OUTPUT}" \
  --window 4096 \
  --max-windows 1200

printf '%s\n' "${SLURM_JOB_ID}" > "${OUTPUT}/JOBID"
