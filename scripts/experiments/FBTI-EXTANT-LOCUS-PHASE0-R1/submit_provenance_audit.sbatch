#!/usr/bin/env bash
# Prefill the main-panel Gate-L provenance audit; human deep-audit calls remain blank.
#SBATCH --job-name=FBTI_L_PROV
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/provenance-audit-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/provenance-audit-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set a unique ATTEMPT_TAG before submission}"

ROOT=/home/users/j/jwang/ab-initio-TE
PANEL=${ROOT}/docs/experiments/manifests/FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3
PACKETS=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-packets-v1.3-20260901-r1
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-provenance-audit-${ATTEMPT_TAG}
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/build_provenance_audit.py

cd "${ROOT}"
python3 "${SCRIPT}" \
  --packages "${PANEL}/packages.tsv" \
  --packet-manifest "${PACKETS}/packet_manifest.tsv" \
  --packet-bundle "${PACKETS}" \
  --source-assembly-id dmel_r6.68 \
  --output "${OUT}/provenance_audit.tsv"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
