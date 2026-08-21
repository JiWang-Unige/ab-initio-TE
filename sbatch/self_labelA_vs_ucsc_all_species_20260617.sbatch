#!/usr/bin/env bash
#SBATCH --job-name=labelA_ucsc_all
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=160G
#SBATCH --time=04:00:00
#SBATCH --output=logs/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617_%j.out
#SBATCH --error=logs/repeatmasker_dfam/SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617_%j.err

set -euo pipefail

RUN_ID=SELF_LABELA_VS_UCSC_ALL_SPECIES_20260617
OUTDIR="reports/repeatmasker_dfam/${RUN_ID}"
MANIFEST="${OUTDIR}/pair_manifest.tsv"
JOBS="${JOBS:-12}"

mkdir -p "${OUTDIR}" logs/repeatmasker_dfam

echo "RUN_ID=${RUN_ID}"
echo "HOST=$(hostname)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-NA}"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-NA}"
echo "JOBS=${JOBS}"
echo "MANIFEST=${MANIFEST}"
date -Is

if [[ ! -s "${MANIFEST}" ]]; then
  echo "Missing pair manifest: ${MANIFEST}" >&2
  exit 2
fi

srun --cpu-bind=cores python3 scripts/experiments/compare_self_labelA_ucsc.py \
  --manifest "${MANIFEST}" \
  --outdir "${OUTDIR}" \
  --jobs "${JOBS}"

date -Is
echo "COMPLETED"
