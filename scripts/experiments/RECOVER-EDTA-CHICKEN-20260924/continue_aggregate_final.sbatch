#!/bin/bash
# Repair the skipped EDTA ALL-label raw aggregation, then run FINAL/ANNO.
# Submission is intentionally held until the Helitron continuation is terminal
# and its exact Slurm elapsed time has been charged.
#SBATCH --job-name=edta-chicken-aggregate-final
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=5-00:48:56
#SBATCH --output=logs/edta-chicken-aggregate-final-%j.out
#SBATCH --error=logs/edta-chicken-aggregate-final-%j.err
set -euo pipefail

TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"

python3 scripts/experiments/RECOVER-EDTA-CHICKEN-20260924/continue_aggregate_final.py \
  --root "$TASK_ROOT" \
  --failed "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-helitron-cont-13189902" \
  --output "$TASK_ROOT/outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-aggregate-final-${SLURM_JOB_ID}" \
  --image "/home/users/j/jwang/ab-initio-TE/container_candidates/E1B-OCI-ACQUIRE-20260809A/edta_2_3_0.sif" \
  --source-overlay "/home/users/j/jwang/ab-initio-TE/software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/edta/source-2.3.0" \
  --budget-seconds "${RECOVERY_BUDGET_SECONDS:?set remaining budget}" \
  --prior-slurm-seconds "${PRIOR_HELITRON_SLURM_SECONDS:?set prior elapsed}"
