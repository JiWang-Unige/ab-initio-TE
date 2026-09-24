#!/bin/bash
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --output=outputs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/logs/%x-%A_%a.out
#SBATCH --error=outputs/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/logs/%x-%A_%a.err
set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
cd /home/users/j/jwang/ab-initio-TE

ACTION="${ACTION:?set ACTION=prepare|predict|score}"
SPECIES="${SPECIES:?set SPECIES=chicken|zebrafish}"
SCRIPT="scripts/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925/pilot.py"

if [[ "${ACTION}" == "predict" ]]; then
  python -u "${SCRIPT}" predict "${SPECIES}" --index "${SLURM_ARRAY_TASK_ID}"
else
  python -u "${SCRIPT}" "${ACTION}" "${SPECIES}"
fi
