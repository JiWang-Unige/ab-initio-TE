#!/bin/bash
# Continue the preserved EDTA retry after TIR succeeded but Helitron was not
# generated.  This is a native CPU job; it intentionally uses no GPU.
#SBATCH --job-name=edta-chicken-helitron
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=5-00:48:56
#SBATCH --output=logs/edta-chicken-helitron-%j.out
#SBATCH --error=logs/edta-chicken-helitron-%j.err
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"

python3 scripts/experiments/RECOVER-EDTA-CHICKEN-20260924/continue_helitron.py \
  --root "$TASK_ROOT" \
  --failed "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-recovery-13189201" \
  --output "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-helitron-cont-${SLURM_JOB_ID}" \
  --image "/home/users/j/jwang/ab-initio-TE/container_candidates/E1B-OCI-ACQUIRE-20260809A/edta_2_3_0.sif" \
  --source-overlay "/home/users/j/jwang/ab-initio-TE/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/edta/source-2.3.0" \
  --budget-seconds "${RECOVERY_BUDGET_SECONDS:?set remaining budget}" \
  --prior-slurm-seconds 2669
