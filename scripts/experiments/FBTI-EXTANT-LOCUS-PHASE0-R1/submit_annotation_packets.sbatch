#!/usr/bin/env bash
# Build frozen P3-blind Gate-L main and reserve packets; CPU-only.
#SBATCH --job-name=FBTI_L_PACKETS
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --array=0-1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/annotation-packets-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FBTI-EXTANT-LOCUS-PHASE0-R1/annotation-packets-%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
PANEL=${ROOT}/docs/experiments/manifests/FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3
ASSET=${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68
SCRIPT=${ROOT}/scripts/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1/build_calibration_packets.py

if [[ ${SLURM_ARRAY_TASK_ID} -eq 0 ]]; then
  ROLE=main
else
  ROLE=reserve
fi
OUT=${ROOT}/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/${ROLE}-packets-v1.3-20260901-r1

cd "${ROOT}"
python3 "${SCRIPT}" \
  --role "${ROLE}" \
  --packages "${PANEL}/packages.tsv" \
  --context-features "${PANEL}/context_features.tsv" \
  --assembly-fasta "${ASSET}/dmel-all-chromosome-r6.68.fasta.gz" \
  --flybase-gff <(tar -xOzf "${ASSET}/dmel-all-r6.68.gff.gz" dmel-all-r6.68.gff) \
  --output-dir "${OUT}"

printf '%s_%s\n' "${SLURM_ARRAY_JOB_ID}" "${SLURM_ARRAY_TASK_ID}" > "${OUT}/JOBID"
printf 'PASS\n' > "${OUT}/STATUS"
