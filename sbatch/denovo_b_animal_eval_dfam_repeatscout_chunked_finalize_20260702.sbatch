#!/usr/bin/env bash
# Finalize chunked RepeatScout + Dfam rescue rows and refresh the monitor matrix.
#SBATCH --job-name=DFAM_RS_CHUNK_FINALIZE
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/dfam_repeatscout_chunked_rescue_20260702/finalize_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/slurm_logs/dfam_repeatscout_chunked_rescue_20260702/finalize_%j.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
RUN_ROOT=/home/users/j/jwang/ab-initio-TE/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620
LOG_DIR=${RUN_ROOT}/slurm_logs/dfam_repeatscout_chunked_rescue_20260702

mkdir -p "${LOG_DIR}"
cd "${PROJECT_ROOT}"

for species in cattle opossum pig; do
  python3 scripts/experiments/denovo_benchmark/run_chunked_dfam_repeatmasker.py finalize \
    --manifest "${RUN_ROOT}/dfam_augmented/${species}/repeatscout_chunked_rescue_20260702/manifest.tsv"
done

python3 scripts/experiments/denovo_benchmark/refresh_denovo_monitor.py --run-root "${RUN_ROOT}"
