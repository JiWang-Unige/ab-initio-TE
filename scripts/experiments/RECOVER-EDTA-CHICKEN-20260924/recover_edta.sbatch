#!/bin/bash
#SBATCH --job-name=edta-chicken-recovery
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=5-01:33:25
#SBATCH --output=logs/edta-chicken-recovery-%j.out
#SBATCH --error=logs/edta-chicken-recovery-%j.err
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"

python3 scripts/experiments/RECOVER-EDTA-CHICKEN-20260924/recover_edta.py \
  --root "$TASK_ROOT" \
  --failed "$TASK_ROOT/outputs/WHOLE-GENOME-BENCHMARK-20260918/native/chicken/EDTA" \
  --output "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-recovery-${SLURM_JOB_ID}" \
  --image "/home/users/j/jwang/ab-initio-TE/container_candidates/E1B-OCI-ACQUIRE-20260809A/edta_2_3_0.sif" \
  --source-overlay "/home/users/j/jwang/ab-initio-TE/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/edta/source-2.3.0" \
  --budget-seconds "${RECOVERY_BUDGET_SECONDS:?set remaining budget after fixture}" \
  --prior-slurm-seconds 166862 \
  --fixture-job "${FIXTURE_JOB:?set fixture job}" \
  --fixture-seconds "${FIXTURE_SECONDS:?set fixture seconds}"
