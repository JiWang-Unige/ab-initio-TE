#!/usr/bin/env bash
#SBATCH --job-name=te_id_loss_controls
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_id_controls_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_id_controls_%j.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$ROOT"
python3 scripts/experiments/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/training_controls.py --root "$ROOT" \
  --output "$ROOT/outputs/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914/training-controls-${SLURM_JOB_ID}"
