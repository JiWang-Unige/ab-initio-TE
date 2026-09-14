#!/usr/bin/env bash
# Timing-only CPU adapter for the first fixed panel region.  It is not an
# accuracy result and does not change the GPU RC0 score contract.
#SBATCH --job-name=te_d_cpu_timing
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --array=0-2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_cpu_timing_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_cpu_timing_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
REMOTE_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONFIG="${ROOT}/scripts/experiments/D-EXTERNAL-RC0-20260914/config/panel.json"
SCRIPT="${ROOT}/scripts/experiments/D-EXTERNAL-RC0-20260914/timing.py"
case "${SLURM_ARRAY_TASK_ID:?array index is required}" in
  0) CANDIDATE=platypus ;;
  1) CANDIDATE=sea_urchin ;;
  2) CANDIDATE=c_briggsae ;;
  *) echo "unsupported array index ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

OUT="${ROOT}/outputs/D-EXTERNAL-RC0-20260914/cpu-timing/${CANDIDATE}/slurm-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "${ROOT}"
python3 "${SCRIPT}" \
  --config "${CONFIG}" \
  --candidate "${CANDIDATE}" \
  --remote-root "${REMOTE_ROOT}" \
  --output-dir "${OUT}" \
  --batch-size 12 \
  --cpu
