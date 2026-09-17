#!/usr/bin/env bash
# One-GPU serial array for the frozen D external screen.  No training or
# target-specific calibration is performed.
#SBATCH --job-name=d_animal_screen
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --array=0-2%1
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/d_animal_screen_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/d_animal_screen_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
CONFIG="${ROOT}/outputs/ANIMAL-GENERALIZATION-CLOSURE-20260917/prepared_config.json"
RUNNER="${ROOT}/scripts/experiments/ANIMAL-GENERALIZATION-CLOSURE-20260917/run_fixed_screen.py"
case "${SLURM_ARRAY_TASK_ID:?array index is required}" in
  0) CANDIDATE=western_clawed_frog ;;
  1) CANDIDATE=western_honey_bee ;;
  2) CANDIDATE=red_flour_beetle ;;
  *) echo "unsupported array index ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

OUT="${ROOT}/outputs/ANIMAL-GENERALIZATION-CLOSURE-20260917/${CANDIDATE}/slurm-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "${ROOT}"
python3 "${RUNNER}" \
  --config "${CONFIG}" \
  --candidate "${CANDIDATE}" \
  --output-dir "${OUT}" \
  --batch-size 12
