#!/usr/bin/env bash
# Build the twelve frozen P3-blind Gate-L calibration packets; CPU-only.
#SBATCH --job-name=FBTI_L_CALIB
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
PANEL=${ROOT}/docs/experiments/manifests/FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3
ASSET=${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-v1.3-20260831-r1
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/build_calibration_packets.py

cd "${ROOT}"
python3 "${SCRIPT}" \
  --packages "${PANEL}/packages.tsv" \
  --context-features "${PANEL}/context_features.tsv" \
  --assembly-fasta "${ASSET}/dmel-all-chromosome-r6.68.fasta.gz" \
  --flybase-gff "${ASSET}/dmel-all-r6.68.gff.gz" \
  --output-dir "${OUT}"

printf '%s\n' "${SLURM_JOB_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
