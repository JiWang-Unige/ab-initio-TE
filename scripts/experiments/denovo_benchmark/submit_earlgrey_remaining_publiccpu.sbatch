#!/usr/bin/env bash
# EarlGrey rerun for the remaining de novo benchmark animal eval species.
#SBATCH --job-name=EG_B_EVAL_RERUN
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=90G
#SBATCH --time=3-12:00:00
#SBATCH --array=4-8%2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/earlgrey_publiccpu_rerun_20260629/slurm_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/earlgrey_publiccpu_rerun_20260629/slurm_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
MATRIX=${1:-${RUN_ROOT}/manifests/earlgrey_task_matrix.tsv}
LOG_DIR=${RUN_ROOT}/slurm_logs/earlgrey_publiccpu_rerun_20260629

mkdir -p "${LOG_DIR}"

cd "${PROJECT_ROOT}"

if [[ -n "${SLURM_TMPDIR:-}" && -d "${SLURM_TMPDIR}" ]]; then
  export EARLGREY_SCRATCH_ROOT="${SLURM_TMPDIR}"
elif [[ -d "/scratch/${USER}" || -d "/scratch" ]]; then
  export EARLGREY_SCRATCH_ROOT="/scratch/${USER}/earlgrey_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
  mkdir -p "${EARLGREY_SCRATCH_ROOT}"
else
  export EARLGREY_SCRATCH_ROOT="/tmp/${USER}/earlgrey_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
  mkdir -p "${EARLGREY_SCRATCH_ROOT}"
fi

echo "[$(date -Iseconds)] HOST=${HOSTNAME} JOB=${SLURM_JOB_ID} TASK=${SLURM_ARRAY_TASK_ID}"
echo "PROJECT_ROOT=${PROJECT_ROOT}"
echo "MATRIX=${MATRIX}"
echo "EARLGREY_SCRATCH_ROOT=${EARLGREY_SCRATCH_ROOT}"
df -h "${EARLGREY_SCRATCH_ROOT}" || true

bash scripts/experiments/denovo_benchmark/run_earlgrey_from_matrix.sh "${MATRIX}" "${SLURM_ARRAY_TASK_ID}"

echo "[$(date -Iseconds)] task ${SLURM_ARRAY_TASK_ID} completed"
