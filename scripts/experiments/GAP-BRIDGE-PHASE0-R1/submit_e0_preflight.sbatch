#!/usr/bin/env bash
# E0 engineering preflight for independent Human chr3/chr5 regions.
# Each array task materializes one 0..50-Mb region and exports frozen P3-R1
# four-state probabilities plus the derived binary intervals and an engineering
# candidate/label census.  No scientific metric is part of this job.
#SBATCH --job-name=TE_E0_PREFLIGHT
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-preflight-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/GAP-BRIDGE-PHASE0-R1/e0-preflight-%A_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submitting E0 preflight}"

ROOT=/home/users/j/jwang/ab-initio-TE
E0_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/gap_bridge_e0.py
GAP_SCRIPT=${ROOT}/scripts/experiments/GAP-BRIDGE-PHASE0-R1/phase0_gap_table.py
ASSEMBLY=${ROOT}/data/raw/ucsc/human/hg38/hg38.fa.gz
COMPARATOR_POSITIVE=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_strict.bed.gz
COMPARATOR_UNKNOWN=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/processed/rmsk_te_plus_unknown.bed.gz
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
RUN_ROOT=${ROOT}/outputs/GAP-BRIDGE-PHASE0-R1/e0-preflight-${ATTEMPT_TAG}

case "${SLURM_ARRAY_TASK_ID}" in
  0) SEQID=chr3 ;;
  1) SEQID=chr5 ;;
  *) echo "unexpected E0 preflight array task: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

TASK_ROOT=${RUN_ROOT}/${SEQID}

for required_path in \
  "${E0_SCRIPT}" \
  "${GAP_SCRIPT}" \
  "${ASSEMBLY}" \
  "${COMPARATOR_POSITIVE}" \
  "${COMPARATOR_UNKNOWN}" \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/tokenizer"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing E0 preflight asset: ${required_path}" >&2
    exit 2
  fi
done

if [[ -e "${TASK_ROOT}" ]]; then
  echo "refusing to reuse E0 preflight output directory: ${TASK_ROOT}" >&2
  exit 2
fi

mkdir -p "${RUN_ROOT}"
mkdir "${TASK_ROOT}"

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
  --start 0 \
  --end 50000000 \
  --output-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --manifest "${TASK_ROOT}/region.manifest.json"

python3 "${E0_SCRIPT}" export-p3 \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --output-pte "${TASK_ROOT}/p_te.npy" \
  --output-states "${TASK_ROOT}/states.npy" \
  --output-canonical "${TASK_ROOT}/prediction.canonical.tsv" \
  --manifest "${TASK_ROOT}/export.manifest.json"

python3 "${GAP_SCRIPT}" candidates \
  --p3-canonical "${TASK_ROOT}/prediction.canonical.tsv" \
  --data-jsonl "${TASK_ROOT}/region.jsonl.gz" \
  --pte-npy "${TASK_ROOT}/p_te.npy" \
  --state-probabilities-npy "${TASK_ROOT}/states.npy" \
  --output "${TASK_ROOT}/candidates.tsv"

python3 "${GAP_SCRIPT}" project-labels \
  --candidates "${TASK_ROOT}/candidates.tsv" \
  --comparator-positive "${COMPARATOR_POSITIVE}" \
  --comparator-unknown "${COMPARATOR_UNKNOWN}" \
  --output "${TASK_ROOT}/labeled.tsv"

python3 "${GAP_SCRIPT}" census \
  --labeled "${TASK_ROOT}/labeled.tsv" \
  --output "${TASK_ROOT}/candidate_census.json"

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${TASK_ROOT}/JOBID"
printf 'PASS\n' > "${TASK_ROOT}/STATUS"
