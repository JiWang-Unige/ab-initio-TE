#!/usr/bin/env bash
# EarlGrey public-cpu rescue for western_honey_bee.
# Matrix task 7 = western_honey_bee.
# This avoids the longrun per-user job limit while keeping a 4-day walltime.
#SBATCH --job-name=EG_B_HB_PCPU
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=4-00:00:00
#SBATCH --array=7
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/earlgrey_publiccpu_rescue_20260703/slurm_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/earlgrey_publiccpu_rescue_20260703/slurm_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
MATRIX=${1:-${RUN_ROOT}/manifests/earlgrey_task_matrix_longrun4.tsv}
LOG_DIR=${RUN_ROOT}/slurm_logs/earlgrey_publiccpu_rescue_20260703

mkdir -p "${LOG_DIR}"

cd "${PROJECT_ROOT}"

if [[ -n "${SLURM_TMPDIR:-}" && -d "${SLURM_TMPDIR}" ]]; then
  export EARLGREY_SCRATCH_ROOT="${SLURM_TMPDIR}"
elif [[ -d "/scratch/${USER}" || -d "/scratch" ]]; then
  export EARLGREY_SCRATCH_ROOT="/scratch/${USER}/earlgrey_publiccpu_rescue_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
  mkdir -p "${EARLGREY_SCRATCH_ROOT}"
else
  export EARLGREY_SCRATCH_ROOT="/tmp/${USER}/earlgrey_publiccpu_rescue_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
  mkdir -p "${EARLGREY_SCRATCH_ROOT}"
fi

echo "[$(date -Iseconds)] HOST=${HOSTNAME} JOB=${SLURM_JOB_ID} TASK=${SLURM_ARRAY_TASK_ID}"
echo "PROJECT_ROOT=${PROJECT_ROOT}"
echo "MATRIX=${MATRIX}"
echo "EARLGREY_SCRATCH_ROOT=${EARLGREY_SCRATCH_ROOT}"
df -h "${EARLGREY_SCRATCH_ROOT}" || true

bash scripts/experiments/denovo_benchmark/run_earlgrey_from_matrix.sh "${MATRIX}" "${SLURM_ARRAY_TASK_ID}"

echo "[$(date -Iseconds)] public-cpu rescue task ${SLURM_ARRAY_TASK_ID} completed"
