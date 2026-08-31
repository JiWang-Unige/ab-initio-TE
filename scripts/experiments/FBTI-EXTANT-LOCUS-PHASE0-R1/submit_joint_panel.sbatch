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
CENSUS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/population-census-${POPULATION_ATTEMPT_TAG}
POPULATION=${CENSUS}/population.tsv
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/joint-panel-${ATTEMPT_TAG}
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/sample_joint_panel.py
MANIFEST_SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/build_panel_manifests.py
TRUTH=${CENSUS}/truth_metadata.tsv
P3=${CENSUS}/p3_atoms.tsv

if [[ -e "${OUT}" ]]; then
  echo "refusing to reuse output directory: ${OUT}" >&2
  exit 2
fi
if [[ "$(cat "${CENSUS}/STATUS")" != PASS ]]; then
  echo "population census did not pass" >&2
  exit 2
fi

cd "${ROOT}"
GIT_COMMIT=$(git rev-parse HEAD)
python3 "${SCRIPT}" \
  --population "${POPULATION}" \
  --population-summary "${CENSUS}/summary.json" \
  --truth-metadata "${TRUTH}" \
  --git-commit "${GIT_COMMIT}" \
  --output-dir "${OUT}"
python3 "${MANIFEST_SCRIPT}" \
  --packages "${OUT}/packages.tsv" \
  --truth-metadata "${TRUTH}" \
  --p3-atoms "${P3}" \
  --output-dir "${OUT}/manifests"
printf 'PASS\n' > "${OUT}/STATUS"
