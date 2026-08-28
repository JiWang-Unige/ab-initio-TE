#!/usr/bin/env bash
# Finalize the complete P3 payload after Job 12097889 failed on its last echo.
#SBATCH --job-name=TE_P3_FINAL
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-finalize-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-finalize-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SOURCE=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.metrics.json
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-finalize-${SLURM_JOB_ID}

mkdir "${RUN_ROOT}"
python3 "${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1/finalize_p3_gate.py" \
  --metrics "${SOURCE}" \
  --output "${RUN_ROOT}/gate.json"
touch "${RUN_ROOT}/COMPLETED"
