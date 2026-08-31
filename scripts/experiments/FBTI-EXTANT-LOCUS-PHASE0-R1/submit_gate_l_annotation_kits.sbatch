#!/usr/bin/env bash
# Prepare calibration and main Gate-L response kits; CPU-only engineering.
#SBATCH --job-name=FBTI_L_KITS
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --array=0-1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/annotation-kits-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/annotation-kits-%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/prepare_gate_l_annotation_kits.py

if [[ ${SLURM_ARRAY_TASK_ID} -eq 0 ]]; then
  ROLE=calibration
  PACKETS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-v1.3-20260831-r3
else
  ROLE=main
  PACKETS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-packets-v1.3-20260901-r1
fi
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/${ROLE}-annotation-kits-v1.4-proposal-20260901-r1

cd "${ROOT}"
python3 "${SCRIPT}" --packet-bundle "${PACKETS}" --output-dir "${OUT}"
printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
