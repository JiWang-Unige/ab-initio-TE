#!/bin/bash
#SBATCH --job-name=edta-fixture
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=logs/edta-fixture-%j.out
#SBATCH --error=logs/edta-fixture-%j.err
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
OUT="reports/RECOVER-EDTA-CHICKEN-20260924/fixture-${SLURM_JOB_ID}"
mkdir -p "$OUT"
IMG=/home/users/j/jwang/ab-initio-TE/container_candidates/E1B-OCI-ACQUIRE-20260809A/edta_2_3_0.sif
apptainer exec --cleanenv \
  --bind "$TASK_ROOT/scripts/experiments/RECOVER-EDTA-CHICKEN-20260924:/code:ro" \
  --bind "$TASK_ROOT/$OUT:/work" \
  "$IMG" python /code/fixture.py --output /work
