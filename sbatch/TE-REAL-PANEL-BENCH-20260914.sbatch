#!/usr/bin/env bash
#SBATCH --job-name=te_real_panel_native
#SBATCH --partition=public-longrun-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --array=0-8%3
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_real_panel_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_real_panel_%A_%a.err
set -euo pipefail
ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
species=(platypus sea_urchin c_briggsae)
methods=(fixed_rm hite rm2_rm)
i=$((SLURM_ARRAY_TASK_ID / 3))
j=$((SLURM_ARRAY_TASK_ID % 3))
cd "$ROOT"
python3 scripts/experiments/TE-REAL-PANEL-BENCH-20260914/native.py --root "$ROOT" \
  --candidate "${species[$i]}" --method "${methods[$j]}" \
  --output "$ROOT/outputs/TE-REAL-PANEL-BENCH-20260914/${species[$i]}/${methods[$j]}/slurm-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
