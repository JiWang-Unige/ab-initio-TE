#!/bin/bash
#SBATCH --job-name=plat-strong-mask
#SBATCH --partition=public-longrun-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/plat-strong-mask-%j.out
#SBATCH --error=logs/plat-strong-mask-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
python3 scripts/experiments/PLATYPUS-STRONG-MASK-CONTROLS-20260917/run_mask_panel.py "${MASK_METHOD:?}"
