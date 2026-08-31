#!/usr/bin/env bash
# Gate-L label-blind joint challenge-panel selection; CPU-only MILP.
#SBATCH --job-name=FBTI_L_PANEL
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/joint-panel-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/joint-panel-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submission}"
: "${POPULATION_ATTEMPT_TAG:?set the completed population-census attempt tag}"

ROOT=/home/users/j/jwang/ab-initio-TE
POPULATION=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/population-census-${POPULATION_ATTEMPT_TAG}/population.tsv
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/joint-panel-${ATTEMPT_TAG}
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/sample_joint_panel.py

if [[ -e "${OUT}" ]]; then
  echo "refusing to reuse output directory: ${OUT}" >&2
  exit 2
fi

cd "${ROOT}"
python3 "${SCRIPT}" --population "${POPULATION}" --output-dir "${OUT}"
printf 'PASS\n' > "${OUT}/STATUS"
