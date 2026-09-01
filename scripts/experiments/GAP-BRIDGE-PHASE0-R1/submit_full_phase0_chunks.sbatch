#!/usr/bin/env bash
# Full Human Phase-0 P3 export in 8192-aligned shards. Comparator labels are
# not read by this GPU stage.
#SBATCH --job-name=TE_GAP_FULL_CHUNK
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=05:00:00
#SBATCH --array=0-12%7
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/full-chunk-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/full-chunk-%A_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submitting full Phase 0 chunks}"

ROOT=/home/users/j/jwang/ab-initio-TE
PLAN=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/full_phase0_chunks.tsv
E0_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py
ASSEMBLY=${ROOT}/data/raw/ucsc/human/hg38/hg38.fa.gz
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/full-chunks-${ATTEMPT_TAG}

PLAN_ROW=$(awk -F '\t' -v task_id="${SLURM_ARRAY_TASK_ID}" 'NR > 1 && $1 == task_id {print $1 "\t" $2 "\t" $3 "\t" $4}' "${PLAN}")
if [[ -z "${PLAN_ROW}" ]]; then
  echo "missing full Phase-0 chunk plan row: ${SLURM_ARRAY_TASK_ID}" >&2
  exit 2
fi
IFS=$'\t' read -r TASK_ID SEQID START END <<< "${PLAN_ROW}"
FINAL_TASK_ROOT=${RUN_ROOT}/${SEQID}/${START}-${END}

for required_path in \
  "${PLAN}" \
  "${E0_SCRIPT}" \
  "${ASSEMBLY}" \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/tokenizer"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing full Phase-0 chunk asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${FINAL_TASK_ROOT}" ]]; then
  echo "refusing to reuse full Phase-0 chunk output: ${FINAL_TASK_ROOT}" >&2
  exit 2
fi

LOCAL_SCRATCH=${SLURM_TMPDIR:-/tmp}
TASK_ROOT=$(mktemp -d "${LOCAL_SCRATCH}/te-gap-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}-XXXXXX")
trap 'rm -rf "${TASK_ROOT}"' EXIT

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python3 "${E0_SCRIPT}" materialize-region \
  --assembly "${ASSEMBLY}" \
  --seqid "${SEQID}" \
  --start "${START}" \
  --end "${END}" \
  --output-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --manifest "${TASK_ROOT}/region.manifest.json" >/dev/null

python3 "${E0_SCRIPT}" export-p3 \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --output-pte "${TASK_ROOT}/p_te.npy" \
  --output-states "${TASK_ROOT}/states.npy" \
  --output-canonical "${TASK_ROOT}/prediction.canonical.tsv" \
  --manifest "${TASK_ROOT}/export.manifest.json" >/dev/null

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${TASK_ROOT}/JOBID"
printf 'PASS\n' > "${TASK_ROOT}/STATUS"

mkdir -p "${RUN_ROOT}/${SEQID}"
TRANSFER_ROOT=${RUN_ROOT}/${SEQID}/.transfer-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}
mkdir "${TRANSFER_ROOT}"
cp -a "${TASK_ROOT}/." "${TRANSFER_ROOT}/"
mv "${TRANSFER_ROOT}" "${FINAL_TASK_ROOT}"
