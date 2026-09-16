#!/bin/bash
#SBATCH --job-name=te-species-rm
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --array=0-5%3
#SBATCH --output=outputs/SPECIES-LIBRARY-CONTROL-20260916/rm-%A-%a.log
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 scripts/experiments/SPECIES-LIBRARY-CONTROL-20260916/diagnostic.py annotate --index "$SLURM_ARRAY_TASK_ID"
