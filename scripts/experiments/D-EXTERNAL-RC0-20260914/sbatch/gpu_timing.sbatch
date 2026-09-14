#!/usr/bin/env bash
# Same timing.py, first 1-MiB regions and batch size as the completed CPU cells.
#SBATCH --job-name=te_d_gpu_timing_matched
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --array=0-2
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_d_gpu_timing_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_d_gpu_timing_%A_%a.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
case "${SLURM_ARRAY_TASK_ID}" in
  0) CANDIDATE=platypus ;;
  1) CANDIDATE=sea_urchin ;;
  2) CANDIDATE=c_briggsae ;;
esac
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$ROOT"
python3 scripts/experiments/D-EXTERNAL-RC0-20260914/timing.py \
  --config scripts/experiments/D-EXTERNAL-RC0-20260914/config/panel.json \
  --candidate "$CANDIDATE" --remote-root "$ROOT" --batch-size 12 \
  --output-dir "$ROOT/outputs/D-EXTERNAL-RC0-20260914/gpu-timing/$CANDIDATE/slurm-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
