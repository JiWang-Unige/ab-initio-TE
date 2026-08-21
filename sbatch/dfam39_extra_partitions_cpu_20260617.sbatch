#!/usr/bin/env bash
#SBATCH --job-name=dfam39_parts_cpu
#SBATCH --partition=public-longrun-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=12:00:00
#SBATCH --output=logs/repeatmasker_dfam/dfam39_parts_cpu_20260617_%j.out
#SBATCH --error=logs/repeatmasker_dfam/dfam39_parts_cpu_20260617_%j.err

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE}"
FAMDB="${FAMDB:-/home/users/j/jwang/.conda/envs/te_benchmark/share/RepeatMasker/Libraries/famdb}"
LOGDIR="${PROJECT_ROOT}/software_outputs/repeatmasker_dfam/99_internal/dfam_partition_downloads/DFAM39_EXTRA_PARTITIONS_20260617"
PARTS="${PARTS:-1 2 3 4 5 6 12 13 15}"
JOBS="${JOBS:-2}"

cd "${PROJECT_ROOT}"
mkdir -p logs/repeatmasker_dfam "${LOGDIR}"

export FAMDB LOGDIR PARTS JOBS
"${LOGDIR}/download_extra_dfam39_partitions_parallel.sh"
