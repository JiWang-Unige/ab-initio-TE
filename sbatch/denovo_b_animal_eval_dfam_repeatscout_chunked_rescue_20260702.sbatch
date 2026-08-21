#!/usr/bin/env bash
# Chunked rescue for long de novo RepeatScout + Dfam RepeatMasker rows.
# Final outputs are written by the paired finalize job after all chunks finish.
#SBATCH --job-name=DFAM_RS_CHUNK_RESCUE
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=4-00:00:00
#SBATCH --array=1-63%24
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/dfam_repeatscout_chunked_rescue_20260702/slurm_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/dfam_repeatscout_chunked_rescue_20260702/slurm_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
MANIFEST=${RUN_ROOT}/dfam_augmented/repeatscout_chunked_rescue_20260702_manifest.tsv
LOG_DIR=${RUN_ROOT}/slurm_logs/dfam_repeatscout_chunked_rescue_20260702

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

python3 scripts/experiments/denovo_benchmark/run_chunked_dfam_repeatmasker.py run \
  --manifest "${MANIFEST}" \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --cpus "${SLURM_CPUS_PER_TASK:-8}"
