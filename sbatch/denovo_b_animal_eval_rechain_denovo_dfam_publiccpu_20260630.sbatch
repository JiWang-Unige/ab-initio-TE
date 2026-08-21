#!/usr/bin/env bash
# Full de novo library + Dfam specieslib RepeatMasker augmentation for B eval species.
# Existing DONE outputs are skipped by run_denovo_dfam_repeatmasker.py.
#SBATCH --job-name=DENOVO_DFAM_B_R2
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-12:00:00
#SBATCH --array=1-32%8
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_dfam_20260630/slurm_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/rechain_dfam_20260630/slurm_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
MATRIX=${1:-${RUN_ROOT}/denovo_dfam_task_manifest_full_20260630.tsv}
LOG_DIR=${RUN_ROOT}/slurm_logs/rechain_dfam_20260630

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

export RM_PA=${SLURM_CPUS_PER_TASK}
bash scripts/experiments/denovo_benchmark/run_denovo_dfam_from_matrix.sh "${MATRIX}" "${SLURM_ARRAY_TASK_ID}"
