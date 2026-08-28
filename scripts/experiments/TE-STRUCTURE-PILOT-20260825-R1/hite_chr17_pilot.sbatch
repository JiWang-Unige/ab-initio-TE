#!/usr/bin/env bash
# HiTE Human chr17 engineering pilot on the same 1,200-window prefix.
# Submit only after the remote smart-sbatch Phase-1/2 checks.
#SBATCH --job-name=TE_HITE_H1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=40
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/hite-human-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/hite-human-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
: "${SLURM_TMPDIR:?SLURM_TMPDIR is required for the HiTE working set}"
ASSEMBLY=${ROOT}/.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa
STRICT_BED=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/human_hs1.rmsk_te_strict.bed
PLUS_UNKNOWN_BED=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/human_hs1.rmsk_te_plus_unknown.bed
SIF=${ROOT}/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/hite/hite_3_3_3.sif
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/hite-chr17-${SLURM_JOB_ID:?numeric SLURM_JOB_ID is required}

MODEL_ARGS=()
if [[ -n "${BASE_PREDICTION:-}" ]]; then
  MODEL_ARGS+=(--model-prediction "base=${BASE_PREDICTION}")
fi
if [[ -n "${DAPT_PREDICTION:-}" ]]; then
  MODEL_ARGS+=(--model-prediction "dapt=${DAPT_PREDICTION}")
fi

cd "${ROOT}"
python "${SCRIPT_ROOT}/run_hite_chr17_pilot.py" \
  --project-root "${ROOT}" --assembly "${ASSEMBLY}" \
  --strict-bed "${STRICT_BED}" --plus-unknown-bed "${PLUS_UNKNOWN_BED}" \
  --sif "${SIF}" --output-root "${RUN_ROOT}" \
  --threads "${SLURM_CPUS_PER_TASK}" "${MODEL_ARGS[@]}"

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
