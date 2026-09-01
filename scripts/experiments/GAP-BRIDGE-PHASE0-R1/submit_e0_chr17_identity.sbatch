#!/usr/bin/env bash
# E0 engineering identity regression for the consumed Human chr17 prefix.
# Re-export the frozen P3-R1 track on the existing 1,200 test windows and
# compare ordered interval tuples and declared length exactly.  No metrics are
# computed by this engineering job.
#SBATCH --job-name=TE_E0_ID
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-chr17-identity-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-chr17-identity-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submitting E0 identity}"

ROOT=/home/users/j/jwang/ab-initio-TE
E0_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
DATA_JSONL=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/test/data.jsonl.gz
EXPECTED_CANONICAL=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.prediction.tsv
EXPECTED_LENGTHS=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.lengths.json
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/e0-chr17-identity-${ATTEMPT_TAG}

for required_path in \
  "${E0_SCRIPT}" \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/tokenizer" \
  "${DATA_JSONL}" \
  "${EXPECTED_CANONICAL}" \
  "${EXPECTED_LENGTHS}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing E0 identity asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse E0 identity output directory: ${RUN_ROOT}" >&2
  exit 2
fi

mkdir -p "${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1"
mkdir "${RUN_ROOT}"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python3 "${E0_SCRIPT}" export-p3 \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${DATA_JSONL}" \
  --output-pte "${RUN_ROOT}/p_te.npy" \
  --output-states "${RUN_ROOT}/states.npy" \
  --output-canonical "${RUN_ROOT}/observed.canonical.tsv" \
  --manifest "${RUN_ROOT}/export.manifest.json" \
  --max-windows 1200

python3 "${E0_SCRIPT}" identity \
  --expected-canonical "${EXPECTED_CANONICAL}" \
  --observed-canonical "${RUN_ROOT}/observed.canonical.tsv" \
  --expected-lengths-json "${EXPECTED_LENGTHS}" \
  --observed-export-manifest "${RUN_ROOT}/export.manifest.json" \
  --output-json "${RUN_ROOT}/identity.json"

printf '%s\n' "${SLURM_JOB_ID}" > "${RUN_ROOT}/JOBID"
printf 'PASS\n' > "${RUN_ROOT}/STATUS"
