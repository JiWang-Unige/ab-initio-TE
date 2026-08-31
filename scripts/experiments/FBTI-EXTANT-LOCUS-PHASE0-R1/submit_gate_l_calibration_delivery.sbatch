#!/usr/bin/env bash
# Build the two independent P3-blind Gate-L calibration deliveries.
#SBATCH --job-name=FBTI_L_DELIV
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --array=0-1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-delivery-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-delivery-%A_%a.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submission}"

ROOT=/home/users/j/jwang/ab-initio-TE
PACKETS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-v1.3-20260831-r3
KITS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-annotation-kits-v1.4-proposal-20260901-r1
HANDBOOK=${ROOT}/docs/experiments/FBTI-GATE-L-ANNOTATOR-HANDBOOK-V1.4-20260901.md
REGISTRY=${ROOT}/docs/experiments/manifests/FBTI-EXTANT-LOCUS-GATE-L-V1.4/evidence_registry.tsv
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/assemble_gate_l_delivery.py

if [[ ${SLURM_ARRAY_TASK_ID} -eq 0 ]]; then
  ACTOR=A1
else
  ACTOR=A2
fi
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-delivery-${ATTEMPT_TAG}/${ACTOR}

cd "${ROOT}"
python "${SCRIPT}" \
  --packet-bundle "${PACKETS}" \
  --kit-dir "${KITS}" \
  --handbook "${HANDBOOK}" \
  --evidence-registry "${REGISTRY}" \
  --actor "${ACTOR}" \
  --output-dir "${OUT}"

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
